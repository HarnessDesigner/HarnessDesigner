## FILES

#### __init__.py

Re-exports the module as `_browser_dock` only; no public symbols of its own.

#### browser_dock.py

`ScraperBrowser(_dock_base.DockBase)` and `ScraperBrowserPanel(QtWidgets.QWidget)` -- `ScraperBrowserPanel.__init__(self, storage_path, parent=None)` lays out the browser and the `ui/scraper_inspector/inspector.ScraperInspector` in a splitter; `set_sink()` wires the inspector's generated snippets to a target editor. This is the scraper's Web Browser dock (design doc: `SCRAPER_DESIGN.md`); `MainFrame.show_scraper_browser()` creates it on first use, restores its saved position, and `closeEvent` destroys it again -- the General toolbar's Internet button (`ui/toolbar/toolbar.py`'s `GeneralToolbar`) is what calls `show_scraper_browser()` (there is no menu entry for it yet).

#### browser_widget.py

`BrowserWidget(QtWidgets.QWidget)` -- address bar, `QWebEngineView`, persistent browser profile, JS hook injection, downloads refused, permissions denied, new windows opened in place instead of as separate popups, a "Scraper" page context menu, and source fetching (as served, or the live rendered DOM). `shorten_url` (referenced from `ui/widgets/wrap_label.py`'s MAP.md entry) lives here and is the helper other labels use to cut a long embedded address down before display. This module, and the directory generally, imports `QtWebEngine`-dependent types, which is why the whole dock is created lazily (see `browser_dock.py` above) rather than at startup -- `app.py` also sets `QSG_RHI_BACKEND=opengl` before the `QApplication` exists specifically so this view composites correctly inside the OpenGL-composited main window (see MEMORY.md's "QtWebEngine in the main window needs Qt Quick on OpenGL" entry); removing that env var or constructing a `QWebEngineView` in a context that doesn't honor it will bring back the black-page/duplicate-open-project-dialog symptom that entry documents.

#### capture_bridge.py

`CaptureBridge(QtCore.QObject)` -- the `QWebChannel` object the injected page-side hook (`...scraping.capture_hook`) calls into from JS, feeding captured network/DOM data back into `...scraping.capture_model` on the Python side.
