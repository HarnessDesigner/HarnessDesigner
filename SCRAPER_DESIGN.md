# Scraper tool design

Point-and-click scraper authoring inside harness_designer: a built-in web browser, tools that turn what the
user sees/selects (page source text, XHR/fetch responses) into Python code, a script editor, and a Claude
assistant that helps design the scraper. Add new scraper decisions HERE, not in MEMORY.md.

Status (2026-10-16): design agreed. Phases 1 (snippet engine) and 2 (browser, XHR capture, inspector) are built and
tested headless; they have NOT been run in the real application. Phases 3-5 are not started. See "Phasing" and
"Phase 2 as built".

Running the tests (no app launch, no `Config`/log side effects -- `tests/_bootstrap.py` loads the real modules
under a stub package so `harness_designer/__init__.py` never runs):

    C:\python3.11.14\python.exe -m unittest discover -s tests -t .

The interpreter needs the new dependencies first (`pip install -r requirements.txt`: `beautifulsoup4`, `lxml`,
`anthropic`). 176 tests at the end of Phase 2: each snippet action is checked by executing its output against
sample pages (indented, minified, CRLF, and one made of identical rows); the widgets are driven headless
(`QT_QPA_PLATFORM=offscreen`); and `test_browser_integration.py` runs the real QtWebEngine against a local
`http.server` on 127.0.0.1 (about 15 s). Generated scripts are executed with `requests` swapped out in
`sys.modules`, so no test touches the network. The browser tests need a Qt install with QtWebEngine.

## Decisions (user, 2026-10-16)

- **Placement: docks in the main window.** `ui/web_viewer/` and `ui/editor_script/` (both empty stubs until now)
  become `DockBase` subclasses created by `MainFrame.__init__` like `LogViewer`, each lazily imported there.
  Not a separate window, not a plugin.
- **Not started by default (user, 2026-10-16).** The browser and the script editor docks are NOT created at
  startup. They are created on first use, triggered from toolbar buttons and from the system menu. The user has
  not decided which system menu holds the entries, so both entry points call the same `MainFrame` method
  (`show_scraper_browser()` / `show_script_editor()`: create the dock on first call, show and raise it after),
  and the menu placement is a one-line change in `ui/system_menu/` when decided. Consequences: (a) the lazy
  `import` of QtWebEngine happens at first use, so startup cost is unchanged; (b) `restoreState()` at startup
  only restores docks that already exist, so after creating a dock lazily call `restoreDockWidget(dock)` so a
  saved position is honoured, otherwise it opens in its default area; (c) the toolbar buttons need icons from
  the existing icon set (`image/icons`).
- **Libraries: generated and Claude-written scripts may use `beautifulsoup4` + `lxml`** (plus `requests`, `re`,
  `json`, stdlib). CSS selectors and XPath are first-class snippet actions. Both go into `pyproject.toml` and
  `requirements.txt` pinned like every other dependency; the frozen build must bundle them (lxml is a C
  extension -- check the PyInstaller hidden imports when the build is next exercised).
- **Claude client: the official `anthropic` SDK, in its own shared package** (user, 2026-10-17: it must be usable
  from more than one place -- concentric twisting is the next user). It lives in `harness_designer/claude/`;
  see CLAUDE_API_DESIGN.md. The old `requests`-based `scraping/claude_client.py` is gone. The scraper assistant
  (Phase 3) is a CONSUMER of that package: it builds its prompts, calls `ClaudeClient` / `ClaudeJob`, and shows
  the settings with `claude.qt.key_dialog.ApiKeyDialog`; it contains no API code of its own.
- **Running scripts: see "Running scripts" -- user asked how other apps do it; recommendation below, awaiting
  the user's reaction before Phase 4.**

## Already in the tree when this started (untracked, from an earlier session)

- `scraping/json_extract.py`: JSON path clicks -> extraction code (`generate_extraction_code`, groups paths
  that share an array ancestor into one `for` loop), and `describe()` (ask Claude for code from a sample).
