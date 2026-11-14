# harness_designer/process_memory.py

## Line 53-100 (`_windows_memory`) — redefines a ctypes Structure and reloads two DLLs on every call
`_ProcessMemoryCountersEx` (a `ctypes.Structure` subclass, line 60) is declared inside the function, and `ctypes.WinDLL('kernel32.dll')` / `WinDLL('psapi.dll')` plus the `restype`/`argtypes` assignments run on every call. Creating a ctypes structure class costs tens of microseconds and is the largest part of the call. It is only called by `memory_diagnostics` (a developer-only listener, on request), so it does not matter today. If it is ever polled on a timer, hoist the class and the DLL handles to module level (a few hundred bytes of memory).

No macOS implementation exists at this layer; that is a gap, not a cost.
