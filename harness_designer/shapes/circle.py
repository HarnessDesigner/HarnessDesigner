# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""2D circle drawing helper for the editor canvas.

Instances cache a :class:`~PySide6.QtGui.QPixmap` representation that can be
attached to the 2D editor provided by :mod:`harness_designer.ui`.
"""

from typing import TYPE_CHECKING

from PySide6.QtGui import QPixmap, QPainter, QColor, QBrush, Qt

from ..geometry import point as _point
from ..geometry.decimal import Decimal as _d
from .. import color as _color


if TYPE_CHECKING:
    from ..ui import editor_2d as _editor_2d


class Circle:
    """Represent a filled circular marker in the 2D editor.

    The circle tracks a bound :class:`harness_designer.geometry.point.Point`
    and rebuilds its cached pixmap whenever relevant geometry or color values
    change.
    """

    def __init__(self, center: _point.Point, diameter: _d, color: _color.Color):
        """Initialize the circle overlay.

        :param center: Circle center point monitored for updates.
        :type center: :class:`harness_designer.geometry.point.Point`
        :param diameter: Diameter of the circle in editor units.
        :type diameter: :class:`harness_designer.geometry.decimal.Decimal`
        :param color: Fill color used when painting the circle.
        :type color: :class:`harness_designer.color.Color`
        """
        self._center = center
        self._diameter = diameter
        self._color = color
        self._pixmap: QPixmap | None = None
        self.artist = None

        center.bind(self._update_point)

    @property
    def diameter(self) -> _d:
        """Return the current circle diameter.

        :returns: Diameter in editor units.
        :rtype: :class:`harness_designer.geometry.decimal.Decimal`
        """
        return self._diameter

    @diameter.setter
    def diameter(self, value: _d):
        """Set the circle diameter and refresh the cached pixmap.

        :param value: New diameter in editor units.
        :type value: :class:`harness_designer.geometry.decimal.Decimal`
        :returns: ``None``
        :rtype: None
        """
        self._diameter = value
        self._pixmap = None
        self._update_artist()

    @property
    def color(self) -> _color.Color:
        """Return the current fill color.

        :returns: RGBA color tuple-like value.
        :rtype: :class:`harness_designer.color.Color`
        """
        return self._color

    @color.setter
    def color(self, value: _color.Color):
        """Set the fill color and invalidate the cached pixmap.

        :param value: Replacement fill color.
        :type value: :class:`harness_designer.color.Color`
        :returns: ``None``
        :rtype: None
        """
        self._color = value
        self._pixmap = None
        self._update_artist()

    @property
    def center(self) -> _point.Point:
        """Return the bound center point.

        :returns: Point used as the circle center.
        :rtype: :class:`harness_designer.geometry.point.Point`
        """
        return self._center

    @center.setter
    def center(self, value: _point.Point):
        """Replace the bound center point.

        The old point is unbound from update notifications and the new point is
        bound so later edits refresh the artist.

        :param value: New center point.
        :type value: :class:`harness_designer.geometry.point.Point`
        :returns: ``None``
        :rtype: None
        """
        self._center.unbind(self._update_artist)
        value.bind(self._update_artist)
        self._center = value

        self._pixmap = None
        self._update_artist()

    def _get_pixmap(self):
        """Build or return the cached pixmap for the circle.

        :returns: Cached pixmap containing the drawn circle.
        :rtype: :class:`~PySide6.QtGui.QPixmap`
        """
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
        """Return whether the circle currently has an attached artist.

        :returns: ``True`` when :meth:`add_to_plot` has attached an artist.
        :rtype: bool
        """
        return self.artist is not None

    def _update_artist(self, p: _point.Point | None = None):
        """Refresh the backing artist if one has been attached.

        :param p: Updated point data from a bound callback, if provided.
        :type p: :class:`harness_designer.geometry.point.Point` or None
        :returns: ``None``
        :rtype: None
        """
        if not self.is_added:
            return

        if p is not None:
            self._pixmap = None

        pixmap = self._get_pixmap()
        self.artist.update((5, 5), pixmap)

    def _update_point(self, p: _point.Point | None = None):
        """Forward point change notifications to :meth:`_update_artist`.

        :param p: Updated point supplied by the bound point callback.
        :type p: :class:`harness_designer.geometry.point.Point` or None
        :returns: ``None``
        :rtype: None
        """
        self._update_artist(p)

    def add_to_plot(self, axes: "_editor_2d.Editor2D") -> None:
        """Add the circle to an editor plot.

        :param axes: Editor surface that can create an artist for this circle.
        :type axes: :class:`harness_designer.ui.editor_2d.Editor2D`
        :returns: ``None``
        :rtype: None
        """
        self.artist = axes.add_line(self)
        self._update_artist()
