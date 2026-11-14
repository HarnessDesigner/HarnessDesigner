# harness_designer/app.py

## Line 45-85 (`_qt_message_handler`) — a full Python stack is formatted for every Qt message
`''.join(_traceback.format_stack())` (line 78) runs for every message Qt delivers, including `QtWarningMsg`/`QtInfoMsg`/`QtDebugMsg`, and the whole stack is appended to the log text. `format_stack` walks the frames, reads source lines through `linecache` and builds a string of several KB. The one known noisy message (`belongs to QRhi`, line 68) is already filtered before this point.
If Qt ever emits warnings in a burst (GL surface setup, dock drags, resizes), each one pays the stack walk on whichever thread raised it, plus a large log write. Options, cheapest first: only attach the stack for `QtCriticalMsg`/`QtFatalMsg`; or keep it for warnings but cap it (`format_stack(limit=12)`). No memory cost either way. The stack is the one thing a bare Qt message lacks, so if you want to keep it for warnings, rate-limit by message text instead of dropping it.

## Line 89-100 (`CallLater`) — a new lambda and a timer per call
`QTimer.singleShot(0, lambda ...)` creates a closure and a Qt timer each call. Callers batch their own work (the arena maintenance in `gl/arena_pool.py` guards with a pending flag, which is the right pattern). Any new caller that fires it per mouse move should do the same.

## Line 193-250 (`App._init`), 341-404 (`_thread_loop`) — import-heavy startup
Four to five local imports and the main-frame import happen on the loading thread, which is the intended way to hide startup latency behind the splash screen. Nothing to change; the cost is the import time of the whole UI, which is Cython-compiled in release builds.

## Line 253-276 (`App._start_hang_watchdog`)
Off (`_HANG_WATCHDOG = False`, line 41). When on, a 1 s timer re-arms `faulthandler.dump_traceback_later`, which is cheap.
