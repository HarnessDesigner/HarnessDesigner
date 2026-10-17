# Scraper tool design

Point-and-click scraper authoring inside harness_designer: a built-in web browser, tools that turn what the
user sees/selects (page source text, XHR/fetch responses) into Python code, a script editor, and a Claude
assistant that helps design the scraper. Add new scraper decisions HERE, not in MEMORY.md.

Status (2026-10-17): design agreed. Phases 1 (snippet engine), 2 (browser, XHR capture, inspector), 3 (script
editor dock + Claude assistant) and 4 (run / stop, console, examples) are built; they have NOT been run in the real
application, and the assistant has only ever talked to a fake server, never the live API. Phase 5 (toolbar buttons,
menu entries) is partly done. See "Phasing" and the "Phase N as built" sections.

Tests: there are none, and none are to be written (user, 2026-10-17). Phases 1-2 and the Claude package had
`unittest` suites (the snippet engine run against sample pages, the widgets headless, QtWebEngine against a local
HTTP server, the Claude client against a fake Messages API server); they are gone from the working tree and exist
only in git history. The checks made while building Phases 3 and 4 (the assistant panel, the runner, the examples,
the editor) were made the same way and never committed. So where this file says something was "checked" or "seen
working", it was checked once, headless, and cannot be re-checked from the repository; none of it has been run in
the real application.

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
- **Running scripts (user, 2026-10-17): in a thread of the application process; a Stop button raises `SystemExit`
  in it.** A warning says when that cannot work (a wait at the OS level) and examples show how to write scripts whose
  waits can be ended from outside. See "Running scripts".

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
    assistant.py       system prompt, what can be sent + its budgets, the message, reply parsing   [Phase 3]
    assistant_tools.py the tools Claude checks selectors / JSON paths with, against the real page  [Phase 3]
    script_files.py    read / atomic write of scripts, the autosaved working copy's path           [Phase 3]
    runner.py          run a script in a thread of this process; Stop raises SystemExit in it    [Phase 4]
    examples.py        the editor's Examples: scripts whose waits can be ended from outside       [Phase 4]
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
harness_designer/ui/editor_script/      the Script Editor dock                                         [Phase 3]
    script_editor.py   ScriptEditorPanel (CodeEditorCtrl, file toolbar, working copy) + ScriptEditor(DockBase)
    assistant_panel.py AssistantPanel -- the Claude assistant under the editor
    console_panel.py   ConsolePanel -- the runs, their output, Stop's state and the "did not stop" signal [Phase 4]
    message_dialog.py  ask() -- a message with buttons in the application's dialog style              [Phase 4]
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
the selection. Every action's output was checked by `exec`-ing the generated code against sample
documents (indented, minified, CRLF, repeated rows) while the tests existed. Not built: "Strip tags / get text".

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
- As built (it differs from this sketch in places -- per-piece budgets instead of one truncation cap, tools that
  check selectors, a refresh rule for the tick boxes): see "Phase 3 as built".

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

