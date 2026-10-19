# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The inspector: Source / Network / Response tabs plus the generated-script
pane, and the wiring that lets a snippet from any tab reach the script."""

from PySide6 import QtCore
from PySide6 import QtWidgets

from . import insertion as _insertion
from . import network_panel as _network_panel
from . import response_panel as _response_panel
from . import snippet_pane as _snippet_pane
from . import source_viewer as _source_viewer
from ..widgets import wrap_label as _wrap_label
from ...scraping import assistant as _assistant
from ...scraping import browser_pick as _browser_pick
from ...scraping import capture_model as _capture_model
from ...scraping import request_code as _request_code
from ...scraping import snippets as _snippets
from ... import check_types as _check_types

_RENDERED_WARNING = (
    'This selection comes from the rendered page (after JavaScript ran). A script that downloads the page '
    'with requests sees the original HTML, which may not contain this -- check the "As served" source.')


class ScraperInspector(QtWidgets.QWidget, _assistant.AssistantContext):
    """:ivar messageRaised: Something the user should be told (``str``)."""

    messageRaised = QtCore.Signal(str)

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._page_url = ''
        self._user_agent = ''
        self._rendered = False

        self.source = _source_viewer.SourceViewer(self)
        self.network = _network_panel.NetworkPanel(self)
        self.response = _response_panel.ResponsePanel(self)
        self.pane = _snippet_pane.SnippetPane(self)
        self._sink: _insertion.SnippetSink = self.pane

        self.tabs = QtWidgets.QTabWidget(self)
        self.tabs.addTab(self.source, 'Source')
        self.tabs.addTab(self.network, 'Network')
        self.tabs.addTab(self.response, 'Response')

        self._message = _wrap_label.WrapLabel('', self)
        self._message.setStyleSheet('color: #d7ba7d;')

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical, self)
        self._splitter.addWidget(self.tabs)
        self._splitter.addWidget(self.pane)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._splitter, 1)
        layout.addWidget(self._message)

        for panel in (self.source, self.response):
            panel.snippetReady.connect(self._deliver)
            panel.messageRaised.connect(self._show_message)

        self.source.set_taken_provider(self._names)
        self.response.set_taken_provider(self._names)

        self.network.requestSelected.connect(self._request_selected)
        self.network.requestsCleared.connect(self.response.clear)

    @_check_types.do
    def set_sink(self, sink: _insertion.SnippetSink | None) -> None:
        """Send snippets to *sink* (the script editor) instead of the
        built-in pane, which is hidden while a sink is set. ``None`` goes
        back to the pane."""
        if sink is None:
            self._sink = self.pane
            self.pane.show()
            return

        self._sink = sink
        self.pane.hide()

    @_check_types.do
    def add_request(self, request: _capture_model.CapturedRequest) -> None:
        self.network.add_request(request)

    @_check_types.do
    def set_page(self, url: str, user_agent: str = '') -> None:
        """The page the browser is on: generated code downloads this URL."""
        self._page_url = url
        self._user_agent = user_agent

    @_check_types.do
    def set_page_source(self, url: str, text: str, rendered: bool, user_agent: str = '') -> None:
        """Show the page at *url*: its source *text*, either as served by
        the server or (*rendered*) as the browser's DOM now stands."""
        self.set_page(url, user_agent)
        self._rendered = rendered

        self.source.set_preamble(self._page_preamble)
        self.source.set_document(text, 'html', 'html')

    @_check_types.do
    def show_in_source(self, text: str) -> None:
        """Switch to the Source tab and select *text* there."""
        self.tabs.setCurrentWidget(self.source)
        if not self.source.select_text(text):
            self._show_message('That text was not found in the source. If JavaScript created it, switch the '
                               'Source to "Rendered DOM".')

    @_check_types.do
    def deliver_pick(self, pick: dict, what: str, every_similar: bool) -> None:
        """Turn an element picked in the live page into code (after the
        code that downloads the page, if the script has none yet)."""
        taken = self._names()
        if 'html' not in taken:
            preamble = self._page_preamble(taken, False)
            if preamble is not None:
                self._deliver(preamble)
                taken = self._names()

        try:
            snippet = _browser_pick.pick_snippet(pick, what, every_similar=every_similar, taken=taken)
        except ValueError as error:
            self._show_message(str(error))
            return

        self._deliver(snippet)

    @_check_types.do
    def show_message(self, text: str) -> None:
        self._show_message(text)

    # -- AssistantContext: what the script editor's assistant can see ------------
    #
    # The assistant's tools call page_source() and selected_request() from a
    # worker thread, so those two only read plain Python attributes. The other
    # two touch widgets and are called on the GUI thread only.

    @_check_types.do
    def page_url(self) -> str:
        return self._page_url

    @_check_types.do
    def page_source(self) -> str | None:
        text = self.source.document_text()
        if not text:
            return None

        return text

    @_check_types.do
    def source_selection(self) -> tuple[str, int, int] | None:
        selection = self.source.selection()
        if selection is None:
            return None

        return self.source.document_text(), selection[0], selection[1]

    @_check_types.do
    def selected_request(self) -> _capture_model.CapturedRequest | None:
        return self.response.current_request()

    @_check_types.do
    def _page_preamble(self, taken: set[str], warn_if_rendered: bool = True) -> _snippets.Snippet | None:
        if not self._page_url:
            return None

        snippet = _request_code.generate_page_load(
            self._page_url, user_agent=self._user_agent, doc_name='html', taken=taken)
        if self._rendered and warn_if_rendered:
            snippet.warnings.append(_RENDERED_WARNING)

        return snippet

    @_check_types.do
    def _names(self) -> set[str]:
        return self._sink.taken_names()

    @_check_types.do
    def _deliver(self, snippet: _snippets.Snippet) -> None:
        self._sink.insert_snippet(snippet)
        if snippet.warnings:
            self._show_message(' '.join(snippet.warnings))
        else:
            self._show_message(f'Added: {snippet.description}')

    @_check_types.do
    def _request_selected(self, request: _capture_model.CapturedRequest) -> None:
        self.response.show_request(request)
        self.tabs.setCurrentWidget(self.response)

    @_check_types.do
    def _show_message(self, text: str) -> None:
        self._message.setText(text)
        self.messageRaised.emit(text)