- `scraping/claude_client.py`: keyring key storage + one-shot Messages call over `requests`. REPLACED
  2026-10-17 by `harness_designer/claude/` (its `max_tokens=2048` default was too small for the 5.5 models:
  thinking tokens count against `max_tokens`, so a reply could be cut off). The stored key still works: the new
  package uses the same credential slot.
- `ui/widgets/code_editor_ctrl.py`: `CodeEditorCtrl`, a `QPlainTextEdit` with line numbers, Pygments Python
  highlighting and auto-indent. This is the script editor widget.
- `Pygments==2.19.2` already added to `pyproject.toml` / `requirements.txt`.

## Package layout

```
harness_designer/scraping/              non-UI logic; no Qt
    snippets.py        selection in a document -> code (split/find/between/regex)                  [Phase 1]
    html_locate.py     source offset -> enclosing element, unique CSS selector / XPath            [Phase 1]
    request_code.py    captured request -> `requests` code; page download code                    [Phase 1/2]
    json_extract.py    JSON path clicks -> code (incl. "every item"); `describe()` asks Claude    [exists/2]
    capture_hook.py    the JS that records fetch / XHR and can re-download the page               [Phase 2]
    capture_model.py   CapturedRequest + parse_record() (validates what the page reports)         [Phase 2]
    soft_wrap.py       adds line breaks for display + maps selections back to original offsets    [Phase 2]
    highlight.py       one-pass Pygments spans (HTML / XML / JSON) as plain data                  [Phase 2]
    script_builder.py  where imports go, how warnings become comments                             [Phase 2]
    browser_pick.py    "element under the pointer" JS + its answer -> snippet                     [Phase 2]
    url_input.py       address-bar text -> URL                                                    [Phase 2]
    assistant.py       prompt + context packing/truncation + reply parsing (uses `claude/`)       [Phase 3]
    runner.py          run a script in a child process, stream output, terminate                  [Phase 4]
harness_designer/ui/scraper_inspector/  the inspector widgets; no QtWebEngine, so testable alone  [Phase 2]
    source_viewer.py   Source tab: highlighted read-only text, right-click -> code actions
    network_panel.py   Network tab: the captured requests, filter, JSON-only
    response_panel.py  Response tab: JSON tree or source text, request details, "repeat request"
    json_tree.py       lazy JSON tree; select values -> extraction code
    snippet_pane.py    the "generated script" pane (CodeEditorCtrl) used until the script editor exists
    insertion.py       SnippetSink + insert_snippet(): how code lands in an editor (one undo step)
    inspector.py       the three tabs + pane, and the wiring between them
harness_designer/ui/web_viewer/         the browser dock (imports QtWebEngine -- only on first open) [Phase 2]
    browser_widget.py  address bar, QWebEngineView, profile, hook injection, page context menu
    capture_bridge.py  the QWebChannel object the hook calls (validates everything)
    browser_dock.py    ScraperBrowser(DockBase) = browser | inspector, side by side
harness_designer/ui/editor_script/      ScriptEditor dock: CodeEditorCtrl, toolbar, console, assistant [Phase 3]
tests/                                  unittest; `_bootstrap.py` loads modules without `import harness_designer`
```

**One dock holds the browser and the inspector** (changed from the three-dock sketch): the user asked for
"tools built into the browser", and an inspector without its page is useless, so they open and close together.
The script editor is the second dock. While no editor is open, the inspector's own "generated script" pane
collects the code; `ScraperInspector.set_sink(editor)` redirects snippets to the editor and hides the pane.

