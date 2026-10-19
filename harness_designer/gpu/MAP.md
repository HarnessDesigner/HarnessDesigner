## FILES

#### __init__.py

Re-exports `GPU` from `gpu.py` (`from harness_designer.gpu import GPU`) — the one name the rest of the app
should import; everything else in this package is an implementation detail `GPU.detect()` drives. Note:
`CODEBASE_MAP.md` (repo root) documents this directory under the name `gpu_mem/` — the real directory on
disk is `gpu/` (no `_mem`). Treat that doc's `gpu_mem/` section as describing this directory, renamed;
`gpu_table.json` is new since that doc was written and the `manager` module it mentions no longer exists
(`gpu.py` now plays that role directly).

#### _dxgi_win.py

Hand-declared `comtypes` COM interfaces for DXGI (no typelib exists to generate a wrapper from) —
`IDXGIObject` → `IDXGIAdapter` → `IDXGIAdapter1` → `IDXGIAdapter2` → `IDXGIAdapter3`, vtable order matching
the real inheritance chain exactly (every ancestor method must be declared even though only
`IDXGIAdapter3`'s own methods are called, or every vtable offset after them is wrong). `query_current_usage
(adapter_index=0)` calls `IDXGIAdapter3::QueryVideoMemoryInfo` — the same API backing Task Manager's
per-process GPU memory column; used by `os_vram_usage.py` on Windows.

#### backend_base.py

`GPUBackend` — the base every vendor backend subclasses; every metric defaults to `None` ("not collected",
not an error) and `ATTRIBUTE_NAMES` lists the ~30 names mirrored on `GPU` one-to-one, so `GPU._collect_generic`/
`_collect_gaps` need no vendor-specific branching. Also defines `DisplayPortInfo` (one physical display
connector + whatever's plugged into it — index/connector_type/is_connected/is_active/monitor_name/edid_data/
resolution, all defaulting to `None`/`False`).

#### gl_meminfo.py

`GLMemInfoBackend` — the GL-extension/table fallback, needs no vendor SDK or OS API, just the current GL
context. `GL_NVX_gpu_memory_info` (NVIDIA) gives a real total+available pair; `GL_ATI_meminfo` (AMD,
including Mesa's open `radeonsi`/`r600g`) only exposes *free* pools, no total; when neither extension exists
(Nouveau/NVK, non-Mesa AMD, or Intel — which has never had either), total VRAM comes from
`gpu_specs_lookup`'s table matched against `GL_RENDERER`, and used VRAM from `os_vram_usage`. Also always
(regardless of which VRAM path ran) enriches static spec fields (architecture, boost clock, PCIe generation,
memory type/bandwidth, core count, ...) from the same table match — fields no vendor SDK here reports at all
or reports incompletely.

#### gpu.py

`GPU` — the one class the rest of the app should import. `detect()` reads the active vendor
(`gpu_vendor.get()`) and dispatches to `_nvidia()`/`_amd()`/`_intel()`/`_apple()`/`_fallback()`. Each vendor
path first tries that vendor's own SDK backend (`_collect_generic`, overwrites), then unconditionally runs
the GL/table-based fallback as a *gap-fill* (`_collect_gaps`, only fills still-`'Unknown'` fields — never
clobbers a real SDK measurement), then estimates from the configured OpenCL device (`_opencl_estimate`) if
VRAM is still not usable. `get_chunk_size(width, height, target_usage)` is what `ray_tracing/renderer.py`
actually calls: picks a render-chunk row count from free VRAM, clamped to `[50, height]`. `_opencl_estimate`
previously stored total VRAM in GiB (divided by 1024**3) while every vendor backend and `_fallback()` store
bytes — broke `GPU.is_ok()`'s `isinstance(..., int)` check on any real float total and was inconsistent with
the rest of the class; fixed to store bytes like everywhere else. The `multiplier` parameter's intended
semantics beyond `used = total - total * multiplier` are explicitly documented in the source as **unknown** —
don't assume a specific meaning (e.g. "fraction free") without checking call sites. `_fallback()` hardcodes
4 GiB total / 2 GiB used VRAM as a last-resort guess when nothing else worked — not a measurement, a
conservative placeholder.

#### gpu_base.py

`GPUAttribute` — a tiny labeled value holder (`.label`, `.value`, defaults to `'Unknown'`); every one of
`GPU`'s ~30 fields is one of these.

#### gpu_specs_lookup.py

`lookup(renderer_string, manufacturer=None)` — `GL_RENDERER` string → spec dict, backed by `gpu_table.json`
(1757 real GPUs: 791 AMD / 931 NVIDIA / 35 Intel, filtered from the `RightNow-GPU-Database` project's
TechPowerUp-sourced data to GL ≥ 3.3-capable parts). Keyed `{"AMD": {...}, "NVIDIA": {...}, "INTEL": {...}}`
on disk; `lookup()` adds `gpu_manufacturer` back onto the matched dict. Re-reads and re-parses the JSON file
on every call rather than caching in memory (the installed GPU doesn't change mid-process, so there's
nothing to gain from residency).

#### gpu_table.json

The 1757-entry spec table `gpu_specs_lookup.py` reads. Not Python source; a generated/curated data file —
don't hand-edit without regenerating it the same way it was built.

#### gpu_vendor.py

`get()` — reads `GL_VENDOR`/`GL_RENDERER` off the *already-current* OpenGL context and returns one of
`GPU_UNKNOWN`/`GPU_NVIDIA`/`GPU_AMD`/`GPU_APPLE`/`GPU_INTEL` via substring matching (vendor string first,
renderer string as a fallback for `'geforce'`/`'quadro'`/`'radeon'`/`'iris'` etc.).

#### os_vram_usage.py

`get_current_usage_bytes(adapter_index=0)` — vendor-agnostic *current VRAM usage*, read straight from the
OS, for whichever vendor's own SDK/GL extension can't supply it (currently: Intel). Windows dispatches to
`_windows_usage` (DXGI, see `_dxgi_win.py`); Linux to `_linux_usage` (reads `/proc/self/fdinfo/<fd>` `drm-*`
keys, the same mechanism `nvtop`/`intel_gpu_top`/`radeontop` use). Both readings are scoped to *this
process's* allocations, not an adapter-wide total — there is no OS-level API for that on either platform.

## FOLDERS

#### amd/

AMD's `GPUBackend` subclass (`AMDBackend`, via `pyamd_adl`) — see `amd/MAP.md`. Explicitly **not verified
against real AMD hardware** (the dev machine has none); ADL's surface is more control-oriented than a clean
read-only sensor API.

#### apple/

Apple Silicon's `GPUBackend` subclass (`AppleBackend`, via `apple_smi`) — see `apple/MAP.md`. Has no
GL-extension fallback step the way NVIDIA/AMD/Intel do.

#### intel/

Intel's `GPUBackend` subclass — see `intel/MAP.md`. Currently a complete no-op placeholder; Intel's real
data comes entirely from `gl_meminfo.py`'s fallback path treated as Intel's *primary* source, not a
last resort.

#### nvidia/

NVIDIA's `GPUBackend` subclass (`NvidiaBackend`, via `nvapi`) — see `nvidia/MAP.md`.
