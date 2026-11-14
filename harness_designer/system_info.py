# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The machine's physical memory and processor core/thread counts, for the
"Machine" block of the startup log.

No third-party package (``psutil`` would do all of it): the same approach as
:mod:`.process_memory`, a hand-rolled binding per platform.

Windows: ``GlobalMemoryStatusEx`` and ``GetLogicalProcessorInformationEx``
(``kernel32.dll``) via ``ctypes``.

Linux: ``/proc/meminfo`` and ``/sys/devices/system/cpu/cpuN/topology``.

macOS: the ``sysctl`` and ``vm_stat`` command line tools.

Every value is ``None`` when it cannot be read on the platform (nothing is
raised). The logical thread count comes from :func:`os.cpu_count` everywhere.
"""

import os
import re
import struct
import subprocess
import sys

from . import check_types as _check_types


_GIB = 1024 ** 3


@_check_types.do
def get() -> dict[str, int | None]:
    """The machine's memory and processor counts.

    :returns: ``physical_cores``, ``logical_cores`` (threads),
        ``memory_total`` and ``memory_available`` (bytes of physical memory);
        any of them ``None`` if it could not be read.
    :rtype: dict[str, int | None]
    """
    if sys.platform == 'win32':
        total, available = _windows_memory()
        physical_cores = _windows_physical_cores()
    elif sys.platform.startswith('linux'):
        total, available = _linux_memory()
        physical_cores = _linux_physical_cores()
    elif sys.platform == 'darwin':
        total, available = _macos_memory()
        physical_cores = _macos_sysctl_int('hw.physicalcpu')
    else:
        total = None
        available = None
        physical_cores = None

    return {
        'physical_cores': physical_cores,
        'logical_cores': os.cpu_count(),
        'memory_total': total,
        'memory_available': available
    }


@_check_types.do
def describe() -> list[str]:
    """The lines the startup log's Machine block adds for :func:`get`.

    :rtype: list[str]
    """
    info = get()

    lines = [
        f'CPU cores (physical): {_count(info["physical_cores"])}',
        f'CPU threads (logical): {_count(info["logical_cores"])}'
    ]

    total = info['memory_total']
    available = info['memory_available']

    lines.append(f'Physical memory total: {_gib(total)}')
    lines.append(f'Physical memory available: {_gib(available)}')

    if total is None or available is None or total <= 0:
        lines.append('Physical memory used: unknown')
    else:
        used = total - available
        percent = used * 100.0 / total
        lines.append(f'Physical memory used: {_gib(used)} ({percent:.1f}%)')

    return lines


@_check_types.do
def _count(value: int | None) -> str:
    if value is None:
        return 'unknown'

    return str(value)


@_check_types.do
def _gib(value: int | None) -> str:
    if value is None:
        return 'unknown'

    return f'{value / _GIB:.2f} GiB'


@_check_types.do
def _windows_memory() -> tuple[int | None, int | None]:
    """:returns: ``(total_bytes, available_bytes)`` or ``(None, None)``.
    :rtype: tuple[int | None, int | None]
    """
    import ctypes
    from ctypes import wintypes

    class _MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ('dwLength', wintypes.DWORD),
            ('dwMemoryLoad', wintypes.DWORD),
            ('ullTotalPhys', ctypes.c_ulonglong),
            ('ullAvailPhys', ctypes.c_ulonglong),
            ('ullTotalPageFile', ctypes.c_ulonglong),
            ('ullAvailPageFile', ctypes.c_ulonglong),
            ('ullTotalVirtual', ctypes.c_ulonglong),
            ('ullAvailVirtual', ctypes.c_ulonglong),
            ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
        ]

    try:
        kernel32 = ctypes.WinDLL('kernel32.dll', use_last_error=True)
        kernel32.GlobalMemoryStatusEx.restype = wintypes.BOOL
        kernel32.GlobalMemoryStatusEx.argtypes = [
            ctypes.POINTER(_MemoryStatusEx)]

        status = _MemoryStatusEx()
        status.dwLength = ctypes.sizeof(_MemoryStatusEx)

        if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None, None

        return int(status.ullTotalPhys), int(status.ullAvailPhys)
    except Exception:  # NOQA -- the call itself failed
        return None, None


@_check_types.do
def _windows_physical_cores() -> int | None:
    """Count the ``RelationProcessorCore`` records of
    ``GetLogicalProcessorInformationEx`` -- one per physical core.

    :rtype: int | None
    """
    import ctypes
    from ctypes import wintypes

    relation_processor_core = 0

    try:
        kernel32 = ctypes.WinDLL('kernel32.dll', use_last_error=True)
        kernel32.GetLogicalProcessorInformationEx.restype = wintypes.BOOL
        kernel32.GetLogicalProcessorInformationEx.argtypes = [
            wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD)]

        # The first call only reports how big the buffer has to be (it
        # fails with ERROR_INSUFFICIENT_BUFFER on purpose).
        length = wintypes.DWORD(0)
        kernel32.GetLogicalProcessorInformationEx(
            relation_processor_core, None, ctypes.byref(length))

        if length.value == 0:
            return None

        buffer = ctypes.create_string_buffer(length.value)
        if not kernel32.GetLogicalProcessorInformationEx(
                relation_processor_core, buffer, ctypes.byref(length)):
            return None

        raw = buffer.raw[:length.value]

        # Variable length records: DWORD Relationship, DWORD Size, payload.
        count = 0
        offset = 0
        while offset + 8 <= len(raw):
            relationship, size = struct.unpack_from('<II', raw, offset)
            if size == 0:
                break

            if relationship == relation_processor_core:
                count += 1

            offset += size

        if count == 0:
            return None

        return count
    except Exception:  # NOQA
        return None


@_check_types.do
def _linux_memory() -> tuple[int | None, int | None]:
    """:returns: ``(MemTotal, MemAvailable)`` in bytes or ``(None, None)``.
    :rtype: tuple[int | None, int | None]
    """
    try:
        total = None
        available = None

        with open('/proc/meminfo', 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    total = int(line.split()[1]) * 1024
                elif line.startswith('MemAvailable:'):
                    available = int(line.split()[1]) * 1024

        return total, available
    except Exception:  # NOQA
        return None, None


@_check_types.do
def _linux_physical_cores() -> int | None:
    """Count the distinct (package, core) pairs the kernel lists for the
    CPUs that are online (an offline CPU has no ``topology`` folder).

    :rtype: int | None
    """
    base = '/sys/devices/system/cpu'

    try:
        cores = set()

        for name in os.listdir(base):
            if re.fullmatch(r'cpu\d+', name) is None:
                continue

            topology = os.path.join(base, name, 'topology')

            try:
                with open(os.path.join(topology, 'physical_package_id'),
                          'r', encoding='utf-8') as f:
                    package = f.read().strip()

                with open(os.path.join(topology, 'core_id'),
                          'r', encoding='utf-8') as f:
                    core = f.read().strip()
            except OSError:
                continue

            cores.add((package, core))

        if not cores:
            return None

        return len(cores)
    except Exception:  # NOQA
        return None


@_check_types.do
def _macos_sysctl_int(name: str) -> int | None:
    """:returns: the integer ``sysctl -n <name>`` prints, or ``None``.
    :rtype: int | None
    """
    try:
        result = subprocess.run(
            ['sysctl', '-n', name], capture_output=True, text=True,
            timeout=5, check=True)

        return int(result.stdout.strip())
    except Exception:  # NOQA
        return None


@_check_types.do
def _macos_memory() -> tuple[int | None, int | None]:
    """Total from ``hw.memsize``; available is ``vm_stat``'s free plus
    inactive pages (what ``psutil`` reports as available).

    :returns: ``(total_bytes, available_bytes)``, each possibly ``None``.
    :rtype: tuple[int | None, int | None]
    """
    total = _macos_sysctl_int('hw.memsize')

    try:
        result = subprocess.run(
            ['vm_stat'], capture_output=True, text=True, timeout=5,
            check=True)

        page_size = None
        pages = {}

        for line in result.stdout.splitlines():
            match = re.search(r'page size of (\d+) bytes', line)
            if match is not None:
                page_size = int(match.group(1))
                continue

            key, separator, value = line.partition(':')
            if separator:
                pages[key.strip()] = int(value.strip().rstrip('.'))

        if page_size is None:
            return total, None

        free_pages = pages['Pages free'] + pages['Pages inactive']
        return total, free_pages * page_size
    except Exception:  # NOQA
        return total, None
