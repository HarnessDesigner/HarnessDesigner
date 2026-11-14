# harness_designer/gpu/gpu_vendor.py

## Line 17-68 (`get`) — two GL string queries per call
Reads `GL_VENDOR` and `GL_RENDERER`, decodes and lowercases both, then checks substrings. Runs once per detection. Cheap.

**Bare `except` (flagged, not changed):** the function ends with `except:` (line 66), which also swallows `KeyboardInterrupt`, and it returns `GPU_UNKNOWN` on any failure, including when no GL context is current. That hides the real error. `except Exception:` would be safer.
