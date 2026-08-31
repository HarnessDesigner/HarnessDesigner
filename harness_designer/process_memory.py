# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""This process's own OS-reported memory footprint -- independent of
anything Python's own allocator tracks.

:mod:`tracemalloc` only ever sees Python-managed allocations (anything
going through ``PyMem_*``/``PyObject_*`` -- including numpy, which registers
its own tracemalloc domain). It has no visibility at all into native
buffers a C extension allocates directly with ``malloc``, Qt widget/pixmap
backing stores, OpenGL client-side staging buffers, memory-mapped files, or
anything else the OS still charges to this process. When a reported total
(Task Manager, a support ticket, ``gpu_growth``'s VRAM figure) is much
bigger than what ``tracemalloc``/``growth`` show, that gap is the reason --
this module measures the OS's side of that gap so it can be quantified
instead of guessed at.

Windows: ``GetProcessMemoryInfo`` (``psapi.dll``) via ``ctypes`` -- no
dependency beyond the stdlib, same reasoning as this project's other
hand-rolled Windows API bindings (see e.g. :mod:`.gpu._dxgi_win`).

Linux: ``/proc/self/status`` -- ``VmRSS``/``VmData``, the same source
``ps``/``top`` themselves read.
"""

import sys

from . import check_types as _check_types


@_check_types.do
def get_process_memory():
    """This process's current OS-reported memory footprint.

    :returns: ``(rss_bytes, private_bytes)``. Either may be ``None`` if
        unavailable on this platform or the underlying call failed.
        ``rss_bytes`` is physical/working-set memory currently resident;
        ``private_bytes`` is memory committed to this process alone, not
        shared with others (e.g. via shared DLLs/mapped files) -- the more
        useful figure when hunting a process-specific leak, since RSS can
        include pages this process doesn't exclusively own.
    :rtype: tuple[int | None, int | None]
    """
    if sys.platform == 'win32':
        return _windows_memory()

    if sys.platform.startswith('linux'):
        return _linux_memory()

    return None, None


@_check_types.do
def _windows_memory():
    """:returns: ``(working_set_bytes, private_usage_bytes)`` or ``(None, None)``.
    :rtype: tuple[int | None, int | None]
    """
    import ctypes
    from ctypes import wintypes

    class _ProcessMemoryCountersEx(ctypes.Structure):
        _fields_ = [
            ('cb', wintypes.DWORD),
            ('PageFaultCount', wintypes.DWORD),
            ('PeakWorkingSetSize', ctypes.c_size_t),
            ('WorkingSetSize', ctypes.c_size_t),
            ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
            ('QuotaPagedPoolUsage', ctypes.c_size_t),
            ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
            ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
            ('PagefileUsage', ctypes.c_size_t),
            ('PeakPagefileUsage', ctypes.c_size_t),
            ('PrivateUsage', ctypes.c_size_t),
        ]

    try:
        kernel32 = ctypes.WinDLL('kernel32.dll', use_last_error=True)
        psapi = ctypes.WinDLL('psapi.dll', use_last_error=True)

        # GetCurrentProcess() returns the pseudo-handle -1 -- as a full
        # 64-bit value (0xFFFFFFFFFFFFFFFF), not the 32-bit -1 ctypes'
        # default (unset) restype of c_int would sign-extend it to. Left
        # undeclared, GetProcessMemoryInfo below receives a silently
        # truncated/corrupted handle and just fails (returns 0, no
        # exception) instead of reading this process's own memory info.
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.GetCurrentProcess.argtypes = []

        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(_ProcessMemoryCountersEx), wintypes.DWORD]

        counters = _ProcessMemoryCountersEx()
        counters.cb = ctypes.sizeof(_ProcessMemoryCountersEx)
        handle = kernel32.GetCurrentProcess()
        ok = psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
        if not ok:
            return None, None
        return counters.WorkingSetSize, counters.PrivateUsage
    except Exception:  # NOQA -- psapi unavailable, or the call itself failed
        return None, None


@_check_types.do
def _linux_memory():
    """:returns: ``(rss_bytes, data_segment_bytes)`` or ``(None, None)``.
    :rtype: tuple[int | None, int | None]
    """
    try:
        rss = private = None
        with open('/proc/self/status', 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    rss = int(line.split()[1]) * 1024
                elif line.startswith('VmData:'):
                    private = int(line.split()[1]) * 1024

        return rss, private
    except Exception:  # NOQA
        return None, None
