# harness_designer/gpu/apple/backend.py

## Line 20-47 (`AppleBackend.__init__`) — one SoC query and one sampler read per detection
Calls `soc_info.get_soc_info()` once and creates a `sampler.Sampler()` for one `get_metrics()` read. Creating a sampler on every detection is the costlier part; if detections were frequent, one sampler could be kept. Each field is in its own `try` block, so a failure degrades to `None`.

**Typing (fixed in this pass):** `__init__` returns `None`.
