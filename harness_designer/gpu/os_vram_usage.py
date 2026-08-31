# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Vendor-agnostic *current VRAM usage* reading, straight from the OS --
used as the "used" half of a size/usage pair for any vendor whose own SDK
or GL extension can't supply it (currently: Intel, which has no equivalent
of ``GL_NVX_gpu_memory_info``/``GL_ATI_meminfo`` at all, and no vendor SDK
in this codebase either -- see :mod:`.gl_meminfo` and :mod:`.intel`).

Windows: DXGI's ``IDXGIAdapter3::QueryVideoMemoryInfo`` -- the same API
backing Task Manager's *per-process* GPU memory column (not its adapter-
wide overview), bound here directly via ``comtypes`` (no typelib for DXGI
exists to generate a wrapper from, so the interfaces are hand-declared,
vtable order matching the real inheritance chain IDXGIObject ->
IDXGIAdapter -> IDXGIAdapter1 -> IDXGIAdapter2 -> IDXGIAdapter3 exactly --
every ancestor method must be declared even though only the
IDXGIAdapter3-added ones are ever called, or the vtable offsets for
everything after them are wrong). Verified live against real hardware: a
fresh process reads 0 before any GL/D3D context exists, and jumps by (very
close to) the exact byte size of a VBO immediately after allocating one --
see :mod:`._dxgi_win`'s own docstring.

Linux: no C-library equivalent exists for this (see this module's own
design notes / the conversation that led here) -- the kernel's own sanctioned
mechanism is the ``drm-*``-keyed text format in ``/proc/self/fdinfo/<fd>``,
documented at https://docs.kernel.org/gpu/drm-usage-stats.html and read the
same way every real Linux GPU monitoring tool (nvtop, intel_gpu_top,
radeontop) does. ``drm-total-memory`` is also *this process's* allocated
buffer total -- the same per-process scope as the Windows path above, not
a coincidence: neither OS exposes a clean adapter-wide "everyone's total
usage" figure this way, which is why this module is paired with each
vendor's own :mod:`.vram_lookup`-based table for the total-capacity half
instead of trying to get that from here too.
"""

import sys

from .. import check_types as _check_types


@_check_types.do
def get_current_usage_bytes(adapter_index: int = 0):
    """Current VRAM usage, in bytes, attributed to *this process* --
    verified live on Windows (see :mod:`._dxgi_win`); not tested against a
    real GPU on Linux (see this module's own docstring for why that
    reading is structurally the same per-process scope regardless).

    :param adapter_index: Which adapter to query (Windows: DXGI enumeration
        order; ignored on Linux, which only ever looks at this process's
        own open DRM file descriptors).
    :returns: Bytes currently in use by this process, or ``None`` if
        nothing could be read.
    :rtype: int | None
    """
    if sys.platform == 'win32':
        return _windows_usage(adapter_index)

    if sys.platform.startswith('linux'):
        return _linux_usage()

    return None


@_check_types.do
def _windows_usage(adapter_index: int):
    try:
        from . import _dxgi_win
    except Exception:  # NOQA -- comtypes not installed, or DXGI unavailable
        return None

    try:
        return _dxgi_win.query_current_usage(adapter_index)
    except Exception:  # NOQA
        return None


@_check_types.do
def _linux_usage():
    import os
    import re

    total = 0
    found = False

    try:
        fd_dir = '/proc/self/fdinfo'
        for entry in os.listdir(fd_dir):
            try:
                with open(os.path.join(fd_dir, entry), 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception:  # NOQA -- fd closed/raced/not readable
                continue

            if 'drm-total-memory' not in content:
                continue

            for line in content.splitlines():
                match = re.match(r'drm-total-memory:\s*(\d+)\s*(KiB|MiB|GiB|B)?', line)
                if not match:
                    continue

                found = True
                value = int(match.group(1))
                unit = match.group(2) or 'B'
                multiplier = {'B': 1, 'KiB': 1024, 'MiB': 1024 ** 2, 'GiB': 1024 ** 3}[unit]
                total += value * multiplier
    except Exception:  # NOQA
        return None

    return total if found else None
