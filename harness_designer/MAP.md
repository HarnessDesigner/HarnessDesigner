## FILES

#### __init__.py

Package init — no logic beyond making `harness_designer` importable (a bare `import harness_designer` still triggers `config.py`'s `Config.open()` and the logger's startup, see below).

#### __version__.py

Version string only, no logic.

#### app.py

Qt application bootstrap. `App(QtCore.QObject)` owns the `QApplication`, splash screen, background loading thread, and shutdown sequence. Sets `AA_ShareOpenGLContexts` and `QSG_RHI_BACKEND=opengl` at **import time**, before the `QApplication` is constructed — both are load-bearing and easy to break by moving/removing. `AA_ShareOpenGLContexts` is what lets uploaded model VBOs be shared across every GL canvas (editor3d, model_preview) — see `gl/MAP.md`'s 3D rendering pipeline notes. `QSG_RHI_BACKEND=opengl` exists because the 3D canvases are `QOpenGLWidget`s (Qt composes the main window with OpenGL) while `QWebEngineView` (`ui/web_viewer/`) is a `QQuickWidget` whose default Windows API is Direct3D 11 — without this setting the first browser dock re-creates the main window's native window (a Hide then a second Show — and `MainFrame.showEvent` re-runs `_open_project`, so the open-project dialog reappears) and the page renders black. Also defines `CallAfter(func, *args)` (marshal a call onto the main thread via a Qt **direct** signal connection — runs synchronously if already on the main thread, no deferral) and `CallLater(func, *args)` (`QTimer.singleShot(0, ...)` — always defers until the event loop regains control after the current handler returns; use this when deferring work that must happen after the current call stack unwinds, e.g. after a selection signal has propagated and the GL canvas has painted) and `CallAfterStart` (startup-time variant used before the signal plumbing is fully wired).

#### check_types.py

