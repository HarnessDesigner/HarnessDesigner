# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math
import re

import numpy as np
import build123d
from PySide6.QtWidgets import QMenu

from . import base_schematic as _base_schematic
from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl.canvas_base import interaction as _interaction
from ... import config as _config
from ... import color as _color
from ...gl import materials as _materials
from ...shapes import rectangle as _rectangle
from ...shapes import text as _text
from ... import utils as _utils
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_housing as _pjt_housing
    from .. import housing as _housing
    from ... import ui as _ui


Config = _config.Config.editor_schematic

# shapes.text.Text has no multi-line support of its own (its glyph
# cache has no '\n' entry) and build123d's own multi-line layout
# metrics aren't available here to match exactly -- the corner label's
# 3 lines (name/part number/manufacturer) are built as separate Text
# instances and stacked manually (see Housing._build_corner_label/
# render) using this as an approximate line-height multiple of
# the font size. Retune if the stacking looks off once rendered.
_CORNER_LABEL_LINE_HEIGHT_SCALE = 1.2

_DIGIT_RUN = re.compile(r'(\d+)')


def _natural_sort_key(name: str) -> tuple:
    """Split *name* into alternating text/number chunks (numeric chunks
    compared as ints) so ``"2"`` sorts before ``"10"`` -- a plain string
    sort relies on cavity names being zero-padded to read in order,
    which real project data isn't guaranteed to be.

    Each chunk tagged ``(0, int)`` for a digit run or ``(1, str)`` for
    text -- comparing two chunks always compares the leading kind tag
    (int vs int) first, so same-position chunks of different kinds
    decide right there and never fall through to comparing an int
    against a str (a TypeError in Python 3).
    """
    return tuple(
        (0, int(chunk)) if chunk.isdigit() else (1, chunk.lower())
        for chunk in _DIGIT_RUN.split(name) if chunk)


def _sort_cavities(cavities: list) -> list:
    """Natural-sort *cavities* -- a list of ``(name, PJTCavity)`` pairs
    -- by their own ``name``. Returns the same shape, sorted.
    """
    return sorted(cavities, key=lambda c: _natural_sort_key(c[0]))


