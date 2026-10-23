## FILES

#### __init__.py

Package init — no logic beyond making `harness_designer` importable (a bare `import harness_designer` still triggers `config.py`'s `Config.open()` and the logger's startup, see below).

#### __version__.py

Version string only, no logic.

#### app.py

Qt application bootstrap. `App(QtCore.QObject)` owns the `QApplication`, splash screen, background loading thread, and shutdown sequence. Sets `AA_ShareOpenGLContexts` and `QSG_RHI_BACKEND=opengl` at **import time**, before the `QApplication` is constructed — both are load-bearing and easy to break by moving/removing. `AA_ShareOpenGLContexts` is what lets uploaded model VBOs be shared across every GL canvas (editor3d, model_preview) — see `gl/MAP.md`'s 3D rendering pipeline notes. `QSG_RHI_BACKEND=opengl` exists because the 3D canvases are `QOpenGLWidget`s (Qt composes the main window with OpenGL) while `QWebEngineView` (`ui/web_viewer/`) is a `QQuickWidget` whose default Windows API is Direct3D 11 — without this setting the first browser dock re-creates the main window's native window (a Hide then a second Show — and `MainFrame.showEvent` re-runs `_open_project`, so the open-project dialog reappears) and the page renders black. Also defines `CallAfter(func, *args)` (marshal a call onto the main thread via a Qt **direct** signal connection — runs synchronously if already on the main thread, no deferral) and `CallLater(func, *args)` (`QTimer.singleShot(0, ...)` — always defers until the event loop regains control after the current handler returns; use this when deferring work that must happen after the current call stack unwinds, e.g. after a selection signal has propagated and the GL canvas has painted) and `CallAfterStart` (startup-time variant used before the signal plumbing is fully wired).

#### check_types.py

