# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Turns a selection in a document string (page source, an XHR text
response, ...) into Python code that finds the same text again.

Every function takes the document and the selection as character offsets
``document[start:end]`` and returns a :class:`Snippet`. The generated code
refers to the document through a variable (``html`` by default) that the
script is expected to already define.

The code a snippet contains must reproduce the selection when it is run
against the same document -- the tests under ``tests/scraping`` check every
action by executing its output. When the selected text appears more than
once, the code is not allowed to quietly pick a different occurrence: the
marker it searches for is grown outward until the first occurrence of the
marker is the selected one, and the snippet says so in ``warnings``.
"""

import re
from dataclasses import dataclass, field

from .. import check_types as _check_types

# Longest stretch of context, in characters, a marker or a regex is allowed
# to grow to before the snippet warns that the page repeats this structure.
_MAX_CONTEXT = 300

# Longest start or end tag a marker may be stretched across to avoid
# stopping inside it.
_MAX_TAG = 200

# A marker is written inline when it is this short and on one line,
# otherwise it gets its own variable so the statement stays readable.
_INLINE_LITERAL_LIMIT = 60

_IDENTIFIER = re.compile(r'[A-Za-z_]\w*')
_TOKEN = re.compile(r'\s+|\w+|[^\w\s]')
_WORD_CHAR = re.compile(r'\w')


@dataclass
class Snippet:
    """Code ready to be inserted into the script editor.

    :ivar code: Python source, no trailing newline.
    :ivar description: One line for the menu / status bar.
    :ivar imports: Import lines the code needs (``import re`` ...).
    :ivar warnings: Things the user should know (ambiguous selection,
        a long marker, a selector that could not be verified).
    :ivar result_name: The variable the code defines, if it defines one.
    """

    code: str
    description: str
    imports: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    result_name: str = ''


class Names:
    """Hands out variable names that do not collide with anything already
    in the script (or with names this snippet handed out earlier)."""

    @_check_types.do
    def __init__(self, taken: set[str] | None = None) -> None:
        self._taken: set[str] = set()
        if taken is not None:
            self._taken.update(taken)

    @_check_types.do
    def new(self, base: str) -> str:
        name = free_name(base, self._taken)
        self._taken.add(name)
        return name


@_check_types.do
def taken_names(script: str) -> set[str]:
    """Every identifier appearing anywhere in *script*.

    A plain token scan rather than a parse, so it still works while the
    script is half typed and would not compile.
    """
    return set(_IDENTIFIER.findall(script))


@_check_types.do
def free_name(base: str, taken: set[str]) -> str:
    if base not in taken:
        return base

    number = 2
    while f'{base}_{number}' in taken:
        number += 1

    return f'{base}_{number}'


@_check_types.do
def trim_selection(document: str, start: int, end: int) -> tuple[int, int]:
    """Drop whitespace from both ends of a selection.

    Users select ``' Price: '`` with the stray spaces more often than not;
    a marker with leading blanks is exactly the kind that stops matching
    when the page's indentation changes.
    """
    while start < end and document[start].isspace():
        start += 1

    while end > start and document[end - 1].isspace():
        end -= 1

    return start, end


@_check_types.do
def python_literal(text: str) -> str:
    """Python source for the string *text* (always a valid literal)."""
    return repr(text)


@_check_types.do
def split_at_every(document: str, start: int, end: int, *, doc_name: str = 'html',
                   taken: set[str] | None = None) -> Snippet:
    """``parts = html.split('selection')`` -- the document cut at every
    occurrence of the selected text."""
    selected = _selected_text(document, start, end)
    names = Names(taken)
    result = names.new('parts')
    count = document.count(selected)

    lines: list[str] = []
    marker = _literal_or_variable(selected, 'separator', names, lines)
    lines.append(f'{result} = {doc_name}.split({marker})')

    return Snippet(
        code='\n'.join(lines),
        description=f'Split the document at the selected text ({count} occurrence(s) -> {count + 1} parts)',
        warnings=[],
        result_name=result)


@_check_types.do
def text_after(document: str, start: int, end: int, *, doc_name: str = 'html',
               taken: set[str] | None = None) -> Snippet:
    """Everything in the document after the selected text."""
    selected = _selected_text(document, start, end)
    names = Names(taken)
    result = names.new('after')

    anchor, grown = _anchor_ending_at(document, start, end)
    warnings = _anchor_warnings(document, selected, grown, 'left')

    lines: list[str] = []
    marker = _literal_or_variable(anchor, 'marker', names, lines)
    lines.append(f'{result} = {doc_name}.partition({marker})[2]')

    return Snippet(
        code='\n'.join(lines),
        description='Take the text after the selection',
        warnings=warnings,
        result_name=result)


@_check_types.do
def text_before(document: str, start: int, end: int, *, doc_name: str = 'html',
                taken: set[str] | None = None) -> Snippet:
    """Everything in the document before the selected text."""
    selected = _selected_text(document, start, end)
    names = Names(taken)
    result = names.new('before')

    anchor, grown = _anchor_starting_at(document, start, end, 0)
    warnings = _anchor_warnings(document, selected, grown, 'right')

    lines: list[str] = []
    marker = _literal_or_variable(anchor, 'marker', names, lines)
    lines.append(f'{result} = {doc_name}.partition({marker})[0]')

    return Snippet(
        code='\n'.join(lines),
        description='Take the text before the selection',
        warnings=warnings,
        result_name=result)


@_check_types.do
def find_position(document: str, start: int, end: int, *, at_end: bool = False,
                  doc_name: str = 'html', taken: set[str] | None = None) -> Snippet:
    """The index of the selected text (its start, or with *at_end* the
    index just past it)."""
    selected = _selected_text(document, start, end)
    names = Names(taken)
    lines: list[str] = []

    if at_end:
        result = names.new('end')
        anchor, grown = _anchor_ending_at(document, start, end)
        side = 'left'
        marker = _literal_or_variable(anchor, 'marker', names, lines)
        lines.append(f'{result} = {doc_name}.find({marker}) + len({marker})')
        description = 'Find the index just past the selection'
    else:
        result = names.new('position')
        anchor, grown = _anchor_starting_at(document, start, end, 0)
        side = 'right'
        marker = _literal_or_variable(anchor, 'marker', names, lines)
        lines.append(f'{result} = {doc_name}.find({marker})')
        description = 'Find the index of the selection'

    return Snippet(
        code='\n'.join(lines),
        description=description,
        warnings=_anchor_warnings(document, selected, grown, side),
        result_name=result)


@_check_types.do
def between(document: str, first_start: int, first_end: int, second_start: int, second_end: int,
            *, doc_name: str = 'html', taken: set[str] | None = None) -> Snippet:
    """The text between two selections: after the first, up to the second."""
    if first_end > second_start:
        raise ValueError('the second selection must come after the first')

    first = _selected_text(document, first_start, first_end)
    second = _selected_text(document, second_start, second_end)
    names = Names(taken)
    result = names.new('value')

    first_anchor, first_grown = _anchor_ending_at(document, first_start, first_end)
    second_anchor, second_grown = _anchor_starting_at(document, second_start, second_end, first_end)

    warnings = _anchor_warnings(document, first, first_grown, 'left')
    warnings.extend(_anchor_warnings(document, second, second_grown, 'right'))

    lines: list[str] = []
    start_marker = _literal_or_variable(first_anchor, 'start_marker', names, lines)
    end_marker = _literal_or_variable(second_anchor, 'end_marker', names, lines)
    lines.append(f'{result} = {doc_name}.partition({start_marker})[2].partition({end_marker})[0]')

    return Snippet(
        code='\n'.join(lines),
        description='Take the text between the two selections',
        warnings=warnings,
        result_name=result)


@_check_types.do
def regex_capture(document: str, start: int, end: int, *, doc_name: str = 'html',
                  taken: set[str] | None = None) -> Snippet:
    """``re.search`` with the selection as the capture group and just enough
    text on each side to make the first match land on this selection."""
    selected = _selected_text(document, start, end)
    names = Names(taken)
    match_name = names.new('match')
    result = names.new('value')

    prefix, suffix = _unique_context(document, start, end)
    pattern = _context_pattern(prefix, suffix)

    warnings = _pattern_warnings(document, pattern, start, end, selected)
    if len(prefix) > _MAX_CONTEXT or len(suffix) > _MAX_CONTEXT:
        warnings.append('The page repeats this structure, so the pattern needed a lot of surrounding text '
                        'to tell this one apart -- consider "All matches" or a CSS selector instead.')

    lines = [
        f'{match_name} = re.search({_regex_literal(pattern)}, {doc_name}, re.S)',
        f'{result} = {match_name}.group(1)']

    return Snippet(
        code='\n'.join(lines),
        description='Capture the selection with a regular expression',
        imports=['import re'],
        warnings=warnings,
        result_name=result)


@_check_types.do
def regex_all(document: str, start: int, end: int, *, doc_name: str = 'html',
              taken: set[str] | None = None) -> Snippet:
    """``re.findall`` for every piece of text that sits in the same markup
    as the selection (the tag before it and the tag after it)."""
    selected = _selected_text(document, start, end)
    names = Names(taken)
    result = names.new('values')

    prefix, suffix = _markup_context(document, start, end)
    pattern = _context_pattern(prefix, suffix)

    warnings = _pattern_warnings(document, pattern, start, end, selected, expect_unique=False)
    count = len(re.findall(pattern, document, re.S))

    lines = [f'{result} = re.findall({_regex_literal(pattern)}, {doc_name}, re.S)']

    return Snippet(
        code='\n'.join(lines),
        description=f'Find every piece of text in the same markup as the selection ({count} match(es))',
        imports=['import re'],
        warnings=warnings,
        result_name=result)


@_check_types.do
def _selected_text(document: str, start: int, end: int) -> str:
    if not 0 <= start < end <= len(document):
        raise ValueError(f'selection {start}:{end} is not inside a document of {len(document)} characters')

    return document[start:end]


@_check_types.do
def _literal_or_variable(text: str, base_name: str, names: Names, lines: list[str]) -> str:
    """The expression to use for *text* inside a statement.

    Short single-line text goes inline as a literal. Anything else is
    assigned to its own variable first (one quoted line per source line, so
    it reads like the document does), and the variable's name is returned.
    """
    if '\n' not in text and len(text) <= _INLINE_LITERAL_LIMIT:
        return python_literal(text)

    name = names.new(base_name)
    pieces = text.splitlines(keepends=True)

    if len(pieces) <= 1:
        lines.append(f'{name} = {python_literal(text)}')
        return name

    lines.append(f'{name} = (')
    for piece in pieces:
        lines.append(f'    {python_literal(piece)}')
    lines.append(')')

    return name


@_check_types.do
def _anchor_warnings(document: str, selected: str, grown: int, side: str) -> list[str]:
    warnings: list[str] = []
    count = document.count(selected)

    if grown > 0:
        warnings.append(
            f'The selected text appears {count} times, so the marker was extended {grown} character(s) '
            f'to the {side} to match only the one you selected.')
    elif count > 1:
        warnings.append(
            f'The selected text appears {count} times in the document; the code uses the first one.')

    if grown > _MAX_CONTEXT:
        warnings.append('The marker had to grow very long to be unique, which usually means the page '
                        'repeats this structure -- it may stop matching when the page changes.')

    return warnings


@_check_types.do
def _anchor_ending_at(document: str, start: int, end: int) -> tuple[str, int]:
    """The shortest text that ends exactly at *end* and whose first
    occurrence in the document is the one at the selection.

    Searching for it and taking what follows is then the same as taking
    what follows the selection. Returns the text and how many characters
    were added to the left of the selection to get there.
    """
    grown = 0
    while True:
        anchor_start = start - grown
        anchor = document[anchor_start:end]
        if document.find(anchor) == anchor_start:
            break

        grown += 1

    # Growing a unique anchor further keeps it unique; use that to avoid
    # starting the marker in the middle of a word.
    while grown > 0 and anchor_start > 0 and _is_word_boundary_cut(document, anchor_start):
        anchor_start -= 1
        grown += 1

    return document[anchor_start:end], grown


@_check_types.do
def _anchor_starting_at(document: str, start: int, end: int, search_from: int) -> tuple[str, int]:
    """The shortest text that starts exactly at *start* and whose first
    occurrence at or after *search_from* is the one at the selection.

    Returns the text and how many characters were added to the right of
    the selection.
    """
    grown = 0
    while True:
        anchor_end = end + grown
        anchor = document[start:anchor_end]
        if document.find(anchor, search_from) == start:
            break

        grown += 1

    while grown > 0 and anchor_end < len(document) and _is_word_boundary_cut(document, anchor_end):
        anchor_end += 1
        grown += 1

    return document[start:anchor_end], grown


@_check_types.do
def _is_word_boundary_cut(document: str, position: int) -> bool:
    """True when a cut at *position* would split a word in two."""
    if position <= 0 or position >= len(document):
        return False

    return bool(_WORD_CHAR.match(document[position - 1]) and _WORD_CHAR.match(document[position]))


@_check_types.do
def _left_tokens(document: str, start: int, max_chars: int) -> list[str]:
    """Tokens (words, whitespace runs, single symbols) before *start*,
    nearest first, from at most *max_chars* characters back."""
    window_start = max(0, start - max_chars)
    tokens = _TOKEN.findall(document[window_start:start])

    # The window may start in the middle of a token.
    if window_start > 0 and tokens:
        tokens = tokens[1:]

    tokens.reverse()
    return tokens


@_check_types.do
def _right_tokens(document: str, end: int, max_chars: int) -> list[str]:
    """Tokens after *end*, nearest first, from at most *max_chars* on."""
    window_end = min(len(document), end + max_chars)
    tokens = _TOKEN.findall(document[end:window_end])

    if window_end < len(document) and tokens:
        tokens = tokens[:-1]

    return tokens


@_check_types.do
def _unique_context(document: str, start: int, end: int) -> tuple[str, str]:
    """Text before and after the selection such that
    ``prefix(.*?)suffix`` first matches exactly the selection.

    The prefix grows (token by token) until its first occurrence in the
    document is the one just before the selection; the suffix then grows
    until the first place it occurs after the prefix is just after the
    selection.
    """
    left = _left_tokens(document, start, _MAX_CONTEXT * 2)
    prefix = ''
    prefix_tokens = 0

    while True:
        prefix_start = start - len(prefix)
        if document.find(prefix) == prefix_start:
            break

        if prefix_tokens >= len(left):
            break

        prefix_tokens += 1
        prefix = ''.join(reversed(left[:prefix_tokens]))

    right = _right_tokens(document, end, _MAX_CONTEXT * 2)
    suffix = ''
    suffix_tokens = 0

    while True:
        if document.find(suffix, start) == end:
            break

        if suffix_tokens >= len(right):
            break

        suffix_tokens += 1
        suffix = ''.join(right[:suffix_tokens])

    # Never end a marker half way through a tag: `/2">` reads better, and
    # survives a changed attribute order better, as the whole `<a href="/p/2">`.
    suffix = document[end:_snap_to_tag_end(document, end + len(suffix))]
    prefix = _snapped_prefix(document, start, prefix)

    # The searches above compare text exactly; the pattern lets any run of
    # whitespace match any other. Confirm with the real pattern, and keep
    # adding prefix until it agrees.
    while prefix_tokens < len(left):
        match = re.search(_context_pattern(prefix, suffix), document, re.S)
        if match is not None and match.span(1) == (start, end):
            break

        prefix_tokens += 1
        prefix = _snapped_prefix(document, start, ''.join(reversed(left[:prefix_tokens])))

    return prefix, suffix


@_check_types.do
def _snapped_prefix(document: str, start: int, prefix: str) -> str:
    """*prefix* (the text just before *start*), extended left to the
    beginning of the tag it starts inside, if it starts inside one."""
    prefix_start = start - len(prefix)
    tag_open = document.rfind('<', 0, prefix_start + 1)
    tag_close = document.rfind('>', 0, prefix_start)

    if tag_open > tag_close and prefix_start - tag_open <= _MAX_TAG:
        prefix_start = tag_open

    return document[prefix_start:start]


@_check_types.do
def _snap_to_tag_end(document: str, position: int) -> int:
    """*position*, moved right to just past the ``>`` of the tag it is
    inside, if it is inside one."""
    last_open = document.rfind('<', 0, position)
    last_close = document.rfind('>', 0, position)

    if last_open > last_close:
        close = document.find('>', position)
        if close != -1 and close + 1 - position <= _MAX_TAG:
            return close + 1

    return position


@_check_types.do
def _markup_context(document: str, start: int, end: int) -> tuple[str, str]:
    """The tag just before the selection and the one just after it, when
    the selection is the text between two tags; otherwise a few tokens
    either side."""
    prefix = ''
    suffix = ''

    tag_close = document.rfind('>', 0, start)
    if tag_close != -1 and '<' not in document[tag_close + 1:start]:
        tag_open = document.rfind('<', 0, tag_close)
        if tag_open != -1 and start - tag_open <= _MAX_CONTEXT:
            prefix = document[tag_open:start]

    next_open = document.find('<', end)
    if next_open != -1 and '>' not in document[end:next_open]:
        next_close = document.find('>', next_open)
        if next_close != -1 and next_close + 1 - end <= _MAX_CONTEXT:
            suffix = document[end:next_close + 1]

    if prefix and suffix:
        return prefix, suffix

    left = _left_tokens(document, start, 60)
    right = _right_tokens(document, end, 60)
    return ''.join(reversed(left[:3])), ''.join(right[:3])


@_check_types.do
def _context_pattern(prefix: str, suffix: str) -> str:
    """Regex source: the prefix, a lazy capture group, the suffix."""
    if suffix:
        capture = '(.*?)'
    else:
        capture = '(.*)'

    return _literal_pattern(prefix) + capture + _literal_pattern(suffix)


@_check_types.do
def _literal_pattern(text: str) -> str:
    """Regex matching *text* literally, except that any run of whitespace in
    it matches any run of whitespace -- so a re-indented page still matches."""
    out: list[str] = []
    for piece in re.split(r'(\s+)', text):
        if not piece:
            continue

        if piece.isspace():
            out.append(r'\s+')
        else:
            out.append(re.escape(piece))

    return ''.join(out)


@_check_types.do
def _regex_literal(pattern: str) -> str:
    """Python source for the pattern: a raw string when that is safe."""
    can_be_raw = "'" not in pattern and '\n' not in pattern and not pattern.endswith('\\')
    if can_be_raw:
        return "r'" + pattern + "'"

    return python_literal(pattern)


@_check_types.do
def _pattern_warnings(document: str, pattern: str, start: int, end: int, selected: str,
                      expect_unique: bool = True) -> list[str]:
    """Run the pattern against the document and report anything that does
    not hold up."""
    warnings: list[str] = []
    matches = list(re.finditer(pattern, document, re.S))

    if not matches:
        warnings.append('The pattern does not match the document it was built from.')
        return warnings

    if expect_unique:
        first = matches[0]
        if first.span(1) != (start, end):
            warnings.append('The first match of the pattern is not the text you selected.')
        elif len(matches) > 1:
            warnings.append(f'The pattern matches {len(matches)} places; re.search returns the first, '
                            'which is the one you selected.')

        return warnings

    spans = [match.span(1) for match in matches]
    if (start, end) not in spans:
        warnings.append('The pattern does not match the text you selected.')

    return warnings
