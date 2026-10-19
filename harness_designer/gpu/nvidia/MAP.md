## FILES

#### __init__.py

Re-exports `NvidiaBackend` from `backend.py`.

#### backend.py

`NvidiaBackend(GPUBackend)` — queries the first NVIDIA GPU via `nvapi` (replaces an earlier `pynvml`-based
implementation; `pynvml` needs a separately-installed system component and exposes materially less than
`nvapi`'s direct driver dispatch). Everything is queried once at construction time; any single metric
`nvapi` doesn't support on the current driver/hardware (e.g. legacy fan APIs on a card whose driver moved to
the newer ClientFanCoolers API) is left at the base class's `None` default rather than raising.
`driverVersion` is decoded per NVIDIA's own convention (raw integer = version * 100, e.g. `57342` →
`"573.42"`). `GPU._nvidia()` (in `../gpu.py`) doesn't trust OpenGL reporting NVIDIA as vendor to mean
`nvapi` itself can actually load — the shared library can be missing or fail at import time for unrelated
reasons. The GL/table fallback (`../gl_meminfo.py`) always runs afterward regardless, both to supply VRAM
when `nvapi` has nothing and to fill static fields `nvapi` never reports even when it works.
