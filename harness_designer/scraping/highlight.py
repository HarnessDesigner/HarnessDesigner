# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Syntax highlighting for large read-only text, computed in one pass.

``ui/widgets/code_editor_ctrl.py`` re-lexes the whole document for every
line it paints, which is fine for a short script and unusable for a 500 KB
page. This lexes the text once, off the GUI thread if the caller likes, and
returns plain data -- per display line, which column ranges get which
style -- that a ``QSyntaxHighlighter`` can apply in constant time per line.
No Qt in here.
"""

from pygments.lexers.data import JsonLexer
from pygments.lexers.html import HtmlLexer, XmlLexer
from pygments.styles import get_style_by_name

from .. import check_types as _check_types

STYLE_NAME = 'monokai'

# Past this size the text is shown unhighlighted: the lexer is pure Python.
MAX_HIGHLIGHT_CHARS = 3_000_000

# (color as 'rrggbb' or None, bold, italic, underline)
Style = tuple[str | None, bool, bool, bool]

# column, length, style
Span = tuple[int, int, Style]

_LEXERS = {'html': HtmlLexer, 'xml': XmlLexer, 'json': JsonLexer}


@_check_types.do
def highlight_spans(text: str, kind: str) -> list[list[Span]]:
    """Styled column ranges for every line of *text*.

    :param kind: ``'html'``, ``'xml'`` or ``'json'``; anything else (or a
        text past :data:`MAX_HIGHLIGHT_CHARS`) gives no spans at all.
    :return: One list of spans per line (``text.split('\\n')``).
    """
    line_count = text.count('\n') + 1
    lines: list[list[Span]] = [[] for _ in range(line_count)]

    lexer_class = _LEXERS.get(kind)
    if lexer_class is None or len(text) > MAX_HIGHLIGHT_CHARS:
        return lines

    style = get_style_by_name(STYLE_NAME)
    cache: dict[object, Style | None] = {}
    line_number = 0
    column = 0

    for token_type, value in lexer_class().get_tokens(text):
        if token_type in cache:
            token_style = cache[token_type]
        else:
            token_style = _style_for(style, token_type)
            cache[token_type] = token_style

        pieces = value.split('\n')
        for index, piece in enumerate(pieces):
            if index > 0:
                line_number += 1
                column = 0

            if piece and token_style is not None and line_number < line_count:
                lines[line_number].append((column, len(piece), token_style))

            column += len(piece)

    return lines


@_check_types.do
def _style_for(style: object, token_type: object) -> Style | None:
    entry = style.style_for_token(token_type)
    color = entry['color'] or None
    bold = bool(entry['bold'])
    italic = bool(entry['italic'])
    underline = bool(entry['underline'])

    if color is None and not (bold or italic or underline):
        return None

    return color, bold, italic, underline
