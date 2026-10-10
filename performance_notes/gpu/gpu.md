# harness_designer/gpu/gpu.py

## Line 79-97 (`GPU.detect`) — one vendor probe per detection
Detection runs on demand (from `memory_diagnostics.py`, via `detect_blocking` and `_format_gpu_growth`), not on a timer. Each call builds a new backend and runs a chain of GL, SDK and OS queries. Cost is whatever the chosen vendor path does (see the backend notes). Fine as an on-demand operation.

## Line 170-212 (`_collect_generic`, `_collect_gaps`, `_backend_pairs`) — thirty pairs built per call
`_backend_pairs` builds a list of thirty `(attribute, value)` tuples each time. Both collectors call it once. The list is short and runs once per detection, so the cost is negligible. It replaces the earlier `getattr`/`setattr` loop, which did the same work with reflection.

## Line 214-233 (`_gl_meminfo_fallback`) — constructs a GL backend per detection
Creates a `GLMemInfoBackend` every time, which does the spec-table lookup and the extension scan (see `gl_meminfo.md`). Runs once per vendor path, so once per detection.

## Line 297-420 (`_intel`, `_apple`, `_opencl_estimate`, `get_chunk_size`) — arithmetic only
`get_chunk_size` does a few divisions and four log calls. Nothing heavy.

## Line 17-76 (`GPU.__init__`) — thirty `GPUAttribute` objects per instance
Small, once per instance.

**Functional issue (fixed in this pass):** `__str__` had a missing comma after `gpu_temp`, so the temperature and GPU engine lines were joined into one string. The comma is now present, and the temperature prints on its own line.

**Typing (fixed in this pass):** `opencl_device` is now `_Union["_cl.Device", None]` (a `pyopencl.Device`, per `ray_tracing/renderer.py`), and every method has a return type. `getattr`/`setattr` removed.
