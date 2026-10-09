# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets

from . import point_prop as _point_prop


class ScaleProperty(_point_prop.PointProperty):

    MIN_VALUE: float = 0.01
    MAX_VALUE: float = 9.9
    INCREMENT: float = 0.01

    def __init__(self, parent: QtWidgets.QWidget, label: str, axes: str = 'xyz') -> None:
        super().__init__(parent, label, '', axes)