**Decision (user, 2026-10-17): the script runs in a THREAD of the application process, and a Stop button raises
`SystemExit` inside it** (`PyThreadState_SetAsyncExc`, as in the user's own snippet). The child-process plan that was
recommended here (a `multiprocessing` runner with Stop = `terminate()`) was heard and not taken: the user's position
is that some responsibility is left to the person writing the script, because no scheme makes a script editor
completely safe. Do not move this to a child process without asking. What the choice costs, measured on this
machine on 2026-10-17 (`kick_experiment*.py`):

- Stop only reaches a thread while it is running Python code. A thread inside a blocking OS call is not reached:
  `time.sleep()`, a socket read with no timeout, `Thread.join()`, `Queue.get()`, `Lock.acquire()`. A bare
  `except:` swallows it (pressing Stop again helps).
- A single thread cannot be signalled: Windows has no `pthread_kill`; `CancelSynchronousIo` answered "nothing to
  cancel" for a thread in `recv`; `socket.shutdown()` from another thread did not wake it. What does wake it is
  closing the socket from outside: plain `sock.close()` for a bare socket, and for `requests` (which reads through
  `makefile()`, so `close()` is deferred) the C-level `_socket.socket.close(sock)`. On Linux/macOS `shutdown()`
  is what wakes a reader, so the examples do `shutdown()` then `close()`.
- A catastrophic regex (any long native call that holds the GIL) cannot be interrupted and freezes the whole
  application, GUI included: the main thread's heartbeat stopped when the regex started and never resumed.
  Accepted by the user; the only way out is to close the application.
- `os._exit()`, a crash inside a C extension, or a script that closes the application's own resources take the
  application with them.

What is built instead of the guarantee: Run / Stop with a console (several runs may be alive at once), a **warning
that appears when Stop has not taken effect** (the script is waiting at the OS level, and what to do about it),
and **Examples** in the editor that teach the pattern that makes a wait endable: do the blocking work in a
`threading.Thread` SUBCLASS that keeps the socket / `Event` / `Queue` it waits on as instance attributes and has a
`stop()` method; then a second script, run while the first is stuck, walks `threading.enumerate()`, finds the thread
that holds such an object and ends the wait on it.

## Phasing

1. **Snippet engine (pure Python).** DONE 2026-10-16: `snippets.py`, `html_locate.py`, `request_code.py`,
   dependencies added to `pyproject.toml` / `requirements.txt`. No Qt, no app launch. Not yet covered: a
   Source-tab "mark start, then select end" UI flow for `between` (the function exists; the UI is Phase 2).
2. **Browser + capture + inspector.** DONE 2026-10-16 (see "Phase 2 as built"). NOT yet run in the real
   application.
3. **Script editor dock + Claude assistant.** DONE 2026-10-17 (see "Phase 3 as built"): editor dock,
   insert-at-cursor (`insertion.insert_snippet` reused), assistant panel. The Claude API layer it sits on (client,
   key dialog, jobs) is `harness_designer/claude/`; the assistant only supplies prompts, tools and UI. NOT yet run
   in the real application or against the live API.
4. **Run / Stop.** DONE 2026-10-17 (see "Phase 4 as built"): `runner.py`, console tab, the "did not stop" warning,
   Examples. Thread-based, as the user decided; NOT yet run in the real application.
5. **MainFrame wiring.** PARTLY DONE: `MainFrame.show_scraper_browser()` and `MainFrame.show_script_editor()` each
   create their dock on first call, restore its saved position, show it, and are torn down in `closeEvent`'s
   sequence; `_link_scraper_docks()` joins the two once both exist. The General toolbar opens them (2026-10-17): the
   existing "Internet" button (its handler was an empty stub) calls `show_scraper_browser()`, and a new "Script
   Editor" button (icon `note_pen`, which nothing else used) calls `show_script_editor()`; the editor's Run / Stop
   use the `run_script` / `stop_script` icons that were already in the set. Still to do: the system-menu entries
   (location undecided by the user).

## Phase 2 as built

- **Opening it:** the General toolbar's Internet button (`mainframe.show_scraper_browser()`). The dock is
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
- **Gotchas found while building it:**
  - PySide6: the wrapper `QAction.menu()` returns OWNS the submenu -- a temporary one that is collected destroys
    the submenu and its actions. Never call it (`addMenu()` results are fine); find submenus with `findChildren`.
  - `QWebEngineHistory` has no change signal; the back/forward buttons follow `urlChanged`.
  - `QSortFilterProxyModel.invalidateFilter()` is deprecated in Qt 6.9+; use `beginFilterChange()` /
    `endFilterChange()`.
  - `QWebEnginePage.runJavaScript` cannot await a promise, so the "as served" source comes back through the
    channel (`bridge.pageSource`) instead of the callback.

## Phase 3 as built

- **Opening it:** the General toolbar's Script Editor button (`mainframe.show_script_editor()`). The dock is `Script Editor` (right dock area): the editor on
  top, a tab area underneath that holds the assistant (Phase 4's console will be a second tab). When both docks
  exist `MainFrame._link_scraper_docks()` connects them -- creating the second one triggers it, in either order:
  `inspector.set_sink(editor)` (code made in the Source / Response tabs lands in the editor, and a closed editor
  is shown again) and `assistant.set_context(inspector)`.
- **The editor** (`ui/editor_script/script_editor.py`): `CodeEditorCtrl` with New / Open / Save / Save as / Undo /
  Redo; the header shows the file name and `*` when there are unsaved changes. Saving is atomic
  (`scraping/script_files.py`: temporary file + `os.replace`), always UTF-8 with `\n` line ends. The dialogs start
  in `<Documents>/HarnessDesigner/scrapers`. **The working copy is not lost:** a second after the last change the
  unsaved text is written to `<appdata>/scraper/scratch_script.py`, and when the application closes it is written
  once more; next time it comes back marked "recovered". Saving to a file, or New, removes it. New / Open with
  unsaved changes asks Save / Discard / Cancel.
- **What the assistant sends** (`scraping/assistant.py`). The user ticks pieces: the script, the text selected in
  the editor, the open page's address, the text selected in the page source (with 1,500 characters either side,
  the selection marked), the network request picked in the inspector, and the start of the page source (off by
  default). Each has a budget (script 60,000 characters, selected editor text 8,000, selected source text 4,000,
  request body 4,000, response 8,000, page source 40,000) and the whole message is capped at 100,000 characters
  (about 33,000 tokens). A script over its budget makes its box unavailable, with the reason as the tooltip -- it
  is never cut silently. Cookie / Authorization / Set-Cookie header values are replaced by "[omitted - secret]";
  a JSON response goes as a digest (long lists and strings shortened). The panel shows the size and a cost
  estimate for the model in use, "Preview" shows the exact text, and nothing is sent until Send (Ctrl+Enter).
  "Edit my script" asks for one complete script in a single python block; "Just answer" asks only for an answer.
- **The tick boxes are current when it matters.** They are refreshed when the editor's text or selection changes,
  every 0.7 s while the panel is visible (nothing signals a selection change in the browser dock), and at the
  moment Send is pressed. A box the user has clicked keeps their choice.
- **Claude checks before it answers.** Four tools run against the real page and the picked response, on the worker
  thread (`scraping/assistant_tools.py`): `find_text`, `test_css_selector` (BeautifulSoup + lxml, as the script will
  run it), `test_xpath` (lxml.html) and `inspect_json`. They only read plain Python state through the context
  (`page_source()`, `selected_request()`), never a widget. A tool with nothing to look at says so, and the model is
  told to ask the user to load a page or pick a request. There is deliberately no regex tool: a pattern with
  catastrophic backtracking cannot be interrupted, which would break Stop. Each check is listed under the
  answer ("Claude checked: ...").
- **An answer is never applied by itself.** The code blocks in the reply are listed, the last Python block is
  preselected (replies end with the whole script), and the user chooses Insert at cursor, Replace script (one
  undo step each) or Copy. "View changes" shows a coloured unified diff against the current script first.
- **The chat.** One append-only `Conversation` (system prompt and the four tools fixed when it is created);
  the next message continues it and "New chat" starts over. Changing the model or effort in the settings dialog
  starts a new chat by itself (a conversation's settings are fixed) and says so. A failed or stopped turn is rolled
  back, so the next message does not carry it. With no key the panel opens the settings dialog instead of sending.
- **Settings button:** opens `claude.qt.key_dialog.ApiKeyDialog` (key, model, effort, Test) and then refreshes the
  header line ("<model>, <effort> effort"). This is the first place in the UI that opens that dialog.
- **`ScraperInspector` is the `AssistantContext`** (`page_url`, `page_source`, `source_selection`,
  `selected_request`); `EmptyContext` is what the assistant sees when there is no browser.
- **Gotchas found while building it:**
  - Qt's `QAction.triggered(bool)` passes `checked` as the first argument, so connecting a bound method such as
    `open_script(path)` directly puts `False` in `path`. The toolbar goes through `lambda checked=False: callback()`.
  - The tick boxes were only refreshed by the timer, so a task typed right after the script was written was sent
    without it. Now they refresh on every editor change and again at Send.
  - The editor's highlighter re-lexes the whole document for every line (it says so in `code_editor_ctrl.py`), so
    its cost grows with the square of the line count: a 20,000-line paste froze the editor for minutes. That is
    fine for scraper scripts, but opening a very large file will hang it.

## Phase 4 as built

- **Run / Stop** (`F5` / `Shift+F5`, in the editor's toolbar). Run takes the text in the editor as it is now, saved
  or not, and starts it in a `ScriptRun` thread (`scraping/runner.py`, no Qt). Several runs may be alive at once --
  that is what lets a second script release a stuck first one. The script gets a fresh namespace
  (`__name__ == '__main__'`, `__file__` = the saved path or `<name run N>`), so runs share nothing but the process.
  `print` is the script's own (the thread's output goes to the console, not to `sys.stdout`, so nothing global is
  patched); `print(file=sys.stderr)` also goes to the console; `input()` raises (there is no keyboard input). A
  failure shows the traceback from the script's first frame on, with the script's own lines. `sys.exit()` is a
  normal end. Threads are daemon threads, so a stuck script cannot keep the application from closing.
- **Stop** raises `SystemExit` in the script's thread (`PyThreadState_SetAsyncExc`, as in the user's own snippet), so
  `finally` blocks run. It is not lost when it cannot be delivered: it stays pending and fires the moment the thread
  next runs Python code -- when the wait ends. Pressing Stop again sends it again.
  Stop goes to the thread the script runs in, NOT to threads the script started: those keep running unless the
  script stops them (the examples do it in an `except BaseException:` clause around the wait).
- **The Console tab** (`ui/editor_script/console_panel.py`) lists the runs (`#2 shop.py - running`), shows the
  selected run's output, keeps collecting a run's output after it ended (threads the script started may still print),
  and shows the state (`Running (12 s)` / `Stopping...` / `Finished in 3.2 s` / `Failed ...` / `Stopped ...`).
  "Clear finished" forgets ended runs; the 20 newest ended runs are kept. Output the console cannot keep up with is
  dropped oldest-first and counted. Stop in the toolbar is enabled only while the run shown is running.
- **The warning.** If a run is still going 2 seconds after Stop, a dialog (the application's dialog style,
  `ui/editor_script/message_dialog.py`; not `QMessageBox`) says why -- the script is waiting at the operating system
  level, out of Stop's reach; the Stop stays pending -- and what to do, with a button that opens the "Release a
  stuck script" example. Once per Stop press. The same text is in the console's status line.
- **Examples** (toolbar menu; code in `scraping/examples.py`): "A wait that can be ended from outside" (the user's
  own pattern: a `Thread` subclass with `exit_event = threading.Event()`), "A download whose network read can be ended"
  (the socket kept as `self.sock`; `stop()` does `shutdown()` then `close()`), "A plain script with its socket on the
  thread" (`threading.current_thread().sock = ...`), and "Release a stuck script": run it while another script is
  stuck; it lists every thread with the public attributes it holds, and when `TARGET` names one, sets its
  `exit_event` and closes its `sock`. Opening an example replaces the editor's text (asking Save / Discard / Cancel
  first). Conventions the examples agree on: `exit_event`, `sock`, short `join(0.2)` slices instead of a bare
  `join()`, `daemon=True`. The examples were run for real against a local server that never answers (stuck in
  `join()`, Stop ignored, the release script run, the stuck script ends) while the tests existed; they have not
  been run since.