`do(func)` — a decorator that validates argument/return values against their type annotations at **call time** via `isinstance`, applied as `@_check_types.do` to essentially every function/method in the package (~6179 call sites across 587 files). No-ops entirely when frozen (`hasattr(sys, 'frozen')`) — dev-only diagnostic, never adds overhead to the shipped build. Built because the Cython-compiled release build only reveals a bad type hint when that exact code path runs *after* a full compile, so a wrong annotation used to mean compile → crash → fix one hint → recompile, repeated many times; this collapses that loop to "run the app, read the print, fix, no rebuild needed." Deliberately excludes itself, the two `.pyx` Cython files, the entire `logger/` package (decorating it creates a feedback loop — a check_types error reported *through* logging, itself decorated, can deadlock `LogHandler.flush()`'s worker-thread barrier), and the entire `process/` package (excluded on the user's explicit instruction, "I know all of that works properly," not because the mechanism is broken). A bare `-> None` return annotation was the single biggest source of false crashes during rollout (normalized internally now). A `TYPE_CHECKING`-only forward reference that fails to resolve is treated as unverifiable and the check is **accepted**, not rejected, by design (the codebase's standard `_Union["_module.SomeClass", None]` circular-import-dodge convention depends on this). If you hit `TypeError: isinstance() arg 2 must be a type, a tuple of types, or a union`, check whether it's a genuine annotation bug (a factory function, a wrong stdlib type, a copy-paste typo) before assuming it's a checker gap — about half the crashes found during rollout were real bugs in the app's own type hints. Any temporary diagnostic print added *inside* the decorator must use `sys.__stdout__.write(...)`, never bare `print()` — real stdout may be redirected through app machinery that's itself decorated, and a naive `print()` inside every function's wrapper can recurse.

#### color.py

`Color` — the app's color value type. `ColorMeta` (metaclass) intercepts construction; `Color` itself is `CallbackMixin`-backed (see `app_mixins/MAP.md`) so bound listeners are notified on any channel change, the same reactive pattern `Point`/`Angle` use — one of the three primitives making up the codebase's callback/reactive backbone. Exposes `Get*`/`Set*`/`SetRGBA` plus HSV conversions (`colorsys`).

#### config.py

`Config` — the app's settings object. `_ConfigTable`/`_ConfigDB` wrap a SQLite table/connection; the `ConfigDB` metaclass backs every nested `Config.*` class (e.g. `Config.editor3d`, `Config.logging`) so that attribute writes persist straight to `%APPDATA%\HarnessDesigner\config.db` on every non-underscore assignment — `Config.logging.save_path = x` is a permanent, immediate change to the user's real app settings, indistinguishable from a change made through the running app. **Only values changed via a UI element actually get written** — an untouched setting always falls back to the class default in code, so editing a default in `config.py` propagates to users who never touched that setting. This also fires on a bare `import harness_designer`: `config.py` calls `Config.open()` unconditionally at module import time (and `logger/` constructs its `Log()` singleton at import time too, scanning/creating real log files) — **never read or assign `Config.*` in a throwaway script**; sandbox `USERPROFILE`/`HOME` to a scratch directory first if you need to exercise anything that imports this package at all. `Config.__table_name__` derives from `cls.__qualname__` (the full dotted nesting path, not `cls.__name__`) specifically to avoid short-name collisions across nested config classes — part of the codebase-wide `__name__`-dunder "hands off, including from subclasses" naming convention (see MEMORY.md's "Naming convention: dunders" entry).

#### critical_error_dialog.py

`CriticalErrorDialog(QtWidgets.QDialog)` — the last-resort "the app hit an unhandled error" dialog: formats a traceback (`traceback.format_exception`) into a read-only `QTextEdit`, always-on-top, no native close button. Predates/parallels `ui/dialogs/dialog_base.py`'s `BaseDialog` but is intentionally standalone since it must work even if the rest of the UI machinery is what's broken. Exists because uncaught exceptions must never propagate out of low-level layers in this PyInstaller-frozen app — they're always caught, logged, and swallowed; this dialog is the deliberate surface for the rare case where something still needs to tell the user the app is dying.

#### debug.py

`DebugPrinter` — a callable debug-print object (`__call__(*args, end_stack=False)`) that can be pointed at the real logger (`set_logger`) so debug output goes through the same channel as everything else instead of bare `print()`; `_Record` looks like a captured call-site record (args plus, optionally, a stack trace) for later inspection.

#### memory_diagnostics.py

Diagnostic formatters for memory/GPU introspection: `_format_tracemalloc`/`_format_objects`/`_format_growth` (Python-level memory tracking via `tracemalloc`/object counts), `_format_gpu`/`_format_backend`/`_make_gpu_detector` (reports from whichever `gpu/` vendor backend is active — see `gpu/MAP.md`). Likely wired into a debug menu or log dump rather than imported for normal app logic.

#### monkey_patch.py

`get_offsets(hwnd)` — small Windows-specific helper (window frame offset lookup), decorated with `@_check_types.do` like everything else.

#### ocp_ops.py

OCP (OpenCascade / `cadquery-ocp`) text-to-mesh pipeline: `build_text_mesh(text, font_size, depth, font=..., font_style=..., text_align=..., ...)` renders a string through OCP's font/BRep machinery (`_get_font`, `StdPrs_BRepFont`), extrudes and fuses it into a solid (`_extrude_and_fuse`), and tessellates the result into plain vertex/index arrays (`_tessellate_shape`) the rest of the app's mesh pipeline can consume — `FontStyle`/`TextAlign` enums configure the request. This is almost certainly what backs cavity/part label engraving (see `geometry/cavity_layout.py` in `geometry/MAP.md`, and `shapes/text.py` in `shapes/MAP.md`) — one of the deliberate, narrow exceptions to "the rest of the app doesn't use build123d/OCP directly."

#### ocp_threadworker.py

`OCPThreadTask` — a context-manager-shaped (`__enter__`/`__exit__`) callable wrapper (`__call__`, `result()`) for running an OCP operation (e.g. `ocp_ops.build_text_mesh`) off the GUI thread, since OCP calls are almost certainly blocking/CPU-heavy like the rest of the mesh-import pipeline (see `process/model_process.py`).

#### process_memory.py

`get_process_memory()` — cross-platform current-process memory usage (`_windows_memory` via a hand-rolled `ctypes.Structure` for `PROCESS_MEMORY_COUNTERS_EX`, `_linux_memory` via `/proc`), feeding `memory_diagnostics.py`'s reports. No macOS implementation found at this layer.

#### resources.py

Image/model/datasheet file I/O helpers (download, zip/unzip, save/remove) and their exception hierarchy — `ResourceException` base, with `RequestsError`, `ImageReadError`, `SaveFileError`, `RemoveFileError`, `FileTypeNotSupportedError`, `ExistingFileNotFoundError`, etc. as concrete failure modes callers can catch individually.

#### splash.py

`Splash` — the startup splash screen (`_SplashSignals` carries cross-thread updates onto the GUI thread). `wait()`/`Show()`/`Destroy()`/`SetText()`/`flush()` plus a progress-bar API (`start_progress`/`set_progress`/`end_progress_bar`) driven from the background loading thread `app.py` starts.

## FOLDERS

#### add_handlers/

Placement-session ("Add X") handlers — one per object type per view. See `add_handlers/MAP.md`.

#### app_mixins/

Application-level mixins, most importantly the `CallbackMixin` reactive backbone. See `app_mixins/MAP.md`.

#### bounds/

Pooled bounding-box / wire-path storage, one set per view. See `bounds/MAP.md`.

#### crash_dump/

Crash-dump capture/writing. See `crash_dump/MAP.md`.

#### database/

The whole DB layer: catalog (`global_db`), per-project (`project_db`), seed/creation (`create_database`), and connectors. See `database/MAP.md`.

#### drag_handlers/

Per-object-type drag handlers for all three views. See `drag_handlers/MAP.md`.

#### exporter/

Project export. See `exporter/MAP.md`.

#### geometry/

Point/line/angle/quaternion primitives, including the `Point`/`Angle` halves of the callback backbone. See `geometry/MAP.md`.

#### gl/

OpenGL rendering: canvases, shaders, materials, culling, VBO/arena management. See `gl/MAP.md`.

#### gpu/

Per-vendor GPU memory monitoring. See `gpu/MAP.md`.

#### handlers/

Selection/interaction handlers, one per part type, plus the orthogonal wire-routing engine. See `handlers/MAP.md`.

#### image/

Image loading plus bundled icon/cursor/image assets. See `image/MAP.md`.

#### licenses/

Bundled third-party license text. See `licenses/MAP.md`.

#### logger/

Logging (handler + stdout/stderr redirection). See `logger/MAP.md`.

#### models/

See `models/MAP.md`.

#### objects/

Scene-object wrapper classes and their per-view (3D/schematic/pegboard) renderable counterparts. See `objects/MAP.md`.

#### plugins/

The plugin registration framework, including the provider-agnostic AI plugin contract. See `plugins/MAP.md`.

#### process/

Multiprocessing: DB/model/image worker processes. See `process/MAP.md`.

#### ray_tracing/

Offline renderer (BVH-based). See `ray_tracing/MAP.md`.

#### rope_pull/

The peg-board rope-pull solver (keeps a wire's/bundle's peg-board polyline length matching its real 3D length while dragged). See `rope_pull/MAP.md`.

#### rotation_handlers/

The rebuilt protractor-style rotation gizmo, per view. See `rotation_handlers/MAP.md`.

#### scraping/

Point-and-click scraper authoring (non-UI logic). See `scraping/MAP.md`.

#### shapes/

Procedural geometry generators (box, sphere, cylinder, ...). See `shapes/MAP.md`.

#### themes/

Theme manager (Dark/Light). See `themes/MAP.md`.

#### ui/

Every Qt window/dock/dialog/widget in the app. See `ui/MAP.md`.

#### utils/

Stateless utility helpers (paths, conversions, mesh/geometry math). See `utils/MAP.md`.

#### wire_routing/

Orthogonal (H/V-only) auto-routing for the 2D schematic editor's wires. See `wire_routing/MAP.md`.
