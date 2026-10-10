# harness_designer/rope_pull/__init__.py

## Line 20-25 (import of the compiled extension) — tried once at import
Imports the compiled `rope_pull` extension, and falls back to the pure-Python solver if it is not built. The fallback is decided once, at import, so there is no per-call cost to choose an implementation.

## Line 35-59 (`solve_chain`) — one translation per call
Converts the `DragEnd` enum to an integer and wraps the extension's result in a `ChainResult`. Runs once per drag step. Negligible next to the solve itself.
