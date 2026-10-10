# harness_designer/gpu/amd/backend.py

## Line 32-186 (`AMDBackend.__init__`) — about twenty ADL reads per detection
Same shape as the NVIDIA backend: one `try` per field, read once per detection. The display loop (line 136-185) reads each connector's display and EDID. Cost is driver round-trips at detection time.

**Functional issue (flagged, not fixed):** line 113 stores `memory.bandwidth` in `pcie_bandwidth`. The GPU's `memory_bandwidth` attribute exists for memory bandwidth, and `pcie_bandwidth` is for the PCIe link. The AMD backend probably has the mapping backwards. Needs a check against real hardware before changing, since the comments in this file say the coverage is unverified.

**Typing (fixed in this pass):** `__init__` returns `None`.
