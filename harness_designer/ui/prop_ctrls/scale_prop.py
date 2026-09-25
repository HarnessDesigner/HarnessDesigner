# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import point_prop as _point_prop


class ScaleProperty(_point_prop.PointProperty):

    MIN_VALUE: float = 0.01
    MAX_VALUE: float = 9.9
    INCREMENT: float = 0.01

    def __init__(self, parent, label: str, axes: str = 'xyz'):
        super().__init__(parent, label, '', axes)
