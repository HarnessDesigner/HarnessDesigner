# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Page-grid maths for printing the peg board at a chosen scale.

Pure Python (no Qt, no GL) so it can be checked on its own. Everything is in
millimetres: *world* millimetres on the peg board, *paper* millimetres on the
sheet. ``scale`` converts between them (``paper = world * scale``), so a scale
of 1.0 prints one world millimetre as one millimetre of paper.

World X runs to the right of the page and world Z runs DOWN the page, which is
how the peg board canvas draws (see ``gl/canvas_pegboard/camera.py``).
"""

import math
from dataclasses import dataclass


# Float noise must not push an exactly-fitting job onto an extra page.
_EPSILON = 1e-6


@dataclass(frozen=True)
class PageGeometry:
    """One sheet of paper, after orientation has been applied.

    :param paper_width: Sheet width, mm.
    :param paper_height: Sheet height, mm.
    :param margin: Blank border on all four sides, mm. Must be at least what
        the printer cannot reach.
    :param overlap: How far neighbouring pages overlap, mm. The alignment
        marks live in this strip.
    """

    paper_width: float
    paper_height: float
    margin: float
    overlap: float

    def __post_init__(self):
        if self.margin < 0.0 or self.overlap < 0.0:
            raise ValueError('The margin and overlap cannot be negative.')

        if self.area_width <= 0.0 or self.area_height <= 0.0:
            raise ValueError('The margin leaves no room to print on this paper.')

        # The marks sit half an overlap in from each edge, so a pair of them
        # on the same axis needs at least one overlap between them.
        if self.overlap * 2.0 >= min(self.area_width, self.area_height):
            raise ValueError('The overlap is too large for this paper.')

    @property
    def area_width(self) -> float:
        """Printable width inside the margins, mm."""
        return self.paper_width - 2.0 * self.margin

    @property
    def area_height(self) -> float:
        """Printable height inside the margins, mm."""
        return self.paper_height - 2.0 * self.margin

    @property
    def step_x(self) -> float:
        """How far one page's left edge is from the next page's, mm."""
        return self.area_width - self.overlap

    @property
    def step_y(self) -> float:
        """How far one page's top edge is from the next page's, mm."""
        return self.area_height - self.overlap


@dataclass(frozen=True)
class Tile:
    """The part of the peg board one sheet prints.

    :param number: 1-based page number, left to right then top to bottom.
    :param col: 0-based column.
    :param row: 0-based row.
    :param x0: Left edge of the printable area, world mm.
    :param z0: Top edge, world mm.
    :param x1: Right edge, world mm.
    :param z1: Bottom edge, world mm.
    """

    number: int
    col: int
    row: int
    x0: float
    z0: float
    x1: float
    z1: float


@dataclass(frozen=True)
class PrintLayout:
    """The whole job: which tile goes on which sheet.

    :param geometry: The sheet.
    :param scale: Paper millimetres per world millimetre.
    :param bounds: ``(x0, z0, x1, z1)`` of the content, world mm.
    :param cols: Pages across.
    :param rows: Pages down.
    :param tiles: Every page, in print order.
    """

    geometry: PageGeometry
    scale: float
    bounds: tuple[float, float, float, float]
    cols: int
    rows: int
    tiles: tuple[Tile, ...]

    @property
    def page_count(self) -> int:
        """Number of sheets."""
        return len(self.tiles)

    @property
    def printed_size(self) -> tuple[float, float]:
        """Size of the finished, glued-up print (paper mm)."""
        x0, z0, x1, z1 = self.bounds
        return (x1 - x0) * self.scale, (z1 - z0) * self.scale

    def tile_at(self, col: int, row: int) -> Tile | None:
        """The tile in a column/row, or ``None`` when there is none."""
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return self.tiles[row * self.cols + col]

        return None


def _pages_needed(content: float, area: float, step: float) -> int:
    """Pages along one axis for *content* paper-mm of drawing."""
    if content <= area + _EPSILON:
        return 1

    return 1 + math.ceil((content - area) / step - _EPSILON)


def build_layout(bounds: tuple[float, float, float, float], scale: float,
                 geometry: PageGeometry) -> PrintLayout:
    """Split *bounds* into pages.

    The page grid is centred on the content, so the spare room at the end of
    the last row/column is shared between both ends.

    :param bounds: ``(x0, z0, x1, z1)`` of the content, world mm.
    :param scale: Paper mm per world mm; must be positive.
    :param geometry: The sheet.
    :returns: The layout.
    """
    if scale <= 0.0:
        raise ValueError('The scale must be greater than zero.')

    x0, z0, x1, z1 = bounds
    if x1 <= x0 or z1 <= z0:
        raise ValueError('There is nothing to print.')

    content_w = (x1 - x0) * scale
    content_h = (z1 - z0) * scale

    cols = _pages_needed(content_w, geometry.area_width, geometry.step_x)
    rows = _pages_needed(content_h, geometry.area_height, geometry.step_y)

    covered_w = geometry.area_width + (cols - 1) * geometry.step_x
    covered_h = geometry.area_height + (rows - 1) * geometry.step_y

    # Paper mm -> world mm; the grid's top-left corner so the content is centred.
    start_x = x0 - (covered_w - content_w) / 2.0 / scale
    start_z = z0 - (covered_h - content_h) / 2.0 / scale

    area_w = geometry.area_width / scale
    area_h = geometry.area_height / scale
    step_x = geometry.step_x / scale
    step_y = geometry.step_y / scale

    tiles = []
    for row in range(rows):
        for col in range(cols):
            left = start_x + col * step_x
            top = start_z + row * step_y

            tiles.append(Tile(
                row * cols + col + 1, col, row, left, top, left + area_w, top + area_h))

    return PrintLayout(geometry, scale, (x0, z0, x1, z1), cols, rows, tuple(tiles))


def fit_scale(bounds: tuple[float, float, float, float], cols: int, rows: int,
              geometry: PageGeometry) -> float:
    """The largest scale at which the content fits in *cols* x *rows* pages.

    :param bounds: ``(x0, z0, x1, z1)`` of the content, world mm.
    :param cols: Pages across, at least 1.
    :param rows: Pages down, at least 1.
    :param geometry: The sheet.
    :returns: Paper mm per world mm.
    """
    x0, z0, x1, z1 = bounds
    if x1 <= x0 or z1 <= z0:
        raise ValueError('There is nothing to print.')

    cols = max(1, cols)
    rows = max(1, rows)

    covered_w = geometry.area_width + (cols - 1) * geometry.step_x
    covered_h = geometry.area_height + (rows - 1) * geometry.step_y

    return min(covered_w / (x1 - x0), covered_h / (z1 - z0))
