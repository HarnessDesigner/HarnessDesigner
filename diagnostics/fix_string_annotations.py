# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Rewrite over-quoted string type annotations to use the minimum quoting
actually required, converting quoted `|` unions to `typing.Union` along the
way.

Usage::

    python diagnostics/fix_string_annotations.py <file_or_dir> [--json-report PATH]
    python diagnostics/fix_string_annotations.py <file_or_dir> --apply

This codebase writes forward references as quoted strings (``"SomeClass"``)
only where the referenced name genuinely isn't available yet at the point the
annotation is evaluated -- a class only importable under ``if TYPE_CHECKING:``
(to dodge a circular import), a class that's the annotation's own enclosing
class (self-reference, not yet bound while its own body is still executing),
or a class defined later in the same module. Everything else -- builtins
(``int``, ``tuple[float, float, float]``, ``None``, ...), a normally-imported
name, or a same-module class already defined earlier in the file -- must
never be quoted. A bare ``X | None`` union is fine and preferred; a *quoted*
union (``"X | None"``) is not, since Cython reads annotations for compilation
and a quoted expression breaks that -- it must become ``Union[X, None]``
instead, quoting only the members that actually need it.

This tool finds every function parameter/return annotation and every
``AnnAssign`` (class attribute / instance attribute) annotation containing a
string literal anywhere within it, and rewrites the *entire* annotation
expression with minimum-necessary quoting, recursing through unions
(``X | Y``) and subscripts (``tuple[...]``, ``list[...]``, ``dict[...]``, ...)
so only the specific leaf name/dotted-chain that needs deferral stays quoted.
A `typing.Union` import is added (or an existing one reused/extended) in any
file that ends up needing it.

