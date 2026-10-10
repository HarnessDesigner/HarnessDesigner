# harness_designer/process/manager.py

## Line 61-281 (`CredManager`) — keyring round-trips
Each credential is one keyring call (`set_password`, `get_password`, `delete_password`). Store, retrieve and cleanup run at start-up and when a worker is created, not per frame. Fine.

## Line 283-431 (`ProcessManager.__init__`, `start`, `run`) — the monitor loop
`run()` polls the image and model processes. Each pass calls `recv()` and `send()` on the image process, then `recv()` on each model process. If a pass produced no message, it waits up to 50 ms on `_wait_event` (lines 669-670). If a message was processed, the pass continues without waiting, so a busy stream of messages is handled as fast as it arrives. That is an acceptable polling design.

## Line 672-719 (`get_model`) — creates a new model process when none is free
Starts a new `ProcessWorker` (a whole Python process) when every existing model process is busy and the core count allows it. Process start-up is expensive (see `model_process.md`); the core-count cap keeps the number of processes bounded.

## Line 495-646 (nested `_do` closures) — one per message, passed to `CallAfter`
Each is cheap. They run on the UI thread.

## Line 375-431 (`get_image`, `get_datasheet`, `get_cad`) — forwarders
Each forwards to the image process's `add`. Cheap.

**Typing (fixed in this pass):** `print_lock` is `"multiprocessing.synchronize.Lock"`; `db_type` is `int` (the connector constants are 0 and 1); the nested `_do` closures are typed by the arguments they receive.
