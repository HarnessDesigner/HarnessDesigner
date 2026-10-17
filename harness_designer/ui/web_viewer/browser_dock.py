# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The Web Browser dock: the scraper browser on one side, the inspector
(Source / Network / Response and the generated script) on the other."""

from typing import TYPE_CHECKING

import os

from PySide6 import QtCore
from PySide6 import QtWidgets

from . import browser_widget as _browser_widget
from .. import dock_base as _dock_base
from ..scraper_inspector import inspector as _inspector
from ..scraper_inspector import insertion as _insertion
from ...utils import paths as _paths
from ... import check_types as _check_types

if TYPE_CHECKING:
    from .. import mainframe as _mainframe


class ScraperBrowserPanel(QtWidgets.QWidget):
    """The browser and the inspector, wired together."""

    @_check_types.do
    def __init__(self, storage_path: str | None, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        self.browser = _browser_widget.BrowserWidget(storage_path, self)
        self.inspector = _inspector.ScraperInspector(self)

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, self)
        self._splitter.addWidget(self.browser)
        self._splitter.addWidget(self.inspector)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 2)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._splitter)

        self.browser.requestCaptured.connect(self.inspector.add_request)
        self.browser.pageLoaded.connect(self.inspector.set_page)
        self.browser.sourceReady.connect(self._source_ready)
        self.browser.showInSourceRequested.connect(self.inspector.show_in_source)
        self.browser.elementPicked.connect(self.inspector.deliver_pick)
        self.browser.messageRaised.connect(self.inspector.show_message)

    @_check_types.do
    def set_sink(self, sink: _insertion.SnippetSink | None) -> None:
        """Send generated code to the script editor (or back to the
        built-in pane with ``None``)."""
        self.inspector.set_sink(sink)

    @_check_types.do
    def Refresh(self, *_, **__) -> None:  # NOQA -- the call every dock panel gets
        pass

    @_check_types.do
    def shutdown(self) -> None:
        self.browser.shutdown()

    @_check_types.do
    def _source_ready(self, url: str, text: str, rendered: bool) -> None:
        self.inspector.set_page_source(url, text, rendered, self.browser.user_agent())


class ScraperBrowser(_dock_base.DockBase):
    """The dock. Created the first time the user opens the browser, not at
    application start (see SCRAPER_DESIGN.md)."""

    @_check_types.do
    def __init__(self, mainframe: "_mainframe.MainFrame") -> None:
        storage = os.path.join(_paths.get_appdata(), 'scraper', 'browser_profile')
        self._ui_obj = ScraperBrowserPanel(storage, mainframe)
        super().__init__(mainframe, 'Web Browser', 'scraper_browser',
                         QtCore.Qt.DockWidgetArea.RightDockWidgetArea)

    @property
    @_check_types.do
    def panel(self) -> ScraperBrowserPanel:
        return self._ui_obj

    @_check_types.do
    def Destroy(self) -> None:
        self._ui_obj.shutdown()
        super().Destroy()