class Housing(_base_schematic.BaseSchematic):
    """
    2D representation of a housing for schematic view

    Renders ONLY the housing rectangle (unit primitive from
    ``shapes.rectangle``, scaled) plus its own corner label (name/part
    number/manufacturer), via the schematic2d shader/VBO pipeline (see
    ``objects_schematic/base_schematic.py``'s ``BaseSchematic``) -- matches
    how ``Base3D`` subclasses render, no immediate-mode fallback. Every
    cavity's own name, and (for a cavity with a seated terminal) the "("
    bracket and the terminal's own name, are rendered independently by
    ``objects_schematic/cavity.py``'s ``Cavity``/``objects_schematic/terminal.py``'s
    ``Terminal`` -- each a real, individually selectable ``BaseSchematic``
    object with its own OBB/AABB. This class only computes *where* those
    live (see :meth:`get_cavity_aabb`/:meth:`_layout_children`) and
    persists it to their own ``position2d``, whenever the sorted cavity
    order or seated-terminal set changes -- Cavity/Terminal pick the new
    values up automatically through the same bound-Point callback every
    other ``BaseVar`` position update already uses.

    Sizing is font-size-driven rather than a fixed constant: this
    housing's own per-cavity slot height (:attr:`cavity_height`) is
    derived from ``shapes.text.CHARACTER_HEIGHT`` (the tallest glyph in
    the font, at font_size=1.0 -- see :func:`shapes.text.build_chars`)
    times ``Config.object_sizes.terminal.name_font_size`` (a terminal's
    own MAXIMUM font size, not a constant -- an individual terminal may
    render smaller to fit its own name inside this slot), plus 10%
    padding on top and bottom. Computed once per housing, in
    :meth:`__init__`/:meth:`_recompute`, so cavities/terminals can read
    it back via :meth:`get_cavity_aabb` without recomputing.
    """
    _parent: "_housing.Housing" = None
    db_obj: "_pjt_housing.PJTHousing"

    @_check_types.do
    def __init__(self, parent: "_housing.Housing",
                 db_obj: "_pjt_housing.PJTHousing"):
        """Initialise the :class:`Housing` instance.

        :param parent: Parent object.
        :type parent: :class:`_housing.Housing`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_housing.PJTHousing`
        """

        self._part = db_obj.part

        # Nothing built yet -- _recompute()'s first call, below, needs
        # these to already exist.
        self._db_callbacks = []
        self._corner_label_lines = []

        position = db_obj.position2d
        angle = db_obj.angle2d

        # TODO: Lock a hsouing to only be able to be rotated in 90° increments.
        #       this also means the same thing would apply to terminals and also
        #       to cavities.

        material = _materials.Generic(_color.Color(*Config.colors.housing))

        # Every GL call below (the rectangle's own VBO, the corner-label
        # text VBO _recompute() builds, and BaseSchematic.__init__'s own
        # vbo.acquire()) needs a current context -- acquired once here and
        # held for all of it.
        with parent.mainframe.editor2d.editor.context:
            vbo = _rectangle.create_vbo()

            # self._position/._angle don't exist until BaseSchematic.__init__ (below)
            # runs, so _recompute takes this housing's own position/angle
            # explicitly rather than reading self -- see _layout_children.
            cavity_extent, text_extent = self._recompute(db_obj, position, angle)

            scale = _point.Point(text_extent, 1.0, cavity_extent)

            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

    @property
    @_check_types.do
    def smooth(self) -> bool:
        return False

    @smooth.setter
    def smooth(self, value: bool | None):
        pass

    @_check_types.do
    def _recompute(self, db_obj, position: _point.Point, angle: _angle.Angle
                   ) -> tuple[float, float]:
        """(Re)compute this housing's font-driven cavity slot height and
        cavity-axis extent, rebuild the corner label, push every
        cavity's/seated terminal's own world position2d (see
        :meth:`_layout_children`), and (re)bind the DB callbacks that
        trigger the next recompute (a cavity's name changes -- reordering
        its slot -- or a cavity gains/loses its terminal). Shared by
        ``__init__`` (the first build) and :meth:`_rebuild` (every one
        after). Requires a current GL context.

        :param position: This housing's own ``position2d`` -- taken as a
            parameter rather than read from ``self._position`` since
            ``__init__`` calls this before ``BaseSchematic.__init__`` has set
            that attribute yet.
        :param angle: This housing's own ``angle2d``, same reason.
        :returns: ``(cavity_extent, text_extent)``, for
            ``__init__``/:meth:`_rebuild`'s scale-setting code.
        """
        self._release_corner_label()
        self._unbind_callbacks()

        # Sorted by the cavity's own *name* -- the user-facing identifier
        # (can be numeric, alphabetic, or mixed; that's exactly why the
        # name field exists rather than relying on the catalog cavity's
        # idx, which is purely internal bookkeeping and never shown) --
        # natural-sorted so e.g. "2" sorts before "10".
        named = [(c.name, c) for c in db_obj.cavities if c is not None]
        cavities = [c for _name, c in _sort_cavities(named)]

        num_cavities = len(cavities)

        # Font-size-driven slot height -- see the class docstring. Always
        # derived from the terminal font size's configured MAXIMUM, never
        # from any individual terminal's own (possibly shrunk-to-fit)
        # rendered size, so every housing's cavity slots stay a uniform
        # height regardless of what any one terminal's name needs.
        terminal_font_height = (
            _text.CHARACTER_HEIGHT * Config.object_sizes.terminal.name_font_size)
        self.terminal_font_height_padding = terminal_font_height * 0.1
        self.cavity_height = terminal_font_height + (self.terminal_font_height_padding * 2.0)

        text_extent = Config.object_sizes.housing.width + (Config.object_sizes.housing.width / 2.0)
        # +1 accounts for padding applying to both ends of the vertical
        # cavity stack, not just between adjacent cavities.
        cavity_extent = self.cavity_height * (num_cavities + 1)

        # Cached for _update_position/_update_angle below (re-run
        # _layout_children without recomputing), and for
        # get_cavity_aabb (index lookup).
        self._cavities = cavities
        self._cavity_extent = cavity_extent
        self._text_extent = text_extent

        self._layout_children(cavities, position, angle)
        self._build_corner_label(db_obj, cavity_extent, text_extent)

        self._bind_callbacks(cavities)

        return cavity_extent, text_extent

    @_check_types.do
    def get_cavity_aabb(self, cavity) -> np.ndarray:
        """Return *cavity*'s own slot's complete bounding box, in
        housing-local space (not yet rotated/translated by this
        housing's own position/angle) -- the single source of truth
        every cavity/terminal position (cavity name, terminal name, and
        a terminal's own wire attachment point) is derived from, rather
        than each independently re-deriving its own offset.

        This box is INSIDE the housing -- its near edge sits flush at
        the pin edge (``pin_local_x``), extending inward toward the
        housing's far edge, but stopping short of it (at the same
        inset the corner label's own anchor uses -- see
        :meth:`_build_corner_label`) so there's always room for that
        label at the bottom row, kept uniform across every row for
        alignment even though only the bottom row actually needs the
        clearance. The cavity's own NAME TEXT is NOT inside this box --
        it renders entirely outside the housing, disjoint from this box
        entirely (see ``objects_schematic/cavity.py``'s Cavity) -- this
        box is where a seated TERMINAL's own name/"("/wire-stub render
        instead (see ``objects_schematic/terminal.py``'s Terminal).

        Y is always 0 (flat 2D). Z is this slot's own vertical span --
        index 0 (natural-sort order) at the most-negative (top) Z, per
        this housing's own up-is-negative-Z convention (see
        :meth:`_layout_children`).

        :returns: ``[[min_x, min_y, min_z], [max_x, max_y, max_z]]``,
            same shape as :attr:`_aabb`/``BaseVar.local_aabb``.
        :raises ValueError: if *cavity* isn't one of this housing's own
            (already natural-sorted) cavities -- see :meth:`_recompute`.
        """
        index = self._cavities.index(cavity)

        half_cavity_extent = self._cavity_extent / 2.0
        half_text_extent = self._text_extent / 2.0
        pin_local_x = -half_text_extent
        far_local_x = half_text_extent - Config.object_sizes.cavity.padding

        min_z = -half_cavity_extent + index * self.cavity_height
        max_z = min_z + self.cavity_height

        return np.array([
            [pin_local_x, 0.0, min_z],
            [far_local_x, 0.0, max_z],
        ], dtype=np.float32)

    @_check_types.do
    def get_max_cavity_name_width(self) -> float:
        """Return the widest rendered width, at
        ``Config.object_sizes.cavity.name_font_size``, among every
        cavity's own name in this housing -- so every terminal's own
        wire-stub cylinder (see ``objects_schematic/terminal.py``'s
        ``Terminal``) can be the same length, long enough to clear
        whichever cavity name is longest, regardless of which row it's
        actually on.
        """
        font_size = Config.object_sizes.cavity.name_font_size

        widths = [
            _text.Text(cavity.name, font_size, build123d.FontStyle.REGULAR).width
            for cavity in self._cavities
        ]

        return max(widths, default=0.0)

    @_check_types.do
    def _update_position(self, position: _point.Point):
        """Re-run :meth:`_layout_children` after the inherited OBB/AABB
        update -- a housing's cavities/terminals are positioned in
        absolute world space (not relative to the housing at render
        time), so moving the housing must push fresh positions to them,
        not just recompute this housing's own bounds.
        """
        super()._update_position(position)
        self._layout_children(self._cavities, position, self._angle)

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle):
        """See :meth:`_update_position` -- same reason, for rotation."""
        super()._update_angle(angle)
        self._layout_children(self._cavities, self._position, angle)

    @_check_types.do
    def _rebuild(self, _entry=None):
        """Re-run :meth:`_recompute` and update this housing's live scale
        from the result -- bound (see :meth:`_bind_callbacks`) to fire
        whenever a cavity's name changes (reordering slots) or a cavity
        gains/loses its terminal, so the schematic never needs a manual
        refresh to pick those up.
        """
        with self.editor2d.editor.context:
            cavity_extent, text_extent = self._recompute(
                self.db_obj, self._position, self._angle)

            with self._scale:
                self._scale.x = text_extent
                self._scale.z = cavity_extent

        self.editor2d.Refresh()

    @_check_types.do
    def _bind_callbacks(self, cavities):
        """Bind every DB callback that should trigger :meth:`_rebuild`:
        each cavity's own name (its sort order, and so its slot, can
        change) and each cavity's ``'terminal_id'`` (a synthetic tag --
        see ``PJTTerminalsTable.insert``/``PJTTerminal.delete``/the
        ``cavity_id`` setter in ``database/project_db/pjt_terminal.py``
        -- fired when a terminal is seated/unseated/moved between
        cavities, since there's no real ``terminal_id`` column on
        ``pjt_cavities`` to bind to directly). A seated terminal's own
        name no longer matters here -- it doesn't affect this housing's
        fixed-size layout, and ``objects_schematic/terminal.py``'s ``Terminal``
        handles its own name-change rebuild independently.
        """
        for cavity in cavities:
            self._db_callbacks.append(cavity.bind(self._rebuild, 'name'))
            self._db_callbacks.append(cavity.bind(self._rebuild, 'terminal_id'))

    @_check_types.do
    def _unbind_callbacks(self):
        for cb in self._db_callbacks:
            cb.unbind()

        self._db_callbacks = []

    @_check_types.do
    def _release_corner_label(self):
        # No GPU resource to explicitly release -- unlike the old per-
        # instance VBO, a Text's glyph meshes are globally cached/shared
        # (see shapes/text.py's build_chars()), so dropping the
        # reference is all that's needed.
        self._corner_label_lines = []

    @_check_types.do
    def _delete(self):
        self._unbind_callbacks()
        super()._delete()

    @_check_types.do
    def _layout_children(self, cavities, position: _point.Point, angle: _angle.Angle):
        """Compute and persist each cavity's/seated terminal's own world
        ``position2d`` from :meth:`get_cavity_aabb` --
        ``objects_schematic/cavity.py``'s ``Cavity``/``objects_schematic/terminal.py``'s
        ``Terminal`` pick the new values up automatically (each already
        has its own position bound to trigger its inherited
        ``BaseVar._update_position``, which recomputes its own OBB/AABB)
        -- no direct call into either needed here.

        Layout (local X = text/width axis, local Z = cavity/height axis;
        canonical/unrotated pose = this housing on the right edge of the
        schematic, pin edge at local X = -text_extent/2; this housing's
        own local frame is centered on (0, 0, 0), with UP the NEGATIVE-Z
        direction -- cavity slots stack top-to-bottom in ascending
        (natural-sort) order, index 0's slot at the most-negative Z --
        the standard pinout-diagram reading convention):

        - Cavity anchor: its own slot's top-left corner, exactly on the
          pin edge (local X = pin edge, local Z = the slot's own top
          edge). ``objects_schematic/cavity.py``'s ``Cavity`` derives
          its actual rendered text position from this anchor itself --
          a hardcoded X offset outside the pin edge (plus its own
          measured width, for RIGHT-alignment) and a Z offset by
          ``shapes.text.CHARACTER_HEIGHT`` (scaled to its own font
          size) to reach its own baseline -- rather than this method
          computing an already-offset render position the way it used
          to.
        - Terminal name anchor: only when a terminal is seated, *inside*
          the housing rectangle (near the pin edge), bottom edge flush
          with the slot's own bottom boundary (LEFT/BOTTOM-aligned text, so
          this point is exactly its own bottom-left corner --
          ``objects_schematic/terminal.py``'s ``Terminal`` renders the "("
          bracket as an extra at a fixed local offset from this same
          point, RIGHT/BOTTOM-aligned to sit just outside the pin edge).
        """
        cavity_cfg = Config.object_sizes.cavity

        half_text_extent = self._text_extent / 2.0
        pin_local_x = -half_text_extent          # pin edge -- interior-facing side
        terminal_local_x = pin_local_x + cavity_cfg.padding

        for cavity in cavities:
            aabb = self.get_cavity_aabb(cavity)
            slot_top = float(aabb[0][2])
            slot_bottom = float(aabb[1][2])

            # Cavity's own anchor is its slot's top-left corner, exactly
            # on the pin edge -- see the docstring above.
            self._place_child(cavity, pin_local_x, slot_top, position, angle)

            terminal = cavity.terminal
            if terminal is not None and terminal.name:
                self._place_child(terminal, terminal_local_x, slot_bottom, position, angle)

    @staticmethod
    @_check_types.do
    def _place_child(child_db_obj, local_x: float, local_z: float,
                     housing_position: _point.Point, housing_angle: _angle.Angle):
        """Write *child_db_obj*'s own ``position2d`` from a housing-local
        ``(local_x, local_z)`` offset -- same rotate-then-translate math
        used everywhere else a local offset is turned into a world
        ``position2d``, and the same bound-Point write path.

        *child_db_obj*'s own ``angle2d`` is deliberately left untouched
        (stays identity) -- cavity/terminal text must always render
        upright/axis-aligned no matter which way the owning housing is
        rotated, only its anchor position follows the rotation. See
        :meth:`render`, which applies the same "position rotates,
        glyph doesn't" rule to this housing's own corner label.
        """
        points = np.array([[local_x, 0.0, local_z]], dtype=np.float32)
        wx, _wy, wz = _base_schematic._rotate_about_y(points, housing_angle.y)[0]  # NOQA

        position = child_db_obj.position2d
        with position:
            position.x = housing_position.x + float(wx)
            position.z = housing_position.z + float(wz)

    @_check_types.do
    def _build_corner_label(self, db_obj, cavity_extent, text_extent):
        """(Re)build the corner label (name/part number/manufacturer),
        this housing's own -- not a cavity's/terminal's -- extra.

        ``shapes.text.Text`` has no multi-line support of its own (see
        the module-level ``_CORNER_LABEL_LINE_HEIGHT_SCALE`` comment
        above), so this builds one ``Text`` per line instead of a
        single multi-line block -- stacked/anchored in :meth:`render`.
        """
        housing_cfg = Config.object_sizes.housing
        cavity_cfg = Config.object_sizes.cavity

        lines = [db_obj.name, self._part.part_number, self._part.manufacturer.name]
        self._corner_label_lines = [
            _text.Text(line, housing_cfg.font_size, build123d.FontStyle.REGULAR,
                       local_tilt=_text.TOP_DOWN_TILT)
            for line in lines
        ]
        self._corner_label_material = _materials.Generic(_color.Color(*Config.colors.label))

        half_text_extent = text_extent / 2.0
        half_cavity_extent = cavity_extent / 2.0

        corner_local_x = half_text_extent - cavity_cfg.padding
        corner_local_z = -half_cavity_extent + cavity_cfg.padding

        # RIGHT/BOTTOM-aligned (of the whole 3-line block), so this
        # point IS the block's own bottom-right corner -- no width/
        # height offset math needed to keep it from overflowing.
        self._corner_label_local = (corner_local_x, corner_local_z)

    @_check_types.do
    def render(self, shaders):
        """Render the housing rectangle body, then swap this object's
        own ``_vbo``/``_material``/``_angle``/``_scale``/``_position``
        for the corner label's (one line at a time) and render again
        through the exact same inherited pipeline -- the same swap-
        call-super()-restore idiom ``objects_3d/wire.py``'s ``Wire``
        already uses for its own multi-segment render, rather than a
        separate hand-rolled draw path. ``Text`` stands in directly as
        a ``_vbo`` here (see its own "VBOHandlerBase-compatible
        interface" docstring in ``shapes/text.py``).

        This is the entire extent of what a ``Housing`` renders --
        cavity names and terminal brackets/names are each drawn
        independently by their own ``objects_schematic/cavity.py``'s
        ``Cavity``/``objects_schematic/terminal.py``'s ``Terminal``.
        """
        super().render(shaders)

        if not self.is_visible or self._position is None or not self._corner_label_lines:
            return

        real_vbo, real_material, real_selected_material, real_angle, real_scale, real_position = (
            self._vbo, self._material, self._selected_material,
            self._angle, self._scale, self._position)

        # Always this label's own color -- never the rectangle body's,
        # and never selection-tinted either (self.material resolves to
        # self._selected_material while self._is_selected is True, so
        # that has to be overridden too, not just self._material) --
        # only the rectangle body's own color changes on selection.
        self._material = self._corner_label_material
        self._selected_material = self._corner_label_material

        # Identity rotation -- not this housing's own self._angle
        # (which drives the rectangle body) -- so the label always
        # reads upright regardless of the housing's rotation. Its
        # anchor position still follows the rotated corner via
        # _world_offset below; only the glyph orientation is fixed.
        self._angle = _angle.Angle()
        self._scale = _point.Point(1.0, 1.0, 1.0)

        local_x, local_z = self._corner_label_local
        wx, wy, wz = self._world_offset(local_x, local_z)
        anchor = _point.Point(real_position.x + wx, wy, real_position.z + wz)

        line_height = Config.object_sizes.housing.font_size * _CORNER_LABEL_LINE_HEIGHT_SCALE
        line_count = len(self._corner_label_lines)

        for i, line in enumerate(self._corner_label_lines):
            z_offset = (line_count - 1 - i) * line_height

            self._vbo = line
            self._position = _point.Point(anchor.x - line.width, anchor.y, anchor.z + z_offset)

            super().render(shaders)

        self._vbo, self._material, self._selected_material, self._angle, self._scale, self._position = (
            real_vbo, real_material, real_selected_material,
            real_angle, real_scale, real_position)

    @_check_types.do
    def _world_offset(self, local_x: float, local_z: float) -> tuple[float, float, float]:
        """Rotate a ``(local_x, 0, local_z)`` offset by this housing's
        current ``angle2d.y`` (about world Y -- the axis a Y=0-flat 2D
        primitive must spin about to stay flat) -- see
        ``objects_schematic/base_schematic.py``'s ``_rotate_about_y``.
        """
        points = np.array([[local_x, 0.0, local_z]], dtype=np.float32)
        x, y, z = _base_schematic._rotate_about_y(points, self._angle.y)[0]  # NOQA
        return float(x), float(y), float(z)

    @_check_types.do
    def hit_test(self, world_pos: _point.Point) -> bool:
        """
        Test if point is inside the housing rectangle (accounting for
        rotation), using the text-axis/cavity-axis extents computed in
        :meth:`_recompute`.
        """
        if self._position is None:
            return False

        local_x = world_pos.x - self._position.x
        local_z = world_pos.z - self._position.z

        rotation_rad = -math.radians(self._angle.y)
        cos_a = math.cos(rotation_rad)
        sin_a = math.sin(rotation_rad)

        rotated_x = local_x * cos_a - local_z * sin_a
        rotated_z = local_x * sin_a + local_z * cos_a

        return (abs(rotated_x) <= self._text_extent / 2 and
                abs(rotated_z) <= self._cavity_extent / 2)

    @_check_types.do
    def move_to(self, world_x: float, world_y: float):
        """
        Move housing to new position. Cavity/terminal positions cascade
        automatically via :meth:`_update_position`'s
        :meth:`_layout_children` call -- no separate push needed here.
        """
        if self._position is None:
            return

        with self._position:
            self._position.x = world_x
            self._position.z = world_y

    @classmethod
    @_check_types.do
    def start_add(cls, mainframe: "_ui.MainFrame") -> "_housing.Housing | None":
        """Single-click free placement, schematic-native -- mirrors
        objects_3d.housing.Housing.start_add. This housing's own
        position3d is left unset here (None), same as position2d is
        left unset there -- PJTHousingsTable.insert auto-fills whichever
        one is left None with a fresh (0, 0, 0)/(0, 0) placeholder point,
        so it still renders (just unpositioned) in the view that didn't
        place it, rather than being truly inert.
        """
        canvas = mainframe.editor2d.editor

        part_id = mainframe.editor_db.editor.housings.GetSelection()

        if part_id is None:
            from ...ui.dialogs import part_search as _part_search
            from ...ui import editor_db as _editor_db
            from PySide6.QtWidgets import QDialog

            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.HousingsPage, mainframe.global_db.housings_table,
                'Add Housing')

            if dlg.exec() == QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()
            else:
                part_id = None

            dlg.deleteLater()

            if part_id is None:
                return None

        from .. import housing as _housing_facade

        ptables = mainframe.project.ptables
        part = mainframe.project.gtables.housings_table[part_id]
        name = f'{part.manufacturer.name} {part.part_number}'
        position2d = ptables.pjt_points2d_table.insert(0, 0)

        db_obj = ptables.pjt_housings_table.insert(part_id, name, None, position2d.db_id)
        facade = _housing_facade.Housing(mainframe, db_obj)

        from ...add_handlers.editor_schematic import housing as _add_housing

        handler = _add_housing.Housing(canvas, facade)
        facade.objschematic._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.objschematic

        return facade

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        """Forwards to an active add-session (see start_add); falls back
        to BaseSchematic's own generic drag handling otherwise.
        """
        from ...add_handlers.editor_schematic import housing as _add_housing  # NOQA -- avoid a cycle at import time

        if isinstance(self._active_handler, _add_housing.Housing):
            handled = self._active_handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if self._active_handler.is_finished:
                self._active_handler = None

            return handled

        return super().handle_interaction(
            last_pos, current_pos, had_motion, interaction_type, clicked_object)

    @_check_types.do
    def get_context_menu(self):
        """Return this housing's own right-click context menu (see
        ``ui/mainframe.py``'s ``_on_obj_right_click_2d``, which calls
        this on whatever ``objschematic`` was right-clicked).
        """
        return HousingMenu(self.editor2d.editor, self)


