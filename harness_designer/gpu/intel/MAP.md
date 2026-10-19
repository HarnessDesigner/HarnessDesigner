## FILES

#### __init__.py

Re-exports `IntelBackend` from `backend.py`.

#### backend.py

`IntelBackend(GPUBackend)` — a placeholder; `__init__` is a bare `pass` and every attribute stays at the
base class's default. No vendor SDK exists for Intel in this codebase (no equivalent of `nvapi`/`pyamd_adl`
to wrap). Because of that, `../gl_meminfo.py`'s GL/table-based fallback is Intel's **primary** data source in
`GPU._intel()` (`../gpu.py`), not a fallback-of-last-resort the way it is for NVIDIA/AMD — static specs and
total VRAM come from `../gpu_specs_lookup.py`'s table, live "used" VRAM from `../os_vram_usage.py`. If a real
Intel SDK is ever integrated, this class is where it would go.
