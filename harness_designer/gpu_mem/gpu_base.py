# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared GPU attribute containers for :mod:`harness_designer.gpu_mem`."""


class GPUAttribute:
    """Store a labeled GPU attribute value for display purposes.

    :param label: Prefix used when rendering the attribute as text.
    :type label: str
    """

    def __init__(self, label):
        """Initialize the attribute with a display label.

        :param label: Prefix used when the value is converted to text.
        :type label: str
        """
        self.label = label
        self.value = 'Unknown'

    def __str__(self):
        """Return the label and current value as a single string.

        :returns: Human-readable label/value text.
        :rtype: str
        """
        return self.label + str(self.value)


class GPUMeta(type):
    """Metaclass that forwards class stringification to :class:`GPU`."""

    def __str__(cls):
        """Render the shared :class:`GPU` state as text.

        :param cls: GPU class being stringified.
        :type cls: type
        :returns: Formatted GPU information.
        :rtype: str
        """
        return GPU.__str__()


class GPU(metaclass=GPUMeta):
    """Shared container of GPU details collected from vendor-specific APIs."""

    driver_name = GPUAttribute('Name: ')
    driver_version = GPUAttribute('Version: ')
    driver_date = GPUAttribute('Release Date: ')

    gpu_model = GPUAttribute('Model: ')
    gpu_name = GPUAttribute('Name: ')
    gpu_manufacturer = GPUAttribute('Manufacturer: ')
    gpu_serial = GPUAttribute('Serial Number: ')
    gpu_cores = GPUAttribute('Core Count: ')

    vram_size = GPUAttribute('Total Size: ')
    vram_width = GPUAttribute('Bus Width: ')
    vram_use = GPUAttribute('Used: ')

    gpu_engine = GPUAttribute('GPU Engine Utilization: ')
    memory_engine = GPUAttribute('Memory Engine Utilization: ')

    soc_clock = GPUAttribute('SOC: ')
    memory_clock = GPUAttribute('Memory: ')

    pcie_max_width = GPUAttribute('Max Bus Width: ')
    pcie_width = GPUAttribute('Used Bus Width: ')
    pcie_max_speed = GPUAttribute('Max Bus Speed: ')
    pcie_speed = GPUAttribute('Used Bus Speed: ')

    pcie_bandwidth = GPUAttribute('Bandwidth: ')
    pcie_version = GPUAttribute('Version: ')

    fan_speed_rpm = GPUAttribute('Speed (RPM): ')
    fan_speed = GPUAttribute('Speed (%): ')

    gpu_temp = GPUAttribute('Temperature: ')

    @classmethod
    def is_ok(cls):
        """Return whether the collected VRAM values look usable.

        :param cls: GPU class containing shared attribute state.
        :type cls: type
        :returns: ``True`` when VRAM size and usage are integers and size is positive.
        :rtype: bool
        """
        return (
            isinstance(cls.vram_size.value, int) and
            isinstance(cls.vram_use.value, int) and
            cls.vram_size.value > 0)

    @classmethod
    def __str__(cls):
        """Format the current GPU state as a multi-section report.

        :param cls: GPU class containing shared attribute state.
        :type cls: type
        :returns: Multiline summary of driver, GPU, VRAM, clock, PCIe, and fan data.
        :rtype: str
        """
        ret = [
            'Driver',
            '===========================================',
            f'\t{cls.driver_name}',
            f'\t{cls.driver_version}',
            f'\t{cls.driver_date}',
            '',
            'GPU',
            '===========================================',
            f'\t{cls.gpu_model}',
            f'\t{cls.gpu_name}',
            f'\t{cls.gpu_manufacturer}',
            f'\t{cls.gpu_serial}',
            f'\t{cls.gpu_cores}',
            '',
            'VRAM',
            '===========================================',
            f'\t{cls.vram_size}',
            f'\t{cls.vram_width}',
            f'\t{cls.vram_use}',
            '',
            'Clock',
            '===========================================',
            f'\t{cls.soc_clock}',
            f'\t{cls.memory_clock}',
            '',
            'PCIE',
            '===========================================',
            f'\t{cls.pcie_max_width}',
            f'\t{cls.pcie_width}',
            f'\t{cls.pcie_max_speed}',
            f'\t{cls.pcie_speed}',
            f'\t{cls.pcie_bandwidth}',
            f'\t{cls.pcie_version}',
            '',
            'FAN',
            '===========================================',
            f'\t{cls.fan_speed_rpm}',
            f'\t{cls.fan_speed}',
            '',
            f'{cls.gpu_temp}'
            f'{cls.gpu_engine}',
            f'{cls.memory_engine}',
        ]
        return '\n'.join(ret)
