# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Read-only, syntax-highlighted view of a document (page source, an XHR
text response) whose selections turn into code.

Select text, right-click, pick what to do with it. Every action comes from
:mod:`~harness_designer.scraping.snippets` / ``html_locate`` and works on
offsets into the ORIGINAL document: what is shown is a copy with extra line
breaks (see :mod:`~harness_designer.scraping.soft_wrap`), and the
selection is translated back before anything is generated.
"""

from collections.abc import Callable

import html as _html
import re

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from . import background as _background
from ..widgets import wrap_label as _wrap_label
from ...scraping import highlight as _highlight
from ...scraping import html_locate as _html_locate
from ...scraping import snippets as _snippets
from ...scraping import soft_wrap as _soft_wrap
from ... import check_types as _check_types

_STYLE_SHEET = (
    'QPlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3c3c3c; '
    'selection-background-color: #264f78; }')

_MARK_COLOR = QtGui.QColor('#6b5b00')
_FOUND_COLOR = QtGui.QColor('#264f78')

_MENU_PREVIEW_CHARS = 40


@_check_types.do
def _no_names() -> set[str]:
    return set()


class SpanHighlighter(QtGui.QSyntaxHighlighter):
    """Applies spans that were computed beforehand (see
    :func:`~harness_designer.scraping.highlight.highlight_spans`)."""

    @_check_types.do
    def __init__(self, document: QtGui.QTextDocument) -> None:
        super().__init__(document)
        self._lines: list[list[_highlight.Span]] = []
        self._formats: dict[_highlight.Style, QtGui.QTextCharFormat] = {}

    @_check_types.do
    def set_spans(self, lines: list[list[_highlight.Span]]) -> None:
        self._lines = lines
        self.rehighlight()

    @_check_types.do
    def highlightBlock(self, text: str) -> None:  # NOQA -- Qt's own camelCase override
        number = self.currentBlock().blockNumber()
        if number >= len(self._lines):
            return

        for column, length, style in self._lines[number]:
            self.setFormat(column, length, self._format_for(style))

    @_check_types.do
    def _format_for(self, style: _highlight.Style) -> QtGui.QTextCharFormat:
        cached = self._formats.get(style)
        if cached is not None:
            return cached

        color, bold, italic, underline = style
        text_format = QtGui.QTextCharFormat()
        if color:
            text_format.setForeground(QtGui.QColor(f'#{color}'))
        if bold:
            text_format.setFontWeight(QtGui.QFont.Weight.Bold)
        if italic:
            text_format.setFontItalic(True)
        if underline:
            text_format.setFontUnderline(True)

        self._formats[style] = text_format
        return text_format


class _SourceEdit(QtWidgets.QPlainTextEdit):
    contextMenuRequested = QtCore.Signal(QtCore.QPoint)

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        font = QtGui.QFont('Consolas', 10)
        font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setReadOnly(True)
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self.setStyleSheet(_STYLE_SHEET)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:  # NOQA -- Qt's own camelCase override
        self.contextMenuRequested.emit(event.globalPos())


class SourceViewer(QtWidgets.QWidget):
    """The Source tab.

    :ivar snippetReady: A snippet was produced (``Snippet``). If the
        script does not yet define this document's variable, the snippet
        that loads it is emitted first.
    :ivar messageRaised: Something the user should be told (``str``).
    """

    snippetReady = QtCore.Signal(object)
    messageRaised = QtCore.Signal(str)

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = ''
        self._kind = 'text'
        self._doc_name = 'html'
        self._wrap = _soft_wrap.SoftWrap('')
        self._located: _html_locate.LocatedDocument | None = None
        self._mark: tuple[int, int] | None = None
        self._found: tuple[int, int] | None = None
        self._generation = 0
        self._jobs: list[_background.BackgroundJob] = []
        self._taken_provider: Callable[[], set[str]] = _no_names
        self._preamble: Callable[[set[str]], _snippets.Snippet | None] | None = None

        self._edit = _SourceEdit(self)
        self._highlighter = SpanHighlighter(self._edit.document())
        self._status = _wrap_label.WrapLabel('', self, wrap=False)
        self._status.setStyleSheet('color: gray;')

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self._edit, 1)
        layout.addWidget(self._status)

        self._edit.contextMenuRequested.connect(self._show_menu)
        self._update_status()

    # -- public ------------------------------------------------------------

    @_check_types.do
    def set_taken_provider(self, provider: Callable[[], set[str]]) -> None:
        """Where to get the names the script already uses."""
        self._taken_provider = provider

    @_check_types.do
    def set_preamble(self, preamble: Callable[[set[str]], _snippets.Snippet | None] | None) -> None:
        """A function making the snippet that defines this document's
        variable, used when the script does not have it yet."""
        self._preamble = preamble

    @_check_types.do
    def set_document(self, text: str, kind: str = 'html', doc_name: str = 'html') -> None:
        """Show *text*. *kind* is ``'html'``, ``'xml'``, ``'json'`` or
        ``'text'``; *doc_name* is the variable generated code reads it from."""
        self._generation += 1
        generation = self._generation

        self._text = text
        self._kind = kind
        self._doc_name = doc_name
        self._wrap = _soft_wrap.SoftWrap(text)
        self._located = None
        self._mark = None
        self._found = None

        self._highlighter.set_spans([])
        self._edit.setPlainText(self._wrap.display)
        self._update_status()

        display = self._wrap.display
        self._start_job(lambda: _highlight.highlight_spans(display, kind),
                        lambda spans: self._spans_ready(generation, spans))

        if kind == 'html' and text:
            self._start_job(lambda: _html_locate.LocatedDocument(text),
                            lambda located: self._located_ready(generation, located))

    @_check_types.do
    def document_text(self) -> str:
        return self._text

    @_check_types.do
    def selection(self) -> tuple[int, int] | None:
        """The selected range as offsets into the original document, with
        surrounding whitespace removed; ``None`` when nothing is selected."""
        cursor = self._edit.textCursor()
        if not cursor.hasSelection():
            return None

        start, end = sorted((cursor.selectionStart(), cursor.selectionEnd()))
        original_start, original_end = self._wrap.to_original(start, end)
        original_start, original_end = _snippets.trim_selection(self._text, original_start, original_end)
        if original_end <= original_start:
            return None

        return original_start, original_end

    @_check_types.do
    def select_range(self, start: int, end: int) -> None:
        """Select ``document[start:end]`` (offsets into the original text)."""
        display_start, display_end = self._wrap.to_display(start, end)
        cursor = self._edit.textCursor()
        cursor.setPosition(display_start)
        cursor.setPosition(display_end, QtGui.QTextCursor.MoveMode.KeepAnchor)
        self._edit.setTextCursor(cursor)

    @_check_types.do
    def displayed_text(self) -> str:
        """What the widget actually shows (the document with added breaks)."""
        return self._edit.toPlainText()

    @_check_types.do
    def select_text(self, text: str) -> bool:
        """Find *text* in the document and select it; whitespace and HTML
        escaping may differ (text copied from a rendered page). Returns
        whether it was found."""
        found = self._find(text)
        if found is None:
            return False

        self.select_range(*found)
        self._edit.centerCursor()
        self._edit.setFocus()
        return True

    # -- menu --------------------------------------------------------------

    @_check_types.do
    def _show_menu(self, position: QtCore.QPoint) -> None:
        self.build_menu().exec(position)

    @_check_types.do
    def build_menu(self) -> QtWidgets.QMenu:
        """The right-click menu for the current selection."""
        menu = QtWidgets.QMenu(self)
        selection = self.selection()

        if selection is None:
            hint = menu.addAction('Select some text to get code actions')
            hint.setEnabled(False)
            menu.addSeparator()
            select_all = menu.addAction('Select All')
            select_all.triggered.connect(self._edit.selectAll)
            return menu

        start, end = selection
        selected = self._text[start:end]
        header = menu.addAction(self._header_text(selected))
        header.setEnabled(False)
        menu.addSeparator()

        copy = menu.addAction('Copy')
        copy.triggered.connect(lambda: QtWidgets.QApplication.clipboard().setText(selected))
        menu.addSeparator()

        self._add_string_actions(menu, start, end)
        self._add_between_actions(menu, start, end)
        self._add_regex_actions(menu, start, end)
        if self._kind == 'html':
            self._add_element_actions(menu, start, end)

        return menu

    @_check_types.do
    def _header_text(self, selected: str) -> str:
        preview = ' '.join(selected.split())
        if len(preview) > _MENU_PREVIEW_CHARS:
            preview = preview[:_MENU_PREVIEW_CHARS] + '...'

        count = self._text.count(selected)
        preview = preview.replace('&', '&&')
        return f'"{preview}"  -  {count} occurrence(s)'

    @_check_types.do
    def _add_string_actions(self, menu: QtWidgets.QMenu, start: int, end: int) -> None:
        text = self._text
        name = self._doc_name

        self._add(menu, 'Split document at every occurrence',
                  lambda taken: _snippets.split_at_every(text, start, end, doc_name=name, taken=taken))
        self._add(menu, 'Take the text after this',
                  lambda taken: _snippets.text_after(text, start, end, doc_name=name, taken=taken))
        self._add(menu, 'Take the text before this',
                  lambda taken: _snippets.text_before(text, start, end, doc_name=name, taken=taken))

        find_menu = menu.addMenu('Find position')
        self._add(find_menu, 'Index of the start of this',
                  lambda taken: _snippets.find_position(text, start, end, doc_name=name, taken=taken))
        self._add(find_menu, 'Index just past the end of this',
                  lambda taken: _snippets.find_position(text, start, end, at_end=True, doc_name=name, taken=taken))

    @_check_types.do
    def _add_between_actions(self, menu: QtWidgets.QMenu, start: int, end: int) -> None:
        text = self._text
        name = self._doc_name

        menu.addSeparator()
        if self._mark is None:
            mark = menu.addAction('Mark as the start of a "between"')
            mark.triggered.connect(lambda: self._set_mark(start, end))
            return

        mark_start, mark_end = self._mark
        if mark_end <= start:
            self._add(menu, 'Take the text between the marked start and this',
                      lambda taken: _snippets.between(text, mark_start, mark_end, start, end,
                                                      doc_name=name, taken=taken))

        clear = menu.addAction('Clear the "between" mark')
        clear.triggered.connect(lambda: self._set_mark(None, None))

    @_check_types.do
    def _add_regex_actions(self, menu: QtWidgets.QMenu, start: int, end: int) -> None:
        text = self._text
        name = self._doc_name

        menu.addSeparator()
        regex_menu = menu.addMenu('Regular expression')
        self._add(regex_menu, 'Capture this one',
                  lambda taken: _snippets.regex_capture(text, start, end, doc_name=name, taken=taken))
        self._add(regex_menu, 'Capture every piece of text in the same markup',
                  lambda taken: _snippets.regex_all(text, start, end, doc_name=name, taken=taken))

    @_check_types.do
    def _add_element_actions(self, menu: QtWidgets.QMenu, start: int, end: int) -> None:
        text = self._text
        name = self._doc_name
        located = self._ensure_located()
        hit = None
        if located is not None:
            hit = located.element_at(start, end)

        css_menu = menu.addMenu('CSS selector (BeautifulSoup)')
        xpath_menu = menu.addMenu('XPath (lxml)')

        if hit is None:
            css_menu.setEnabled(False)
            xpath_menu.setEnabled(False)
            return

        self._add(css_menu, f'Text of this <{hit.name}>',
                  lambda taken: _html_locate.css_text(text, start, end, doc_name=name, taken=taken,
                                                      located=located))
        self._add(css_menu, f'Text of every similar <{hit.name}>',
                  lambda taken: _html_locate.css_all(text, start, end, doc_name=name, taken=taken,
                                                     located=located))
        self._add(xpath_menu, f'Text of this <{hit.name}>',
                  lambda taken: _html_locate.xpath_text(text, start, end, doc_name=name, taken=taken,
                                                        located=located))
        self._add(xpath_menu, f'Text of every similar <{hit.name}>',
                  lambda taken: _html_locate.xpath_all(text, start, end, doc_name=name, taken=taken,
                                                       located=located))

        if hit.attribute is not None:
            attribute = hit.attribute
            self._add(css_menu, f'The "{attribute}" attribute',
                      lambda taken: _html_locate.css_attribute(text, start, end, doc_name=name, taken=taken,
                                                               located=located))
            self._add(xpath_menu, f'The "{attribute}" attribute',
                      lambda taken: _html_locate.xpath_attribute(text, start, end, doc_name=name, taken=taken,
                                                                 located=located))

    @_check_types.do
    def _add(self, menu: QtWidgets.QMenu, title: str,
             build: Callable[[set[str]], _snippets.Snippet]) -> None:
        action = menu.addAction(title)
        action.triggered.connect(lambda: self._run(build))

    @_check_types.do
    def _run(self, build: Callable[[set[str]], _snippets.Snippet]) -> None:
        """Make the snippet and emit it, first emitting the one that loads
        the document if the script has no variable for it yet."""
        taken = self._taken_provider()

        if self._doc_name not in taken and self._preamble is not None:
            preamble = self._preamble(taken)
            if preamble is not None:
                self.snippetReady.emit(preamble)
                taken = self._taken_provider()

        try:
            snippet = build(taken)
        except ValueError as error:
            self.messageRaised.emit(str(error))
            return

        self.snippetReady.emit(snippet)

    # -- state -------------------------------------------------------------

    @_check_types.do
    def _set_mark(self, start: int | None, end: int | None) -> None:
        if start is None or end is None:
            self._mark = None
        else:
            self._mark = (start, end)

        self._refresh_highlights()

    @_check_types.do
    def _refresh_highlights(self) -> None:
        selections: list[QtWidgets.QTextEdit.ExtraSelection] = []

        if self._mark is not None:
            selections.append(self._extra_selection(self._mark, _MARK_COLOR))

        self._edit.setExtraSelections(selections)

    @_check_types.do
    def _extra_selection(self, original: tuple[int, int], color: QtGui.QColor) -> QtWidgets.QTextEdit.ExtraSelection:
        display_start, display_end = self._wrap.to_display(*original)
        selection = QtWidgets.QTextEdit.ExtraSelection()
        selection.format.setBackground(color)
        cursor = self._edit.textCursor()
        cursor.setPosition(display_start)
        cursor.setPosition(display_end, QtGui.QTextCursor.MoveMode.KeepAnchor)
        selection.cursor = cursor
        return selection

    @_check_types.do
    def _find(self, text: str) -> tuple[int, int] | None:
        for candidate in (text, _html.escape(text, quote=False)):
            index = self._text.find(candidate)
            if index != -1:
                return index, index + len(candidate)

        words = text.split()
        if not words:
            return None

        for candidate in (words, [_html.escape(word, quote=False) for word in words]):
            pattern = r'\s+'.join(re.escape(word) for word in candidate)
            found = re.search(pattern, self._text)
            if found is not None:
                return found.span()

        return None

    @_check_types.do
    def _ensure_located(self) -> _html_locate.LocatedDocument | None:
        """The parsed document, parsing it now if the background parse has
        not finished."""
        if self._located is None and self._text:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
            try:
                self._located = _html_locate.LocatedDocument(self._text)
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()

        return self._located

    @_check_types.do
    def _update_status(self) -> None:
        if not self._text:
            self._status.setText('No document')
            return

        self._status.setText(
            f'{len(self._text):,} characters - select text and right-click for code actions')

    @_check_types.do
    def _start_job(self, work: Callable[[], object], done: Callable[[object], None]) -> None:
        job = _background.BackgroundJob(work, self)
        self._jobs.append(job)

        job.finished.connect(done)
        job.failed.connect(self.messageRaised.emit)
        job.finished.connect(lambda _result: self._forget(job))
        job.failed.connect(lambda _text: self._forget(job))
        job.start()

    @_check_types.do
    def _forget(self, job: _background.BackgroundJob) -> None:
        if job in self._jobs:
            self._jobs.remove(job)

    @_check_types.do
    def _spans_ready(self, generation: int, spans: object) -> None:
        if generation == self._generation:
            self._highlighter.set_spans(spans)

    @_check_types.do
    def _located_ready(self, generation: int, located: object) -> None:
        if generation == self._generation and self._located is None:
            self._located = located
