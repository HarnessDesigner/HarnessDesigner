# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import point_prop as _point_prop


class PositionProperty(_point_prop.PointProperty):

    def __init__(self, parent, label: str, axes: str = 'xyz'):
        super().__init__(parent, label, 'mm', axes)
