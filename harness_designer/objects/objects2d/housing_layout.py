# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Automatic housing placement for the 2D schematic editor.

Places one newly-added housing at a time into the first free (non-
overlapping) spot near the existing formation -- every previously placed
housing (whether auto-placed earlier or moved/rotated by hand since) is
left exactly where it is. There is no shared layout rectangle or "which
edge does this housing belong on" concept any more: a new housing simply
needs a spot where its own footprint doesn't overlap any other housing's
or any connected wire's.

Single entry point: :func:`place_housing`, called after a housing is
added (see ``handlers/housing_handler.py``). A no-op when
``Config.editor2d.layout.auto_layout_enabled`` is ``False``.
"""

from typing import TYPE_CHECKING

from ... import config as _config
from ... import check_types as _check_types

if TYPE_CHECKING:
    from .. import project as _project
    from .. import housing as _housing_obj


Config = _config.Config.editor2d


@_check_types.do
def _footprint(housing: "_housing_obj.Housing") -> tuple[float, float]:
    """This housing's own unrotated ``(width, height)`` footprint -- see
    ``objects2d/housing.py``'s ``Housing._recompute`` (``_text_extent``
    is the fixed cross-axis width, ``_cavity_extent`` is
    ``num_cavities * Config.editor2d.cavity.height``).
    """
    obj2d = housing.obj2d
    return obj2d._text_extent, obj2d._cavity_extent


@_check_types.do
def _occupied_rects(project: "_project.Project", housing: "_housing_obj.Housing"
                    ) -> list[tuple[float, float, float, float]]:
    """Every other housing's, and every connected wire's, world AABB
    (``(min_x, min_z, max_x, max_z)``) expanded by
    ``Config.editor2d.layout.housing_spacing`` on each side -- the set a
    newly placed housing's own footprint must not overlap.

    A wire that hasn't completed its connection at both ends isn't
    treated as an obstacle -- it isn't even shown in the schematic (see
    ``objects/wire.py``'s ``Wire.is_connected``), so there's nothing
    real there yet to avoid.
    """
    spacing = Config.layout.housing_spacing
    rects = []

    for other in project.housings:
        if other is housing:
            continue

        bounds = other.obj2d.get_bounds()
        if bounds is None:
            continue

        min_x, min_z, max_x, max_z = bounds
        rects.append((min_x - spacing, min_z - spacing, max_x + spacing, max_z + spacing))

    for wire in project.wires:
        if not wire.is_connected:
            continue

        bounds = wire.obj2d.get_bounds()
        if bounds is None:
            continue

        min_x, min_z, max_x, max_z = bounds
        rects.append((min_x - spacing, min_z - spacing, max_x + spacing, max_z + spacing))

    return rects


@_check_types.do
def _rects_overlap(a: tuple[float, float, float, float],
                   b: tuple[float, float, float, float]) -> bool:
    a_min_x, a_min_z, a_max_x, a_max_z = a
    b_min_x, b_min_z, b_max_x, b_max_z = b

    return not (a_max_x <= b_min_x or b_max_x <= a_min_x
                or a_max_z <= b_min_z or b_max_z <= a_min_z)


@_check_types.do
def _spiral_offsets(step: float):
    """Yield ``(x, z)`` grid offsets in an outward square spiral around
    the origin, each a multiple of *step* -- ``(0, 0)`` first, then
    1-right, 1-up, 2-left, 2-down, 3-right, 3-up, ... (the standard
    square-spiral walk), so nearer candidates are always tried before
    farther ones.
    """
    yield 0.0, 0.0

    x = z = 0.0
    dx, dz = step, 0.0
    seg_len = 1

    while True:
        for _ in range(2):
            for _ in range(seg_len):
                x += dx
                z += dz
                yield x, z

            dx, dz = -dz, dx

        seg_len += 1


# Hard cap on spiral candidates tried -- a pathological project could
# otherwise loop indefinitely; this is generous enough (hundreds of
# housings deep) that hitting it in practice would mean something else
# is wrong, not that a real spot doesn't exist further out.
_MAX_CANDIDATES = 4000


@_check_types.do
def _centroid(project: "_project.Project", housing: "_housing_obj.Housing"
             ) -> tuple[float, float]:
    others = [h for h in project.housings if h is not housing and h.obj2d.get_bounds() is not None]

    if not others:
        return 0.0, 0.0

    xs = []
    zs = []
    for other in others:
        min_x, min_z, max_x, max_z = other.obj2d.get_bounds()
        xs.append((min_x + max_x) / 2.0)
        zs.append((min_z + max_z) / 2.0)

    return sum(xs) / len(xs), sum(zs) / len(zs)


@_check_types.do
def place_housing(project: "_project.Project", housing: "_housing_obj.Housing"
                  ) -> None:
    """Place *housing* (just added to *project*) at the nearest spot,
    near the existing formation's centroid, whose footprint doesn't
    overlap any other housing's or any connected wire's -- always
    unrotated (``angle2d.y == 0``; the user can rotate it afterward via
    the schematic editor's own Rotate menu). No-op if
    ``Config.editor2d.layout.auto_layout_enabled`` is ``False``.
    """
    if not Config.layout.auto_layout_enabled:
        return

    width, height = _footprint(housing)
    half_w, half_h = width / 2.0, height / 2.0

    occupied = _occupied_rects(project, housing)

    if not occupied:
        _apply_placement(housing, 0.0, 0.0)
        return

    step = Config.layout.housing_spacing + max(width, height)
    cx, cz = _centroid(project, housing)

    for i, (ox, oz) in enumerate(_spiral_offsets(step)):
        if i >= _MAX_CANDIDATES:
            # Give up looking for a gap and place it clear of everything
            # tried so far rather than loop forever.
            _apply_placement(housing, cx + ox, cz + oz)
            return

        x, z = cx + ox, cz + oz
        candidate = (x - half_w, z - half_h, x + half_w, z + half_h)

        if not any(_rects_overlap(candidate, rect) for rect in occupied):
            _apply_placement(housing, x, z)
            return


@_check_types.do
def _apply_placement(housing: "_housing_obj.Housing", x: float, z: float) -> None:
    """Write *x*/*z* to ``position2d`` (angle left untouched -- a newly
    auto-placed housing always keeps whatever ``angle2d.y`` it already
    has, which is identity for a brand new housing) -- the same bound-
    callback write path ``Housing2D.move_to`` already uses, so this
    persists immediately and refreshes the canvas.
    """
    position = housing.db_obj.position2d
    with position:
        position.x = x
        position.z = z
