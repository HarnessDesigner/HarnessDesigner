# harness_designer/logger/log_handler.py

## Line 407-454 (`LogHandler._process_entry`) — one pandas DataFrame and one CSV serialisation per log line
Every entry is written by building a one-row DataFrame (`pd.DataFrame([log_entry])`, line 406) and serialising it with `to_csv` (line 411). Measured 2026-11-13 (pandas, interpreted Python 3.11): building the one-row DataFrame and calling `to_csv` costs about 476 us per line, against about 2 us for a `csv.writer.writerow` of the same fields, a factor of 240. At that rate the worker thread can write roughly 2,000 lines a second, so a burst of log lines (a loop that logs per item, per-frame debug output) makes the worker spend almost all of its time in pandas and the queue falls behind. Each entry also goes to the UI as a DataFrame through `CallAfter` (line 423).

This runs on the worker thread, so callers do not block. But the queue can fall behind during bursts, and the UI receives a DataFrame for every line. A `csv.writer` on the file, plus one batched DataFrame per UI update, would remove most of this cost. Not changed here: the UI callback expects a DataFrame.

## Line 383-401 (`LogHandler.run`) — one flush per batch, pop from the front
The worker drains the whole queue, then flushes once (line 397). That is the right shape. `self._queue.pop(0)` (line 385) shifts the list on every pop; `collections.deque` would make each pop constant-time. Queues here are short, so the gain is small.

## Line 375-381 (`LogHandler.write`) — cheap enqueue
Checks the message, appends to the list and releases the semaphore. Never blocks, as the docstring says.

## Line 670-702 (`Log.error`, `Log.traceback`, `Log.database` and their `_block` forms) — flush on every error
`error`, `error_block`, `traceback`, `database` and `database_block` each call `flush()`, which waits for the worker thread to finish the queue (line 469-484). Each error therefore blocks the calling thread until the disk write completes. That is deliberate (the docstring says so), but it means a code path that logs many errors in a loop will stall on every iteration.

## Line 473-488 (`LogHandler.flush`) — barrier per call
Creates a new `threading.Event`, queues it, and waits. Cheap individually. Its cost is the wait for the worker's pending work.

## Line 542-611 (`Log.startup`) — reads the GL info once at start-up
**Dependency (flagged, not changed):** `startup` calls `_gl_info.get()` (line 515) and then `data.items()`. `gl/info.get()` returns `None` on its first call, and returns the cached dict only after it has been collected (see `gl/info.md`). If `startup` runs before the info has been collected, `data.items()` raises `AttributeError`. The app collects the info before startup, so this works today, but the dependency is implicit.

## Line 110-373 (`_scan`, `_unique_path`, `_compact_logfiles`) — directory and archive work
Directory scans happen once at start-up (`__init__`, line 167-168). Rotation, archiving and unique-name checks happen when a file fills up (`max_logfile_size`). Infrequent. Fine.

## Line 279-315 (`read_log`, `read_archived_log`) — full CSV read into a DataFrame
Reads an entire file on demand. Log viewers call these when the user opens a file. Fine for the size limits in the config.
