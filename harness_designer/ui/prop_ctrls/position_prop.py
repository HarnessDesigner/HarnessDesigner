# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets

from . import point_prop as _point_prop
from ... import check_types as _check_types


class PositionProperty(_point_prop.PointProperty):

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget, label: str, axes: str = 'xyz'):
        super().__init__(parent, label, 'mm', axes)
