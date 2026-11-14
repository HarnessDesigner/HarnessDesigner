# harness_designer/debug.py

## Line 152-210 (`_logfunc`) — free unless timing is configured
`_logfunc` returns `func` unchanged when neither `Config.log_args` nor `Config.log_duration` is true. That is evaluated once, when the decorator is applied (import time), so the roughly 100 functions decorated with `@_debug.logfunc` cost nothing in a normal run. It also means that changing those settings later in the session does not turn timing on for functions that are already decorated.

When timing is on, `_wrapper` adds a Python frame per call and, while a capture is running (`_records is not None`), builds a `_Record` and formats the label with `_format_label` (line 122, an f-string over every argument). The formatting runs for every decorated call during a capture, including hot ones; that is the price of a capture and is fine for a developer tool. `_Record` uses `__slots__`, which keeps per-call memory small. The records list grows without bound while a capture is open, so do not leave a capture running across a long session.

## Line 248-288 (`_format_tree`, `_format_summary`)
Report generation only (end of a capture). Cost is linear in the number of records. Not a runtime concern.
