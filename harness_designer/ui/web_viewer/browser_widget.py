# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The built-in browser: address bar, navigation, the page, and the
plumbing that reports the page's fetch / XHR traffic and its source.

QtWebEngine (Chromium) is heavy, so this module is only imported when the
browser dock is first opened -- never at application start.

The page is locked down the way a scraping browser should be: downloads
are refused, every permission request (camera, location, notifications)
is denied, and a link that wants a new window opens in this one.
"""

from typing import Any

import os
import re

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWebChannel
from PySide6 import QtWebEngineCore
from PySide6 import QtWebEngineWidgets
from PySide6 import QtWidgets

from . import capture_bridge as _capture_bridge
from ...scraping import browser_pick as _browser_pick
from ...scraping import capture_hook as _capture_hook
from ...scraping import url_input as _url_input
from ... import check_types as _check_types

_QWEBCHANNEL_RESOURCE = ':/qtwebchannel/qwebchannel.js'

_ENGINE_TOKEN = re.compile(r'\s*QtWebEngine/[\d.]+')

# What a popup page is allowed to report before it is discarded.
_BLANK_URLS = ('', 'about:blank')

# An address in a message is cut to this many characters (its start and its end are kept).
_URL_SHOWN = 100
_URL_HEAD = 70


@_check_types.do
def clean_user_agent(user_agent: str) -> str:
    """The default user agent without its ``QtWebEngine/x.y.z`` token, so
    sites see an ordinary Chrome."""
    return _ENGINE_TOKEN.sub('', user_agent)


@_check_types.do
def shorten_url(url: str) -> str:
    """*url* as it goes into a message: a long address (search links run past
    a thousand characters) keeps its start and its end."""
    if len(url) <= _URL_SHOWN:
        return url

    return f'{url[:_URL_HEAD]}...{url[-(_URL_SHOWN - _URL_HEAD - 3):]}'


class _ScraperPage(QtWebEngineCore.QWebEnginePage):
    """A page that keeps navigation in the one view and says no to
    permission requests."""

    openRequested = QtCore.Signal(QtCore.QUrl)

    @_check_types.do
    def __init__(self, profile: QtWebEngineCore.QWebEngineProfile, parent: QtCore.QObject | None = None) -> None:
        super().__init__(profile, parent)
        self.permissionRequested.connect(self._deny)

    @_check_types.do
    def _deny(self, permission: QtWebEngineCore.QWebEnginePermission) -> None:
        permission.deny()

    @_check_types.do
    def createWindow(self, window_type: QtWebEngineCore.QWebEnginePage.WebWindowType  # NOQA -- Qt override
                     ) -> QtWebEngineCore.QWebEnginePage:
        """``target="_blank"`` and ``window.open``: open the address in
        this view. The new page only exists long enough to report where it
        was going."""
        popup = QtWebEngineCore.QWebEnginePage(self.profile(), self)
        popup.urlChanged.connect(lambda url: self._popup_navigated(popup, url))
        return popup

    @_check_types.do
    def _popup_navigated(self, popup: QtWebEngineCore.QWebEnginePage, url: QtCore.QUrl) -> None:
        if url.toString() in _BLANK_URLS:
            return

        self.openRequested.emit(url)
        popup.deleteLater()

    @_check_types.do
    def javaScriptConsoleMessage(  # NOQA -- Qt override
            self, level: QtWebEngineCore.QWebEnginePage.JavaScriptConsoleMessageLevel, message: str,
            line_number: int, source_id: str) -> None:
        """The page's console output is not the user's business here."""


class _ScraperView(QtWebEngineWidgets.QWebEngineView):
    """:ivar showInSourceRequested: The user asked to find the selected
        text in the Source tab (``str``).
    :ivar pickRequested: The user asked for a selector for the element
        under the pointer (position in CSS pixels, what to read).
    """

    showInSourceRequested = QtCore.Signal(str)
    pickRequested = QtCore.Signal(QtCore.QPoint, str, bool)

    @_check_types.do
    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:  # NOQA -- Qt override
        request = self.lastContextMenuRequest()
        menu = self.createStandardContextMenu()
        menu.addSeparator()

        scraper = menu.addMenu('Scraper')
        selected = request.selectedText().strip()
        position = QtCore.QPoint(round(request.position().x() / self.zoomFactor()),
                                 round(request.position().y() / self.zoomFactor()))

        show = scraper.addAction('Show the selected text in Source')
        show.setEnabled(bool(selected))
        show.triggered.connect(lambda: self.showInSourceRequested.emit(selected))

        scraper.addSeparator()
        text = scraper.addAction('Selector for this element - its text')
        text.triggered.connect(lambda: self.pickRequested.emit(position, 'text', False))
        similar = scraper.addAction('Selector for every similar element - their text')
        similar.triggered.connect(lambda: self.pickRequested.emit(position, 'text', True))

        link = scraper.addAction('Selector for this element - its link (href)')
        link.setEnabled(not request.linkUrl().isEmpty())
        link.triggered.connect(lambda: self.pickRequested.emit(position, 'href', False))

        image = scraper.addAction('Selector for this element - its image (src)')
        image.setEnabled(not request.mediaUrl().isEmpty())
        image.triggered.connect(lambda: self.pickRequested.emit(position, 'src', False))

        menu.exec(event.globalPos())


class BrowserWidget(QtWidgets.QWidget):
    """:ivar requestCaptured: A fetch / XHR call finished (``CapturedRequest``).
    :ivar pageLoaded: A page finished loading (url, user agent).
    :ivar sourceReady: The page source arrived (url, text, rendered).
    :ivar showInSourceRequested: Find this text in the Source tab (``str``).
    :ivar elementPicked: A selector was built for an element
        (pick dict, what to read, every similar).
    :ivar messageRaised: Something the user should be told (``str``).
    """

    requestCaptured = QtCore.Signal(object)
    pageLoaded = QtCore.Signal(str, str)
    sourceReady = QtCore.Signal(str, str, bool)
    showInSourceRequested = QtCore.Signal(str)
    elementPicked = QtCore.Signal(object, str, bool)
    messageRaised = QtCore.Signal(str)

    @_check_types.do
    def __init__(self, storage_path: str | None = None, parent: QtWidgets.QWidget | None = None) -> None:
        """
        :param storage_path: Folder for cookies and cache, so logins
            survive between sessions. ``None`` browses privately: nothing
            is kept.
        """
        super().__init__(parent)

        self._profile = self._make_profile(storage_path)
        self._page = _ScraperPage(self._profile, self)
        self._view = _ScraperView(self)
        self._view.setPage(self._page)

        self._bridge = _capture_bridge.CaptureBridge(self)
        self._channel = QtWebChannel.QWebChannel(self)
        self._channel.registerObject(_capture_hook.BRIDGE_NAME, self._bridge)
        self._page.setWebChannel(self._channel)
        self._install_scripts()

        self._back = QtWidgets.QToolButton(self)
        self._forward = QtWidgets.QToolButton(self)
        self._reload = QtWidgets.QToolButton(self)
        self._address = QtWidgets.QLineEdit(self)
        self._address.setPlaceholderText('Address')
        self._go = QtWidgets.QPushButton('Go', self)
        self._progress = QtWidgets.QProgressBar(self)
        self._progress.setMaximumHeight(3)
        self._progress.setTextVisible(False)

        style = self.style()
        self._back.setIcon(style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ArrowBack))
        self._forward.setIcon(style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ArrowForward))
        self._reload.setIcon(style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_BrowserReload))
        self._back.setToolTip('Back')
        self._forward.setToolTip('Forward')
        self._reload.setToolTip('Reload')

        self._as_served = QtWidgets.QRadioButton('As served', self)
        self._rendered = QtWidgets.QRadioButton('Rendered DOM', self)
        self._as_served.setChecked(True)
        self._as_served.setToolTip('The HTML the server sends -- what a script using requests receives.')
        self._rendered.setToolTip('The page after JavaScript has run -- what you see in the browser.')
        self._refresh = QtWidgets.QPushButton('Refresh source', self)
        self._auto = QtWidgets.QCheckBox('after each page load', self)
        self._auto.setChecked(True)

        bar = QtWidgets.QHBoxLayout()
        for widget in (self._back, self._forward, self._reload):
            bar.addWidget(widget)
        bar.addWidget(self._address, 1)
        bar.addWidget(self._go)

        source_bar = QtWidgets.QHBoxLayout()
        source_bar.addWidget(QtWidgets.QLabel('Source:', self))
        source_bar.addWidget(self._as_served)
        source_bar.addWidget(self._rendered)
        source_bar.addWidget(self._refresh)
        source_bar.addWidget(self._auto)
        source_bar.addStretch(1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addLayout(bar)
        layout.addWidget(self._progress)
        layout.addWidget(self._view, 1)
        layout.addLayout(source_bar)

        self._connect()

    # -- public ------------------------------------------------------------

    @_check_types.do
    def load(self, text: str) -> None:
        """Go to what was typed in the address bar."""
        url = _url_input.normalize_url(text)
        if not url:
            self.messageRaised.emit('That is not an address the browser can open.')
            return

        self._view.load(QtCore.QUrl(url))

    @_check_types.do
    def current_url(self) -> str:
        return self._view.url().toString()

    @_check_types.do
    def user_agent(self) -> str:
        return self._profile.httpUserAgent()

    @_check_types.do
    def page(self) -> QtWebEngineCore.QWebEnginePage:
        return self._page

    @_check_types.do
    def request_source(self) -> None:
        """Fetch the page source in the chosen mode; the result arrives as
        :attr:`sourceReady`."""
        url = self._view.url().toString()
        if not url.startswith(('http://', 'https://')):
            self.messageRaised.emit('The source can only be shown for pages loaded over http or https.')
            return

        if self._rendered.isChecked():
            self._page.toHtml(lambda text: self.sourceReady.emit(url, text, True))
            return

        self._page.runJavaScript(
            'window.__hdPageSource ? window.__hdPageSource() : false', self._served_started)

    @_check_types.do
    def shutdown(self) -> None:
        """Release the page before the profile it uses (QtWebEngine warns,
        and may misbehave, when a profile goes first)."""
        self._view.stop()
        self._view.setPage(QtWebEngineCore.QWebEnginePage(self))
        self._page.deleteLater()
        self._profile.deleteLater()

    # -- setup -------------------------------------------------------------

    @_check_types.do
    def _make_profile(self, storage_path: str | None) -> QtWebEngineCore.QWebEngineProfile:
        if storage_path is None:
            profile = QtWebEngineCore.QWebEngineProfile(self)
        else:
            os.makedirs(storage_path, exist_ok=True)
            profile = QtWebEngineCore.QWebEngineProfile('scraper', self)
            profile.setPersistentStoragePath(storage_path)
            profile.setCachePath(os.path.join(storage_path, 'cache'))
            profile.setPersistentCookiesPolicy(
                QtWebEngineCore.QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)

        profile.setHttpUserAgent(clean_user_agent(profile.httpUserAgent()))
        profile.downloadRequested.connect(self._refuse_download)
        return profile

    @_check_types.do
    def _install_scripts(self) -> None:
        resource = QtCore.QFile(_QWEBCHANNEL_RESOURCE)
        if not resource.open(QtCore.QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError('QtWebChannel\'s qwebchannel.js is missing from this PySide6 install')

        channel_source = bytes(resource.readAll()).decode('utf-8')
        resource.close()

        for name, source in (('hd-qwebchannel', channel_source), ('hd-capture', _capture_hook.hook_source())):
            script = QtWebEngineCore.QWebEngineScript()
            script.setName(name)
            script.setSourceCode(source)
            script.setInjectionPoint(QtWebEngineCore.QWebEngineScript.InjectionPoint.DocumentCreation)
            script.setWorldId(QtWebEngineCore.QWebEngineScript.ScriptWorldId.MainWorld)
            script.setRunsOnSubFrames(True)
            self._page.scripts().insert(script)

    @_check_types.do
    def _connect(self) -> None:
        self._back.clicked.connect(self._view.back)
        self._forward.clicked.connect(self._view.forward)
        self._reload.clicked.connect(self._reload_or_stop)
        self._go.clicked.connect(lambda: self.load(self._address.text()))
        self._address.returnPressed.connect(lambda: self.load(self._address.text()))
        self._refresh.clicked.connect(self.request_source)

        self._view.urlChanged.connect(lambda url: self._address.setText(url.toString()))
        self._view.loadStarted.connect(self._load_started)
        self._view.loadProgress.connect(self._progress.setValue)
        self._view.loadFinished.connect(self._load_finished)
        self._view.showInSourceRequested.connect(self.showInSourceRequested.emit)
        self._view.pickRequested.connect(self._pick)
        self._page.openRequested.connect(self._view.load)

        self._bridge.captured.connect(self.requestCaptured.emit)
        self._bridge.pageSourceReceived.connect(self._served_received)

        self._view.urlChanged.connect(self._update_buttons)
        self._update_buttons()

    # -- slots -------------------------------------------------------------

    @_check_types.do
    def _reload_or_stop(self) -> None:
        if self._progress.value() not in (0, 100):
            self._view.stop()
        else:
            self._view.reload()

    @_check_types.do
    def _load_started(self) -> None:
        self._reload.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_BrowserStop))
        self._reload.setToolTip('Stop')

    @_check_types.do
    def _load_finished(self, ok: bool) -> None:
        self._reload.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_BrowserReload))
        self._reload.setToolTip('Reload')
        self._progress.setValue(100)
        self._update_buttons()

        if not ok:
            self.messageRaised.emit(f'The page could not be loaded: {shorten_url(self._view.url().toString())}')
            return

        self.pageLoaded.emit(self._view.url().toString(), self._profile.httpUserAgent())
        if self._auto.isChecked():
            self.request_source()

    @_check_types.do
    def _update_buttons(self, *_args: tuple[Any]) -> None:
        history = self._view.history()
        self._back.setEnabled(history.canGoBack())
        self._forward.setEnabled(history.canGoForward())

    @_check_types.do
    def _served_started(self, started: object) -> None:
        if started is not True:
            self.messageRaised.emit('The page is not ready to report its source yet - try again in a moment.')

    @_check_types.do
    def _served_received(self, url: str, text: str) -> None:
        if not text:
            self.messageRaised.emit(f'The source of {shorten_url(url)} could not be downloaded.')
            return

        self.sourceReady.emit(url, text, False)

    @_check_types.do
    def _pick(self, position: QtCore.QPoint, what: str, every_similar: bool) -> None:
        script = _browser_pick.pick_script(position.x(), position.y())
        self._page.runJavaScript(script, lambda answer: self._picked(answer, what, every_similar))

    @_check_types.do
    def _picked(self, answer: object, what: str, every_similar: bool) -> None:
        pick = _browser_pick.parse_pick(answer)
        if pick is None:
            self.messageRaised.emit('No element was found under the pointer.')
            return

        self.elementPicked.emit(pick, what, every_similar)

    @_check_types.do
    def _refuse_download(self, download: QtWebEngineCore.QWebEngineDownloadRequest) -> None:
        download.cancel()
        self.messageRaised.emit('Downloads are not supported in the scraper browser.')
