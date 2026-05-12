# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtGui import QPixmap, QPainter, QColor, QBrush, Qt

from ..geometry import point as _point
from ..geometry.decimal import Decimal as _d
from .. import color as _color


if TYPE_CHECKING:
    from ..ui import editor_2d as _editor_2d


class Circle:

    def __init__(self, center: _point.Point, diameter: _d, color: _color.Color):
        self._center = center
        self._diameter = diameter
        self._color = color
        self._pixmap: QPixmap | None = None
        self.artist = None

        center.bind(self._update_point)

    @property
    def diameter(self) -> _d:
        return self._diameter

    @diameter.setter
    def diameter(self, value: _d):
        self._diameter = value
        self._pixmap = None
        self._update_artist()

    @property
    def color(self) -> _color.Color:
        return self._color

    @color.setter
    def color(self, value: _color.Color):
        self._color = value
        self._pixmap = None
        self._update_artist()

    @property
    def center(self) -> _point.Point:
        return self._center

    @center.setter
    def center(self, value: _point.Point):
        self._center.unbind(self._update_artist)
        value.bind(self._update_artist)
        self._center = value

        self._pixmap = None
        self._update_artist()

    def _get_pixmap(self):
        if self._pixmap is None:
            dia = int(self._diameter)

            pixmap = QPixmap(dia, dia)
            pixmap.fill(Qt.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)

            r, g, b, a = self._color
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(int(r * 255), int(g * 255),
                                           int(b * 255), int(a * 255))))

            x, y = self._center.as_float[:-1]
            x -= self._diameter / _d(2.0)
            y -= self._diameter / _d(2.0)

            painter.drawEllipse(int(x), int(y), dia, dia)
            painter.end()

            self._pixmap = pixmap

        return self._pixmap

    @property
    def is_added(self):
        return self.artist is not None

    def _update_artist(self, p: _point.Point | None = None):
        if not self.is_added:
            return

        if p is not None:
            self._pixmap = None

        pixmap = self._get_pixmap()
        self.artist.update((5, 5), pixmap)

    def _update_point(self, p: _point.Point | None = None):
        self._update_artist(p)

    def add_to_plot(self, axes: "_editor_2d.Editor2D") -> None:
        self.artist = axes.add_line(self)
        self._update_artist()
