# harness_designer/gpu/gpu.py

## Line 84-102 (`GPU.detect`) — one vendor probe per detection
Detection runs on demand (from `memory_diagnostics.py`, via `detect_blocking` and `_format_gpu_growth`), not on a timer. Each call builds a new backend and runs a chain of GL, SDK and OS queries. Cost is whatever the chosen vendor path does (see the backend notes). Fine as an on-demand operation.

## Line 176-263 (`_collect_generic`, `_collect_gaps`, `_backend_pairs`) — thirty pairs built per call
`_backend_pairs` builds a list of thirty `(attribute, value)` tuples each time. Both collectors call it once. The list is short and runs once per detection, so the cost is negligible. It replaces the earlier `getattr`/`setattr` loop, which did the same work with reflection.

## Line 266-284 (`_gl_meminfo_fallback`) — constructs a GL backend per detection
Creates a `GLMemInfoBackend` every time, which does the spec-table lookup and the extension scan (see `gl_meminfo.md`). Runs once per vendor path, so once per detection.

## Line 349-471 (`_intel`, `_apple`, `_opencl_estimate`, `get_chunk_size`) — arithmetic only
`get_chunk_size` does a few divisions and four log calls. Nothing heavy.

## Line 36-81 (`GPU.__init__`) — thirty `GPUAttribute` objects per instance
Small, once per instance.