`QtWebEngine` is imported only inside `ui/web_viewer/` and only when the dock is first built (it is heavy; the
project's own `AA_ShareOpenGLContexts` attribute, set at import time in `app.py`, is what QtWebEngine needs).

## The three code-insertion workflows

All three end in the same place: a `Snippet` (code + description + warnings) that the script editor inserts at
the cursor. Variable names default to `html`, `value`, `value_2`, ... and never collide with names already in
the script.

1. **Source text -> right-click.** The Source tab shows the page as served (Pygments HTML highlighting,
   read-only). Select text, right-click, pick an action. Selection is by character offsets into the exact
   document string, so generated code can be *executed against that document* and must reproduce the selection.
2. **XHR / fetch -> select data.** The Network tab lists captured requests. Selecting one shows request and
   response. A JSON response opens as a tree; Ctrl-click leaf values, name them, "Insert" -> `json_extract`.
   A non-JSON response (HTML fragment, XML, text) opens in the same Source viewer as workflow 1.
   "Copy request into script" inserts the replay (`request_code.py`): the whole point of finding the XHR is that
   the script calls it directly instead of loading the page.
3. **Browser page -> right-click.** The page's context menu gains "Scraper" entries. Selected rendered text
   cannot be mapped to a source offset reliably, so the browser side computes the selection's CSS selector /
   XPath in the page (JS, via `runJavaScript`) and also offers "Show in Source" (best-effort text search).

## Snippet actions (Source tab)

| Action | Generated code (example) |
|---|---|
| Split document at selection | `parts = html.split('<div class="item">')` |
| Text after selection | `after = html.partition('Price:')[2]` |
| Text before selection | `before = html.partition('</table>')[0]` |
| Find position | `pos = html.find('Price:')` |
| Between two marks (mark start, then select end) | `value = html.partition('Price: ')[2].partition('<')[0]` |
| Regex capture around selection | `m = re.search(r'Price: (.*?)<', html, re.S)` |
| All matches | `values = re.findall(r'Price: (.*?)<', html, re.S)` |
| CSS selector of enclosing element | `value = soup.select_one('div.item > span.price').get_text(strip=True)` |
| XPath of enclosing element | `value = tree.xpath('//div[@class="item"]/span')[0].text_content()` |
| Attribute value (selection is inside an attribute) | `href = soup.select_one('a.buy')['href']` |
| Strip tags / get text | `text = BeautifulSoup(html, 'lxml').get_text(' ', strip=True)` |

**Ambiguity rule.** If the selected text occurs more than once, the action does not silently pick a different
occurrence. The marker grows outward (left context for "after", right context for "before") until its FIRST
occurrence in the document is the selected one (that is all `partition` / `find` need), and the snippet says
so in its warnings; if the selection already is the first occurrence it warns that the code uses the first.
Regex actions use the shortest left/right context (whole tags, whitespace-flexible) whose first match is exactly
the selection. Every action's output is verified by tests that `exec` the generated code against sample
documents (indented, minified, CRLF, repeated rows) -- no GUI needed. Not built: "Strip tags / get text".

## XHR capture

- AS BUILT: two `QWebEngineScript`s injected at document creation into the page's own (main) JS world, in all
  frames: Qt's `qwebchannel.js`, then `scraping/capture_hook.py`'s script, which wraps `window.fetch` and
  `XMLHttpRequest`. Each finished call is sent as one JSON string to a `QWebChannel` object (`bridge`, Python
  class `CaptureBridge`) whose only slots are `record(str)` and `pageSource(str, str)`. It records method, URL,
  author-set request headers and body (string / URLSearchParams / FormData; the last two flagged `urlencoded` /
  `multipart` so the generated code uses `data=` / `files=`), status, response headers, and the response body
  when it is text (cut at 2 million characters and flagged; binary and `text/event-stream` skipped). The
  wrappers return the page's original promise / fire its original events and swallow their own errors.
  An earlier sketch used a second, isolated world relaying DOM events; one world was enough (spiked first).
- Because the channel lives in the page's world, page JavaScript can see `qt.webChannelTransport` and call
  those two slots. That is why every report goes through `parse_record()` (type-checked, size-capped) and
  nothing from a report reaches generated code except as a `repr()`'d string literal.
- Known limits of the hook (accepted for v1): requests made by Web Workers / Service Workers, requests made
  before the script runs, `sendBeacon`, and images/scripts/CSS are not captured. The browser's own headers
  (Cookie, Referer, User-Agent, ...) are invisible to page JS: the replay code adds Referer / Origin /
  User-Agent from what the page reports and never adds Cookie. A Chrome-DevTools-Protocol backend (complete,
  but needs a localhost debugging port) could replace the hook later; the inspector only sees
  `CapturedRequest` objects.
- Secrets: `Cookie` / `Authorization` / `Set-Cookie` values are **not** written into generated code by
  default; the snippet gets a comment saying a session/token is required and where to put it.
- The Source tab's "as served" text is `fetch(location.href, {credentials: 'include'})` run in the page
  (the original HTML the server sends, with this browser's cookies). "Rendered DOM" (`page.toHtml()`) is the
  second mode, since JS-built content only exists there.

## Claude assistant

- All the API work -- worker thread, streaming and Cancel, the key and its dialog, model and effort, refusal
  handling, errors, cost -- is `harness_designer/claude/` (CLAUDE_API_DESIGN.md), shared with other features.
  The assistant uses `claude.qt.ClaudeJob` so the GUI never waits, calls `claude.warm_up()` when the panel
  opens (the SDK's first import takes ~3 s), and shows `ClaudeError.user_message` on failure.
- The user pays for their own key: the panel shows what is about to be sent (selected snippet, XHR sample,
  current script) with sizes and a hard truncation cap, and nothing is sent without a click; after each
  answer it can show `Response.estimated_cost`.
- System prompt states the environment: Python 3.11, only `requests`, `beautifulsoup4`, `lxml`, `re`, `json`,
  stdlib; reply with one complete code block; match the existing variable names; keep a polite `timeout=`
  and a realistic `User-Agent`.
- A reply is shown in the assistant panel with Insert / Replace Script / Copy, never auto-applied.

## Running scripts

Question from the user: can a script run on a thread and still be terminated, and how do other applications
do a live script editor? Measured on this machine (Python 3.11.14, `kill_experiment.py` in the scratchpad):

| Script is doing | Thread + async exception (`PyThreadState_SetAsyncExc`) | Process + `terminate()` |
|---|---|---|
| tight Python loop | stopped in 16 ms | stopped in 3 ms |
| `time.sleep(30)` | **not stopped** (4 s) | 3 ms |
| blocking socket `recv` | **not stopped** (4 s) | 3 ms |
| loop wrapped in bare `except` | **not stopped** (4 s) | 15 ms |

A thread cannot be killed from outside in Python; an async exception only lands between bytecodes, so it
misses exactly what a scraper spends its time in (waiting on the network) and any `except Exception/BaseException`
swallows it. Real editors that need Stop to work (IDLE, Thonny, Spyder, Jupyter, PyCharm) run the user's code in
a **separate process** and interrupt or kill that; editors that run scripts inside the host process (QGIS,
Maya and Blender consoles) simply freeze the application on a runaway script.

Plan: a `runner.py` that starts the script in a child process (`multiprocessing`, spawn; the app already calls
`freeze_support()` and has `process/`), streams stdout/stderr and the final status back to the console pane
through a queue read by a worker thread, and implements Stop as `terminate()`. The GUI thread never blocks.
"From a thread" is satisfied in the sense that matters (the UI stays live and the run is stoppable); the run
itself is a process. Child-process caveat to solve in Phase 4: importing anything under `harness_designer`
runs the package `__init__` (Config, logger), so the child must use a runner entry point that avoids that or
tolerates it (see MEMORY.md "Config is a live DB").

## Phasing

1. **Snippet engine (pure Python, tested by execution).** DONE 2026-10-16: `snippets.py`, `html_locate.py`,
   `request_code.py`, dependencies added to `pyproject.toml` / `requirements.txt`, `tests/scraping/`. No Qt,
   no app launch. Not yet covered: a Source-tab "mark start, then select end" UI flow for `between` (the
   function exists; the UI is Phase 2), and `json_extract` has no tests yet.
2. **Browser + capture + inspector.** DONE 2026-10-16 (see "Phase 2 as built"). Verified headless against a
   local HTTP server; NOT yet run in the real application.
3. **Script editor dock + Claude assistant.** Editor dock, insert-at-cursor (`insertion.insert_snippet` is
   ready and reused), assistant panel. The Claude API layer it needs (client, key dialog, jobs) is DONE in
   `harness_designer/claude/` (2026-10-17); the assistant only supplies prompts and UI on top of it.
4. **Run / Stop.** `runner.py`, console pane.
5. **MainFrame wiring.** PARTLY DONE: `MainFrame.show_scraper_browser()` creates the dock on first call, restores
   its saved position, shows it, and is torn down in `closeEvent`'s sequence. Still to do: the same for the
   script editor, the toolbar buttons (icons), and the system-menu entries (location undecided by the user).
   Until a button or menu entry calls `show_scraper_browser()`, nothing in the app opens the browser.

## Phase 2 as built

- **Opening it:** call `mainframe.show_scraper_browser()` (from a toolbar button or menu action). The dock is
  `Web Browser`, right dock area, browser on the left and the inspector on the right (a splitter).
- **Address bar** takes `example.com/shop`, `localhost:8000`, or a full URL (`scraping/url_input.py`).
- **Profile:** persistent under `<appdata>/scraper/browser_profile` (cookies survive, so logged-in sites work).
  The user agent has the `QtWebEngine/x.y.z` token removed so sites see an ordinary Chrome.
- **Locked down:** downloads are cancelled with a message, every permission request (camera, location,
  notifications) is denied, and `target="_blank"` / `window.open` open in the same view.
- **Source tab:** "As served" re-downloads the page with the browser's cookies using the page's ORIGINAL fetch
  (so it does not appear in the Network list) -- that is what a `requests` script receives. "Rendered DOM" is
  `page.toHtml()`. Updates after each page load (checkbox) or with Refresh. Rendered-DOM selections add a
  warning to the generated code. Long lines are broken for display only (`soft_wrap.py`); selections map back
  to offsets in the original text, including across CRLF line ends.
- **Right-click in the page:** Scraper > Show the selected text in Source; selector for this element (text /
  every similar element / link / image).
- **Network tab:** rolling window of 2000 requests, filter box, JSON-only, Clear. Selecting a row opens the
  Response tab: JSON as a lazy tree (select values with Ctrl-click, rename the variable in the last column,
  "From every item"), anything else in the Source viewer; "Repeat this request in the script".
- **Code lands in** the inspector's "generated script" pane (a `CodeEditorCtrl`): imports are merged at the
  top once, warnings become `# NOTE:` comments, each insertion is one undo step, and the line that downloads
  the page (or replays the request) is inserted first when the script does not have it yet.
- **Gotchas found while building it** (each has a test):
  - PySide6: the wrapper `QAction.menu()` returns OWNS the submenu -- a temporary one that is collected destroys
    the submenu and its actions. Production code never calls it (`addMenu()` results are fine); tests use
    `findChildren`.
  - `QWebEngineHistory` has no change signal; the back/forward buttons follow `urlChanged`.
  - `QSortFilterProxyModel.invalidateFilter()` is deprecated in Qt 6.9+; use `beginFilterChange()` /
    `endFilterChange()`.
  - `QWebEnginePage.runJavaScript` cannot await a promise, so the "as served" source comes back through the
    channel (`bridge.pageSource`) instead of the callback.
  - Executing a snippet's `import requests` line in a test replaces a fake `requests` with the real one (one
    test made a real GET before this was caught); tests now swap `sys.modules['requests']`.

## Open points

- QtWebEngine adds roughly 150-300 MB to the frozen build (Chromium); not measured here.
- Browser profile: persistent (cookies survive, so logged-in sites work) under `get_appdata()`. Built that way
  without asking; not yet confirmed with the user. A Clear Data action (cookies / cache) is not built.
- Whether scraped output feeds the parts database (global_db importers) is out of scope here.
