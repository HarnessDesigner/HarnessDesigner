import amdsmi

from . import gpu_base as _gpu_base


def collect():
    amdsmi.amdsmi_init()

    devices = amdsmi.amdsmi_get_processor_handles()
    if devices:
        device = devices[0]
        GPU = _gpu_base.GPU

        ret = amdsmi.amdsmi_get_gpu_driver_info(device)
        GPU.driver_name.value = ret['driver_name']
        GPU.driver_version.value = ret['driver_version']
        GPU.driver_date.value = ret['driver_date']

        ret = amdsmi.amdsmi_get_gpu_asic_info(device)
        GPU.gpu_name.value = ret['market_name']
        GPU.gpu_manufacturer.value = ret['vendor_name']

        ret = amdsmi.amdsmi_get_gpu_vram_info(device)
        GPU.vram_size.value = ret['vram_size'] * 1024
        GPU.vram_width.value = ret['vram_bit_width']

        ret = amdsmi.amdsmi_get_gpu_board_info(device)
        GPU.gpu_model.value = ret['model_number']
        GPU.gpu_serial.value = ret['product_serial']

        ret = amdsmi.amdsmi_get_gpu_activity(device)
        GPU.gpu_engine.value = ret['gfx_activity']
        GPU.memory_engine.value = ret['umc_activity']

        ret = amdsmi.amdsmi_get_gpu_vram_usage(device)
        GPU.vram_use = ret['vram_used'] * 1024

        ret = amdsmi.amdsmi_get_clock_info(device, amdsmi.AmdSmiClkType.SOC)
        GPU.soc_clock.value = ret['clk']

        ret = amdsmi.amdsmi_get_clock_info(device, amdsmi.AmdSmiClkType.MEM)
        GPU.memory_clock.value = ret['clk']

        ret = amdsmi.amdsmi_get_pcie_info(device)

        pcie_static = ret['pcie_static']
        pcie_metric = ret['pcie_metric']

        GPU.pcie_max_width.value = pcie_static['max_pcie_width']
        GPU.pcie_max_speed.value = pcie_static['max_pcie_speed']
        GPU.pcie_version.value = pcie_static['pcie_interface_version']

        GPU.pcie_width.value = pcie_metric['pcie_width']
        GPU.pcie_speed.value = pcie_metric['pcie_speed']
        GPU.pcie_bandwidth.value = pcie_metric['pcie_bandwidth']

        GPU.fan_speed_rpm.value = amdsmi.amdsmi_get_gpu_fan_rpms(device, 0)

        fan_speed_scalar = amdsmi.amdsmi_get_gpu_fan_speed(device, 0)
        fan_speed_max_scalar = amdsmi.amdsmi_get_gpu_fan_speed_max(device, 0)

        GPU.fan_speed.value = round(fan_speed_scalar / fan_speed_max_scalar * 100.0, 2)

        GPU.gpu_temp.value = amdsmi.amdsmi_get_temp_metric(
            device, amdsmi.AmdSmiTemperatureType.HOTSPOT,
            amdsmi.AmdSmiTemperatureMetric.CURRENT)

        amdsmi.amdsmi_shut_down()
