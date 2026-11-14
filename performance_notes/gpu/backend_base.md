# harness_designer/gpu/backend_base.py

## Line 27-109 (`DisplayPortInfo`, `GPUBackend`) — class attributes only
Every metric is a class attribute defaulting to `None`. Instances set only the fields a vendor collects. No per-call work. The `ATTRIBUTE_NAMES` tuple is still used by `memory_diagnostics.py`, so it stays.