class HousingMenu(QMenu):
    """Represent a housing menu in :mod:`harness_designer.objects.objects_schematic.housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas, selected):
        """Initialise the :class:`HousingMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Seal')
        action.triggered.connect(self.on_add_seal)

        action = self.addAction('Add Terminal')
        action.triggered.connect(self.on_add_terminal)

        action = self.addAction('Add CPA Lock')
        action.triggered.connect(self.on_add_cpa_lock)

        action = self.addAction('Add TPA Lock')
        action.triggered.connect(self.on_add_tpa_lock)

        action = self.addAction('Add Cover')
        action.triggered.connect(self.on_add_cover)

        action = self.addAction('Add Boot')
        action.triggered.connect(self.on_add_boot)

        self.addSeparator()

        rotate_menu = _context_menus.Rotate2DMenu(canvas, selected)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror2DMenu(canvas, selected)
        self.addMenu(mirror_menu)

        self.addSeparator()
        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        action = self.addAction('Clone')
        action.triggered.connect(self.on_clone)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    @_check_types.do
    def on_add_seal(self):
        """Handle the add seal event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_add_terminal(self):
        """Add terminals to this housing's cavities -- pick an empty
        cavity in the schematic view to seat one (see
        add_handlers.editor_schematic.terminal)."""
        from PySide6.QtCore import QTimer
        from . import terminal as _terminal_2d

        mainframe = self.selected.mainframe
        housing = self.selected.parent

        @_check_types.do
        def _do():
            _terminal_2d.Terminal.start_add(mainframe, housing=housing)

        QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_cpa_lock(self):
        """Handle the add CPA lock event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_add_tpa_lock(self):
        """Handle the add TPA lock event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_add_cover(self):
        """Handle the add cover event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_add_boot(self):
        """Handle the add boot event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_select(self):
        """Handle the select event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_clone(self):
        """Handle the clone event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_delete(self):
        """Handle the delete event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_properties(self):
        """Handle the properties event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass
