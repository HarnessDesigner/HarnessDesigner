# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Apple GPU metrics backend for :mod:`harness_designer.gpu`, via
``apple_smi``.
"""

from ..backend_base import GPUBackend
from ... import check_types as _check_types


class AppleBackend(GPUBackend):
    """Collects metrics from Apple Silicon's GPU via :mod:`apple_smi`.

    Every metric is queried once at construction time; any single reading
    failing degrades to :class:`..backend_base.GPUBackend`'s default of
    ``None`` rather than raising, same convention as every other vendor
    backend.
    """

    @_check_types.do
    def __init__(self):
        from apple_smi import soc_info, sampler

        self.gpu_manufacturer = 'Apple'

        try:
            res = soc_info.get_soc_info()
            self.gpu_name = res.chip_name
            self.gpu_model = res.mac_model
            self.gpu_cores = res.gpu_cores
        except Exception:  # NOQA
            pass

        try:
            samp = sampler.Sampler()
            res = samp.get_metrics()
            self.soc_clock = res.gpu_freq_mhz
            self.gpu_engine = res.gpu_usage_pct
            # A plain number, not a "45.2°C" string -- matches every other
            # vendor backend's gpu_temp convention (see nvidia/backend.py,
            # amd/backend.py); the display label/unit belongs to
            # gpu.GPUAttribute's rendering, not baked into the stored value.
            self.gpu_temp = res.gpu_temp_c
            self.vram_size = res.memory.ram_total
            self.vram_use = res.memory.ram_used
        except Exception:  # NOQA
            pass
