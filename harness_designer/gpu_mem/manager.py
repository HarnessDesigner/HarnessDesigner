# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""GPU memory detection and chunk sizing helpers."""

from . import gpu_vendor as _gpu_vendor
from .gpu_base import GPU

from .. import logger as _logger


class GPUMemoryManager:
    """Detect GPU memory details and derive renderer chunk sizes.

    :param opencl_device: Optional OpenCL device used for fallback estimation.
    :type opencl_device: object | None
    """

    def __init__(self, opencl_device=None):
        """Store the optional OpenCL device used for fallback estimation.

        :param opencl_device: Optional OpenCL device exposing ``global_mem_size``.
        :type opencl_device: object | None
        """
        self.device = opencl_device

    def detect(self):
        """Detect the GPU vendor and populate shared GPU metrics.

        :returns: ``None``.
        :rtype: None
        """
        vendor = _gpu_vendor.get()

        if vendor == _gpu_vendor.GPU_NVIDIA:
            self._nvidia()
        elif vendor == _gpu_vendor.GPU_AMD:
            self._amd()
        elif vendor == _gpu_vendor.GPU_APPLE:
            self._apple()
        elif vendor == _gpu_vendor.GPU_INTEL:
            self._intel()
        else:
            # _gpu_vendor.GPU_UNKNOWN
            self._fallback()

    def _nvidia(self):
        """Collect NVIDIA metrics and estimate VRAM if required.

        :returns: ``None``.
        :rtype: None
        """
        from . import nvidia
        nvidia.collect()

        if not GPU.is_ok():
            self._opencl_estimate(multiplier=0.5)

    def _amd(self):
        """Collect AMD metrics and estimate VRAM if required.

        :returns: ``None``.
        :rtype: None
        """
        from . import amd

        amd.collect()

        if not GPU.is_ok():
            self._opencl_estimate(multiplier=0.5)

    def _intel(self):
        """Collect Intel metrics and estimate VRAM if required.

        :returns: ``None``.
        :rtype: None
        """
        from . import intel

        intel.collect()

        if not GPU.is_ok():
            self._opencl_estimate(multiplier=0.4)

    def _apple(self):
        """Collect Apple metrics and estimate VRAM if required.

        :returns: ``None``.
        :rtype: None
        """
        from . import apple

        apple.collect()

        if not GPU.is_ok():
            self._opencl_estimate(multiplier=0.4)

    def _opencl_estimate(self, multiplier):
        """Estimate VRAM values from the configured OpenCL device.

        The method stores total memory in GiB and computes used memory as
        ``total - total * multiplier``. The intended semantic of ``multiplier``
        beyond that calculation is UNKNOWN.

        :param multiplier: Multiplier used by the current estimation formula.
        :type multiplier: float
        :returns: ``None``.
        :rtype: None
        """
        if self.device:
            total = self.device.global_mem_size / (1024 ** 3)
            GPU.vram_size.value = total
            GPU.vram_use.value = total - total * multiplier
            return

        self._fallback()

    def _fallback(self):  # NOQA
        """Populate conservative default VRAM values.

        The fallback uses 4 GiB total VRAM and 2 GiB used VRAM.

        :returns: ``None``.
        :rtype: None
        """
        GPU.vram_size.value = 4294967296
        GPU.vram_use.value = 2147483648

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
        free_mem = GPU.vram_size - GPU.vram_use

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
