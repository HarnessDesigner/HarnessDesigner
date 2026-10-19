## FILES

#### __init__.py

Re-exports `inspector` (as `_inspector`) and `insertion` (as `_insertion`); no public symbols of its own.

#### background.py

`BackgroundJob(QtCore.QObject)` -- `__init__(self, work: Callable[[], object], parent=None)`; runs an arbitrary callable off the GUI thread via `threading`, reporting the result (or a captured `traceback`) back through a Qt signal. Used by `source_viewer.py` so turning a selection into code doesn't block the UI thread.

#### insertion.py

`SnippetSink` (ABC-like protocol: `insert_snippet(self, snippet)`) -- what a generated-code snippet is sent to -- and the module-level `insert_snippet(editor: QtWidgets.QPlainTextEdit, snippet)` function that actually performs the insert: merges the snippet's required imports into the target editor's existing import block and performs the whole insert (imports + body) as one undo step. `snippet_pane.SnippetPane` is the built-in sink (`SnippetPane.insert_snippet`); `inspector.ScraperInspector.set_sink()` can redirect snippets to an external sink (the script editor) instead of this pane.

#### inspector.py

`ScraperInspector(QtWidgets.QWidget, _assistant.AssistantContext)` -- the Source / Network / Response tabs plus the generated-script pane, assembled from the other files in this directory (`insertion`, `network_panel`, `response_panel`, `snippet_pane`, `source_viewer`). `set_sink()` redirects generated snippets to the script editor instead of the built-in `snippet_pane.SnippetPane`. As `AssistantContext`, it also exposes the current page address and source, the current source selection, and the currently-picked network request to the AI assistant plugin.

#### json_tree.py

`JsonTree(QtWidgets.QTreeWidget)` -- a lazily-expanded tree view over an arbitrary JSON value; selecting a node offers extraction code (via `...scraping.json_extract`) that `response_panel.py` sends through `insertion.insert_snippet`.

#### network_panel.py

`NetworkModel(QtCore.QAbstractTableModel)` and `NetworkPanel(QtWidgets.QWidget)` -- the captured-requests table, backed by a rolling window of 2000 entries (`...scraping.capture_model`) so a long scraping session doesn't grow this table's memory unbounded. Selecting a row feeds `response_panel.py`'s detail view.

#### response_panel.py

`ResponsePanel(QtWidgets.QWidget)` -- shows one selected request's response as either a `json_tree.JsonTree` or plain source text (`source_viewer.SourceViewer`), plus request details and a "repeat request" action. Uses `ui/widgets/wrap_label.py`'s `WrapLabel` for its Response header line, per that widget's "any label that can show a server/API message" rule (see `ui/widgets/MAP.md`).

#### snippet_pane.py

`SnippetPane(QtWidgets.QWidget, _insertion.SnippetSink)` -- the built-in generated-script pane, a thin wrapper around `ui/widgets/code_editor_ctrl.CodeEditorCtrl`; implements `SnippetSink.insert_snippet` to append generated code into its own editor. Its title label uses `WrapLabel` (see `ui/widgets/MAP.md`'s wrap_label entry) since the title can echo a page address or script name of unbounded length.

#### source_viewer.py

`SourceViewer(QtWidgets.QWidget)` -- a highlighted, read-only view of a page's source (via `...scraping.highlight`/`html_locate`/`soft_wrap`); its right-click menu (`build_menu()`) turns the current selection into extraction code via `...scraping.snippets`, sent off-thread through `background.BackgroundJob` so highlighting/locating a selection in a large page doesn't block the UI. Its own status line (and the inspector's message line generally) uses `ui/widgets/wrap_label.py`'s `WrapLabel`, which exists specifically because an unbroken long address or server message in a plain `QLabel` here once blew the whole main window out to ~5,800px wide -- see `ui/widgets/MAP.md`'s `wrap_label.py` entry for the full incident.
