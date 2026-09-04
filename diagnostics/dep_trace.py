# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Locate things in a Python codebase without grepping: what a file imports
and uses, where a type/class/function is defined, who calls it, and how
overrides relate to their superclass implementation.

Usage::

    python diagnostics/dep_trace.py <file_or_dir> [--depth shallow|deep] [--name PATTERN] [--local] [--json]
    python diagnostics/dep_trace.py <file_or_dir> --types       [--name PATTERN] [--json]
    python diagnostics/dep_trace.py <file_or_dir> --calls       [--name PATTERN] [--json]
    python diagnostics/dep_trace.py <file_or_dir> --overrides   [--name PATTERN] [--json]
    python diagnostics/dep_trace.py <file_or_dir> --imported-by [--name PATTERN] [--json]

``target`` (a file or directory) and the four mode flags (``--types``, ``--calls``,
``--overrides``, ``--imported-by``) can appear in any order on the command line. The filter
pattern for whichever mode(s) are active is always given via the separate ``--name PATTERN``
flag, never attached to a mode flag itself -- this is deliberate: an early version let the mode
flags optionally take their own trailing value (``--imported-by [NAME]``), but that is ambiguous
for argparse whenever ``target`` immediately follows the mode flag with no ``--name``/``--local``/
etc in between (argparse can't tell whether that bare word is the mode's optional value or the
positional ``target``, and silently consumes it as the former, leaving ``target`` unfilled).
Splitting the filter into its own always-named flag removes the ambiguity entirely, independent
of argument order.

Any combination of the four mode flags can be given together in one run, sharing the one
``--name`` filter -- e.g. ``--calls --overrides --name __init__`` runs both and reports both.
Each mode still runs exactly as it would alone (results are identical either way); only the
output shape changes once more than one mode is active: text output prints one ``== --mode ==``
labeled section per active mode, back to back, and ``--json`` output becomes a single object
keyed by mode name (``{"calls": [...], "overrides": [...]}``) instead of a bare array. With
exactly one mode active (or none), output is the flat single-mode form shown in the per-mode
sections below -- no wrapping, unchanged from before this existed. ``--calls`` and
``--overrides`` share one class-registry build when both are active in the same run, so
combining them costs one extra pass over the target, not two.

There used to be a separate ``--find`` mode for definition lookup, but it was nothing more than
"index everything and filter by NAME" -- exactly what ``--name`` alone already means. So: no mode
flag plus no ``--name`` is the default import-trace mode; no mode flag *with* ``--name`` is
definition-lookup (the old ``--find``) instead.

Import-trace mode (default, no mode flag and no ``--name``) lists, for every
``import``/``from ... import`` statement found, the specific attributes,
calls, and bare-name usages pulled from that import elsewhere in the file --
including references inside quoted TYPE_CHECKING-style forward-reference
annotations (e.g. ``Union["_somemodule.SomeClass", None]``), which a plain
``ast`` name walk would otherwise miss. ``--depth shallow`` lists just the
import statements themselves with no usage detail; ``--depth deep`` (the
default) is the full usage trace. ``--local`` restricts the report to
in-project imports -- relative imports, plus absolute imports whose
top-level package matches the scanned file's own top-level package
(auto-detected by walking up through ``__init__.py`` files) -- hiding
stdlib/third-party noise like ``numpy`` or ``PySide6``.

``--name PATTERN`` is matched with ``re.search`` (not exact/substring
equality) -- a plain literal like ``Housing3D`` behaves exactly like a
substring search since it has no special regex characters, but anything
with regex syntax (``^set_.*``, ``__(init|new)__``, ``Q.*Event$``) works too,
with no separate flag needed to "turn on" regex matching. Anchor with
``^``/``$`` for an exact match. Omitting ``--name`` entirely dumps everything
the active mode tracks, unfiltered.

Type-index mode (``--types``) scans function parameter/return annotations
and variable (``AnnAssign``) annotations and reports every location a given
type is used, e.g. "every function that takes a ``Housing3D`` parameter" --
handy when changing a class and needing to find every call site that would
need updating. Pass ``--types`` alone to dump the whole index, or add
``--name SomeClass`` to filter to types matching that pattern.

Definition-lookup mode (no mode flag, but ``--name`` given) finds every
class/function/method definition whose name matches it, with its file:line
and signature -- "where is X defined," answered directly instead of
guessing at a grep pattern.

Call-site mode (``--calls``) finds every call to a function/method matching
``--name``. For ``self.X(...)``/``cls.X(...)``/``super().X(...)`` calls, it
also resolves the receiver against the class hierarchy (built from every
class found under the target) to report which class's implementation
actually runs -- the override, or a specific ancestor's, when one exists.
Calls through any other receiver expression are still listed but can't be
resolved statically (heuristic name match only).

Override-mapping mode (``--overrides``) takes ``--name`` as a class name or
a method name and reports every override relationship found: which
ancestor(s) define the same method, and whether the override calls
``super().method()`` (extends the base behavior) or not (fully shadows it).
Pass ``--overrides`` alone to dump every override relationship found under
the target.