Runtime annotation check behind `@_check_types.do`, applied to essentially every function and method in the package (8,571 uses). Repurposed 2026-10-22: `do` used to validate arguments with `isinstance`, but that checker was dead code behind an unconditional `return func` and was removed (git history, last at commit `dfe1066`). It was first rewritten as a recorder of every type seen, then (user decision, same day) as what it is now: **it verifies the annotations itself, at run time, and stores only what does not fit.** The settings are plain constants near the top of the file (`_ENABLED`, `_FULL_CALLS` = the first N calls of each function are checked, `_STRIDE` = after that every Nth call, 1 = every call, `_FLUSH_SECONDS`, `_SITE_LIMIT`, `_SAMPLES`, `_SHAPE_DEPTH`); the user edited them by hand, so leave them as they are. The environment variable `HARNESS_TYPE_AUDIT_DB` names another database file (default `type_audit.sqlite3` in the repo root, git-ignored). With `_ENABLED` on, `do` wraps the function and, per checked call, compares every annotated parameter and the return value (each item, for a generator) with its hint. A hint is turned into a small tree on the function's first checked call, when its module is complete: classes (subclasses and ABC-registered classes accepted, `float` takes `int`), `X | None` / `Union`, generics (`list[int]`, `dict[str, X]`, `tuple[int, ...]`, `Iterable[X]`) judged on the contents sampled by `_shape` (up to 8 items, 3 levels deep, so a lone odd item in the middle of a long list can be missed), `Callable` (anything with `__call__`), `type[X]`, and quoted names that cannot be imported at run time (`TYPE_CHECKING` imports), which are matched by class name against the type's bases. A bare `_Name` that cannot be imported is an import alias (`from .. import ObjectBase as _ObjectBase` under `TYPE_CHECKING`): it is matched as `Name` and otherwise left alone -- matching it literally flagged every call (fixed 2026-10-23, after the first real run). An `__init__` builds the object and returns nothing, and by project convention has no return annotation (see MEMORY.md): its return is neither checked nor reported, so its rows show the parameters only (a subclass that does not override `__init__` is recorded against the base class's `__init__`, where it is defined). What cannot be understood (`TypeVar`, `Protocol`, `Literal`, `Self`, numpy scalars for a number hint) is never reported. Verdicts are cached per (function, slot, type), so a call that fits costs a few dict lookups (measured: ~0.36 us per call with 1000-then-every-8th, ~1.1 us with every call checked, ~0.05 us undecorated). **Storage, two tables.** `functions`: name, signature and return type as annotated, source file, line. `calls`: calling function, its file and line, the signature of the call as it was made (the type of everything passed), the type returned (empty when the call raised; a generator's wrong item shows as `yield X`). Before writing, the database is asked: is there a function with this name and source file (take its id, add it only if absent), and a call with that function id, calling function, calling file, signature and return type (add it only if absent). The line number is stored but is not part of the match. A function is matched by name + source file, so a property's accessors would collide: when the name is looked up, the class is found through the module and, if the attribute is a `property` whose getter / setter / deleter leads back to the function (through `__wrapped__`), the stored name gets `(getter) `, `(setter) ` or `(deleter) ` in front (`(setter) Terminal.size`). Each accessor is its own function with its own wrapper and state, so which one is running is always known; the label is worked out once per function. A decorator in between that does not keep `__wrapped__` hides the link and the plain name is used. At most `_SITE_LIMIT` rows are kept per (function, parameter, type that arrived). Wrong calls sit in plain lists until the flush thread writes them into an in-memory SQLite database every `_FLUSH_SECONDS`; that database is written to the file in one transaction, only when something was added, and once more at exit (`atexit` for the app; a `multiprocessing.util.Finalize` for the worker processes in `process/`, which leave through `os._exit` and skip `atexit`). The same look-up-then-add runs against the file, so the app, its workers and every session add to one file without repeats; delete the file to start over. A killed process, or an `os._exit` worker, loses at most one interval; a failed write is reported once and retried on the next tick; a file from an older layout is refused with a message saying to delete it. Forked children (not Windows) are not checked. It only ever runs from source, so it is not written or tested for the Cython-compiled case. Read the file with `diagnostics/type_audit_report.py`. Standalone by design (standard library only, no package imports) so it can be imported from anywhere without an import cycle. Deliberately free of type annotations except the signature of `do`, which is the ParamSpec form `Callable[_P, _R] -> Callable[_P, _R]` (user decision 2026-10-22): that is the one signature mypy, basedpyright and pyrefly all read as 'same signature in, same signature out', so every decorated function keeps its real signature at every call site (a bare `-> Callable` shows `(...) -> Unknown`; unannotated only works in some checkers, by accident). `do` ends in a `cast` so its typed signature is not held to the unannotated helpers. Do not add hints anywhere else in this file. A recorder failure is printed once to the real stderr and never raised into the app. Deliberately not decorated: this module itself, the `.pyx` files, the `logger/` package (a recorder problem reported through the logger, itself decorated, could deadlock `LogHandler.flush()`) and the `process/` package. Async functions are returned undecorated (there are none today). Coverage (2026-10-22): 8,571 of the 8,737 functions in the package carry the decorator (everything except this file). The 166 that do not are deliberate: `logger/` and `process/` (148), `debug.py`'s profiler internals (7), the `__init__.py`/`__main__.py` files (6; the Cython build skips them), and 5 functions that are themselves used as decorators (`capturable`, `dump_property` and the inner `decorator` of each, `register` in `shapes/text.py`). **Never decorate a function that is used as a decorator, or one nested inside such a function**: the typed `do` would hide what it returns from type checkers, which lose the call-site return inference that lets `@dump_property(...)` pass the decorated function straight through. Every closure made from one `def` shares a single recorder state (keyed by its code object), so a nested function decorated inside a hot function does not register a new state on every call. The 751 decorators added on 2026-10-22 were put in by a one-off byte-level codemod (innermost position, import added in the local group); it was purely additive and verified reversible. Not seen by construction: functions never called while recording, and code paths nobody exercised -- a clean report means no recorded value broke a hint, not that none ever will.

#### color.py

`Color` — the app's color value type. `ColorMeta` (metaclass) intercepts construction; `Color` itself is `CallbackMixin`-backed (see `app_mixins/MAP.md`) so bound listeners are notified on any channel change, the same reactive pattern `Point`/`Angle` use — one of the three primitives making up the codebase's callback/reactive backbone. Exposes `Get*`/`Set*`/`SetRGBA` plus HSV conversions (`colorsys`).

