# harness_designer/memory_diagnostics.py

Developer tooling. Entirely off unless `Config.debug.memory.enabled` is true (`start`, line 565, returns first). When it is on it changes the process's speed and memory profile on purpose, so measurements taken with it on are not representative.

## Line 565-608 (`start`) — `tracemalloc` slows the whole process
`tracemalloc.start(Config.debug.memory.tracemalloc_frames)` traces every Python allocation. Expect a large slowdown (commonly 2x or worse) and extra memory that grows with `tracemalloc_frames` (frames kept per allocation). Keep the frame count low unless a deep trace is needed. This is the biggest cost in the module.

## Line 565-608 — a 40-60 s warm-up thread
A background `GPU Detector Warmup` thread pays a one-time cross-thread `GPU.detect()` cost (measured in the code comment at 40-60 s) so the first real `gpu_growth` query does not freeze the UI. It waits rather than burning CPU, but it holds a thread for that time.

## Line 521-551 (`_MemoryDiagnosticsListener.run`)
Blocks on `Listener.accept()` and handles one command per connection. No polling, no cost while idle. Each command builds a report string; `_format_heap_snapshot` (461), `_format_objects` (123) and `_format_stacks` (399) walk large object graphs or all thread frames and can take noticeable time and temporary memory. They run on the listener thread, except the GPU ones which marshal to the main thread.
