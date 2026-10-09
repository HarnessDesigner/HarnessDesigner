# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""NVIDIA GPU metrics backend for :mod:`harness_designer.gpu`, via ``nvapi``
(replaces the previous ``pynvml``-based implementation -- ``pynvml`` requires
a separately-installed system component and exposes materially less than
``nvapi``'s direct driver dispatch)."""

from ..backend_base import GPUBackend, DisplayPortInfo
from ... import check_types as _check_types


class NvidiaBackend(GPUBackend):
    """Collects metrics from the first NVIDIA GPU via :mod:`nvapi`.

    Every metric is queried once at construction time. Any single metric
    nvapi doesn't support on the current driver/hardware (e.g. legacy fan
    APIs on a card whose driver has moved to the newer ClientFanCoolers
    API) is left at :class:`.backend_base.GPUBackend`'s default of ``None``
    rather than raising -- see that class's own docstring.
    """

    @_check_types.do
    def __init__(self) -> None:
        import nvapi

        gpus = nvapi.GPUs()

        try:
            # nvapi's driverVersion is the standard NVIDIA convention: the
            # raw integer is version * 100 (e.g. 57342 -> "573.42").
            self.driver_version = f'{gpus.driver_info.driver_version / 100:.2f}'
        except Exception:  # NOQA
            pass

        gpu = None
        target_logical_gpu = None
        for logical_gpu in gpus:
            for physical_gpu in logical_gpu.physical_gpus:
                gpu = physical_gpu
                target_logical_gpu = logical_gpu
                break
            if gpu is not None:
                break

        if gpu is None:
            return

        self.gpu_manufacturer = 'NVIDIA'

        try:
            self.gpu_name = gpu.full_name
        except Exception:  # NOQA
            pass

        try:
            self.gpu_model = f'{gpu.quadro_status} {gpu.short_name}'
        except Exception:  # NOQA
            pass

        try:
            self.gpu_serial = gpu.serial_number
        except Exception:  # NOQA
            pass

        try:
            self.gpu_cores = gpu.core_count
        except Exception:  # NOQA
            pass

        try:
            self.vram_size = gpu.dedicated_memory * 1024  # nvapi reports KB
        except Exception:  # NOQA
            pass

        try:
            self.vram_width = gpu.ram_bus_width
        except Exception:  # NOQA
            pass

        try:
            self.vram_use = (gpu.dedicated_memory -
                             gpu.current_available_dedicated_memory) * 1024
        except Exception:  # NOQA
            pass

        try:
            # Driver-documented utilization-domain order: 0=GPU, 1=frame
            # buffer (memory), 2=video engine, 3=bus interface.
            utilization = gpu.performance_monitor.get('utilization')
            if utilization:
                if len(utilization) > 0 and utilization[0] is not None:
                    self.gpu_engine = utilization[0]
                if len(utilization) > 1 and utilization[1] is not None:
                    self.memory_engine = utilization[1]
        except Exception:  # NOQA
            pass

        try:
            clocks = gpu.clock_frequencies.current
            if clocks.graphics is not None:
                self.soc_clock = clocks.graphics / 1000  # kHz -> MHz
            if clocks.memory is not None:
                self.memory_clock = clocks.memory / 1000
        except Exception:  # NOQA
            pass

        try:
            # nvapi only exposes current lane width, not max width/speed/
            # bandwidth/PCIe generation -- those stay None/'Unknown'.
            self.pcie_width = gpu.current_pcie_downstream_width
        except Exception:  # NOQA
            pass

        try:
            self.fan_speed_rpm = gpu.tach_reading
        except Exception:  # NOQA
            pass

        try:
            self.fan_speed = gpu.current_fan_speed_level
        except Exception:  # NOQA
            pass

        try:
            sensors = gpu.thermal_sensors
            if sensors:
                self.gpu_temp = sensors[0].current_temp
        except Exception:  # NOQA
            pass

        self.displays = []
        try:
            for port_index, port in enumerate(target_logical_gpu):
                display_list = list(port)

                if not display_list:
                    info = DisplayPortInfo()
                    info.index = port_index
                    try:
                        info.connector_type = str(port.connector_type)
                    except Exception:  # NOQA
                        pass
                    try:
                        info.is_connected = bool(port.is_connected)
                        info.is_active = bool(port.is_active)
                    except Exception:  # NOQA
                        pass
                    self.displays.append(info)
                    continue

                for display in display_list:
                    info = DisplayPortInfo()
                    info.index = port_index

                    try:
                        info.connector_type = str(port.connector_type)
                    except Exception:  # NOQA
                        pass

                    try:
                        info.is_connected = bool(port.is_connected)
                        info.is_active = bool(port.is_active)
                    except Exception:  # NOQA
                        pass

                    try:
                        info.edid_data = display.edid_data
                    except Exception:  # NOQA
                        pass

                    try:
                        edid_info = display.edid_info
                        if edid_info is not None:
                            info.monitor_name = edid_info.monitor_name
                    except Exception:  # NOQA
                        pass

                    try:
                        timing = display.get_timing(0, 0, 0)
                        if timing.h_total and timing.v_total:
                            refresh_hz = (timing.pixel_clock_10khz * 10000) / \
                                        (timing.h_total * timing.v_total)
                            info.resolution = (timing.h_visible, timing.v_visible, refresh_hz)
                    except Exception:  # NOQA
                        pass

                    self.displays.append(info)
        except Exception:  # NOQA
            pass
