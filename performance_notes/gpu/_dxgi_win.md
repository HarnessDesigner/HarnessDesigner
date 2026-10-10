# harness_designer/gpu/_dxgi_win.py

## Line 202-238 (`query_current_usage`) — builds a DXGI factory and adapter on every call
Each call creates an `IDXGIFactory1`, enumerates an adapter, queries `IDXGIAdapter3`, and reads the local-segment usage. Nothing is cached. Called once per detection, so the cost is small. If the used-VRAM figure were ever polled, the factory should be created once and kept.

**Resource handling (flagged, not changed):** the factory and adapter COM pointers are not released explicitly. Release relies on comtypes' garbage collection of the pointer objects. That works in practice but is not deterministic. Calling `Release()` explicitly would make it so.

**Typing (fixed in this pass):** `query_current_usage` now declares `-> int`.

Structures and interface declarations (lines 1-200) are module-level definitions, created once at import. No runtime cost.
