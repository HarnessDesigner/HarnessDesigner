# harness_designer/gpu/gl_meminfo.py

## Line 49-69 (`_has_extension`) — one `glGetStringi` call per extension
`_has_extension` reads `GL_NUM_EXTENSIONS` and then calls `glGetStringi` for every extension until it finds a match. A modern driver reports a few hundred extensions. The function runs up to twice per `GLMemInfoBackend()` (once for the NVIDIA extension, once for the AMD extension), so a few hundred GL calls per detection. Fine on demand; a single cached extension set per context would avoid the repeat.

**Functional issue (fixed in this pass):** `range(count)` was given the raw `glGetIntegerv` result, which PyOpenGL returns as a numpy array. Python's `range()` rejects a one-element numpy array (`TypeError`; checked directly against numpy). If PyOpenGL returns the count as an array, which the existing `int(...)` casts elsewhere in this file suggest, the broad `except` in this function returns `False` for every extension and the NVIDIA `GL_NVX_gpu_memory_info` path never runs. Not confirmed against a live context. The count is now wrapped in `int()`, which works either way.

## Line 72-93 (`_get_renderer`) — one string query, decoded per call
Cheap. Called once per backend.

## Line 96-147 (`GLMemInfoBackend.__init__`) — the spec table is read on every construction
`_gpu_specs_lookup.lookup(renderer)` reads and parses the 1757-entry JSON table every time a backend is built (see `gpu_specs_lookup.md`). That is a few megabytes of JSON per detection. The GL renderer string does not change while the app runs, so the lookup result could be cached for the process. Not done here.

The static-spec copy used to be a `setattr` loop over a tuple. It is now fourteen explicit `spec.get(name, self.name)` assignments. Each one keeps the attribute's current value when the table has no entry for it, which matches the old behaviour.

**Typing (fixed in this pass):** `_get_renderer` returns `str | None`; `__init__` returns `None`.

**Comment fix:** the comment about int32 overflow contained a half-finished correction ("... no, above ~2M KB"). It now states the rule plainly.
