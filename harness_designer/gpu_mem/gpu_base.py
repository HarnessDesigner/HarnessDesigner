

class GPUAttribute:

    def __init__(self, label):
        self.label = label
        self.value = 'Unknown'

    def __str__(self):
        return self.label + str(self.value)


class GPUMeta(type):

    def __str__(cls):
        return GPU.__str__()


class GPU(metaclass=GPUMeta):

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
        return (
            isinstance(cls.vram_size.value, int) and
            isinstance(cls.vram_use.value, int) and
            cls.vram_size.value > 0)

    @classmethod
    def __str__(cls):
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


print(GPU)
