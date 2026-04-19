from . import gpu_vendor as _gpu_vendor
from .gpu_base import GPU

from .. import logger as _logger


class GPUMemoryManager:

    def __init__(self, opencl_device=None):
        self.device = opencl_device

    def detect(self):
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
        from . import nvidia
        nvidia.collect()

        if not GPU.is_ok():
            self._opencl_estimate(multiplier=0.5)

    def _amd(self):
        from . import amd

        amd.collect()

        if not GPU.is_ok():
            self._opencl_estimate(multiplier=0.5)

    def _intel(self):
        from . import intel

        intel.collect()

        if not GPU.is_ok():
            self._opencl_estimate(multiplier=0.4)

    def _apple(self):
        from . import apple

        apple.collect()

        if not GPU.is_ok():
            self._opencl_estimate(multiplier=0.4)

    def _opencl_estimate(self, multiplier):
        if self.device:
            total = self.device.global_mem_size / (1024 ** 3)
            GPU.vram_size.value = total
            GPU.vram_use.value = total - total * multiplier
            return

        self._fallback()

    def _fallback(self):  # NOQA
        GPU.vram_size.value = 4294967296
        GPU.vram_use.value = 2147483648

    def get_chunk_size(self, width, height, target_usage=0.4):  # NOQA
        free_mem = GPU.vram_size - GPU.vram_use

        target_vram = free_mem * target_usage
        bytes_per_pixel = 3 * 4  # RGB float32
        target_pixels = target_vram / bytes_per_pixel

        chunk_size = int(target_pixels / width)

        # Ensure reasonable bounds
        chunk_size = max(50, min(chunk_size, height))

        num_chunks = (height + chunk_size - 1) // chunk_size
        vram_per_chunk = (width * chunk_size * bytes_per_pixel) / (1024 ** 3)

        _logger.logger.info(f"RENDERER: Chunk strategy for {width}x{height}:")
        _logger.logger.info(f"RENDERER:   Chunk size: {chunk_size} rows")
        _logger.logger.info(f"RENDERER:   Num chunks: {num_chunks}")
        _logger.logger.info(f"RENDERER:   VRAM/chunk: {vram_per_chunk:.2f}GB")

        return chunk_size
