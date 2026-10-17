# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""A plain Python code editor: line numbers, syntax highlighting, and
auto-indent -- the host widget for scraper scripts (point-and-click
injected lines, or hand-written/AI-drafted ones) under ``scraping/``.
"""

from pygments.lexers.python import PythonLexer
from pygments.styles import get_style_by_name
from PySide6 import QtCore, QtGui, QtWidgets

from ... import check_types as _check_types

_INDENT = '    '

# Monokai rather than the editor's own hand-picked palette -- Pygments
# already ships a complete, well-tested color mapping for every token
# type its lexers produce (f-strings, raw/byte-string prefixes, decorators,
# magic methods, ...), far more thorough than re-picking a handful of
# categories by hand would be.
_STYLE_NAME = 'monokai'


class _PygmentsHighlighter(QtGui.QSyntaxHighlighter):
    """Python syntax highlighting driven by Pygments' own lexer + style,
    not a hand-rolled regex/keyword-list approximation of one.

    ``QSyntaxHighlighter`` calls ``highlightBlock`` once per line, but
    Pygments' lexer needs the whole document for context (a multi-line
    docstring has to be tokenized as one spanning token to come out right)
    -- so the whole document is re-lexed on every call. That's O(n^2) over
    a full-document repaint, but Pygments is fast and these are short,
    hand-authored scraper scripts, not large source files -- not worth
    the complexity of caching against ``QTextDocument`` edit state, which
    turns out not to reliably reflect "the text is fully settled" at the
    exact moment ``highlightBlock`` fires during a bulk text replace.
    """

    @_check_types.do
    def __init__(self, document: QtGui.QTextDocument) -> None:
        super().__init__(document)

        self._lexer = PythonLexer()
        self._style = get_style_by_name(_STYLE_NAME)
        self._formats: dict[object, QtGui.QTextCharFormat] = {}

    @_check_types.do
    def highlightBlock(self, text: str) -> None:  # NOQA -- Qt's own camelCase override
        block_start = self.currentBlock().position()
        block_end = block_start + len(text)

        offset = 0
        for token_type, value in self._lexer.get_tokens(self.document().toPlainText()):
            token_start = offset
            token_end = offset + len(value)
            offset = token_end

            if token_end <= block_start:
                continue
            if token_start >= block_end:
                break

            overlap_start = max(token_start, block_start)
            overlap_end = min(token_end, block_end)
            if overlap_end <= overlap_start:
                continue

            self.setFormat(overlap_start - block_start, overlap_end - overlap_start, self._format_for(token_type))

    def _format_for(self, token_type) -> QtGui.QTextCharFormat:
        cached = self._formats.get(token_type)
        if cached is not None:
            return cached

        style_entry = self._style.style_for_token(token_type)
        text_format = QtGui.QTextCharFormat()
        if style_entry['color']:
            text_format.setForeground(QtGui.QColor(f"#{style_entry['color']}"))
        if style_entry['bold']:
            text_format.setFontWeight(QtGui.QFont.Weight.Bold)
        if style_entry['italic']:
            text_format.setFontItalic(True)
        if style_entry['underline']:
            text_format.setFontUnderline(True)

        self._formats[token_type] = text_format
        return text_format


class _LineNumberArea(QtWidgets.QWidget):
    @_check_types.do
    def __init__(self, editor: 'CodeEditorCtrl') -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QtCore.QSize:  # NOQA -- Qt's own camelCase override
        return QtCore.QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # NOQA -- Qt's own camelCase override
        self._editor.paint_line_numbers(event)


class CodeEditorCtrl(QtWidgets.QPlainTextEdit):
    """Plain-Python code editor: line numbers, syntax highlighting, and
    auto-indent (Enter copies the current line's indent, adding one more
    level after a line ending in ``:``; Tab/Shift+Tab indent or dedent the
    current line or selection by one level).
    """

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        font = QtGui.QFont('Consolas', 11)
        font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setTabChangesFocus(False)
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)

        self.setStyleSheet(
            'QPlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; '
            'border: 1px solid #3c3c3c; selection-background-color: #264f78; }'
        )

        self._highlighter = _PygmentsHighlighter(self.document())
        self._line_number_area = _LineNumberArea(self)

        self.blockCountChanged.connect(self._on_block_count_changed)
        self.updateRequest.connect(self._on_update_request)
        self.cursorPositionChanged.connect(self._highlight_current_line)

        self._on_block_count_changed(0)
        self._highlight_current_line()

    def line_number_area_width(self) -> int:
        digits = max(1, len(str(max(1, self.blockCount()))))
        return 10 + self.fontMetrics().horizontalAdvance('9') * digits

    def paint_line_numbers(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QtGui.QColor('#252526'))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QtGui.QColor('#858585'))
                painter.drawText(
                    0, top, self._line_number_area.width() - 6, self.fontMetrics().height(),
                    QtCore.Qt.AlignmentFlag.AlignRight, str(block_number + 1))

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # NOQA -- Qt's own camelCase override
        super().resizeEvent(event)
        contents_rect = self.contentsRect()
        self._line_number_area.setGeometry(
            QtCore.QRect(contents_rect.left(), contents_rect.top(),
                         self.line_number_area_width(), contents_rect.height()))

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:  # NOQA -- Qt's own camelCase override
        key = event.key()
        has_selection = self.textCursor().hasSelection()

        if key == QtCore.Qt.Key.Key_Tab and not has_selection:
            self.textCursor().insertText(_INDENT)
            return

        if key == QtCore.Qt.Key.Key_Tab and has_selection:
            self._indent_selection()
            return

        if key == QtCore.Qt.Key.Key_Backtab:
            self._dedent_selection()
            return

        if key in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            self._insert_auto_indented_newline()
            return

        super().keyPressEvent(event)

    def _insert_auto_indented_newline(self) -> None:
        cursor = self.textCursor()
        current_line = cursor.block().text()
        leading_whitespace = current_line[:len(current_line) - len(current_line.lstrip(' '))]

        new_indent = leading_whitespace
        if current_line.rstrip().endswith(':'):
            new_indent += _INDENT

        cursor.insertText('\n' + new_indent)

    def _indent_selection(self) -> None:
        cursor = self.textCursor()
        start, end = sorted((cursor.selectionStart(), cursor.selectionEnd()))

        cursor.setPosition(start)
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
        cursor.setPosition(end, QtGui.QTextCursor.MoveMode.KeepAnchor)
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfBlock, QtGui.QTextCursor.MoveMode.KeepAnchor)

        selected_lines = cursor.selection().toPlainText().split('\n')
        indented_lines = [_INDENT + line for line in selected_lines]
        cursor.insertText('\n'.join(indented_lines))

    def _dedent_selection(self) -> None:
        cursor = self.textCursor()
        start, end = sorted((cursor.selectionStart(), cursor.selectionEnd()))

        cursor.setPosition(start)
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
        cursor.setPosition(end, QtGui.QTextCursor.MoveMode.KeepAnchor)
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfBlock, QtGui.QTextCursor.MoveMode.KeepAnchor)

        selected_lines = cursor.selection().toPlainText().split('\n')
        dedented_lines = [_dedent_one_line(line) for line in selected_lines]
        cursor.insertText('\n'.join(dedented_lines))

    def _on_block_count_changed(self, _new_block_count: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _on_update_request(self, rect: QtCore.QRect, dy: int) -> None:
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self._on_block_count_changed(0)

    def _highlight_current_line(self) -> None:
        selection = QtWidgets.QTextEdit.ExtraSelection()
        selection.format.setBackground(QtGui.QColor('#2a2d2e'))
        selection.format.setProperty(QtGui.QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])


def _dedent_one_line(line: str) -> str:
    removed = 0
    while removed < len(_INDENT) and removed < len(line) and line[removed] == ' ':
        removed += 1
    return line[removed:]
