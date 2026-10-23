# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The Response tab: one captured request, with its response as a JSON
tree or as source text, and its request details."""

from collections.abc import Callable

import json

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from . import json_tree as _json_tree
from . import source_viewer as _source_viewer
from ..widgets import wrap_label as _wrap_label
from ...scraping import capture_model as _capture_model
from ...scraping import request_code as _request_code
from ...scraping import snippets as _snippets
from ... import check_types as _check_types


@_check_types.do
def _no_names() -> set[str]:
    return set()


class ResponsePanel(QtWidgets.QWidget):
    """:ivar snippetReady: Code was produced (``Snippet``).
    :ivar messageRaised: Something the user should be told (``str``).
    """

    snippetReady = QtCore.Signal(object)
    messageRaised = QtCore.Signal(str)

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._request: _capture_model.CapturedRequest | None = None
        self._taken_provider: Callable[[], set[str]] = _no_names

        self._header = _wrap_label.WrapLabel('Select a request in the Network tab', self)
        self._header.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)

        self._tree = _json_tree.JsonTree(self)
        self._source = _source_viewer.SourceViewer(self)
        self._stack = QtWidgets.QStackedWidget(self)
        self._stack.addWidget(self._tree)
        self._stack.addWidget(self._source)

        self._extract = QtWidgets.QPushButton('Extract selected', self)
        self._every_item = QtWidgets.QCheckBox('From every item', self)
        self._raw = QtWidgets.QCheckBox('Raw', self)
        self._replay = QtWidgets.QPushButton('Repeat this request in the script', self)

        json_bar = QtWidgets.QHBoxLayout()
        json_bar.addWidget(self._extract)
        json_bar.addWidget(self._every_item)
        json_bar.addStretch(1)
        json_bar.addWidget(self._raw)
        self._json_bar = QtWidgets.QWidget(self)
        self._json_bar.setLayout(json_bar)
        json_bar.setContentsMargins(0, 0, 0, 0)

        response_page = QtWidgets.QWidget(self)
        response_layout = QtWidgets.QVBoxLayout(response_page)
        response_layout.setContentsMargins(0, 0, 0, 0)
        response_layout.addWidget(self._json_bar)
        response_layout.addWidget(self._stack, 1)

        self._request_text = QtWidgets.QPlainTextEdit(self)
        self._request_text.setReadOnly(True)
        font = QtGui.QFont('Consolas', 10)
        font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        self._request_text.setFont(font)

        self._tabs = QtWidgets.QTabWidget(self)
        self._tabs.addTab(response_page, 'Response')
        self._tabs.addTab(self._request_text, 'Request')

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._header)
        layout.addWidget(self._tabs, 1)
        layout.addWidget(self._replay)

        self._extract.clicked.connect(lambda: self._tree.extract_selected(self._every_item.isChecked()))
        self._raw.toggled.connect(self._show_raw)
        self._replay.clicked.connect(self._repeat_request)
        self._tree.itemSelectionChanged.connect(self._selection_changed)

        for child in (self._tree, self._source):
            child.snippetReady.connect(self.snippetReady.emit)
            child.messageRaised.connect(self.messageRaised.emit)

        self._set_empty()

    @_check_types.do
    def set_taken_provider(self, provider: Callable[[], set[str]]) -> None:
        self._taken_provider = provider
        self._tree.set_taken_provider(provider)
        self._source.set_taken_provider(provider)

    @_check_types.do
    def current_request(self) -> _capture_model.CapturedRequest | None:
        return self._request

    @_check_types.do
    def show_request(self, request: _capture_model.CapturedRequest) -> None:
        self._request = request
        self._header.setText(f'{request.method} {request.url}   ->   {self._status_text(request)}')
        self._request_text.setPlainText(self._request_details(request))

        self._raw.blockSignals(True)
        self._raw.setChecked(False)
        self._raw.blockSignals(False)

        body = request.response_body
        if body is None:
            self._json_bar.hide()
            self._source.set_preamble(None)
            self._tree.set_preamble(None)
            self._source.set_document('(no text body was captured - binary, empty, or not readable)', 'text', 'text')
            self._stack.setCurrentWidget(self._source)
            self._replay.setEnabled(True)
            return

        spec = request.to_spec()

        if request.is_json:
            self._json_bar.show()
            self._tree.set_preamble(lambda taken: _request_code.generate_request_code(spec, taken=taken))
            self._tree.set_value(request.parsed_json())
            self._source.set_preamble(None)
            self._source.set_document(self._pretty_json(request), 'json', 'text')
            self._stack.setCurrentWidget(self._tree)
        else:
            kind = 'text'
            doc_name = 'text'
            if request.is_html:
                kind = 'html'
                doc_name = 'html'
            elif request.is_xml:
                kind = 'xml'

            self._json_bar.hide()
            self._tree.set_preamble(None)
            self._source.set_preamble(
                lambda taken: _request_code.generate_request_code(spec, taken=taken, text_name=doc_name))
            self._source.set_document(body, kind, doc_name)
            self._stack.setCurrentWidget(self._source)

        self._replay.setEnabled(True)
        self._selection_changed()

    @_check_types.do
    def clear(self) -> None:
        self._request = None
        self._set_empty()

    @_check_types.do
    def _set_empty(self) -> None:
        self._header.setText('Select a request in the Network tab')
        self._request_text.clear()
        self._json_bar.hide()
        self._source.set_document('')
        self._stack.setCurrentWidget(self._source)
        self._replay.setEnabled(False)

    @_check_types.do
    def _show_raw(self, raw: bool) -> None:
        if self._request is None or not self._request.is_json:
            return

        if raw:
            self._stack.setCurrentWidget(self._source)
        else:
            self._stack.setCurrentWidget(self._tree)

    @_check_types.do
    def _selection_changed(self) -> None:
        self._extract.setEnabled(bool(self._tree.selected_paths()))
        self._every_item.setEnabled(self._tree.can_extract_every_item())
        if not self._every_item.isEnabled():
            self._every_item.setChecked(False)

    @_check_types.do
    def _repeat_request(self) -> None:
        if self._request is None:
            return

        text_name = None
        if not self._request.is_json:
            text_name = 'html'
            if not self._request.is_html:
                text_name = 'text'

        snippet = _request_code.generate_request_code(
            self._request.to_spec(), taken=self._taken_provider(), text_name=text_name)
        self.snippetReady.emit(snippet)

    @_check_types.do
    def _pretty_json(self, request: _capture_model.CapturedRequest) -> str:
        return json.dumps(request.parsed_json(), indent=2, ensure_ascii=False)

    @_check_types.do
    def _status_text(self, request: _capture_model.CapturedRequest) -> str:
        if request.error:
            return f'failed ({request.error})'

        text = f'{request.status}  {request.content_type or "unknown type"}  {_capture_model.describe_size(request.size)}'
        if request.response_truncated:
            text += '  (truncated)'

        return text

    @_check_types.do
    def _request_details(self, request: _capture_model.CapturedRequest) -> str:
        lines = [f'{request.method} {request.url}', f'(sent by {request.kind}() on {request.page_url})', '']

        lines.append('Request headers set by the page:')
        for name, value in request.request_headers.items():
            lines.append(f'  {name}: {value}')

        if not request.request_headers:
            lines.append('  (none -- the browser adds Cookie, Referer, User-Agent and others itself)')

        lines.append('')
        lines.append('Request body:')
        if request.request_body:
            lines.append(request.request_body)
        else:
            lines.append('  (none)')

        lines.append('')
        lines.append('Response headers:')
        for name, value in request.response_headers.items():
            lines.append(f'  {name}: {value}')

        return '\n'.join(lines)
