# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""2D line drawing helper for the editor canvas.

This module renders wire-like lines, optionally with stripe markers, using a
cached :class:`~PySide6.QtGui.QPixmap`.
"""

from typing import TYPE_CHECKING

from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, Qt

from ..geometry import point as _point
from ..geometry import line as _line
from ..geometry.decimal import Decimal as _decimal
from .. import color as _color


if TYPE_CHECKING:
    from .. import Editor2D


class Line:
    """Represent a drawable 2D line segment for the editor.

    The line listens for endpoint updates and rebuilds its pixmap whenever its
    geometry or colors change.
    """

    def __init__(self, p1: _point.Point, p2: _point.Point, width: _decimal,
                 color: _color.Color, stripe_color: _color.Color | None):
        """Initialize the drawable line.

        :param p1: Start point of the line.
        :type p1: :class:`harness_designer.geometry.point.Point`
        :param p2: End point of the line.
        :type p2: :class:`harness_designer.geometry.point.Point`
        :param width: Drawn line width.
        :type width: :class:`harness_designer.geometry.decimal.Decimal`
        :param color: Primary wire color.
        :type color: :class:`harness_designer.color.Color`
        :param stripe_color: Optional stripe color drawn across the wire.
        :type stripe_color: :class:`harness_designer.color.Color` or None
        """
        self._p1 = p1
        self._p2 = p2
        self._width = width
        self._color = color
        self._stripe_color = stripe_color
        self._pixmap: QPixmap | None = None
        self.artist = None

        p1.bind(self._update_artist)
        p2.bind(self._update_artist)

    @property
    def width(self) -> _decimal:
        """Return the current line width.

        :returns: Width in editor units.
        :rtype: :class:`harness_designer.geometry.decimal.Decimal`
        """
        return self._width

    @width.setter
    def width(self, value: _decimal):
        """Set the line width and refresh the artist.

        :param value: Replacement line width.
        :type value: :class:`harness_designer.geometry.decimal.Decimal`
        :returns: ``None``
        :rtype: None
        """
        self._width = value
        self._pixmap = None
        self._update_artist()

    @property
    def color(self) -> _color.Color:
        """Return the primary line color.

        :returns: RGBA color tuple-like value.
        :rtype: :class:`harness_designer.color.Color`
        """
        return self._color

    @color.setter
    def color(self, value: _color.Color):
        """Set the primary line color.

        :param value: Replacement wire color.
        :type value: :class:`harness_designer.color.Color`
        :returns: ``None``
        :rtype: None
        """
        self._color = value
        self._pixmap = None
        self._update_artist()

    @property
    def stripe_color(self) -> _color.Color:
        """Return the optional stripe color.

        :returns: Stripe color or ``None`` when stripes are disabled.
        :rtype: :class:`harness_designer.color.Color` or None
        """
        return self._stripe_color

    @stripe_color.setter
    def stripe_color(self, value: _color.Color):
        """Set the optional stripe color.

        :param value: Replacement stripe color.
        :type value: :class:`harness_designer.color.Color`
        :returns: ``None``
        :rtype: None
        """
        self._stripe_color = value
        self._pixmap = None
        self._update_artist()

    @property
    def p1(self) -> _point.Point:
        """Return the start point.

        :returns: Current line start point.
        :rtype: :class:`harness_designer.geometry.point.Point`
        """
        return self._p1

    @p1.setter
    def p1(self, value: _point.Point):
        """Replace the start point and refresh callbacks.

        :param value: New start point.
        :type value: :class:`harness_designer.geometry.point.Point`
        :returns: ``None``
        :rtype: None
        """
        self._p1.unbind(self._update_artist)
        value.bind(self._update_artist)
        self._p1 = value

        self._pixmap = None
        self._update_artist()

    @property
    def p2(self) -> _point.Point:
        """Return the end point.

        :returns: Current line end point.
        :rtype: :class:`harness_designer.geometry.point.Point`
        """
        return self._p2

    @p2.setter
    def p2(self, value: _point.Point):
        """Replace the end point and refresh callbacks.

        :param value: New end point.
        :type value: :class:`harness_designer.geometry.point.Point`
        :returns: ``None``
        :rtype: None
        """
        self._p2.unbind(self._update_artist)
        value.bind(self._update_artist)
        self._p2 = value

        self._pixmap = None
        self._update_artist()

    @staticmethod
    def _make_qcolor(c: _color.Color) -> QColor:
        """Convert an internal color value into :class:`QColor`.

        :param c: RGBA color tuple-like value.
        :type c: :class:`harness_designer.color.Color`
        :returns: Qt color instance for painting.
        :rtype: :class:`~PySide6.QtGui.QColor`
        """
        r, g, b, a = c
        return QColor(int(r * 255), int(g * 255), int(b * 255), int(a * 255))

    def _get_pixmap(self):
        """Build or return the cached pixmap for the line.

        The pixmap includes the base line and any stripe markings.

        :returns: Cached pixmap for the current line state.
        :rtype: :class:`~PySide6.QtGui.QPixmap`
        """
        if self._pixmap is None:
            p2 = self._p2 - self._p1
            p2 = p2.as_int[:-1]

            width = p2[0] + 11
            height = p2[1] + 11
            p2[0] += 5
            p2[1] += 5
            p1 = [5, 5]

            pixmap = QPixmap(int(width), int(height))
            pixmap.fill(Qt.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(Qt.NoBrush))

            line = _line.Line(self._p1, self._p2)
            line_angle = line.get_z_angle()

            stripe_line = _line.Line(
                _point.Point(_decimal(68), _decimal(0), _decimal(0)),
                _point.Point(_decimal(68 - 32), _decimal(24), _decimal(0))
            )

            stripe_angle = line_angle + stripe_line.get_z_angle()
            line_len = line.length()
            step = 25

            wire_size = self._width

            pen = QPen(self._make_qcolor(self._color), float(self._width))
            pen.setCapStyle(Qt.FlatCap)
            painter.setPen(pen)

            p1f = line.p1.as_float[:-1]
            p2f = line.p2.as_float[:-1]
            painter.drawLine(int(p1f[0]), int(p1f[1]), int(p2f[0]), int(p2f[1]))

            if self._stripe_color is not None:
                curr_dist = 3

                stripe_pen = QPen(self._make_qcolor(self._stripe_color), 3)
                stripe_pen.setCapStyle(Qt.FlatCap)
                painter.setPen(stripe_pen)

                while curr_dist < line_len - step - 10:
                    curr_dist += step

                    p = line.point_from_start(curr_dist)
                    s1 = _line.Line(p, None, max(wire_size - 2, 1), _decimal(0.0),
                                    _decimal(0.0), stripe_angle)
                    s2 = _line.Line(p, None, max(wire_size - 2, 1), _decimal(0.0),
                                    _decimal(0.0), stripe_angle + _decimal(180.0))

                    s1f = s1.p2.as_float[:-1]
                    s2f = s2.p2.as_float[:-1]
                    painter.drawLine(int(s1f[0]), int(s1f[1]),
                                     int(s2f[0]), int(s2f[1]))

            painter.end()

            self._pixmap = pixmap

        return self._pixmap

    @property
    def is_added(self):
        """Return whether the line currently has an attached artist.

        :returns: ``True`` when the line has been added to a plot.
        :rtype: bool
        """
        return self.artist is not None

    def _update_artist(self, p: _point.Point | None = None):
        """Refresh the backing artist if one exists.

        :param p: Updated point supplied by a bound point callback, if any.
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

    def add_to_plot(self, axes: "Editor2D") -> None:
        """Add the line to an editor plot.

        :param axes: Editor surface that can create an artist for this line.
        :type axes: :class:`Editor2D`
        :returns: ``None``
        :rtype: None
        """
        self.artist = axes.add_line(self)
        self._update_artist()


