# harness_designer/critical_error_dialog.py

One dialog that formats a traceback into a read-only text box. It is shown at most once per fatal error, so there is no hot path. One rule from MEMORY.md applies: the code that raises it must not call it from a loop (mouse-move handler, hover preview), so callers must rate-limit.
