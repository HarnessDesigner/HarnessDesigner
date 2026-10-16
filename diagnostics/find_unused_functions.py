"""Locate module-level functions that appear to have no usages elsewhere in
the codebase.

    python diagnostics/find_unused_functions.py

Always scans the whole ``harness_designer`` package -- no arguments.

Reuses ``dep_trace.py``'s own file-parsing/parent-tracking helpers
(``_parse_file``, ``_attach_parents``) for consistency, then:

1. Walks every ``*.py`` file under ``target`` and records every module-level
   function/async-function definition (name, file, line) -- "module level"
   means not nested inside a class or another function; nesting inside a
   module-level ``if``/``try`` guard still counts as module level.
2. Reads the raw text of every ``*.py`` file under ``target`` and counts
   literal, word-boundary-matched occurrences of ``name(`` -- a plain text
   search, not an AST walk -- for each collected function's name. This
   catches both a bare call (``foo(``) and an attribute-style call
   (``obj.foo(``), and excludes the function's own ``def foo(``/``async def
   foo(`` line(s).
3. Reports each function's name, file:line, and usage count.

Usage counting is name-based, like ``dep_trace.py``'s own heuristic matching
for non-``self``/``cls``/``super`` call receivers: it can't statically
resolve which specific definition a given reference points at. Two
consequences:

- If two unrelated module-level functions share the same name in different
  files, their usage counts are combined, and both are flagged ``ambiguous``
  rather than silently splitting (or inventing) a per-definition count that
  can't actually be determined without full import resolution.
- Restricting the match to ``name(`` (rather than any bare-name/attribute
  reference) trades away visibility into a function that's only ever passed
  by reference without being called at the reference site itself (e.g. the
  ``bind()``/``unbind()`` callback pattern this codebase relies on
  throughout) -- a callback-only function can show as unused here even
  though something does hold and eventually call it. This was a deliberate
  choice to cut the much larger noise source: unrelated attributes/
  variables/methods that merely share a function's name, which a bare
  ``ast.Name``/``ast.Attribute`` match (the previous approach) couldn't tell
  apart from a real reference.
- A call reached only through ``getattr``/``setattr`` or a star import can't
  be seen at all -- see the getattr/setattr note the report prints at the
  end when any show up under ``target`` (same blind spot ``dep_trace.py``
  already flags for its own modes).
"""

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import dep_trace as _dep_trace

REPO_ROOT = Path(__file__).parent.parent
TARGET = REPO_ROOT / 'harness_designer'


@dataclass
class FunctionDef:
    name: str
    file: str
    lineno: int


def _is_module_level(node: ast.AST) -> bool:
    current = getattr(node, 'parent', None)
    while current is not None and not isinstance(current, ast.Module):
        if isinstance(current, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            return False
        current = getattr(current, 'parent', None)
    return True


def collect_module_level_functions(paths: list[Path]) -> list[FunctionDef]:
    results: list[FunctionDef] = []
    for path in paths:
        tree = _dep_trace._parse_file(path)
        if tree is None:
            continue
        _dep_trace._attach_parents(tree)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_module_level(node):
                results.append(FunctionDef(node.name, str(path.relative_to(REPO_ROOT)), node.lineno))

    return results


def count_call_like_references(paths: list[Path], names: set[str]) -> dict[str, int]:
    counts: dict[str, int] = {name: 0 for name in names}
    if not names:
        return counts

    escaped = sorted((re.escape(name) for name in names), key=len, reverse=True)
    pattern = re.compile(r'\b(' + '|'.join(escaped) + r')\(')

    for path in paths:
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue

        for match in pattern.finditer(text):
            counts[match.group(1)] += 1

    return counts


def count_getattr_setattr_files(paths: list[Path]) -> int:
    flagged = 0

    for path in paths:
        tree = _dep_trace._parse_file(path)
        if tree is None:
            continue
        if _dep_trace._find_getattr_setattr(tree):
            flagged += 1

    return flagged


@dataclass
class Finding:
    name: str
    file: str
    lineno: int
    count: int
    ambiguous: bool


def build_findings(paths: list[Path]) -> list[Finding]:
    functions = collect_module_level_functions(paths)

    names_seen: dict[str, int] = {}
    for fn in functions:
        names_seen[fn.name] = names_seen.get(fn.name, 0) + 1

    raw_counts = count_call_like_references(paths, set(names_seen))

    findings: list[Finding] = []
    for fn in functions:
        # every definition's own "def name(" / "async def name(" line matches
        # the same pattern, so subtract one occurrence per definition sharing
        # this name to exclude the definition line(s) themselves.
        count = max(0, raw_counts[fn.name] - names_seen[fn.name])
        findings.append(Finding(fn.name, fn.file, fn.lineno, count, names_seen[fn.name] > 1))

    return findings


def print_report(findings: list[Finding], getattr_setattr_files: int) -> None:
    if not findings:
        print('no module-level functions found')
        return

    for f in sorted(findings, key=lambda f: (f.count, f.file, f.lineno)):
        marker = ' [ambiguous name]' if f.ambiguous else ''
        print(f'{f.file}:{f.lineno}  {f.name}  used={f.count}{marker}')

    if getattr_setattr_files:
        print(
            f'\nnote: {getattr_setattr_files} file(s) under target call getattr()/setattr() -- '
            'usage counts cannot see references made that way',
        )


def main() -> None:
    paths = sorted(TARGET.rglob('*.py'))
    findings = build_findings(paths)
    print_report(findings, count_getattr_setattr_files(paths))


if __name__ == '__main__':
    main()