#### config.py

`Config` — the app's settings object. `_ConfigTable`/`_ConfigDB` wrap a SQLite table/connection; the `ConfigDB` metaclass backs every nested `Config.*` class (e.g. `Config.editor3d`, `Config.logging`) so that attribute writes persist straight to `%APPDATA%\HarnessDesigner\config.db` on every non-underscore assignment — `Config.logging.save_path = x` is a permanent, immediate change to the user's real app settings, indistinguishable from a change made through the running app. **Only values changed via a UI element actually get written** — an untouched setting always falls back to the class default in code, so editing a default in `config.py` propagates to users who never touched that setting. This also fires on a bare `import harness_designer`: `config.py` calls `Config.open()` unconditionally at module import time (and `logger/` constructs its `Log()` singleton at import time too, scanning/creating real log files) — **never read or assign `Config.*` in a throwaway script**; sandbox `USERPROFILE`/`HOME` to a scratch directory first if you need to exercise anything that imports this package at all. `Config.__table_name__` derives from `cls.__qualname__` (the full dotted nesting path, not `cls.__name__`) specifically to avoid short-name collisions across nested config classes — part of the codebase-wide `__name__`-dunder "hands off, including from subclasses" naming convention (see MEMORY.md's "Naming convention: dunders" entry). **One exception to the import-time behaviour above: PyCharm's skeleton generator.** To build stubs it imports every compiled module in the project interpreter, each in a throwaway worker process named `Skeleton Generator Worker`, so an installed copy of this package gets imported without the app ever starting. `_ConfigDB.open()` compares `multiprocessing.current_process().name` with `utils.SKELETON_WORKER_NAME` and, there, connects to an in-memory SQLite database instead (`save_all=True`): the real `config.db` is never created, read or written, and assignments made at import time (e.g. the MySQL connector's `Config.client_flags`) still land somewhere. Nothing needs guarding on the save side -- `Config.close()` is only ever called from `App.OnExit`, which a skeleton worker never reaches.

#### critical_error_dialog.py

`CriticalErrorDialog(QtWidgets.QDialog)` — the last-resort "the app hit an unhandled error" dialog: formats a traceback (`traceback.format_exception`) into a read-only `QTextEdit`, always-on-top, no native close button. Predates/parallels `ui/dialogs/dialog_base.py`'s `BaseDialog` but is intentionally standalone since it must work even if the rest of the UI machinery is what's broken. Exists because uncaught exceptions must never propagate out of low-level layers in this PyInstaller-frozen app — they're always caught, logged, and swallowed; this dialog is the deliberate surface for the rare case where something still needs to tell the user the app is dying.

#### debug.py

`DebugPrinter` — a callable debug-print object (`__call__(*args, end_stack=False)`) that can be pointed at the real logger (`set_logger`) so debug output goes through the same channel as everything else instead of bare `print()`; `_Record` looks like a captured call-site record (args plus, optionally, a stack trace) for later inspection. `logfunc` carries the ParamSpec signature `Callable[_P, _R] -> Callable[_P, _R]` (2026-10-22) but is only a one-line trampoline: it returns `cast(Callable[_P, _R], _logfunc(func))`, and the real body lives in `_logfunc`, which (with its `_wrapper`) is deliberately unannotated. `logfunc` is stacked on `@_check_types.do` on ~104 functions, and a bare `-> Callable` would hide every decorated function's real signature from type checkers (see the `check_types.py` entry); keeping the body behind the trampoline stops the typed signature from adding checker errors inside it. Do not move the body back into `logfunc`. In `_wrapper`'s static-method branch `positional_args` is a **tuple**, not a list: `_format_label` is hinted `args: tuple[Any]`, which the compiled build checks for an exact type, so the list that used to be built there raised `TypeError: Argument 'args' has incorrect type (expected tuple, got list)` whenever a capture was running (`begin_capture()`) -- found 2026-10-22 by compiling the real source with MSVC; the plain-Python run never showed it. Only three `@_debug.logfunc` functions are also `@staticmethod` (`_rotate_about`, `_rebind`, `_ensure_stripe_capacity`).

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
