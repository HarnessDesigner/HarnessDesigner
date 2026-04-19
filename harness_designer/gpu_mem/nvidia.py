import pynvml

from . import gpu_base as _gpu_base


def collect():
    GPU = _gpu_base.GPU

    pynvml.nvmlInit()

    device = pynvml.nvmlDeviceGetHandleByIndex(0)

    GPU.pcie_speed.value = pynvml.nvmlDeviceGetPcieSpeed(device)
    GPU.gpu_cores.value = pynvml.nvmlDeviceGetNumGpuCores(device)

    res = pynvml.nvmlDeviceGetUtilizationRates(device)
    GPU.gpu_engine.value = res.gpu
    GPU.memory_engine.value = res.memory

    res = pynvml.nvmlDeviceGetMemoryInfo(device)
    GPU.vram_size.value = res.total  # NOQA
    GPU.vram_use.value = res.used  # NOQA

    GPU.vram_width.value = pynvml.nvmlDeviceGetMemoryBusWidth(device)
    GPU.gpu_temp.value = pynvml.nvmlDeviceGetTemperatureV(device, 0)
    GPU.fan_speed_rpm.value = pynvml.nvmlDeviceGetFanSpeedRPM(device)
    GPU.fan_speed.value = pynvml.nvmlDeviceGetFanSpeed(device)
    GPU.soc_clock.value = pynvml.nvmlDeviceGetClockInfo(device, pynvml.NVML_CLOCK_GRAPHICS)
    GPU.memory_clock.value = pynvml.nvmlDeviceGetClockInfo(device, pynvml.NVML_CLOCK_MEM)
    GPU.gpu_serial.value = pynvml.nvmlDeviceGetSerial(device)

    brand = pynvml.nvmlDeviceGetBrand

    brand_maping = {
        pynvml.NVML_BRAND_UNKNOWN: 'Unknown',
        pynvml.NVML_BRAND_QUADRO: 'Quadro',
        pynvml.NVML_BRAND_TESLA: 'Tesla',
        pynvml.NVML_BRAND_NVS: 'NVS',
        pynvml.NVML_BRAND_GEFORCE: 'GeForce',
        pynvml.NVML_BRAND_TITAN: 'Titan',
        pynvml.NVML_BRAND_NVIDIA_VAPPS: 'Virtual Applications',
        pynvml.NVML_BRAND_NVIDIA_VPC: 'Virtual PC',
        pynvml.NVML_BRAND_NVIDIA_VCS: 'vGPU for Compute',
        pynvml.NVML_BRAND_NVIDIA_VWS: 'RTX Virtual Workstation',
        pynvml.NVML_BRAND_NVIDIA_CLOUD_GAMING: 'Gaming',
        pynvml.NVML_BRAND_QUADRO_RTX: 'Quadro RTX',
        pynvml.NVML_BRAND_NVIDIA_RTX: 'RTX',
        pynvml.NVML_BRAND_NVIDIA: 'NVidia'
    }

    GPU.gpu_model.value = brand_maping.get(brand, 'Unknown') + ' ' + pynvml.nvmlDeviceGetBoardPartNumber(device)
    GPU.gpu_name.value = pynvml.nvmlDeviceGetName(device)
    GPU.driver_version.value = pynvml.nvmlSystemGetDriverVersion(device)

    pynvml.nvmlShutdown()
