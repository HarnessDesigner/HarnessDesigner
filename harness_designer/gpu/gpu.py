# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Entry point for :mod:`harness_designer.gpu` -- picks, loads, and queries
whichever vendor GPU backend actually applies to this machine.

:class:`GPU` is the one thing the rest of the app should ever import from
this package (``from harness_designer.gpu import GPU``) -- everything else
here (per-vendor subpackages, :mod:`.gl_meminfo`, :mod:`.gpu_specs_lookup`,
:mod:`.os_vram_usage`, ...) is an implementation detail ``GPU.detect()``
drives, not a separate public surface.
"""

from .gpu_base import GPUAttribute
from .gpu_vendor import get as _get_vendor
from .gpu_vendor import GPU_NVIDIA, GPU_AMD, GPU_APPLE, GPU_INTEL
from .backend_base import GPUBackend as _GPUBackend

from .. import logger as _logger
from .. import check_types as _check_types


class GPU:
    """Detected GPU details, plus the detection/fallback logic that fills
    them in.

    :param opencl_device: Optional OpenCL device used for fallback estimation.
    :type opencl_device: object | None
    """

    @_check_types.do
    def __init__(self, opencl_device=None):
        """Create the attribute set (all start at ``'Unknown'``) and store
        the optional OpenCL device used for fallback estimation.

        :param opencl_device: Optional OpenCL device exposing ``global_mem_size``.
        :type opencl_device: object | None
        """
        self.device = opencl_device

        self.driver_name = GPUAttribute('Name: ')
        self.driver_version = GPUAttribute('Version: ')
        self.driver_date = GPUAttribute('Release Date: ')

        self.gpu_model = GPUAttribute('Model: ')
        self.gpu_name = GPUAttribute('Name: ')
        self.gpu_manufacturer = GPUAttribute('Manufacturer: ')
        self.gpu_serial = GPUAttribute('Serial Number: ')
        self.gpu_cores = GPUAttribute('Core Count: ')
        self.architecture = GPUAttribute('Architecture: ')
        self.generation = GPUAttribute('Generation: ')
        self.foundry = GPUAttribute('Foundry: ')

        self.vram_size = GPUAttribute('Total Size: ')
        self.vram_width = GPUAttribute('Bus Width: ')
        self.vram_use = GPUAttribute('Used: ')
        self.memory_type = GPUAttribute('Type: ')
        self.memory_bandwidth = GPUAttribute('Bandwidth: ')

        self.gpu_engine = GPUAttribute('GPU Engine Utilization: ')
        self.memory_engine = GPUAttribute('Memory Engine Utilization: ')

        self.soc_clock = GPUAttribute('SOC: ')
        self.boost_clock = GPUAttribute('Boost (rated): ')
        self.memory_clock = GPUAttribute('Memory: ')

        self.pcie_max_width = GPUAttribute('Max Bus Width: ')
        self.pcie_width = GPUAttribute('Used Bus Width: ')
        self.pcie_max_speed = GPUAttribute('Max Bus Speed: ')
        self.pcie_speed = GPUAttribute('Used Bus Speed: ')
        self.pcie_bandwidth = GPUAttribute('Bandwidth: ')
        self.pcie_version = GPUAttribute('Version: ')

        self.fan_speed_rpm = GPUAttribute('Speed (RPM): ')
        self.fan_speed = GPUAttribute('Speed (%): ')

        self.gpu_temp = GPUAttribute('Temperature: ')

    @_check_types.do
    def detect(self):
        """Detect the GPU vendor and populate this instance's attributes.

        :returns: ``None``.
        :rtype: None
        """
        vendor = _get_vendor()

        if vendor == GPU_NVIDIA:
            self._nvidia()
        elif vendor == GPU_AMD:
            self._amd()
        elif vendor == GPU_APPLE:
            self._apple()
        elif vendor == GPU_INTEL:
            self._intel()
        else:
            # GPU_UNKNOWN
            self._fallback()

    @_check_types.do
    def is_ok(self):
        """Return whether the collected VRAM values look usable.

        :returns: ``True`` when VRAM size and usage are integers and size is positive.
        :rtype: bool
        """
        return (
            isinstance(self.vram_size.value, int) and
            isinstance(self.vram_use.value, int) and
            self.vram_size.value > 0)

    @_check_types.do
    def __str__(self):
        """Format the current GPU state as a multi-section report.

        :returns: Multiline summary of driver, GPU, VRAM, clock, PCIe, and fan data.
        :rtype: str
        """
        ret = [
            'Driver',
            '===========================================',
            f'\t{self.driver_name}',
            f'\t{self.driver_version}',
            f'\t{self.driver_date}',
            '',
            'GPU',
            '===========================================',
            f'\t{self.gpu_model}',
            f'\t{self.gpu_name}',
            f'\t{self.gpu_manufacturer}',
            f'\t{self.gpu_serial}',
            f'\t{self.gpu_cores}',
            f'\t{self.architecture}',
            f'\t{self.generation}',
            f'\t{self.foundry}',
            '',
            'VRAM',
            '===========================================',
            f'\t{self.vram_size}',
            f'\t{self.vram_width}',
            f'\t{self.vram_use}',
            f'\t{self.memory_type}',
            f'\t{self.memory_bandwidth}',
            '',
            'Clock',
            '===========================================',
            f'\t{self.soc_clock}',
            f'\t{self.boost_clock}',
            f'\t{self.memory_clock}',
            '',
            'PCIE',
            '===========================================',
            f'\t{self.pcie_max_width}',
            f'\t{self.pcie_width}',
            f'\t{self.pcie_max_speed}',
            f'\t{self.pcie_speed}',
            f'\t{self.pcie_bandwidth}',
            f'\t{self.pcie_version}',
            '',
            'FAN',
            '===========================================',
            f'\t{self.fan_speed_rpm}',
            f'\t{self.fan_speed}',
            '',
            f'{self.gpu_temp}'
            f'{self.gpu_engine}',
            f'{self.memory_engine}',
        ]
        return '\n'.join(ret)

    @_check_types.do
    def _collect_generic(self, backend: _GPUBackend):
        """Copy every non-``None`` metric off a vendor backend onto ``self``.

        Every concrete backend (:class:`.nvidia.NvidiaBackend`,
        :class:`.amd.AMDBackend`, ...) exposes the same attribute names as
        :class:`.backend_base.GPUBackend` -- see that module's docstring --
        so this one loop works for any vendor with no branching.

        :param backend: Vendor backend already queried at construction time.
        :type backend: :class:`.backend_base.GPUBackend`
        :returns: ``None``.
        :rtype: None
        """
        for name in _GPUBackend.ATTRIBUTE_NAMES:
            value = getattr(backend, name, None)
            if value is not None:
                getattr(self, name).value = value

    @_check_types.do
    def _collect_gaps(self, backend: _GPUBackend):
        """Like :meth:`_collect_generic`, but only fills attributes that
        don't already have a real value.

        Used for the GL/table-based fallback (:class:`.gl_meminfo.GLMemInfoBackend`)
        so it can supplement a vendor SDK that partially succeeded --
        e.g. filling in ``architecture``/``boost_clock`` nvapi/pyamd_adl
        never reported -- without clobbering ``vram_use`` or anything else
        the SDK already measured for real.

        :param backend: Fallback backend already queried at construction time.
        :type backend: :class:`.backend_base.GPUBackend`
        :returns: ``None``.
        :rtype: None
        """
        for name in _GPUBackend.ATTRIBUTE_NAMES:
            attr = getattr(self, name)
            if attr.value != 'Unknown':
                continue

            value = getattr(backend, name, None)
            if value is not None:
                attr.value = value

    @_check_types.do
    def _gl_meminfo_fallback(self) -> bool:
        """Run the GL/table-based fallback as a gap-fill; report whether
        this instance now has a usable VRAM size/usage pair.

        Always worth running regardless of whether a vendor SDK already
        succeeded -- see :meth:`_collect_gaps` and :mod:`.gl_meminfo`'s own
        docstring for why this supplements rather than replaces SDK data.

        :returns: ``True`` if :meth:`is_ok` passes after this call.
        :rtype: bool
        """
        from .gl_meminfo import GLMemInfoBackend

        try:
            self._collect_gaps(GLMemInfoBackend())
        except Exception as err:  # NOQA
            _logger.warning(f'GLMemInfoBackend unavailable: {err!r}')

        return self.is_ok()

    @_check_types.do
    def _nvidia(self):
        """Collect NVIDIA metrics, then fill in anything nvapi couldn't,
        then estimate VRAM if even that came up short.

        OpenGL reporting NVIDIA as the active vendor doesn't guarantee
        ``nvapi`` itself can actually get anywhere -- the shared library
        can be missing/fail to load (a separate concern from OpenGL's own
        ICD binding), or its own import-time init can raise for other
        reasons. Either way, the GL/table-based fallback runs regardless
        (as a gap-fill, see :meth:`_collect_gaps`) -- both to supply VRAM
        when nvapi has nothing (``GL_NVX_gpu_memory_info`` is cheap, no new
        library involved, and often still works even when nvapi can't load
        at all), and to fill static fields (architecture, boost clock,
        PCIe generation, ...) nvapi never reports even when it did work.

        :returns: ``None``.
        :rtype: None
        """
        from .nvidia import NvidiaBackend

        try:
            backend = NvidiaBackend()
        except Exception as err:  # NOQA
            _logger.warning(f'NvidiaBackend unavailable: {err!r}')
            backend = None

        if backend is not None:
            self._collect_generic(backend)

        if not self._gl_meminfo_fallback():
            self._opencl_estimate(multiplier=0.5)

    @_check_types.do
    def _amd(self):
        """Collect AMD metrics, then fill in anything pyamd_adl couldn't,
        then estimate VRAM if even that came up short.

        See :meth:`_nvidia` -- same reasoning. The GL fallback's VRAM half
        here (``GL_ATI_meminfo``) can only produce a usable result when the
        GPU model parsed from ``GL_RENDERER`` is in :mod:`.gpu_specs_lookup`'s
        table (the extension itself has no total-capacity query at all) --
        when it misses, VRAM stays whatever pyamd_adl left it at, but static
        fields can still get filled in from the same table match.

        :returns: ``None``.
        :rtype: None
        """
        from .amd import AMDBackend

        try:
            backend = AMDBackend()
        except Exception as err:  # NOQA
            _logger.warning(f'AMDBackend unavailable: {err!r}')
            backend = None

        if backend is not None:
            self._collect_generic(backend)

        if not self._gl_meminfo_fallback():
            self._opencl_estimate(multiplier=0.5)

    @_check_types.do
    def _intel(self):
        """Collect Intel metrics and estimate VRAM if required.

        No vendor SDK exists for Intel in this codebase yet (:class:`.intel.IntelBackend`
        is a placeholder, currently a no-op) -- the GL/table-based fallback
        (:mod:`.gl_meminfo`) *is* the primary source here, not a fallback of
        one: the combined spec table for static specs and total VRAM (Intel
        has never had a ``GL_NVX_gpu_memory_info``/``GL_ATI_meminfo``
        equivalent either), :mod:`.os_vram_usage` for the live "used" figure.

        :returns: ``None``.
        :rtype: None
        """
        from .intel import IntelBackend

        try:
            backend = IntelBackend()
        except Exception as err:  # NOQA
            _logger.warning(f'IntelBackend unavailable: {err!r}')
            backend = None

        if backend is not None:
            self._collect_generic(backend)

        if not self._gl_meminfo_fallback():
            self._opencl_estimate(multiplier=0.4)

    @_check_types.do
    def _apple(self):
        """Collect Apple metrics and estimate VRAM if required.

        :returns: ``None``.
        :rtype: None
        """
        from .apple import AppleBackend

        try:
            backend = AppleBackend()
        except Exception as err:  # NOQA
            _logger.warning(f'AppleBackend unavailable: {err!r}')
            backend = None

        if backend is not None:
            self._collect_generic(backend)

        if not self.is_ok():
            self._opencl_estimate(multiplier=0.4)

    @_check_types.do
    def _opencl_estimate(self, multiplier):
        """Estimate VRAM values from the configured OpenCL device.

        The method stores total memory in bytes (``global_mem_size`` is
        already bytes per the OpenCL standard -- previously divided by
        1024**3 here, storing GiB instead, which both broke :meth:`is_ok`'s
        ``isinstance(..., int)`` check on any real float total and was
        inconsistent with every vendor backend and :meth:`_fallback`, which
        both already store bytes) and computes used memory as
        ``total - total * multiplier``. The intended semantic of ``multiplier``
        beyond that calculation is UNKNOWN.

        :param multiplier: Multiplier used by the current estimation formula.
        :type multiplier: float
        :returns: ``None``.
        :rtype: None
        """
        if self.device:
            total = int(self.device.global_mem_size)
            self.vram_size.value = total
            self.vram_use.value = int(total - total * multiplier)
            return

        self._fallback()

    @_check_types.do
    def _fallback(self):  # NOQA
        """Populate conservative default VRAM values.

        The fallback uses 4 GiB total VRAM and 2 GiB used VRAM.

        :returns: ``None``.
        :rtype: None
        """
        self.vram_size.value = 4294967296
        self.vram_use.value = 2147483648

    @_check_types.do
    def get_chunk_size(self, width, height, target_usage=0.4):  # NOQA
        """Compute a render chunk height from the stored VRAM information.

        The method estimates per-chunk memory use for RGB ``float32`` pixels,
        clamps the chunk height to at least 50 rows and at most ``height``, and
        logs the resulting strategy.

        :param width: Image width in pixels.
        :type width: int
        :param height: Image height in pixels.
        :type height: int
        :param target_usage: Fraction of free VRAM to target.
        :type target_usage: float
        :returns: Chunk height in rows.
        :rtype: int
        """
        free_mem = self.vram_size.value - self.vram_use.value

        target_vram = free_mem * target_usage
        bytes_per_pixel = 3 * 4  # RGB float32
        target_pixels = target_vram / bytes_per_pixel

        chunk_size = int(target_pixels / width)

        # Ensure reasonable bounds
        chunk_size = max(50, min(chunk_size, height))

        num_chunks = (height + chunk_size - 1) // chunk_size
        vram_per_chunk = (width * chunk_size * bytes_per_pixel) / (1024 ** 3)

        _logger.info(f"RENDERER: Chunk strategy for {width}x{height}:")
        _logger.info(f"RENDERER:   Chunk size: {chunk_size} rows")
        _logger.info(f"RENDERER:   Num chunks: {num_chunks}")
        _logger.info(f"RENDERER:   VRAM/chunk: {vram_per_chunk:.2f}GB")

        return chunk_size
