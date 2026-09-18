# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import array_pool as _array_pool


class OBB(_array_pool.ArrayPool):

    def __init__(self):
        super().__init__([[0.0] * 3] * 8)
