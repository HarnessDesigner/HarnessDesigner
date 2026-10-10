# harness_designer/logger/__init__.py

## Line 13-37 — import-time construction of the one logger
Creates the `Log` instance once at import, which starts the worker thread (see `log_handler.md`). Module-level names are bound to its methods, so each call is a direct method call. No per-call cost beyond the call itself.
