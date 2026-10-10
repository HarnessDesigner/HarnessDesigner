# harness_designer/gpu/backend_base.py

## Line 27-109 (`DisplayPortInfo`, `GPUBackend`) — class attributes only
Every metric is a class attribute defaulting to `None`. Instances set only the fields a vendor collects. No per-call work. The `ATTRIBUTE_NAMES` tuple is still used by `memory_diagnostics.py`, so it stays.

**Typing (fixed in this pass):** `displays` was annotated `list` but defaults to the tuple `()`, and its comment says it is always a list. The annotation now says `tuple[DisplayPortInfo, ...] | list[DisplayPortInfo]`, which matches the default. The comment still says "always a list"; that wording is now misleading and should be corrected, or the default should become a list. Left as is, to avoid a shared mutable class default.
