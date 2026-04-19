from . import gpu_base as _gpu_base
from . import manager as _manager


GPU = _gpu_base.GPU
GPUMemoryManager = _manager.GPUMemoryManager


del _gpu_base
del _manager
