## FILES

#### __init__.py

Re-exports `AppleBackend` from `backend.py`.

#### backend.py

`AppleBackend(GPUBackend)` — queries Apple Silicon's GPU via `apple_smi` (`soc_info`/`sampler`). Sets
`gpu_manufacturer = 'Apple'` directly, then fills `gpu_name`/`gpu_model`/`gpu_cores` etc. from
`soc_info.get_soc_info()`; any single reading failing degrades to the base class's `None` default, same
convention as every other vendor backend. `GPU._apple()` (in `../gpu.py`) has no GL-extension fallback step
the way NVIDIA/AMD/Intel do — if this backend doesn't leave VRAM usable, it goes straight to the OpenCL
estimate, skipping `../gl_meminfo.py` entirely.
