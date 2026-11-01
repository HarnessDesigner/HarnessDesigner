# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Prints a :class:`~harness_designer.pegboard_print.layout.PrintLayout`.

One sheet per tile: the tile is rendered at ``dpi`` (see :mod:`.renderer`),
placed so that one world millimetre is ``layout.scale`` millimetres of paper,
and the alignment marks (see :mod:`.marks`) are drawn over it.
"""

import math
from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6 import QtCore, QtGui, QtPrintSupport

from . import layout as _layout
from . import marks as _marks
from . import renderer as _renderer

if TYPE_CHECKING:
    from ..gl.canvas_pegboard import canvas as _canvas


MM_PER_INCH = 25.4


def page_geometry(printer: QtPrintSupport.QPrinter, margin: float,
                  overlap: float) -> _layout.PageGeometry:
    """The sheet the printer is currently set up for.

    :param printer: Printer whose paper size and orientation are used.
    :param margin: Blank border, mm.
    :param overlap: Overlap between neighbouring pages, mm.
    :returns: The geometry, orientation applied.
    """
    paper = printer.pageLayout().fullRect(QtGui.QPageLayout.Unit.Millimeter)

    return _layout.PageGeometry(paper.width(), paper.height(), margin, overlap)


def minimum_margin(printer: QtPrintSupport.QPrinter) -> float:
    """The largest border (mm) the printer cannot print inside."""
    margins = printer.pageLayout().minimumMargins()

    return max(margins.left(), margins.top(), margins.right(), margins.bottom())


def print_layout(canvas: "_canvas.Canvas", printer: QtPrintSupport.QPrinter,
                 layout: _layout.PrintLayout, dpi: int,
                 progress: Callable[[int, int], bool] | None = None) -> bool:
    """Print every page of *layout*.

    :param canvas: The peg board's canvas.
    :param printer: Printer or PDF writer to print on; its paper must be the
        one *layout* was built for.
    :param layout: What to print.
    :param dpi: Resolution the peg board is rendered at.
    :param progress: Called with ``(pages done, pages in all)`` before each
        page; return ``False`` to cancel.
    :returns: ``True`` if every page was printed, ``False`` if cancelled.
    """
    geo = layout.geometry

    # With a full page the origin is the paper's corner, so the margins are
    # ours to place rather than the driver's.
    printer.setFullPage(True)

    painter = QtGui.QPainter()
    if not painter.begin(printer):
        raise RuntimeError('The printer could not be opened.')

    px_per_mm = printer.resolution() / MM_PER_INCH
    mm_per_pixel = MM_PER_INCH / (dpi * layout.scale)
    width_px = math.ceil(geo.area_width * dpi / MM_PER_INCH)
    height_px = math.ceil(geo.area_height * dpi / MM_PER_INCH)

    # Where the picture goes on the paper: the pixels are a hair larger than
    # the area (they are whole), so the overhang is clipped, not squeezed.
    area = QtCore.QRectF(geo.margin * px_per_mm, geo.margin * px_per_mm,
                         geo.area_width * px_per_mm, geo.area_height * px_per_mm)
    target = QtCore.QRectF(area.topLeft(), QtCore.QSizeF(
        width_px / dpi * MM_PER_INCH * px_per_mm, height_px / dpi * MM_PER_INCH * px_per_mm))

    finished = False
    try:
        # The tables are captured finer for the whole job, not once per page.
        with _renderer.sharp_tables(canvas, dpi, layout.scale):
            for index, tile in enumerate(layout.tiles):
                if progress is not None and not progress(index, layout.page_count):
                    printer.abort()
                    return False

                image = _renderer.render_tile(
                    canvas, tile.x0, tile.z0, width_px, height_px, mm_per_pixel)

                if index:
                    printer.newPage()

                painter.save()
                painter.setClipRect(area)
                painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
                painter.drawImage(target, image)
                painter.restore()

                _marks.draw_page_marks(painter, layout, tile, px_per_mm)

        finished = True

    finally:
        painter.end()

    if progress is not None:
        progress(layout.page_count, layout.page_count)

    return finished
