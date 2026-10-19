## FILES

#### __init__.py

Re-exports `AMDBackend` from `backend.py`.

#### backend.py

`AMDBackend(GPUBackend)` — queries the first AMD GPU via `pyamd_adl` (replaces an earlier `amdsmi`-based
implementation). ADL initialization itself raises outright with no AMD adapter/driver present; that, like
every individual metric, leaves this backend at the base class's all-`None` default rather than propagating
(every field access is wrapped individually so one wrong field degrades gracefully instead of breaking
collection of everything else). Explicitly **not verified against real AMD hardware** — the source's own
docstring says the dev machine has none. ADL's surface is more control-oriented (OverDrive tuning) than a
clean read-only sensor API and has shifted shape across OverDrive versions 5/6/7/8 (`pyamd_adl`'s own
`adapter_h.py` abstracts that internally via `Adapter.core`/`.memory`) — if a field here turns out wrong or
missing once run against real hardware, fix it in `pyamd_adl`, not here. `GL_ATI_meminfo` (the GL-fallback
path AMD shares with `../gl_meminfo.py`) only reports *free* memory pools — total VRAM for AMD still comes
from the `../gpu_specs_lookup.py` table match, not the extension itself.
