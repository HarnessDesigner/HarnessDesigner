# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""GL-extension/table VRAM and static-spec fallback for
:mod:`harness_designer.gpu`.

Neither a vendor SDK nor an OS API -- this reads whatever it can directly
off the already-current OpenGL context, so it needs no shared library of
its own and works identically on Windows and Linux (GL extensions are
exposed by the driver, not the OS; ``GL_ATI_meminfo`` in particular is
implemented by Mesa's open-source ``radeonsi``/``r600g`` drivers, not just
AMD's proprietary one, which is the common case on Linux).

Requires an OpenGL context to already be current on the calling thread --
same requirement :mod:`.gpu_vendor` already has for its own
``glGetString(GL_VENDOR)`` call. Invoked from :class:`.gpu.GPU` both as the
VRAM fallback when a vendor SDK failed outright, and unconditionally
afterward to fill in static spec fields (architecture, clocks, PCIe, ...)
no live SDK in this codebase supplies at all.

Two independent things happen here, in order:

1. VRAM size/usage, vendor-extension best case first:

   - ``GL_NVX_gpu_memory_info`` (NVIDIA) gives both total dedicated VRAM
     and currently-available VRAM directly -- a complete, measured pair.
   - ``GL_ATI_meminfo`` (AMD) only exposes *free* memory pools; nothing in
     the extension reports total capacity at all, so the total half still
     comes from the table lookup below -- only the used half (derived from
     the live free reading) is a real measurement in this branch.
   - Neither extension present (e.g. Nouveau/NVK on Linux for NVIDIA, any
     non-Mesa AMD driver, or Intel -- which has never had an equivalent of
     either extension): total comes from :mod:`.gpu_specs_lookup`'s single
     combined table, matched against the GPU model parsed out of
     ``GL_RENDERER`` (searched across every vendor at once -- harmless,
     since a real AMD string will never match an NVIDIA/Intel entry), and
     used comes from :mod:`.os_vram_usage`'s OS-level per-process reading.
     Both are estimates, not measurements -- but far better than nothing.

2. Static spec enrichment, always attempted regardless of which VRAM path
   above ran: the same table match (by ``GL_RENDERER``) also supplies
   ``gpu_manufacturer``, ``architecture``, ``generation``, ``foundry``,
   ``memory_type``, ``memory_bandwidth``, ``boost_clock``, ``gpu_cores``,
   ``pcie_version``, ``pcie_max_width`` -- fields no vendor SDK in this
   codebase reports at all (``pyamd_adl``) or reports incompletely
   (``nvapi``). :class:`.gpu.GPU` only ever copies these in where the SDK
   left a gap, never overwriting a real measurement with a table guess.
"""

from OpenGL import GL

from . import gpu_specs_lookup as _gpu_specs_lookup
from . import os_vram_usage as _os_vram_usage
from .backend_base import GPUBackend
from .. import check_types as _check_types

_NVX_DEDICATED_VIDMEM = 0x9047
_NVX_CURRENT_AVAILABLE_VIDMEM = 0x9049

_ATI_VBO_FREE_MEMORY = 0x87FB

@_check_types.do
def _has_extension(name: str) -> bool:
    try:
        count = int(GL.glGetIntegerv(GL.GL_NUM_EXTENSIONS))
        for i in range(count):
            if GL.glGetStringi(GL.GL_EXTENSIONS, i) == name.encode('ascii'):
                return True
    except Exception:  # NOQA -- e.g. no current context, or a legacy driver
        pass

    return False


@_check_types.do
def _get_renderer() -> str | None:
    try:
        renderer = GL.glGetString(GL.GL_RENDERER)
        if isinstance(renderer, bytes):
            renderer = renderer.decode('utf-8', errors='ignore')
        return renderer or None
    except Exception:  # NOQA
        return None


class GLMemInfoBackend(GPUBackend):
    """Best-effort VRAM and static specs, read off the current GL context
    plus (see this module's own docstring) a matched spec table.

    Fields this backend never touches (``driver_*``, live utilization,
    fan/temp -- nothing here or in a static table can supply those) stay at
    :class:`.backend_base.GPUBackend`'s default.
    """

    @_check_types.do
    def __init__(self) -> None:
        renderer = _get_renderer()
        spec = _gpu_specs_lookup.lookup(renderer) if renderer else None

        if _has_extension('GL_NVX_gpu_memory_info'):
            try:
                # PyOpenGL's glGetIntegerv returns a fixed-width numpy int32.
                # Converting with int() first matters: multiplying by 1024
                # in int32 overflows for any card above about 2 GiB.
                total_kb = int(GL.glGetIntegerv(_NVX_DEDICATED_VIDMEM))
                current_kb = int(GL.glGetIntegerv(_NVX_CURRENT_AVAILABLE_VIDMEM))
                self.vram_size = total_kb * 1024
                self.vram_use = (total_kb - current_kb) * 1024
            except Exception:  # NOQA
                pass

        elif _has_extension('GL_ATI_meminfo') and spec is not None:
            try:
                total_bytes = spec.get('vram_size')
                if total_bytes is not None:
                    # 4-tuple: total free, largest free block, total aux
                    # free, largest aux free -- index 0 is the pool total.
                    # int() for the same numpy-int32-overflow reason as above.
                    free_kb = int(GL.glGetIntegerv(_ATI_VBO_FREE_MEMORY)[0])
                    self.vram_size = total_bytes
                    self.vram_use = max(0, total_bytes - free_kb * 1024)
            except Exception:  # NOQA
                pass

        elif spec is not None:
            total_bytes = spec.get('vram_size')
            if total_bytes is not None:
                self.vram_size = total_bytes
                self.vram_use = _os_vram_usage.get_current_usage_bytes()

        if spec is not None:
            # A field the table has no entry for keeps its current value.
            self.gpu_model = spec.get('gpu_model', self.gpu_model)
            self.gpu_manufacturer = spec.get('gpu_manufacturer', self.gpu_manufacturer)
            self.architecture = spec.get('architecture', self.architecture)
            self.generation = spec.get('generation', self.generation)
            self.foundry = spec.get('foundry', self.foundry)
            self.memory_type = spec.get('memory_type', self.memory_type)
            self.vram_width = spec.get('vram_width', self.vram_width)
            self.memory_bandwidth = spec.get('memory_bandwidth', self.memory_bandwidth)
            self.soc_clock = spec.get('soc_clock', self.soc_clock)
            self.boost_clock = spec.get('boost_clock', self.boost_clock)
            self.memory_clock = spec.get('memory_clock', self.memory_clock)
            self.gpu_cores = spec.get('gpu_cores', self.gpu_cores)
            self.pcie_version = spec.get('pcie_version', self.pcie_version)
            self.pcie_max_width = spec.get('pcie_max_width', self.pcie_max_width)
