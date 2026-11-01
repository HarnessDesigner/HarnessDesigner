# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
The alignment marks, page labels and scale bar printed on every sheet.

Neighbouring pages overlap by ``geometry.overlap``. Each mark sits half an
overlap in from the edge of the printable area, which puts the right-hand mark
of one page on exactly the same peg board point as the left-hand mark of the
page next to it (and likewise top/bottom). To glue up, lay the sheets so the
crosshairs of neighbours sit on top of each other.
"""

from PySide6 import QtCore, QtGui

from . import layout as _layout


_ARM_MM = 4.0
_RING_MM = 1.1
_LINE_MM = 0.25
_HALO_MM = 0.9
_LABEL_POINTS = 6.0

# Lengths (world mm) the scale bar can be, longest first.
_BAR_LENGTHS = (2000, 1000, 500, 200, 100, 50, 20, 10, 5, 2, 1)


def _page_name(col: int, row: int) -> str:
    """The short name pages use to refer to each other."""
    return f'R{row + 1}C{col + 1}'


def _draw_crosshair(painter: QtGui.QPainter, x: float, y: float, px_per_mm: float) -> None:
    """A crosshair with a ring, over a white halo so it shows on dark parts."""
    arm = _ARM_MM * px_per_mm
    ring = _RING_MM * px_per_mm

    for width_mm, colour in ((_HALO_MM, QtGui.QColor(255, 255, 255)),
                             (_LINE_MM, QtGui.QColor(0, 0, 0))):
        pen = QtGui.QPen(colour)
        pen.setWidthF(width_mm * px_per_mm)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.FlatCap)

        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawLine(QtCore.QPointF(x - arm, y), QtCore.QPointF(x + arm, y))
        painter.drawLine(QtCore.QPointF(x, y - arm), QtCore.QPointF(x, y + arm))
        painter.drawEllipse(QtCore.QPointF(x, y), ring, ring)


def _draw_label(painter: QtGui.QPainter, text: str, centre: QtCore.QPointF,
                px_per_mm: float) -> None:
    """Small text on a white box, centred on *centre*."""
    font = QtGui.QFont(painter.font())
    font.setPointSizeF(_LABEL_POINTS)
    painter.setFont(font)

    metrics = QtGui.QFontMetricsF(font, painter.device())
    pad = 0.6 * px_per_mm
    rect = QtCore.QRectF(0.0, 0.0, metrics.horizontalAdvance(text) + 2.0 * pad,
                         metrics.height() + pad)
    rect.moveCenter(centre)

    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    painter.setBrush(QtGui.QColor(255, 255, 255, 215))
    painter.drawRoundedRect(rect, pad, pad)

    painter.setPen(QtGui.QColor(0, 0, 0))
    painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, text)


def _bar_length(layout: _layout.PrintLayout) -> int:
    """The longest round world length whose printed bar is a third of a page wide."""
    limit = layout.geometry.area_width / 3.0

    for length in _BAR_LENGTHS:
        if length * layout.scale <= limit:
            return length

    return _BAR_LENGTHS[-1]


def _draw_scale_bar(painter: QtGui.QPainter, layout: _layout.PrintLayout,
                    centre_x: float, y: float, px_per_mm: float) -> None:
    """A bar whose printed length is a known number of world millimetres.

    Measure it with a ruler: if it is not that long the printer scaled the
    page ("fit to page" and similar must be off).
    """
    length = _bar_length(layout)
    width = length * layout.scale * px_per_mm
    tick = 1.2 * px_per_mm
    left = centre_x - width / 2.0

    pen = QtGui.QPen(QtGui.QColor(0, 0, 0))
    pen.setWidthF(0.3 * px_per_mm)
    pen.setCapStyle(QtCore.Qt.PenCapStyle.FlatCap)
    painter.setPen(pen)

    painter.drawLine(QtCore.QPointF(left, y), QtCore.QPointF(left + width, y))
    painter.drawLine(QtCore.QPointF(left, y - tick), QtCore.QPointF(left, y + tick))
    painter.drawLine(QtCore.QPointF(left + width, y - tick), QtCore.QPointF(left + width, y + tick))

    _draw_label(painter, f'{length} mm', QtCore.QPointF(centre_x, y - 2.6 * px_per_mm), px_per_mm)


def draw_page_marks(painter: QtGui.QPainter, layout: _layout.PrintLayout,
                    tile: _layout.Tile, px_per_mm: float) -> None:
    """Draw everything that is not the peg board itself onto one sheet.

    :param painter: Painter open on the printer, in device pixels with the
        origin at the paper's top-left corner.
    :param layout: The whole job.
    :param tile: The page being drawn.
    :param px_per_mm: Device pixels per paper millimetre.
    """
    geo = layout.geometry
    painter.save()
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

    half = geo.overlap / 2.0
    left = (geo.margin + half) * px_per_mm
    right = (geo.margin + geo.area_width - half) * px_per_mm
    top = (geo.margin + half) * px_per_mm
    bottom = (geo.margin + geo.area_height - half) * px_per_mm
    mid_x = (geo.margin + geo.area_width / 2.0) * px_per_mm
    mid_y = (geo.margin + geo.area_height / 2.0) * px_per_mm

    has_left = tile.col > 0
    has_right = tile.col < layout.cols - 1
    has_up = tile.row > 0
    has_down = tile.row < layout.rows - 1

    # A mark is only worth printing where a neighbour will be glued to that
    # edge (or, for a corner, to either edge that meets there).
    points = []
    for x, side_x in ((left, has_left), (right, has_right)):
        for y, side_y in ((top, has_up), (bottom, has_down)):
            if side_x or side_y:
                points.append((x, y))

    if has_left:
        points.append((left, mid_y))
    if has_right:
        points.append((right, mid_y))
    if has_up:
        points.append((mid_x, top))
    if has_down:
        points.append((mid_x, bottom))

    for x, y in points:
        _draw_crosshair(painter, x, y, px_per_mm)

    # Which page sits beyond each edge, next to the edge's middle mark.
    gap = (_ARM_MM + 4.5) * px_per_mm
    for present, col, row, centre in (
            (has_left, tile.col - 1, tile.row, QtCore.QPointF(left + gap, mid_y)),
            (has_right, tile.col + 1, tile.row, QtCore.QPointF(right - gap, mid_y)),
            (has_up, tile.col, tile.row - 1, QtCore.QPointF(mid_x + gap, top)),
            (has_down, tile.col, tile.row + 1, QtCore.QPointF(mid_x + gap, bottom))):
        if present:
            _draw_label(painter, 'joins ' + _page_name(col, row), centre, px_per_mm)

    # Page id and scale to one side of the bottom-middle crosshair, the scale
    # bar to the other, in the strip along the bottom of the page.
    info_y = (geo.margin + geo.area_height - geo.overlap * 0.25) * px_per_mm
    percent = layout.scale * 100.0
    side = geo.area_width * px_per_mm

    _draw_label(
        painter,
        f'Page {tile.number}/{layout.page_count} {_page_name(tile.col, tile.row)}'
        f'  scale {percent:g}%',
        QtCore.QPointF(mid_x - 0.2 * side, info_y), px_per_mm)

    _draw_scale_bar(painter, layout, mid_x + 0.22 * side, info_y, px_per_mm)

    painter.restore()
