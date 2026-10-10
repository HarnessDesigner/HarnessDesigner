# harness_designer/logger/redirect.py

## Line 46-64 (`_StreamRedirector.write`) — one logger call per completed line
`write` appends to a partial-line buffer and calls `_log_line` for each newline. A library that prints many lines produces one log entry per line, and each entry costs the pandas path described in `log_handler.md`. A noisy third-party library can therefore dominate the logger thread. Filtering or batching at the redirect would limit the volume.

`self._line += s` builds the partial line by string concatenation. Lines are short, so this is fine.

## Line 66-81 (`writelines`) — joins the whole batch before logging
Joins all lines into one entry, or one per line. Same concern as `write`.

## Line 83-92 (`flush`) — logs any partial line on flush
Fine.

## Line 101-186 (file-like plumbing) — delegation
Each method forwards to the original stream or returns a constant. Cheap.

## Line 189-218 (`StdOut`, `StdErr`) — install themselves over `sys.stdout`/`sys.stderr` at construction
Runs once at start-up.
