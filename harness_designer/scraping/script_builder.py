# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Putting a :class:`~.snippets.Snippet` into a script.

Plain text in, plain text out -- no Qt -- so the rules (where imports go,
how warnings are written) are tested without a widget. The editor applies
the result as ordinary edits, which keeps the user's undo history intact.
"""

import re
import textwrap

from . import snippets as _snippets
from .. import check_types as _check_types

_IMPORT_LINE = re.compile(r'^(import|from)\s+\S')
_DOCSTRING_START = re.compile(r'^\s*[rRuUbB]*("""|\'\'\')')

_COMMENT_WIDTH = 100


@_check_types.do
def snippet_block(snippet: _snippets.Snippet) -> str:
    """The text to insert for *snippet*: its warnings as ``# NOTE:`` comment
    lines, then its code. No trailing newline."""
    lines: list[str] = []

    for warning in snippet.warnings:
        wrapped = textwrap.wrap(warning, width=_COMMENT_WIDTH - len('# NOTE: '))
        for number, text in enumerate(wrapped):
            if number == 0:
                lines.append('# NOTE: ' + text)
            else:
                lines.append('#       ' + text)

    lines.append(snippet.code)
    return '\n'.join(lines)


@_check_types.do
def missing_imports(script: str, imports: list[str]) -> list[str]:
    """The lines of *imports* the script does not already contain, in the
    order given and without repeats."""
    present = {line.strip() for line in script.split('\n')}
    missing: list[str] = []

    for line in imports:
        if line.strip() not in present and line not in missing:
            missing.append(line)

    return missing


@_check_types.do
def import_position(script: str) -> int:
    """The line index (0-based) at which new imports belong: right after
    the script's last leading import, or if it has none, after the opening
    comments and docstring."""
    if not script.strip():
        return 0

    lines = script.split('\n')
    index = _skip_header(lines)

    last_import = -1
    scan = index
    while scan < len(lines):
        stripped = lines[scan].strip()
        if _IMPORT_LINE.match(stripped):
            last_import = scan
        elif stripped and not stripped.startswith('#'):
            break

        scan += 1

    if last_import != -1:
        return last_import + 1

    return index


@_check_types.do
def import_text(script: str, imports: list[str]) -> str:
    """Text to insert at :func:`import_position` to add the missing
    *imports* (empty when there is nothing to add). Ends with a newline and,
    when the script has no imports yet, a blank line to set them off."""
    wanted = missing_imports(script, imports)
    if not wanted:
        return ''

    text = '\n'.join(wanted) + '\n'

    lines = script.split('\n')
    position = import_position(script)
    already_has_imports = position > 0 and _IMPORT_LINE.match(lines[position - 1].strip()) is not None
    following_is_code = position < len(lines) and lines[position].strip() != ''

    if not already_has_imports and following_is_code:
        text += '\n'

    return text


@_check_types.do
def _skip_header(lines: list[str]) -> int:
    """Index of the first line after any shebang, leading comments and
    module docstring."""
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped == '' or stripped.startswith('#'):
            index += 1
            continue

        found = _DOCSTRING_START.match(lines[index])
        if found is None:
            return index

        quote = found.group(1)
        rest = lines[index][found.end():]
        if quote in rest:
            return index + 1

        index += 1
        while index < len(lines):
            if quote in lines[index]:
                return index + 1

            index += 1

        return len(lines)

    return index