- **Dialogs:** the Phase 3 save / warn prompts used `QMessageBox`, which nothing else in the application does; they
  now use `message_dialog.ask()` (a `BaseDialog`).
- **Not built, on purpose:** an automatic "close this script's network connections" button in the warning (the
  tracked-socket approach measured in `kick_experiment3.py` would work); the user chose examples that teach the pattern
  instead. Easy to add later if the examples prove too much work for users.

## Open points

- The assistant has never talked to the live API (only the fake server). The first real session will show whether
  the prompts, the tool loop and the thinking-with-tools handling behave as intended; worth doing once, with a
  cheap effort setting, before relying on it.
- `CodeEditorCtrl`'s highlighter is quadratic in the number of lines (see Phase 3 gotchas): opening or pasting a
  file of a few thousand lines will freeze the editor for a long while. Not changed (it is not part of this
  feature and is documented in the widget); a cheap fix would be to lex once per edit instead of once per line.

- QtWebEngine adds roughly 150-300 MB to the frozen build (Chromium); not measured here.
- Browser profile: persistent (cookies survive, so logged-in sites work) under `get_appdata()`. Built that way
  without asking; not yet confirmed with the user. A Clear Data action (cookies / cache) is not built.
- Whether scraped output feeds the parts database (global_db importers) is out of scope here.
