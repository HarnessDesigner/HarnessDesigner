# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Apple GPU memory collection helpers for :mod:`harness_designer.gpu_mem`."""

from apple_smi import soc_info
from apple_smi import sampler

from . import gpu_base as _gpu_base


def collect():
    """Populate :class:`.gpu_base.GPU` with metrics from Apple SMI helpers.

    The function gathers static SoC details with :mod:`apple_smi.soc_info` and
    then samples live metrics with :class:`apple_smi.sampler.Sampler`.

    :raises Exception: Propagates Apple SMI errors raised while collecting data.
    """
    GPU = _gpu_base.GPU

    res = soc_info.get_soc_info()

    GPU.gpu_name.value = res.chip_name
    GPU.gpu_model.value = res.mac_model
    GPU.gpu_manufacturer.value = 'Apple'
    GPU.gpu_cores.value = res.gpu_cores

    samp = sampler.Sampler()
    res = samp.get_metrics()
    GPU.soc_clock.value = res.gpu_freq_mhz
    GPU.gpu_engine.value = res.gpu_usage_pct
    GPU.gpu_temp.value = str(res.gpu_temp_c) + '°C'

    GPU.vram_size.value = res.memory.ram_total
    GPU.vram_use = res.memory.ram_used
