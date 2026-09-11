# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Pure cavity-slot stacking math for a housing's schematic (2D) view.

:func:`compute_housing_cavity_geometry` is the single entry point --
``database/project_db/pjt_housing.py``'s ``PJTHousingsTable.insert``
(fresh cavity rows, names already known) and ``PJTHousing.
cavity_geometry`` (an existing housing loaded from a project) both just
hand it their own cavity names and get back one :class:`CavityGeometry`
per cavity, so the two can never independently drift apart the way they
did before this module existed: the insert-time copy once had its
local X/Z axes swapped relative to the live schematic layout's own
convention, a different (wrong) pin-edge constant, and a missing "+1"
padding term.

Convention (matches ``objects_schematic/housing.py``'s ``Housing`` --
local X = text/width axis, local Z = cavity/height axis; this housing's
own local frame is centered on (0, 0, 0), UP is the POSITIVE-Z
direction (the schematic editor's own camera renders Z+ up, Z- down)
-- cavity slots stack top-to-bottom in ascending natural-sort-by-name
order, the first name at the most-positive Z): a cavity's own anchor is
its own slot's horizontal CENTER (not the pin edge itself -- the
cavity band spans from the housing's own physical left edge,
``-housing_width / 2``, inward by ``cavity_width``, so the center sits
at ``-cavity_width / 2``). The rendered housing rectangle is exactly
``housing_width`` wide, flush with the pin edge on the left.
"""

from typing import NamedTuple

import build123d
import numpy as np

from ..shapes import text as _text
from .. import config as _config
from .. import utils as _utils


Config = _config.Config


class CavityStackGeometry(NamedTuple):
    cavity_height: float
    cavity_width: float
    cavity_extent: float
    housing_width: float
    font_height: float
    text_padding: float


def compute_stack_geometry(num_cavities: int) -> CavityStackGeometry:
    """Derive a housing's font-size-driven per-cavity slot height and
    its cavity-axis/text-axis extents. Used on its own by
    ``objects_schematic/housing.py``'s ``Housing._recompute`` for this
    housing's own rectangle size -- unlike per-cavity geometry (see
    :func:`compute_housing_cavity_geometry`), that doesn't depend on
    any cavity's own name.

    :param num_cavities: How many cavity slots this housing stacks.
    """
    housing_width = Config.editor_schematic.object_sizes.housing.width

    terminal_font_height = (
        _text.CHARACTER_HEIGHT * Config.editor_schematic.object_sizes.terminal.name_font_size)

    padding = terminal_font_height * 0.2
    cavity_height = terminal_font_height + (padding * 3.0)
    cavity_width = housing_width / 2.0

    # +1 accounts for padding applying to both ends of the vertical
    # cavity stack, not just between adjacent cavities.
    cavity_extent = cavity_height * (num_cavities + 1)

    return CavityStackGeometry(cavity_height, cavity_width, cavity_extent, housing_width, terminal_font_height, padding)


def _box_corners(center_x: float, center_z: float, width: float, height: float) -> np.ndarray:
    """4 local corners of a ``width`` x ``height`` box centered on
    ``(center_x, center_z)`` -- ``(min_x,min_z), (min_x,max_z),
    (max_x,min_z), (max_x,max_z)``, the same corner order/shape every
    ``_compute_obb``/``_compute_aabb`` override in this codebase already
    expects (rotate by ``@ angle``, translate by ``+ position``).
    """
    half_w = width / 2.0
    half_h = height / 2.0

    return np.array([
        [center_x - half_w, 0.0, center_z - half_h],
        [center_x - half_w, 0.0, center_z + half_h],
        [center_x + half_w, 0.0, center_z - half_h],
        [center_x + half_w, 0.0, center_z + half_h],
    ], dtype=np.float32)


class CavityGeometry(NamedTuple):
    name: str
    text: _text.Text
    original_index: int
    position: tuple[float, float]
    name_position: tuple[float, float]
    obb: np.ndarray
    terminal_obb: np.ndarray
    bracket_position: tuple[float, float]
    bracket_font_size: float
    cylinder_start: tuple[float, float]
    cylinder_stop: tuple[float, float]
    cavity_height: float
    cavity_width: float
    term_text_height: float
    term_text_width: float
    text_padding: float


def compute_housing_cavity_geometry(cavity_names: list[str]) -> list[CavityGeometry]:
    """Compute every cavity's own complete schematic geometry for a
    housing with these *cavity_names*, in ANY order -- natural-sort
    ordering (which determines each cavity's own vertical STACK
    position, top to bottom) is handled entirely here, so callers never
    pre-sort. Each returned :class:`CavityGeometry` carries its own
    ``name`` and ``original_index`` (this cavity's own position in
    *cavity_names*, NOT its sorted stack position) back, and the
    returned list is itself in that same original order (``result[i]``
    is ``cavity_names[i]``'s own geometry) -- a caller with its own
    parallel list of cavity rows/ids in that same order can zip the two
    directly, no re-sorting or re-matching needed.

    Everything here is knowable the moment a cavity's own row exists --
    even before any terminal is ever seated in it -- EXCEPT a seated
    terminal's own NAME text (its shrink-to-fit font size depends on
    the actual terminal part's own name string, which doesn't exist
    until one is actually seated) -- see
    ``objects_schematic/terminal.py``'s own ``Terminal._rebuild_geometry``,
    which still computes that part live. Everything else -- a cavity's
    own name position/hit-box, a terminal's own hit-box, and a seated
    terminal's own "(" bracket position/font size and wire-stub cylinder
    endpoints -- is reserved/computed here regardless of whether a
    terminal is actually seated, so ``database/project_db/
    pjt_housing.py``'s ``PJTHousingsTable.insert``/``PJTHousing.
    cavity_geometry`` can cache all of it up front, one batched pass per
    housing.

    Everything returned is housing-local and unrotated -- callers
    rotate by the housing's own current ``angle2d``/translate by its
    own ``position2d`` to get world-space values (see
    ``database/project_db/pjt_housing.py``'s ``PJTHousingsTable.insert``
    for a cavity's own initial world ``position2d``, and
    ``objects_schematic/terminal.py``'s ``Terminal.__init__`` for a
    seated terminal's own).

    Per-:class:`CavityGeometry` field meanings:

    - ``position``: this cavity's own anchor -- its slot's CENTER (both
      axes), persisted as ``PJTCavity.position2d``.
    - ``name_position``: this cavity's own NAME label's render anchor
      -- the CENTER of its own text block. Cavity names render entirely
      OUTSIDE the housing, on the pin-edge side, positioned so the
      label's own right edge lands just in front of where a seated
      terminal's own "(" bracket renders (``bracket_position``) --
      reserved whether or not a terminal is actually seated, so a
      cavity's own name never shifts when one is added/removed.
    - ``obb``: 4 local corners of this cavity's own hit-test region --
      its NAME label's own bounds, NOT the cavity band itself -- a
      cavity is clicked via its rendered name, not the (invisible) slot
      area.
    - ``terminal_obb``: 4 local corners of a seated terminal's own
      hit-test region -- the text area inside the cavity rectangle
      (``cavity_width - text_padding*2`` by ``font_height``), centered
      on ``position`` (INSIDE the cavity rectangle, unlike ``obb``) --
      independent of any specific terminal's own rendered name/bracket/
      wire-stub extents (those still come from
      ``Terminal._rebuild_geometry``; only this hit box is fixed).
    - ``bracket_position``: a seated terminal's own "(" bracket render
      anchor (bottom-left corner) -- independently
      ``pin_edge - pin_edge_padding``, landing at the same X as
      ``name_position``'s own right edge only because both use that
      same formula, not because they're aligned to each other.
    - ``bracket_font_size``: the font size a seated terminal's own real
      "(" ``Text`` VBO must be built at to exactly match this
      precomputed geometry (``Terminal._rebuild_geometry`` still builds
      that VBO itself -- rendering needs a real glyph mesh -- just no
      longer needs to re-derive its own font size).
    - ``cylinder_start``/``cylinder_stop``: the wire-stub cylinder's own
      endpoints -- start at the "(" bracket's own vertical center, its
      own left edge; stop the housing-wide widest cavity name's own
      width further left than the bracket's own right edge, so every
      terminal's own stub in this housing is the same length.
    """
    n = len(cavity_names)
    stack_geometry = compute_stack_geometry(n)

    cavity_font_size = Config.editor_schematic.object_sizes.cavity.name_font_size
    pin_edge_padding = stack_geometry.text_padding

    # Reserved space for a terminal's own "(" bracket, present or not --
    # the "(" fills whatever vertical space a cavity's own (unshrunk)
    # name text doesn't use within one slot. Same formula
    # objects_schematic/terminal.py's own Terminal._rebuild_geometry
    # used to derive its real bracket's own font size before this
    # module took over computing it -- must stay in sync.
    cavity_char_height = _text.CHARACTER_HEIGHT * cavity_font_size
    remaining_height = abs(stack_geometry.cavity_height - cavity_char_height)
    bracket_font_size = remaining_height / _text.CHARACTER_HEIGHT * 1.30
    par = _text.Text(
        '(', bracket_font_size, build123d.FontStyle.REGULAR,
        local_tilt=_text.TOP_DOWN_TILT)

    par_width = par.width
    par_height = par.height

    pin_local_x = -(stack_geometry.housing_width / 2.0)
    bracket_right_x = pin_local_x - pin_edge_padding
    bracket_left_x = bracket_right_x - par_width

    cavity_x = -(stack_geometry.cavity_width / 2.0)
    term_width = stack_geometry.cavity_width - (stack_geometry.text_padding * 2.0)
    term_height = stack_geometry.cavity_height - (stack_geometry.text_padding * 2.0)

    # Measure every cavity's own name label once, in ORIGINAL order, so
    # results[i] below lines up with cavity_names[i] directly.
    # center_anchor=True -- local (0, 0, 0) is this block's own CENTER,
    # matching name_position/name_center_x/name_center_z below (the
    # CENTER of the text block, not its bottom-left-of-widest-line
    # corner) -- objects_schematic/cavity.py's Cavity has no render()
    # override, so this Text's own local origin IS what self._position
    # (== name_position, rotated/translated to world) renders at
    # directly; without center_anchor here, that position would land at
    # the wrong corner of the glyph mesh instead of its center, same
    # reasoning as objects_schematic/terminal.py's own name Text.
    measured = [
        _text.Text(name, cavity_font_size, build123d.FontStyle.REGULAR,
                   local_tilt=_text.TOP_DOWN_TILT, center_anchor=True)
        for name in cavity_names
    ]
    max_cavity_name_width = max((t.width for t in measured), default=0.0)

    # Natural-sort by name to determine each cavity's own vertical
    # STACK position -- ordering handled entirely here (see the
    # docstring above) rather than requiring every caller to pre-sort.
    stack_order = sorted(range(n), key=lambda i: _utils.natural_sort_key(cavity_names[i]))

    half_cavity_extent = stack_geometry.cavity_extent / 2.0

    results: list[CavityGeometry | None] = [None] * n

    cavity_z = half_cavity_extent

    for stack_index, original_index in enumerate(stack_order):
        name = cavity_names[original_index]
        text = measured[original_index]
        name_width = measured[original_index].width
        name_height = measured[original_index].height

        cavity_z -= stack_geometry.cavity_height

        slot_top = cavity_z + (stack_geometry.cavity_height / 2.0)

        name_center_x = bracket_left_x - pin_edge_padding - (name_width / 2.0)

        # The name's own center sits half its own height BELOW the
        # slot's own top edge, so its own top edge lands exactly on it.
        name_center_z = slot_top - (name_height / 2.0)

        name_obb = _box_corners(name_center_x, name_center_z, name_width, name_height)
        terminal_obb = _box_corners(cavity_x, cavity_z, term_width, term_height)

        # Starts exactly at the cavity name's own baseline (rendered
        # below it, i.e. further DOWN -- more negative Z, Z+ is up),
        # extends down by its own full height.
        bracket_bottom_z = cavity_z - (stack_geometry.cavity_height / 2.0) + stack_geometry.text_padding
        bracket_z = bracket_bottom_z + (par_height / 2.0)
        bracket_position = (bracket_left_x + (par_width / 4.0), bracket_z)

        cylinder_start = (bracket_left_x,
                          bracket_z - (stack_geometry.text_padding * 1.5))

        cylinder_stop = (name_center_x - (max_cavity_name_width * 2.0),
                         bracket_z - (stack_geometry.text_padding * 1.5))

        results[original_index] = CavityGeometry(
            name, text, original_index, (cavity_x, cavity_z), (name_center_x, name_center_z),
            name_obb, terminal_obb, bracket_position, bracket_font_size,
            cylinder_start, cylinder_stop, stack_geometry.cavity_height,
            stack_geometry.cavity_width, term_height, term_width,
            stack_geometry.text_padding)

    return results