Reverse-import mode (``--imported-by``) is the mirror image of the default
mode: instead of "what does this file import," it answers "who imports this
file." For every file under the target it resolves each
``import``/``from ... import`` statement (relative or absolute, including
``if TYPE_CHECKING:``-guarded ones, which are tagged as such) down to the
actual file it points at, then reports, per target file, every other file
that imports it and at which line. Pass ``--imported-by`` alone to dump the
whole reverse graph, or add ``--name`` to filter to one file -- it may match
a bare filename (``camera``), a path fragment (``gl/canvas_3d/camera.py``),
or a dotted module path (``harness_designer.gl.canvas_3d.camera``).

``--calls``, ``--overrides``, and ``--imported-by`` all build their picture
from every file under the given target, so point them at a directory (or
the whole package) for meaningful cross-file resolution -- a single file
only resolves against things defined/reachable in that same file.

If given a directory, recurses through it and reports on every ``*.py`` file
found.

Limitations: usage/calls reached only through ``getattr``/``setattr``,
``importlib``, or a star import (``from x import *``) can't be resolved
statically. Star imports are flagged as untraceable rather than silently
skipped; any ``getattr``/``setattr`` calls found in the file are flagged too
so you know where a blind spot might be hiding. Ancestor ordering is a
simple depth-first walk of written base order, not a full C3 linearization
-- an approximation that's exact for single inheritance and virtually all
non-diamond multiple inheritance, which covers ordinary mixin usage.
"""

import argparse
import ast
import contextlib
import io
import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

_ANNOTATION_NOISE = {
    'None', 'Any', 'Union', '_Union', 'Optional', 'TYPE_CHECKING', 'Callable', 'ClassVar',
    'Final', 'Literal', 'list', 'dict', 'tuple', 'set', 'frozenset', 'type',
    'bool', 'int', 'float', 'str', 'bytes', 'bytearray', 'complex', 'object',
}


@dataclass
class Usage:
    count: int = 0
    called: bool = False
    type_only: bool = False
    lines: list[int] = field(default_factory=list)


@dataclass
class ImportBinding:
    local_name: str
    module: str
    imported_name: str | None
    lineno: int
    is_type_checking: bool = False
    usages: dict[str, Usage] = field(default_factory=dict)


def _make_matcher(name_filter: str | None) -> Callable[[str], bool]:
    if not name_filter:
        return lambda candidate: True
    pattern = re.compile(name_filter)
    return lambda candidate: pattern.search(candidate) is not None


def _module_name(node: ast.Import | ast.ImportFrom) -> str:
    if isinstance(node, ast.ImportFrom):
        return '.' * node.level + (node.module or '')
    return ''


def _is_type_checking_test(test: ast.expr) -> bool:
    if isinstance(test, ast.Name) and test.id == 'TYPE_CHECKING':
        return True
    return isinstance(test, ast.Attribute) and test.attr == 'TYPE_CHECKING'


def _iter_module_level_imports(tree: ast.Module) -> list[tuple[ast.stmt, bool]]:
    """Module-level import statements, descending into ``if``/``try`` bodies
    (so ``if TYPE_CHECKING:`` and ``try/except ImportError`` guards are seen)
    but not into function/class scopes. Each result is tagged with whether it
    sits inside an ``if TYPE_CHECKING:`` branch."""
    results: list[tuple[ast.stmt, bool]] = []

    def _walk(stmts: list[ast.stmt], type_checking: bool) -> None:
        for stmt in stmts:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                results.append((stmt, type_checking))
            elif isinstance(stmt, ast.If):
                _walk(stmt.body, type_checking or _is_type_checking_test(stmt.test))
                _walk(stmt.orelse, type_checking)
            elif isinstance(stmt, ast.Try):
                _walk(stmt.body, type_checking)
                for handler in stmt.handlers:
                    _walk(handler.body, type_checking)
                _walk(stmt.orelse, type_checking)
                _walk(stmt.finalbody, type_checking)

    _walk(tree.body, False)
    return results


def _attach_parents(tree: ast.AST) -> None:
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent


def _parse_file(path: Path) -> ast.Module | None:
    try:
        source = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        print(f'skipping {path}: {exc}', file=sys.stderr)
        return None

    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        print(f'skipping {path}: {exc}', file=sys.stderr)
        return None


def collect_bindings(tree: ast.Module) -> tuple[dict[str, ImportBinding], list[tuple[int, str, bool]]]:
    bindings: dict[str, ImportBinding] = {}
    star_imports: list[tuple[int, str, bool]] = []

    for node, is_type_checking in _iter_module_level_imports(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    local_name = alias.asname
                else:
                    local_name = alias.name.split('.')[0]
                bindings[local_name] = ImportBinding(
                    local_name=local_name,
                    module=alias.name,
                    imported_name=None,
                    lineno=node.lineno,
                    is_type_checking=is_type_checking,
                )
        elif isinstance(node, ast.ImportFrom):
            module = _module_name(node)
            for alias in node.names:
                if alias.name == '*':
                    star_imports.append((node.lineno, module, is_type_checking))
                    continue
                local_name = alias.asname or alias.name
                bindings[local_name] = ImportBinding(
                    local_name=local_name,
                    module=module,
                    imported_name=alias.name,
                    lineno=node.lineno,
                    is_type_checking=is_type_checking,
                )

    return bindings, star_imports


def _record_chain(name_node: ast.Name, bindings: dict[str, ImportBinding], type_only: bool, lineno: int) -> None:
    binding = bindings[name_node.id]
    parts = [name_node.id]
    current: ast.AST = name_node
    parent = getattr(current, 'parent', None)

    while isinstance(parent, ast.Attribute) and parent.value is current:
        parts.append(parent.attr)
        current = parent
        parent = getattr(current, 'parent', None)

    chain = '.'.join(parts)
    called = isinstance(parent, ast.Call) and parent.func is current

    usage = binding.usages.setdefault(chain, Usage())
    usage.count += 1
    if called:
        usage.called = True
    if type_only:
        usage.type_only = True
    if lineno not in usage.lines:
        usage.lines.append(lineno)


def _record_usages(tree: ast.AST, bindings: dict[str, ImportBinding], type_only: bool) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in bindings:
            _record_chain(node, bindings, type_only, getattr(node, 'lineno', -1))


def _scan_string_annotations(tree: ast.Module, bindings: dict[str, ImportBinding]) -> None:
    annotation_nodes: list[ast.AST] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            all_args = [*args.posonlyargs, *args.args, *args.kwonlyargs]
            if args.vararg:
                all_args.append(args.vararg)
            if args.kwarg:
                all_args.append(args.kwarg)
            for arg in all_args:
                if arg.annotation is not None:
                    annotation_nodes.append(arg.annotation)
            if node.returns is not None:
                annotation_nodes.append(node.returns)
        elif isinstance(node, ast.AnnAssign):
            annotation_nodes.append(node.annotation)

    for annotation in annotation_nodes:
        for sub in ast.walk(annotation):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                try:
                    parsed = ast.parse(sub.value, mode='eval')
                except SyntaxError:
                    continue
                _attach_parents(parsed)
                for inner in ast.walk(parsed):
                    if isinstance(inner, ast.Name):
                        inner.lineno = getattr(sub, 'lineno', annotation.lineno)
                _record_usages(parsed, bindings, type_only=True)


@dataclass
class TypeUsage:
    chain: str
    file: str
    qualname: str
    role: str
    member: str | None
    lineno: int


def _qualname(node: ast.AST) -> str:
    parts: list[str] = []
    current: ast.AST | None = node

    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            parts.append(current.name)
        current = getattr(current, 'parent', None)

    return '.'.join(reversed(parts))


def _annotation_chains(annotation: ast.AST) -> set[str]:
    chains: set[str] = set()

    for node in ast.walk(annotation):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                parsed = ast.parse(node.value, mode='eval')
            except SyntaxError:
                continue
            _attach_parents(parsed)
            chains |= _annotation_chains(parsed)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            parts = [node.id]
            current: ast.AST = node
            parent = getattr(current, 'parent', None)
            while isinstance(parent, ast.Attribute) and parent.value is current:
                parts.append(parent.attr)
                current = parent
                parent = getattr(current, 'parent', None)
            chains.add('.'.join(parts))

    return {chain for chain in chains if chain.split('.')[0] not in _ANNOTATION_NOISE}


def collect_type_usages(tree: ast.Module, file_path: str) -> list[TypeUsage]:
    usages: list[TypeUsage] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qualname = _qualname(node)
            args = node.args
            all_args = [*args.posonlyargs, *args.args, *args.kwonlyargs]
            if args.vararg:
                all_args.append(args.vararg)
            if args.kwarg:
                all_args.append(args.kwarg)

            for arg in all_args:
                if arg.annotation is None:
                    continue
                for chain in _annotation_chains(arg.annotation):
                    usages.append(TypeUsage(chain, file_path, qualname, 'param', arg.arg, arg.lineno))

            if node.returns is not None:
                for chain in _annotation_chains(node.returns):
                    usages.append(TypeUsage(chain, file_path, qualname, 'return', None, node.returns.lineno))

        elif isinstance(node, ast.AnnAssign):
            qualname = _qualname(node.parent) if getattr(node, 'parent', None) is not None else ''
            if isinstance(node.target, ast.Name):
                target_name = node.target.id
            elif isinstance(node.target, ast.Attribute):
                target_name = node.target.attr
            else:
                target_name = None
            for chain in _annotation_chains(node.annotation):
                usages.append(TypeUsage(chain, file_path, qualname, 'variable', target_name, node.lineno))

    return usages


def _find_getattr_setattr(tree: ast.Module) -> list[int]:
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ('getattr', 'setattr'):
                lines.append(node.lineno)
    return sorted(set(lines))


def _local_package_name(path: Path) -> str | None:
    current = path.resolve().parent
    package_name = None
    while (current / '__init__.py').exists():
        package_name = current.name
        current = current.parent
    return package_name


def _is_local_module(module: str, local_package: str | None) -> bool:
    if module.startswith('.'):
        return True
    if local_package is None:
        return False
    return module.split('.')[0] == local_package


def analyze_file(path: Path) -> dict | None:
    tree = _parse_file(path)
    if tree is None:
        return None
    _attach_parents(tree)

    bindings, star_imports = collect_bindings(tree)
    _record_usages(tree, bindings, type_only=False)
    _scan_string_annotations(tree, bindings)
    dynamic_lines = _find_getattr_setattr(tree)

    return {
        'file': str(path),
        'local_package': _local_package_name(path),
        'bindings': bindings,
        'star_imports': star_imports,
        'dynamic_lines': dynamic_lines,
    }


def _format_usage_kind(usage: Usage) -> str:
    if usage.called:
        return 'called'
    if usage.type_only:
        return 'type-only'
    return 'attr'


def print_report(result: dict, depth: str, local_only: bool = False) -> None:
    print(f'== {result["file"]} ==')

    bindings: dict[str, ImportBinding] = result['bindings']
    if not bindings and not result['star_imports']:
        if local_only:
            print('  (no local imports found)')
        else:
            print('  (no imports found)')

    for binding in sorted(bindings.values(), key=lambda b: b.lineno):
        if binding.imported_name:
            source_desc = f'from {binding.module} import {binding.imported_name}'
        else:
            source_desc = f'import {binding.module}'
        if binding.local_name not in (binding.imported_name, binding.module):
            source_desc += f' as {binding.local_name}'

        if binding.is_type_checking:
            source_desc += '  [TYPE_CHECKING]'

        print(f'Line {binding.lineno}: {source_desc}')

        if depth == 'shallow':
            continue

        if not binding.usages:
            print('    (unused)')
            continue

        for chain, usage in sorted(binding.usages.items()):
            kind = _format_usage_kind(usage)
            lines_desc = ', '.join(str(n) for n in sorted(usage.lines)[:10])
            if len(usage.lines) > 10:
                lines_desc += ', ...'
            print(f'    {chain:<40} {kind:<10} x{usage.count:<4} lines {lines_desc}')

    for lineno, module, is_type_checking in result['star_imports']:
        tag = '  [TYPE_CHECKING]' if is_type_checking else ''
        print(f'Line {lineno}: from {module} import *  -- UNTRACEABLE (star import){tag}')

    if depth == 'deep' and result['dynamic_lines']:
        lines_desc = ', '.join(str(n) for n in result['dynamic_lines'])
        print(f'  note: getattr/setattr used at lines {lines_desc} -- may use imports not detected above')

    print()


def result_to_json(result: dict) -> dict:
    bindings_out = {}
    for local_name, binding in result['bindings'].items():
        bindings_out[local_name] = {
            'module': binding.module,
            'imported_name': binding.imported_name,
            'lineno': binding.lineno,
            'is_type_checking': binding.is_type_checking,
            'usages': {
                chain: {
                    'count': usage.count,
                    'called': usage.called,
                    'type_only': usage.type_only,
                    'lines': sorted(usage.lines),
                }
                for chain, usage in binding.usages.items()
            },
        }

    return {
        'file': result['file'],
        'local_package': result['local_package'],
        'bindings': bindings_out,
        'star_imports': [
            {'lineno': lineno, 'module': module, 'is_type_checking': is_type_checking}
            for lineno, module, is_type_checking in result['star_imports']
        ],
        'dynamic_lines': result['dynamic_lines'],
    }


def _matches_type_filter(chain: str, name_filter: str) -> bool:
    return re.search(name_filter, chain) is not None


def print_type_report(all_usages: list[TypeUsage], name_filter: str | None) -> None:
    if name_filter:
        matches = [u for u in all_usages if _matches_type_filter(u.chain, name_filter)]
        grouped: dict[str, list[TypeUsage]] = {}
        for usage in matches:
            grouped.setdefault(usage.chain, []).append(usage)
    else:
        grouped = {}
        for usage in all_usages:
            grouped.setdefault(usage.chain, []).append(usage)

    if not grouped:
        print(f'no type usages found matching {name_filter!r}' if name_filter else 'no annotated types found')
        return

    for chain in sorted(grouped):
        usages = sorted(grouped[chain], key=lambda u: (u.file, u.lineno))
        print(f'{chain}  (used {len(usages)}x)')
        for usage in usages:
            if usage.role == 'param':
                desc = f'{usage.qualname}(param {usage.member})'
            elif usage.role == 'return':
                desc = f'{usage.qualname}(return)'
            else:
                desc = f'{usage.qualname} (variable {usage.member})'
            print(f'  {usage.file}:{usage.lineno}  {desc}')
        print()


def type_usages_to_json(all_usages: list[TypeUsage], name_filter: str | None) -> list[dict]:
    if name_filter:
        matches = [u for u in all_usages if _matches_type_filter(u.chain, name_filter)]
    else:
        matches = all_usages

    return [
        {
            'chain': usage.chain,
            'file': usage.file,
            'qualname': usage.qualname,
            'role': usage.role,
            'member': usage.member,
            'lineno': usage.lineno,
        }
        for usage in matches
    ]


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        if base is None:
            return node.attr
        return f'{base}.{node.attr}'
    if isinstance(node, ast.Subscript):
        return _dotted_name(node.value)
    return None


@dataclass
class ClassInfo:
    name: str
    file: str
    lineno: int
    base_chains: list[str]
    methods: dict[str, ast.AST]


def build_class_registry(paths: list[Path]) -> dict[str, list[ClassInfo]]:
    registry: dict[str, list[ClassInfo]] = {}

    for path in paths:
        tree = _parse_file(path)
        if tree is None:
            continue
        _attach_parents(tree)

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            base_chains = [chain for base in node.bases if (chain := _dotted_name(base)) is not None]
            methods = {
                item.name: item
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            info = ClassInfo(node.name, str(path), node.lineno, base_chains, methods)
            registry.setdefault(node.name, []).append(info)

    return registry


def _resolve_base(base_chain: str, registry: dict[str, list[ClassInfo]]) -> list[ClassInfo]:
    return registry.get(base_chain.split('.')[-1], [])


def _ancestors(info: ClassInfo, registry: dict[str, list[ClassInfo]], _seen: set[int] | None = None) -> list[ClassInfo]:
    if _seen is None:
        _seen = set()

    result: list[ClassInfo] = []
    for base_chain in info.base_chains:
        for candidate in _resolve_base(base_chain, registry):
            if id(candidate) in _seen:
                continue
            _seen.add(id(candidate))
            result.append(candidate)
            result.extend(_ancestors(candidate, registry, _seen))

    return result


def _enclosing_class(node: ast.AST) -> ast.ClassDef | None:
    current = getattr(node, 'parent', None)
    while current is not None:
        if isinstance(current, ast.ClassDef):
            return current
        current = getattr(current, 'parent', None)
    return None


# ---------------------------------------------------------------------------
# definition index (default mode when --name is given with no other mode flag)
# ---------------------------------------------------------------------------

@dataclass
class DefInfo:
    name: str
    kind: str
    qualname: str
    file: str
    lineno: int
    header: str


def _function_header(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = 'async def' if isinstance(node, ast.AsyncFunctionDef) else 'def'
    args_text = ast.unparse(node.args)
    ret_text = f' -> {ast.unparse(node.returns)}' if node.returns is not None else ''
    return f'{prefix} {node.name}({args_text}){ret_text}:'


def _class_header(node: ast.ClassDef) -> str:
    parts = [ast.unparse(base) for base in node.bases]
    parts += [f'{kw.arg}={ast.unparse(kw.value)}' for kw in node.keywords]
    bases_text = ', '.join(parts)
    if bases_text:
        return f'class {node.name}({bases_text}):'
    return f'class {node.name}:'


def collect_definitions(paths: list[Path], name_filter: str) -> list[DefInfo]:
    matcher = _make_matcher(name_filter)
    results: list[DefInfo] = []

    for path in paths:
        tree = _parse_file(path)
        if tree is None:
            continue
        _attach_parents(tree)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if not matcher(node.name):
                    continue
                results.append(DefInfo(node.name, 'class', _qualname(node), str(path), node.lineno, _class_header(node)))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not matcher(node.name):
                    continue
                kind = 'method' if isinstance(node.parent, ast.ClassDef) else 'function'
                results.append(DefInfo(node.name, kind, _qualname(node), str(path), node.lineno, _function_header(node)))

    return results


def print_def_report(defs: list[DefInfo], name_filter: str | None) -> None:
    if not defs:
        print(f'no definitions found matching {name_filter!r}' if name_filter else 'no definitions found')
        return

    for d in sorted(defs, key=lambda d: (d.file, d.lineno)):
        print(f'{d.file}:{d.lineno}  [{d.kind}] {d.qualname}')
        print(f'    {d.header}')


def defs_to_json(defs: list[DefInfo]) -> list[dict]:
    return [
        {'name': d.name, 'kind': d.kind, 'qualname': d.qualname, 'file': d.file, 'lineno': d.lineno, 'header': d.header}
        for d in defs
    ]


# ---------------------------------------------------------------------------
# --calls: reverse call-site index, with self/super resolution
# ---------------------------------------------------------------------------

@dataclass
class CallSite:
    name: str
    file: str
    lineno: int
    caller_qualname: str
    receiver_kind: str
    receiver_desc: str
    resolved_class: str | None = None
    resolved_file: str | None = None
    resolved_lineno: int | None = None


def _resolve_receiver(node: ast.Call, method_name: str, receiver_kind: str, registry: dict[str, list[ClassInfo]]) -> ClassInfo | None:
    enclosing = _enclosing_class(node)
    if enclosing is None or enclosing.name not in registry:
        return None

    candidates = registry[enclosing.name]
    if len(candidates) != 1:
        return None
    info = candidates[0]

    if receiver_kind == 'super':
        chain = _ancestors(info, registry)
    else:
        chain = [info] + _ancestors(info, registry)

    for candidate in chain:
        if method_name in candidate.methods:
            return candidate

    return None


def collect_calls(paths: list[Path], name_filter: str, registry: dict[str, list[ClassInfo]]) -> list[CallSite]:
    matcher = _make_matcher(name_filter)
    results: list[CallSite] = []

    for path in paths:
        tree = _parse_file(path)
        if tree is None:
            continue
        _attach_parents(tree)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            func = node.func
            if isinstance(func, ast.Name):
                if not matcher(func.id):
                    continue
                results.append(CallSite(func.id, str(path), node.lineno, _qualname(node), 'function', ''))
                continue

            if not isinstance(func, ast.Attribute):
                continue
            if not matcher(func.attr):
                continue

            value = func.value
            if isinstance(value, ast.Name) and value.id == 'self':
                receiver_kind = 'self'
            elif isinstance(value, ast.Name) and value.id == 'cls':
                receiver_kind = 'cls'
            elif isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == 'super':
                receiver_kind = 'super'
            else:
                receiver_kind = 'other'

            try:
                receiver_desc = ast.unparse(value)
            except Exception:
                receiver_desc = ''

            call_site = CallSite(func.attr, str(path), node.lineno, _qualname(node), receiver_kind, receiver_desc)

            if receiver_kind in ('self', 'cls', 'super'):
                resolved = _resolve_receiver(node, func.attr, receiver_kind, registry)
                if resolved is not None:
                    call_site.resolved_class = resolved.name
                    call_site.resolved_file = resolved.file
                    call_site.resolved_lineno = resolved.methods[func.attr].lineno

            results.append(call_site)

    return results


def print_calls_report(call_sites: list[CallSite], name_filter: str | None) -> None:
    if not call_sites:
        print(f'no calls found matching {name_filter!r}' if name_filter else 'no calls found')
        return

    for cs in sorted(call_sites, key=lambda c: (c.file, c.lineno)):
        receiver = f'{cs.receiver_desc}.' if cs.receiver_desc else ''
        print(f'{cs.file}:{cs.lineno}  in {cs.caller_qualname}  [{cs.receiver_kind}]  {receiver}{cs.name}(...)')
        if cs.resolved_class:
            print(f'    -> resolves to {cs.resolved_class}.{cs.name}  {cs.resolved_file}:{cs.resolved_lineno}')

    print()


def calls_to_json(call_sites: list[CallSite]) -> list[dict]:
    return [
        {
            'name': cs.name,
            'file': cs.file,
            'lineno': cs.lineno,
            'caller_qualname': cs.caller_qualname,
            'receiver_kind': cs.receiver_kind,
            'receiver_desc': cs.receiver_desc,
            'resolved_class': cs.resolved_class,
            'resolved_file': cs.resolved_file,
            'resolved_lineno': cs.resolved_lineno,
        }
        for cs in call_sites
    ]


# ---------------------------------------------------------------------------
# --overrides: override / super-call mapping
# ---------------------------------------------------------------------------

@dataclass
class OverrideInfo:
    method_name: str
    class_name: str
    file: str
    lineno: int
    overrides: list[tuple[str, str, int]]
    calls_super: bool
    super_call_line: int | None


def _calls_super_method(func_node: ast.AST, method_name: str, ancestor_names: set[str]) -> int | None:
    for node in ast.walk(func_node):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == method_name):
            continue
        value = node.func.value
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == 'super':
            return node.lineno
        if isinstance(value, ast.Name) and value.id in ancestor_names:
            return node.lineno
    return None


def collect_overrides(registry: dict[str, list[ClassInfo]]) -> list[OverrideInfo]:
    results: list[OverrideInfo] = []

    for infos in registry.values():
        for info in infos:
            ancestors = _ancestors(info, registry)
            ancestor_names = {a.name for a in ancestors}

            for method_name, func_node in info.methods.items():
                defining_ancestors = [a for a in ancestors if method_name in a.methods]
                if not defining_ancestors:
                    continue

                super_line = _calls_super_method(func_node, method_name, ancestor_names)
                results.append(OverrideInfo(
                    method_name=method_name,
                    class_name=info.name,
                    file=info.file,
                    lineno=func_node.lineno,
                    overrides=[(a.name, a.file, a.methods[method_name].lineno) for a in defining_ancestors],
                    calls_super=super_line is not None,
                    super_call_line=super_line,
                ))

    return results


def print_override_report(overrides: list[OverrideInfo], name_filter: str | None) -> None:
    if not name_filter:
        matches = overrides
    else:
        matcher = _make_matcher(name_filter)
        matches = [o for o in overrides if matcher(o.class_name) or matcher(o.method_name)]

    if not matches:
        print(f'no overrides found matching {name_filter!r}' if name_filter else 'no overrides found')
        return

    for o in sorted(matches, key=lambda o: (o.file, o.lineno)):
        print(f'{o.file}:{o.lineno}  {o.class_name}.{o.method_name}')
        for anc_name, anc_file, anc_line in o.overrides:
            print(f'    overrides {anc_name}.{o.method_name}  {anc_file}:{anc_line}')
        if o.calls_super:
            print(f'    calls super().{o.method_name}() at line {o.super_call_line} -- extends base behavior')
        else:
            print('    does NOT call super -- base implementation fully shadowed')

    print()


def overrides_to_json(overrides: list[OverrideInfo]) -> list[dict]:
    return [
        {
            'method_name': o.method_name,
            'class_name': o.class_name,
            'file': o.file,
            'lineno': o.lineno,
            'overrides': [
                {'class_name': n, 'file': f, 'lineno': ln} for n, f, ln in o.overrides
            ],
            'calls_super': o.calls_super,
            'super_call_line': o.super_call_line,
        }
        for o in overrides
    ]


# ---------------------------------------------------------------------------
# --imported-by: reverse import index (who imports this file)
# ---------------------------------------------------------------------------

def _module_path_for_file(path: Path) -> str:
    resolved = path.resolve()
    parts: list[str] = []
    if resolved.stem != '__init__':
        parts.append(resolved.stem)

    current = resolved.parent
    while (current / '__init__.py').exists():
        parts.append(current.name)
        current = current.parent

    return '.'.join(reversed(parts))


def build_module_index(paths: list[Path]) -> dict[str, Path]:
    return {_module_path_for_file(path): path for path in paths}


def _current_package(importing_path: Path, importing_module: str) -> str:
    if importing_path.resolve().stem == '__init__':
        return importing_module
    if '.' in importing_module:
        return importing_module.rsplit('.', 1)[0]
    return ''


def _relative_anchor(current_package: str, level: int) -> str | None:
    parts = current_package.split('.') if current_package else []
    cut = len(parts) - (level - 1)
    if cut < 0:
        return None
    return '.'.join(parts[:cut])


def _from_base(node: ast.ImportFrom, importing_path: Path, importing_module: str) -> str | None:
    if node.level == 0:
        return node.module or ''

    anchor = _relative_anchor(_current_package(importing_path, importing_module), node.level)
    if anchor is None:
        return None
    if node.module:
        return f'{anchor}.{node.module}' if anchor else node.module
    return anchor


@dataclass
class ReverseImportEdge:
    importer_file: str
    lineno: int
    imported_name: str
    is_type_checking: bool


def _resolve_import(node: ast.Import, module_index: dict[str, Path]) -> list[tuple[str, Path]]:
    return [(alias.name, module_index[alias.name]) for alias in node.names if alias.name in module_index]


def _resolve_from_import(
    node: ast.ImportFrom, importing_path: Path, importing_module: str, module_index: dict[str, Path],
) -> list[tuple[str, Path]]:
    base = _from_base(node, importing_path, importing_module)
    if base is None:
        return []

    results: list[tuple[str, Path]] = []
    for alias in node.names:
        if alias.name == '*':
            if base in module_index:
                results.append(('*', module_index[base]))
            continue

        submodule = f'{base}.{alias.name}' if base else alias.name
        if submodule in module_index:
            results.append((alias.name, module_index[submodule]))
        elif base in module_index:
            results.append((alias.name, module_index[base]))

    return results


def collect_reverse_imports(paths: list[Path]) -> dict[str, list[ReverseImportEdge]]:
    module_index = build_module_index(paths)
    reverse: dict[str, list[ReverseImportEdge]] = {}

    for path in paths:
        tree = _parse_file(path)
        if tree is None:
            continue
        importing_module = _module_path_for_file(path)

        for node, is_type_checking in _iter_module_level_imports(tree):
            if isinstance(node, ast.Import):
                resolved = _resolve_import(node, module_index)
            else:
                resolved = _resolve_from_import(node, path, importing_module, module_index)

            for name, target_path in resolved:
                reverse.setdefault(str(target_path), []).append(
                    ReverseImportEdge(str(path), node.lineno, name, is_type_checking)
                )

    return reverse


def _matches_file_filter(file_path: str, module_path: str, name_filter: str) -> bool:
    pattern = re.compile(name_filter)
    normalized_file = file_path.replace('\\', '/')
    return (
        pattern.search(file_path) is not None
        or pattern.search(normalized_file) is not None
        or pattern.search(module_path) is not None
    )


def print_reverse_report(
    reverse: dict[str, list[ReverseImportEdge]], module_index: dict[str, Path], name_filter: str | None,
) -> None:
    path_to_module = {str(path): module for module, path in module_index.items()}

    targets = sorted(reverse.keys(), key=lambda f: (path_to_module.get(f, f)))
    if name_filter:
        targets = [t for t in targets if _matches_file_filter(t, path_to_module.get(t, ''), name_filter)]

    if not targets:
        print(f'no importers found matching {name_filter!r}' if name_filter else 'no imports resolved within target')
        return

    for target in targets:
        edges = reverse[target]
        print(f'{target}  ({path_to_module.get(target, "?")})  imported by {len(edges)}x')
        for edge in sorted(edges, key=lambda e: (e.importer_file, e.lineno)):
            tag = '  [TYPE_CHECKING]' if edge.is_type_checking else ''
            print(f'  {edge.importer_file}:{edge.lineno}  imports {edge.imported_name}{tag}')
        print()


def reverse_to_json(reverse: dict[str, list[ReverseImportEdge]], module_index: dict[str, Path]) -> list[dict]:
    path_to_module = {str(path): module for module, path in module_index.items()}

    return [
        {
            'file': target,
            'module': path_to_module.get(target, None),
            'imported_by': [
                {
                    'importer_file': edge.importer_file,
                    'lineno': edge.lineno,
                    'imported_name': edge.imported_name,
                    'is_type_checking': edge.is_type_checking,
                }
                for edge in edges
            ],
        }
        for target, edges in reverse.items()
    ]


# ---------------------------------------------------------------------------
# mode runners -- each captures its own text report and returns it alongside
# the JSON-serializable data, so main() can run more than one mode per
# invocation and combine their output
# ---------------------------------------------------------------------------

def _capture(fn: Callable[..., None], *args: object) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*args)
    return buf.getvalue()


def _run_types(paths: list[Path], name_filter: str | None) -> tuple[str, list[dict]]:
    all_usages: list[TypeUsage] = []
    for path in paths:
        tree = _parse_file(path)
        if tree is None:
            continue
        _attach_parents(tree)
        all_usages.extend(collect_type_usages(tree, str(path)))

    text = _capture(print_type_report, all_usages, name_filter)
    data = type_usages_to_json(all_usages, name_filter)
    return text, data


def _run_calls(paths: list[Path], name_filter: str | None, registry: dict[str, list[ClassInfo]]) -> tuple[str, list[dict]]:
    call_sites = collect_calls(paths, name_filter or '', registry)
    text = _capture(print_calls_report, call_sites, name_filter)
    data = calls_to_json(call_sites)
    return text, data


def _run_overrides(registry: dict[str, list[ClassInfo]], name_filter: str | None) -> tuple[str, list[dict]]:
    overrides = collect_overrides(registry)
    text = _capture(print_override_report, overrides, name_filter)

    if name_filter:
        matcher = _make_matcher(name_filter)
        json_overrides = [o for o in overrides if matcher(o.class_name) or matcher(o.method_name)]
    else:
        json_overrides = overrides
    data = overrides_to_json(json_overrides)
    return text, data


def _run_imported_by(paths: list[Path], name_filter: str | None, module_index: dict[str, Path]) -> tuple[str, list[dict]]:
    reverse = collect_reverse_imports(paths)

    if name_filter:
        path_to_module = {str(path): module for module, path in module_index.items()}
        reverse = {
            target: edges for target, edges in reverse.items()
            if _matches_file_filter(target, path_to_module.get(target, ''), name_filter)
        }

    text = _capture(print_reverse_report, reverse, module_index, name_filter)
    data = reverse_to_json(reverse, module_index)
    return text, data


def main() -> None:
    parser = argparse.ArgumentParser(description='Trace import, type, call, and override usage in Python source.')
    parser.add_argument('target', help='a .py file, or a directory to scan recursively')
    parser.add_argument('--depth', choices=['shallow', 'deep'], default='deep', help='import-trace detail level')

    parser.add_argument(
        '--types', action='store_true', help='switch to type-usage index mode',
    )
    parser.add_argument(
        '--calls', action='store_true',
        help='switch to call-site mode: find every call to a function/method, '
             'resolving self./super. receivers against the class hierarchy',
    )
    parser.add_argument(
        '--overrides', action='store_true',
        help='switch to override-mapping mode: show override chains and whether each '
             'override calls super()',
    )
    parser.add_argument(
        '--imported-by', action='store_true',
        help='switch to reverse-import mode: for each file, list every other file under '
             'the target that imports it and at which line, resolved against the whole '
             'target tree -- point this at a directory for meaningful results',
    )
    parser.add_argument(
        '--name', default=None, metavar='PATTERN',
        help='regex pattern (matched with re.search) filtering the results of --types/'
             '--calls/--overrides/--imported-by (any combination of these four can be given '
             'together, sharing this one filter); omit for a full unfiltered dump. A plain '
             'literal name works fine here too -- it behaves as a substring match. If no mode '
             'flag is given at all, --name switches from the default import-trace mode to '
             'definition-lookup mode: find class/function/method definitions matching it.',
    )
    parser.add_argument(
        '--local', action='store_true',
        help='import-trace mode only: limit the report to local (in-project) imports -- '
             'relative imports and absolute imports rooted at the same top-level package as '
             'the file being scanned -- hiding stdlib/third-party imports',
    )
    parser.add_argument('--json', action='store_true', help='output JSON instead of a text report')
    args = parser.parse_args()

    target = Path(args.target)
    if target.is_dir():
        paths = sorted(target.rglob('*.py'))
    else:
        paths = [target]

    active_modes: list[str] = []
    if args.types:
        active_modes.append('types')
    if args.calls:
        active_modes.append('calls')
    if args.overrides:
        active_modes.append('overrides')
    if args.imported_by:
        active_modes.append('imported-by')

    if not active_modes:
        if args.name is not None:
            defs = collect_definitions(paths, args.name)
            if args.json:
                print(json.dumps(defs_to_json(defs), indent=2))
            else:
                print_def_report(defs, args.name)
            return

        results = [result for path in paths if (result := analyze_file(path)) is not None]

        if args.local:
            for result in results:
                pkg = result['local_package']
                result['bindings'] = {
                    name: binding for name, binding in result['bindings'].items()
                    if _is_local_module(binding.module, pkg)
                }
                result['star_imports'] = [
                    (lineno, module, is_type_checking) for lineno, module, is_type_checking in result['star_imports']
                    if _is_local_module(module, pkg)
                ]

        if args.json:
            print(json.dumps([result_to_json(result) for result in results], indent=2))
        else:
            for result in results:
                print_report(result, args.depth, args.local)
        return

    registry: dict[str, list[ClassInfo]] | None = None
    if 'calls' in active_modes or 'overrides' in active_modes:
        registry = build_class_registry(paths)

    module_index: dict[str, Path] | None = None
    if 'imported-by' in active_modes:
        module_index = build_module_index(paths)

    texts: dict[str, str] = {}
    json_results: dict[str, list[dict]] = {}

    for mode in active_modes:
        if mode == 'types':
            text, data = _run_types(paths, args.name)
        elif mode == 'calls':
            text, data = _run_calls(paths, args.name, registry)
        elif mode == 'overrides':
            text, data = _run_overrides(registry, args.name)
        else:
            text, data = _run_imported_by(paths, args.name, module_index)
        texts[mode] = text
        json_results[mode] = data

    if len(active_modes) == 1:
        only_mode = active_modes[0]
        if args.json:
            print(json.dumps(json_results[only_mode], indent=2))
        else:
            print(texts[only_mode], end='')
        return

    if args.json:
        print(json.dumps(json_results, indent=2))
    else:
        for mode in active_modes:
            print(f'== --{mode} ==')
            print(texts[mode], end='')


if __name__ == '__main__':
    main()
