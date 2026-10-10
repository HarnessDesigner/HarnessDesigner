# harness_designer/gpu/gpu_specs_lookup.py

## Line 63-108 (`lookup`) — the whole table is read and parsed on every call
`lookup` opens `gpu_table.json` and parses all 1757 entries each time it is called, then searches them. The result is returned and the parsed data is discarded. The module docstring says this is deliberate (nothing stays resident between calls). The trade-off is that a detection pays the parse cost once per backend built (see `gl_meminfo.md`). A process-wide cache would remove the repeat, at the cost of keeping the table in memory. The GPU does not change while the app runs, so caching is safe; this is a choice for the user.

Inside the search, for each bucket the keys are sorted by length on every call (line 102). That sort runs over about 1757 keys per call. It is small compared with the JSON parse.

**Typing (fixed in this pass):** `manufacturer` was `str = None`, now `str | None = None`. Return type is `dict[str, Any] | None`.
