# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""A document prepared for a text widget, with a map back to the original.

Minified pages are one line of several hundred kilobytes, which a
``QPlainTextEdit`` cannot lay out. So the viewer shows a copy with extra
line breaks added, and positions in that copy are translated back to
offsets in the *original* text before any code is generated from them -- a
generated marker must match the real document, never the prettified one.

Two things in the original do not appear in the displayed text one-to-one:

* the line breaks added here (they have no original character), and
* the ``\\r`` of a ``\\r\\n`` pair (Qt keeps only the ``\\n``, so offsets
  taken from the widget would otherwise drift by one per line).
"""

from array import array

from .. import check_types as _check_types

DEFAULT_WIDTH = 160


class SoftWrap:
    """*text* as it should be displayed, plus the position translation.

    :ivar display: The text to put in the widget.
    """

    @_check_types.do
    def __init__(self, text: str, width: int = DEFAULT_WIDTH) -> None:
        if width < 20:
            raise ValueError('width must be at least 20 characters')

        self.original = text
        self.display = ''

        # start_map[d]: the original offset a selection starting at display
        # position d begins at. end_map[d]: where one ending at d ends.
        self._start_map = array('I')
        self._end_map = array('I', [0])

        pieces: list[str] = []
        original_index = 0

        for line in text.split('\n'):
            carriage_return = line.endswith('\r')
            if carriage_return:
                line = line[:-1]

            original_index = self._add_line(pieces, line, original_index, width)

            if carriage_return:
                original_index += 1  # the '\r', which is not displayed

            pieces.append('\n')
            self._start_map.append(original_index)
            self._end_map.append(original_index + 1)
            original_index += 1  # the '\n' itself

        # The loop adds one '\n' too many: the last "line" has none after it.
        pieces.pop()
        self._start_map.pop()
        self._end_map.pop()

        self.display = ''.join(pieces)
        self._start_map.append(len(text))

    @_check_types.do
    def to_original(self, start: int, end: int) -> tuple[int, int]:
        """The original-text range for a selection of ``display[start:end]``."""
        return self._start_map[start], self._end_map[end]

    @_check_types.do
    def to_display(self, start: int, end: int) -> tuple[int, int]:
        """The display range covering the original range ``start:end``."""
        return self._display_start(start), self._display_end(end)

    @_check_types.do
    def _display_start(self, original: int) -> int:
        """Display position a selection starting at *original* begins at.

        Several display positions can map to the same original offset (an
        added break and the character after it): the last is the real
        character. An original offset with no display position at all (a
        removed ``\\r``) moves on to the next one.
        """
        low, high = 0, len(self._start_map)
        while low < high:
            middle = (low + high) // 2
            if self._start_map[middle] <= original:
                low = middle + 1
            else:
                high = middle

        if low > 0 and self._start_map[low - 1] == original:
            return low - 1

        return low

    @_check_types.do
    def _display_end(self, original: int) -> int:
        """Display position a selection ending at *original* ends at: the
        first one that maps there (so an added break is left out), or the
        one before when nothing does."""
        low, high = 0, len(self._end_map)
        while low < high:
            middle = (low + high) // 2
            if self._end_map[middle] < original:
                low = middle + 1
            else:
                high = middle

        if low < len(self._end_map) and self._end_map[low] == original:
            return low

        return max(0, low - 1)

    @_check_types.do
    def _add_line(self, pieces: list[str], line: str, original_index: int, width: int) -> int:
        """Append *line*, breaking it into display lines no longer than
        *width*; returns the original index just past it."""
        remaining = line
        while len(remaining) > width:
            cut = _best_cut(remaining, width)
            self._add_run(pieces, remaining[:cut], original_index)
            original_index += cut
            remaining = remaining[cut:]

            pieces.append('\n')
            self._start_map.append(original_index)  # the added break maps to where the text resumes
            self._end_map.append(original_index)

        self._add_run(pieces, remaining, original_index)
        return original_index + len(remaining)

    @_check_types.do
    def _add_run(self, pieces: list[str], text: str, original_index: int) -> None:
        """Append characters that map one-to-one onto the original."""
        if not text:
            return

        pieces.append(text)
        count = len(text)
        self._start_map.extend(range(original_index, original_index + count))
        self._end_map.extend(range(original_index + 1, original_index + count + 1))


@_check_types.do
def _best_cut(text: str, width: int) -> int:
    """Where to break *text* (longer than *width*): just after the last
    tag end or space in the first *width* characters, so the break falls
    between tags rather than inside one, else at *width*."""
    window = text[:width]
    floor = width // 2

    cut = window.rfind('>') + 1
    if cut >= floor:
        return cut

    cut = window.rfind(' ') + 1
    if cut >= floor:
        return cut

    return width
