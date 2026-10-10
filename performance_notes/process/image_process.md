# harness_designer/process/image_process.py

## Line 23-206 (`_process_worker`) — two busy-wait loops at start-up
Lines 47-48 and 50-51 are `while exit_event.is_set(): pass` and `while in_queue.empty(): pass`. The child process spins on a CPU core until the parent acts. The spin lasts until start-up completes, which can be a few seconds, and it is not bounded. A blocking wait (`exit_event.wait()`, `in_queue.get()`) would stop the spin. This is the most expensive thing in the file.

The job loop itself (lines 81-205) blocks on `in_queue.get(timeout=heartbeat_interval)`, so it is not a spin. Each job makes several database round-trips through `connector.execute`, and it sends one progress message per step.

## Line 209-233 (`ProcessWorker.__init__`) — queues and a process object
Creates two multiprocessing queues and one process. The queue arguments to `Process` are passed in swapped order: `args=(self.out_queue, self.in_queue, ...)` (lines 228-229). The pairing is consistent (the parent's `out_queue` is the child's `in_queue`), but the names are confusing. Renaming would avoid the mistake.

## Line 252-254 (`has_pending`) — builds a list of keys to count them
`len(list(self.queue.keys()))` builds a list just to count. `len(self.queue)` gives the same result. Trivial cost.

## Line 256-280 (`send`) — one message per free slot
Pops the next item by priority under the lock. Cheap.

## Line 282-341 (`add`) — linear scan of the whole queue
Scans every queued item for a duplicate (lines 315-326). The queue holds one entry per pending resource, so the scan is linear in the backlog. The backlog is usually small.

## Line 343-391 (`recv`) — one closure per message type
Defines a nested `_do` for each message type, then passes it to `CallAfter`. The closures are cheap. Each message costs one `CallAfter`.

**Typing (fixed in this pass):** `Union` changed to the `Union as _Union` alias; `_process_worker`, the `ProcessWorker` methods and the three nested closures are typed.