It answers "does this name need to stay quoted" the same way ``dep_trace.py``
already answers "where is this imported / defined" -- by calling straight
into ``dep_trace.collect_bindings()`` (which already tracks whether an import
sits inside an ``if TYPE_CHECKING:`` block) for every file under ``target``,
plus a small module-level-definition-line index (class/function/assignment
statements directly in the file's top level) built the same way. No separate
pre-built reference file is required -- pass ``--json-report PATH`` only if
you want that intermediate data dumped for inspection.

Default is a dry run: prints every annotation it would rewrite (old -> new)
without touching any file. Pass ``--apply`` to actually write the changes.
Every rewritten file is re-parsed before being written, and the whole run
aborts a given file's write (with an error logged) rather than leave it in a
broken state.

If given a directory, recurses through it and processes every ``*.py`` file
found -- same as ``dep_trace.py``. Point it at a directory (not a single
file) for a real cross-file run: the TYPE_CHECKING/definition data is always
built per-file (each file's own imports/definitions only apply to that same
file), so scanning a directory here just means "process every file under it",
not "share bindings across files".

Limitations (shared with ``dep_trace.py``'s own): a name reachable only via
``getattr``/``setattr``, ``importlib``, or a star import can't be resolved,
so a leaf under one of those is left quoted (the safe default) rather than
risk unquoting something that isn't actually available at runtime. A name
that resolves to nothing at all (no import, no module-level definition found
anywhere in the file) is likewise left quoted rather than guessed at -- if
you hit one of these, it usually means the forward reference's import was
never actually added (a latent bug this tool surfaces but won't silently
"fix" by guessing which module it should come from).
"""

import argparse
import ast
import builtins as _builtins
import json
import sys
from pathlib import Path

import dep_trace as dt

BUILTIN_NAMES = set(dir(_builtins)) | {'None', 'True', 'False'}


def _flatten_bitor(node: ast.AST, parts: list[ast.AST]) -> None:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        _flatten_bitor(node.left, parts)
        _flatten_bitor(node.right, parts)
    else:
        parts.append(node)


def _base_name_of(node: ast.AST) -> str | None:
    while isinstance(node, ast.Attribute):
        node = node.value
    if isinstance(node, ast.Name):
        return node.id
    return None


def _line_starts(source: str) -> list[int]:
    starts = [0]
    for line in source.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    return starts


def _abs_offset(starts: list[int], lineno: int, col: int) -> int:
    return starts[lineno - 1] + col


def _module_level_defs(tree: ast.Module) -> dict[str, int]:
    """name -> the line its defining statement starts on, for every
    class/function/plain-assignment/annotated-assignment sitting directly at
    module level (not nested in a class/function/if/try)."""
    defs: dict[str, int] = {}
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.setdefault(node.name, node.lineno)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defs.setdefault(target.id, node.lineno)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            defs.setdefault(node.target.id, node.lineno)
    return defs


def _enclosing_class(node: ast.AST) -> ast.ClassDef | None:
    current = getattr(node, 'parent', None)
    while current is not None:
        if isinstance(current, ast.ClassDef):
            return current
        current = getattr(current, 'parent', None)
    return None


def _has_string_constant(annotation: ast.AST) -> bool:
    return any(isinstance(n, ast.Constant) and isinstance(n.value, str) for n in ast.walk(annotation))


def _is_union_value(value_node: ast.AST, bindings: dict[str, dt.ImportBinding]) -> bool:
    """True if `value_node` (the `X` in a `X[...]` subscript) is bound to
    `typing.Union` in this file -- i.e. the subscript is an existing
    `Union[...]`/`_Union[...]` we may need to collapse back to a bare `|`."""
    base = _base_name_of(value_node)
    if base is None:
        return False
    binding = bindings.get(base)
    return binding is not None and binding.module == 'typing' and binding.imported_name == 'Union'


def _needs_rewrite_check(annotation: ast.AST, bindings: dict[str, dt.ImportBinding]) -> bool:
    """True if this annotation contains either a quoted forward reference to
    resolve, or an existing Union[...]/_Union[...] subscript that might need
    collapsing back to a bare `X | Y` (e.g. a previous, overly-eager pass
    wrapped a union in Union[] even though nothing in it needed quoting)."""
    for node in ast.walk(annotation):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return True
        if isinstance(node, ast.Subscript) and _is_union_value(node.value, bindings):
            return True
    return False


class RewriteContext:
    """Per-annotation-site state needed to decide, for one identifier, whether
    it must stay a quoted forward reference."""

    def __init__(
        self, bindings: dict[str, dt.ImportBinding], mod_defs: dict[str, int],
        union_name: str, enclosing_class_name: str | None, usage_line: int,
    ) -> None:
        self.bindings = bindings
        self.mod_defs = mod_defs
        self.union_name = union_name
        self.enclosing_class_name = enclosing_class_name
        self.usage_line = usage_line
        self.used_union = False


def _needs_quote_leaf(node: ast.AST, ctx: RewriteContext) -> bool:
    base = _base_name_of(node)
    if base is None:
        return False
    if base in BUILTIN_NAMES:
        return False
    if base in ctx.bindings and not ctx.bindings[base].is_type_checking:
        return False
    if base == ctx.enclosing_class_name:
        # Self-reference: the class's own name isn't bound in the enclosing
        # scope until its whole body (including this annotation) finishes
        # executing, so this is a genuine forward reference regardless of
        # where the class itself starts.
        return True
    if base in ctx.mod_defs:
        return ctx.mod_defs[base] > ctx.usage_line
    # No import and no module-level definition found anywhere in the file --
    # can't confirm it's safe to unquote, so leave it quoted.
    return True


def _render_union_members(members: list[ast.AST], ctx: RewriteContext) -> str:
    """Render a flattened list of union members (from a `|` chain or from an
    existing Union[...]/_Union[...] subscript's slice) to minimum-quoting
    text: bare `X | Y` if nothing needs quoting, `Union[...]` -- quoting only
    the members that need it -- otherwise."""
    rendered = []
    any_quoted = False
    for member in members:
        text, quoted = _render_leaf(member, ctx)
        rendered.append(text)
        any_quoted = any_quoted or quoted
    if any_quoted:
        ctx.used_union = True
        return f'{ctx.union_name}[{", ".join(rendered)}]'
    return ' | '.join(rendered)


def _render_leaf(node: ast.AST, ctx: RewriteContext) -> tuple[str, bool]:
    """Render one 'slot' (a union member, or one subscript argument):
    returns (text, was_quoted_here)."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            try:
                inner = ast.parse(node.value, mode='eval').body
            except SyntaxError:
                return ast.unparse(node), True
            return _render_leaf(inner, ctx)
        return ast.unparse(node), False

    if isinstance(node, (ast.Name, ast.Attribute)):
        quote = _needs_quote_leaf(node, ctx)
        text = ast.unparse(node)
        return (f'"{text}"' if quote else text), quote

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _render_slot(node, ctx), False

    if isinstance(node, ast.Subscript):
        return _render_slot(node, ctx), False

    if isinstance(node, ast.List):
        return '[' + ', '.join(_render_leaf(e, ctx)[0] for e in node.elts) + ']', False

    return ast.unparse(node), False


def _render_slot(node: ast.AST, ctx: RewriteContext) -> str:
    """Render a full annotation (or a nested slot that is itself a union or
    subscript) to its minimum-quoting text form."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            try:
                inner = ast.parse(node.value, mode='eval').body
            except SyntaxError:
                return ast.unparse(node)
            return _render_slot(inner, ctx)
        return ast.unparse(node)

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        members: list[ast.AST] = []
        _flatten_bitor(node, members)
        return _render_union_members(members, ctx)

    if isinstance(node, ast.Subscript) and _is_union_value(node.value, ctx.bindings):
        # An existing Union[...]/_Union[...] -- possibly from a previous,
        # overly-eager pass that wrapped a union in Union[] even though
        # nothing in it actually needs quoting. Re-flatten and re-decide
        # rather than assume the wrapper itself is correct.
        sl = node.slice
        members = list(sl.elts) if isinstance(sl, ast.Tuple) else [sl]
        return _render_union_members(members, ctx)

    if isinstance(node, ast.Subscript):
        value_text = _render_slot(node.value, ctx)
        sl = node.slice
        if isinstance(sl, ast.Tuple):
            arg_texts = [_render_leaf(e, ctx)[0] for e in sl.elts]
            return f'{value_text}[{", ".join(arg_texts)}]'
        arg_text, _ = _render_leaf(sl, ctx)
        return f'{value_text}[{arg_text}]'

    if isinstance(node, (ast.Name, ast.Attribute)):
        text, _ = _render_leaf(node, ctx)
        return text

    if isinstance(node, ast.List):
        return '[' + ', '.join(_render_leaf(e, ctx)[0] for e in node.elts) + ']'

    return ast.unparse(node)


def _find_runtime_typing_import(tree: ast.Module) -> ast.ImportFrom | None:
    """The first module-level `from typing import ...` statement that is NOT
    guarded by `if TYPE_CHECKING:` (a Union import must be real at runtime,
    since annotations in this codebase are evaluated eagerly -- no file here
    uses `from __future__ import annotations`)."""
    for node, is_type_checking in dt._iter_module_level_imports(tree):
        if is_type_checking:
            continue
        if isinstance(node, ast.ImportFrom) and node.module == 'typing':
            return node
    return None


def annotation_sites(
    tree: ast.Module, bindings: dict[str, dt.ImportBinding],
) -> list[tuple[ast.AST, int, str | None]]:
    """Every (annotation_node, usage_line, enclosing_class_name) worth
    checking: one containing a string constant (a possible forward reference
    to resolve), or an existing Union[...]/_Union[...] subscript (which may
    need collapsing back to a bare `X | Y` if nothing in it actually needs
    quoting -- see _needs_rewrite_check)."""
    sites: list[tuple[ast.AST, int, str | None]] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            enclosing = _enclosing_class(node)
            enclosing_name = enclosing.name if enclosing is not None else None
            args = node.args
            all_args = [*args.posonlyargs, *args.args, *args.kwonlyargs]
            if args.vararg:
                all_args.append(args.vararg)
            if args.kwarg:
                all_args.append(args.kwarg)
            for arg in all_args:
                if arg.annotation is not None and _needs_rewrite_check(arg.annotation, bindings):
                    sites.append((arg.annotation, node.lineno, enclosing_name))
            if node.returns is not None and _needs_rewrite_check(node.returns, bindings):
                sites.append((node.returns, node.lineno, enclosing_name))
        elif isinstance(node, ast.AnnAssign):
            if _needs_rewrite_check(node.annotation, bindings):
                enclosing = _enclosing_class(node)
                enclosing_name = enclosing.name if enclosing is not None else None
                sites.append((node.annotation, node.lineno, enclosing_name))

    return sites


def build_reference(paths: list[Path]) -> dict[str, dict]:
    """Per-file {imports, module_level_defs} used to decide quoting -- the
    same data dep_trace.py's default mode already reports, plus the
    module-level-definition index this tool additionally needs. Returned in a
    JSON-serializable shape so --json-report can dump it directly."""
    reference: dict[str, dict] = {}

    for path in paths:
        tree = dt._parse_file(path)
        if tree is None:
            continue
        dt._attach_parents(tree)
        bindings, star_imports = dt.collect_bindings(tree)

        reference[str(path)] = {
            'imports': {
                name: {
                    'module': b.module,
                    'imported_name': b.imported_name,
                    'lineno': b.lineno,
                    'is_type_checking': b.is_type_checking,
                }
                for name, b in bindings.items()
            },
            'star_imports': [
                {'lineno': lineno, 'module': module, 'is_type_checking': is_tc}
                for lineno, module, is_tc in star_imports
            ],
            'module_level_defs': _module_level_defs(tree),
        }

    return reference


def _strip_unused_union_import(new_source: str, union_name: str, path: Path, log: list[str]) -> str:
    """Remove `union_name` from its `from typing import ...` line if nothing
    in the rewritten source still references it -- dropping the whole line
    if that was the only name it imported."""
    new_tree = ast.parse(new_source)
    dt._attach_parents(new_tree)

    still_used = any(
        isinstance(n, ast.Name) and n.id == union_name and isinstance(n.ctx, ast.Load) for n in ast.walk(new_tree)
    )
    if still_used:
        return new_source

    target_import = None
    for node, is_type_checking in dt._iter_module_level_imports(new_tree):
        if is_type_checking or not isinstance(node, ast.ImportFrom) or node.module != 'typing':
            continue
        for alias in node.names:
            if (alias.asname or alias.name) == union_name and alias.name == 'Union':
                target_import = node
                break
        if target_import is not None:
            break

    if target_import is None:
        return new_source

    starts = _line_starts(new_source)
    imp_start = _abs_offset(starts, target_import.lineno, target_import.col_offset)
    imp_end = _abs_offset(starts, target_import.end_lineno, target_import.end_col_offset)

    remaining = [a for a in target_import.names if (a.asname or a.name) != union_name]
    if remaining:
        new_import_text = 'from typing import ' + ', '.join(
            f'{a.name} as {a.asname}' if a.asname else a.name for a in remaining
        )
        log.append(f'  {path}: dropped unused "{union_name}" -> {new_import_text}')
        return new_source[:imp_start] + new_import_text + new_source[imp_end:]

    # Union/_Union was the only name imported -- drop the whole line.
    line_end = new_source.find('\n', imp_end)
    line_end = line_end + 1 if line_end != -1 else len(new_source)
    line_start = new_source.rfind('\n', 0, imp_start) + 1
    log.append(f'  {path}: removed now-empty "from typing import {union_name}" line')
    return new_source[:line_start] + new_source[line_end:]


def process_file(path: Path, log: list[str], apply: bool) -> bool:
    source = path.read_text(encoding='utf-8')
    tree = dt._parse_file(path)
    if tree is None:
        return False
    dt._attach_parents(tree)

    bindings, _ = dt.collect_bindings(tree)
    mod_defs = _module_level_defs(tree)

    union_name = 'Union'
    for local_name, binding in bindings.items():
        if binding.module == 'typing' and binding.imported_name == 'Union' and not binding.is_type_checking:
            union_name = local_name
            break

    sites = annotation_sites(tree, bindings)
    if not sites:
        return False

    starts = _line_starts(source)
    edits: list[tuple[int, int, str, str]] = []
    used_union_overall = False

    for annotation, usage_line, enclosing_name in sites:
        ctx = RewriteContext(bindings, mod_defs, union_name, enclosing_name, usage_line)
        new_text = _render_slot(annotation, ctx)

        start = _abs_offset(starts, annotation.lineno, annotation.col_offset)
        end = _abs_offset(starts, annotation.end_lineno, annotation.end_col_offset)
        original_text = source[start:end]

        if new_text == original_text:
            continue

        try:
            ast.parse(new_text, mode='eval')
        except SyntaxError as exc:
            log.append(f'  ERROR (bad rewrite) {path}:{annotation.lineno}: {original_text!r} -> {new_text!r}: {exc}')
            continue

        edits.append((start, end, original_text, new_text))
        if ctx.used_union:
            used_union_overall = True
        log.append(f'  {path}:{annotation.lineno}  {original_text} -> {new_text}')

    if not edits:
        return False

    new_source = source
    for start, end, _orig, replacement in sorted(edits, key=lambda e: -e[0]):
        new_source = new_source[:start] + replacement + new_source[end:]

    have_runtime_union = any(
        b.module == 'typing' and b.imported_name == 'Union' and not b.is_type_checking
        for b in bindings.values()
    )
    if used_union_overall and not have_runtime_union:
        existing = _find_runtime_typing_import(tree)
        if existing is not None:
            imp_start = _abs_offset(starts, existing.lineno, existing.col_offset)
            imp_end = _abs_offset(starts, existing.end_lineno, existing.end_col_offset)
            imp_text = source[imp_start:imp_end]
            shift = sum((len(repl) - (e - s)) for s, e, _o, repl in edits if s < imp_start)
            imp_start_new = imp_start + shift
            imp_end_new = imp_end + shift
            actual = new_source[imp_start_new:imp_end_new]
            if actual != imp_text:
                log.append(f'  ERROR: {path} import text mismatch: expected {imp_text!r} got {actual!r}')
                return False
            new_imp_text = imp_text.rstrip() + ', Union'
            new_source = new_source[:imp_start_new] + new_imp_text + new_source[imp_end_new:]
            log.append(f'  {path}: extended import -> {new_imp_text.strip()}')
        else:
            first_import = next(
                (n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))), None,
            )
            if first_import is not None:
                insert_at = _abs_offset(starts, first_import.lineno, 0)
                new_source = new_source[:insert_at] + 'from typing import Union\n' + new_source[insert_at:]
                log.append(f'  {path}: inserted new "from typing import Union" line')
            else:
                log.append(f'  {path}: WARNING no import statement found to anchor new Union import')

    elif have_runtime_union and not used_union_overall:
        # A pre-existing Union import (possibly left over from an earlier,
        # overly-eager pass) may no longer be used anywhere in the file once
        # every union here collapsed back to a bare `X | Y` -- drop it rather
        # than leave a dangling import.
        new_source = _strip_unused_union_import(new_source, union_name, path, log)

    try:
        ast.parse(new_source, filename=str(path))
    except SyntaxError as exc:
        log.append(f'  ERROR: {path} failed to parse after edit: {exc}')
        return False

    if apply:
        path.write_text(new_source, encoding='utf-8')
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Rewrite over-quoted string type annotations to minimum-necessary quoting, '
                    'converting quoted `|` unions to typing.Union.',
    )
    parser.add_argument('target', help='a .py file, or a directory to scan recursively')
    parser.add_argument(
        '--apply', action='store_true',
        help='write the changes; without this flag, only a dry-run report is printed',
    )
    parser.add_argument(
        '--json-report', default=None, metavar='PATH',
        help='also dump the per-file {imports, module_level_defs} reference data (the same '
             'TYPE_CHECKING/binding info dep_trace.py tracks, used here to decide quoting) '
             'to this path as JSON, for inspection',
    )
    args = parser.parse_args()

    target = Path(args.target)
    paths = sorted(target.rglob('*.py')) if target.is_dir() else [target]

    if args.json_report:
        reference = build_reference(paths)
        with open(args.json_report, 'w', encoding='utf-8') as f:
            json.dump(reference, f, indent=2)
        print(f'wrote reference for {len(reference)} files -> {args.json_report}')

    log: list[str] = []
    changed_files = []
    for path in paths:
        if process_file(path, log, args.apply):
            changed_files.append(str(path))

    print(f'{"APPLIED" if args.apply else "DRY RUN"}: {len(changed_files)} files changed')
    for line in log:
        print(line)


if __name__ == '__main__':
    main()
