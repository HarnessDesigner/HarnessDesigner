# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union

import build123d
import numpy as np
from PySide6 import QtWidgets
from PySide6 import QtCore

from . import base_schematic as _base_schematic
from . import housing as _housing_schematic
from . import wire as _wire_schematic
from .. import housing as _housing
from ... import config as _config
from ... import color as _color
from ... import check_types as _check_types
from ..objects_3d import terminal as _terminal_3d
from ...ui import editor_db as _editor_db
from ...ui.widgets import context_menus as _context_menus
from ...ui.dialogs import part_search as _part_search
from ...ui.dialogs.dimensions_dialog import ensure_dimensions
from ...gl import materials as _materials
from ...gl.canvas_base import interaction as _interaction
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry import line as _line
from ...geometry import cavity_layout as _cavity_layout
from ...shapes import text as _text
from ...shapes import cylinder as _cylinder
from ...shapes import sphere as _sphere
from ...handlers import terminal_handler as _terminal_handler
from ... import utils as _utils


if TYPE_CHECKING:
    from .. import terminal as _terminal
    from ...database.project_db import pjt_terminal as _pjt_terminal
    from ... import ui as _ui


Config = _config.Config.editor_schematic


def _is_180(degrees: float) -> bool:
    """Whether *degrees* (this terminal's own live ``angle2d.y``) is
    the 180 special case -- rotating this terminal's own name glyph a
    full half-turn would render it upside-down, so at that one angle
    the glyph itself renders upright instead (see :meth:`Terminal.render`)
    and the name's own internal line-justification flips to the
    opposite side instead (see :meth:`Terminal.__init__`/
    :meth:`Terminal._update_angle`) to keep reading in the same
    direction relative to its own anchor.
    """
    return round(abs(degrees)) % 360 == 180


# What a name is drawn with at exactly 180 degrees -- see Terminal.render.
_NO_ROTATION = _angle.Angle()

# What a terminal's own wire-junction sphere is drawn with -- see
# Terminal.render. A different color from Config.colors.splice on purpose:
# this is not a real splice, just where several of one terminal's own wires
# fan out from (see objects.terminal.Terminal._make_room_for_second_wire).
_WIRE_JUNCTION_MATERIAL = _materials.Generic(_color.Color(*Config.colors.wire_junction))


class Terminal(_base_schematic.BaseSchematic):
    """
    2D representation of a terminal for schematic view

    Renders three independent pieces, all positioned inside its own
    seated cavity's AABB (see ``objects_schematic/housing.py``'s
    ``Housing.get_cavity_aabb``) -- this is the one schematic object
    type that genuinely needs its own :meth:`render` override rather
    than the standard inherited single-vbo pipeline, since it draws
    multiple independent vbos:

    - Its own name (possibly multiple lines), shrunk below
      ``Config.object_sizes.terminal.name_font_size`` only if needed to
      fit inside the cavity AABB (inset by the shared
      ``Config.object_sizes.pin_edge_padding`` on all 4 sides).
    - A "(" bracket -- a fully separate piece, own size and position:
      sized to exactly fill the vertical space the cavity's own name
      doesn't use (``cavity_height - cavity_name_char_height``),
      rendered below the terminal name, its own right edge aligned with
      the cavity name's own right edge (both independently
      ``pin_edge - pin_edge_padding`` -- not aligned to each other, they
      just land at the same X because they use the same formula).
    - A wire-stub cylinder (diameter ``Config.object_sizes.wire.diameter``),
      starting at the "("'s own left edge, vertically centered on the
      "("'s own height, extending left past the longest cavity name
      anywhere in this housing (see ``Housing.get_max_cavity_name_width``)
      -- every terminal's stub in a housing is the same length for this
      reason, regardless of which row it's actually on.

    All of this is recomputed from scratch in :meth:`_rebuild_geometry`
    -- called at construction and whenever anything that could affect
    it changes (this terminal's own name, or a position2d/angle2d push
    from the owning housing -- a cavity added/removed, the housing's
    own cavity_height changing, or the housing itself moved/rotated) --
    rather than incrementally patched, since a housing-wide change (a
    different cavity's name changing the longest-name cylinder length,
    say) can affect every terminal in the housing at once.

    Unlike ``objects_schematic/cavity.py``'s ``Cavity``, this terminal's own
    ``position2d``/``angle2d`` are NOT what actually drives its render
    position -- every piece is positioned fresh, live, from the owning
    housing's own current AABB/position/angle (see
    :meth:`_local_to_world`) each time :meth:`render` runs. The pushed
    ``position2d``/``angle2d`` still matter as the *trigger* (the bound-
    Point/Angle callback that fires :meth:`_update_position`/
    :meth:`_update_angle`, in turn re-deriving everything), just not as
    the literal anchor value the way every other ``BaseVar`` subclass
    uses them.
    """

    _parent: "_terminal.Terminal" = None
    db_obj: "_pjt_terminal.PJTTerminal" = None

    # The name label sits entirely on top of its housing's rectangle, so a
    # click on it hits both -- the terminal has to win that (a click anywhere
    # else in the housing is the housing's). See
    # objects.objectsvar.base_var.BaseVar._pick_priority.
    _pick_priority = 1

    # Where the name label is drawn and hit-tested: this terminal's position,
    # lifted so the label sits ON the housing's top surface (y = 0) rather than
    # half-buried in it -- see _lift_name.
    _name_position: _point.Point | None = None

    # Cached housing-local geometry (see geometry.cavity_layout.
    # CavityGeometry) -- mirrors
    # objects_schematic/cavity.py's Cavity._geometry exactly, same
    # source (PJTHousing.cavity_geometry, keyed by this terminal's own
    # seated cavity's id).
    _geometry: _cavity_layout.CavityGeometry | None = None

    @_check_types.do
    def __init__(self, parent: "_terminal.Terminal",
                 db_obj: "_pjt_terminal.PJTTerminal"):
        """
        Initialise the :class:`Terminal` instance.

        :param parent: Parent object.
        :type parent: :class:`_terminal.Terminal`

        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_terminal.PJTTerminal`
        """

        self._part = db_obj.part
        self.db_obj = db_obj

        position = db_obj.position2d
        angle = db_obj.angle2d

        cavity = db_obj.cavity
        if cavity is not None:
            housing = cavity.housing

            cavity_geometry = housing.cavity_geometry.get(cavity.db_id)
            if cavity_geometry is None:
                raise RuntimeError('This should not happen')

            self._geometry = cavity_geometry

            # The terminal's own hit-test box (geometry.cavity_layout.
            # terminal_hit_box, "the text area inside the cavity rectangle")
            # doubles as the fitting constraint its own name text shrinks to
            # fit inside -- so the rendered name never overflows its own
            # hit-test region.
            avail_width = cavity_geometry.term_text_width
            avail_height = cavity_geometry.term_text_height

            # --- Name: shrink-to-fit, possibly multi-line (assumes explicit
            # newlines in the name string -- no auto-wrap). ---
            max_font_size = Config.object_sizes.terminal.name_font_size

            if self.db_obj.name:
                lines = self.db_obj.name.split('\n')
            else:
                lines = ['']

            # A Text makes its word VBOs when it is built, which needs the GL
            # context current.
            with parent.mainframe.editor2d.editor.context:
                built = [_text.Text(line, max_font_size,
                                    build123d.FontStyle.REGULAR,
                                    local_tilt=_text.TOP_DOWN_TILT)
                         for line in lines]

            max_line_width = max((t.width for t in built), default=0.0)
            total_height = len(built) * _text.CHARACTER_HEIGHT * max_font_size

            width_scale = 1.0
            if max_line_width > avail_width > 0.0:
                width_scale = avail_width / max_line_width

            height_scale = 1.0
            if total_height > avail_height > 0.0:
                height_scale = avail_height / total_height

            name_font_size = max_font_size * min(width_scale, height_scale, 1.0)

            # Stashed so _update_angle can rebuild this same Text (at
            # this same shrink-to-fit size) with a different h_align,
            # without re-running the shrink-to-fit measurement above --
            # that depends on this terminal's own name/available box,
            # neither of which change just because the angle crossed
            # into/out of 180.
            self._name_font_size = name_font_size

            # center_anchor=True -- local (0, 0, 0) (and so whatever position
            # this Text is rendered at) is this block's own CENTER, not its
            # bottom-left-of-widest-line corner (matching how every other
            # position in this system already means "center" -- see
            # geometry.cavity_layout's own docstring).
            #
            # h_align -- LEFT-justified normally (0/90/270, following
            # this terminal's own angle2d -- see render()), explicit
            # rather than relying on Text's own LEFT default. Flipped to
            # RIGHT at 180, where the glyph itself renders upright
            # instead of rotating with it (see _is_180's own docstring),
            # so a multi-line name's own internal line-justification
            # flips to the opposite side to keep reading in the same
            # direction relative to its own (center) anchor -- a no-op
            # visually for the common single-line-name case (see
            # shapes/text.py's own h_align docstring).
            if _is_180(angle.y):
                name_h_align = build123d.TextAlign.RIGHT
            else:
                name_h_align = build123d.TextAlign.LEFT

            with parent.mainframe.editor2d.editor.context:
                vbo = _text.Text(self.db_obj.name, name_font_size,
                                 build123d.FontStyle.REGULAR,
                                 local_tilt=_text.TOP_DOWN_TILT,
                                 h_align=name_h_align,
                                 center_anchor=True)

            if position is None:
                # The fitting box (avail_width wide, term_text_width) is centered
                # on the cavity's own center (cavity_geometry.position) -- its
                # own LEFT edge is box_left_x. Since *text* is center-anchored
                # (above), the CENTER we hand it has to sit half its own
                # (possibly shrunk-to-fit, so not necessarily == avail_width)
                # measured width to the right of that edge, not at box_left_x
                # itself -- otherwise a text block narrower than avail_width
                # would end up straddling box_left_x (half hanging off the left
                # of the fitting area) instead of flush against it.
                box_left_x = cavity_geometry.position[0] - (avail_width / 2.0)
                name_x = box_left_x + (vbo.width / 2.0)

                position2d = cavity.table.db.pjt_points2d_table.insert(
                    name_x, 0.0, cavity_geometry.position[1])

                db_obj.position2d_id = position2d.db_id
                position = db_obj.position2d

                with position:
                    position @= housing.angle2d

                position += housing.position2d

                position2d = cavity.table.db.pjt_points2d_table.insert(
                    cavity_geometry.cylinder_stop[0], 0.0, cavity_geometry.cylinder_stop[1])

                db_obj.wire_position2d_id = position2d.db_id

                wire_position = db_obj.wire_position2d
                with wire_position:
                    wire_position @= housing.angle2d

                wire_position += housing.position2d

                # See CavityGeometry.point_at_180 -- a plain rotation isn't
                # right for it at exactly 180 degrees (the name position
                # is on the slot's center, so nothing to correct there).
                if _cavity_layout.is_180(housing.angle2d.y):
                    with wire_position:
                        wire_position.z = float(wire_position.z) + cavity_geometry.z_shift_at_180(
                            cavity_geometry.cylinder_stop[1])
            else:
                wire_position = db_obj.wire_position2d

            # The "(" bracket's own position/font size are both precomputed
            # (see geometry.cavity_layout.compute_cavity_geometry) -- still
            # need a real Text VBO to actually render it, built at that
            # exact font size so it matches the precomputed position/cylinder
            # geometry exactly. center_anchor=True -- cavity_geometry's own
            # bracket_position/bracket_z is derived as this glyph's own
            # CENTER (see compute_housing_cavity_geometry's own docstring),
            # so the Text has to be built the same way every other label in
            # this system is, or its default (non-center) anchor renders at
            # that point instead -- shifting the glyph away from where the
            # geometry actually placed it.
            with parent.mainframe.editor2d.editor.context:
                self._bracket = _text.Text('(', cavity_geometry.bracket_font_size,
                                           build123d.FontStyle.REGULAR,
                                           local_tilt=_text.TOP_DOWN_TILT,
                                           center_anchor=True)

            # Through _local_to_world (as _update_position does on every
            # later change) so the 180 layout is applied here too.
            # The ")" drawn instead of the "(" at 180 degrees. Turning the
            # "(" half a turn would put its ink on the mirrored side, but the
            # glyph's own vertical offset from its center anchor would flip
            # with it and land it off the position the layout works out
            # (see CavityGeometry.point_at_180); a real ")" built the same
            # way, at the same size, drawn unturned at the mirrored anchor,
            # is exactly the "(" mirrored.
            with parent.mainframe.editor2d.editor.context:
                self._bracket_close = _text.Text(')', cavity_geometry.bracket_font_size,
                                                 build123d.FontStyle.REGULAR,
                                                 local_tilt=_text.TOP_DOWN_TILT,
                                                 center_anchor=True)

            bracket_position = self._local_to_world(*cavity_geometry.bracket_position)
            cylinder_start = self._local_to_world(*cavity_geometry.cylinder_start)

            line = _line.Line(cylinder_start, wire_position)
            self._cylinder_angle = line.get_angle(cylinder_start)

            cylinder_length = line.length()
            self._cylinder_scale = _point.Point(Config.object_sizes.wire.diameter,
                                                Config.object_sizes.wire.diameter,
                                                cylinder_length)

            self._bracket_position = bracket_position
            self._cylinder_start = cylinder_start
            self._wire_position = wire_position

            scale = _point.Point(1.0, 1.0, 1.0)
            material = _materials.Generic(_color.Color(*Config.colors.label))

            self._name_position = _point.Point(
                float(position.x), self._lift_name(vbo), float(position.z))

            with parent.mainframe.editor2d.editor.context:
                super().__init__(parent, db_obj, vbo, angle,
                                 position, scale, material)

        else:

            super().__init__(parent, db_obj, None, None,
                             None, None, None)

        # TODO: add in recalculating the positions based on the name
        # self._name_cb = self.db_obj.bind(self._rebuild, 'name')

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_terminals

        return smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @property
    @_check_types.do
    def housing(self) -> _housing_schematic.Housing | None:
        """
        This terminal's own seated cavity's owning ``Housing2D``, or
        ``None`` if not resolvable yet (e.g. at this object's own
        construction time -- see :meth:`_rebuild_geometry`'s own guard).
        """

        cavity = self.db_obj.cavity
        if cavity is None:
            return None

        housing_row = cavity.housing
        if housing_row is None:
            return None

        housing_obj = housing_row.get_object()
        if housing_obj is None:
            return None

        return housing_obj.objschematic

    @_check_types.do
    def _local_to_world(self, local_x: float, local_z: float) -> _point.Point:
        """Rotate+translate a housing-local ``(local_x, 0, local_z)``
        point by the owning housing's own LIVE position/angle -- same
        as ``objects_schematic/cavity.py``'s ``Cavity._local_to_world``.
        """
        housing = self.housing

        if _is_180(housing.angle.y):
            # Not a plain rotation -- see CavityGeometry.point_at_180.
            wx, wz = self._geometry.point_at_180((local_x, local_z))
            wy = 0.0
        else:
            points = np.array([[local_x, 0.0, local_z]], dtype=np.float32)
            wx, wy, wz = _base_schematic._rotate_about_y(points, housing.angle.y)[0]  # NOQA

        return _point.Point(
            housing.position.x + float(wx),
            housing.position.y + float(wy),
            housing.position.z + float(wz))

    @staticmethod
    def _lift_name(vbo: _text.Text) -> float:
        """How far a name label has to be raised so its lowest point is at
        y = 0, the housing's top surface.

        The housing is a flat quad at y = 0 and a glyph mesh is extruded and
        centered about its own anchor, so at y = 0 the label would be half
        buried; lifted by half its depth it sits on the surface and sticks out
        above it -- and its hit box is above the housing's, so a click on the
        name is nearer along the ray than the housing under it. Read from the
        label's own mesh bounds, not assumed.
        """
        return -float(vbo.local_aabb[0][1])

    @_check_types.do
    def _update_position(self, position: _point.Point):
        """
        Re-derive the "(" bracket's own world position and the
        wire-stub cylinder's own world start/angle/scale from this
        terminal's own precomputed housing-local geometry
        (:attr:`_geometry`), rotated and translated by the owning
        housing's CURRENT position/angle -- mirrors the same
        bracket/cylinder math ``__init__`` runs once at construction.
        Needed because a housing move pushes a new ``position2d`` here
        (see ``database/project_db/pjt_housing.py``'s
        ``PJTHousing._update_position2d``), but the bracket/cylinder
        aren't bound to that Point themselves -- unlike this terminal's
        own name label (``self._position``), they'd otherwise go stale.

        A full re-derivation via :meth:`_local_to_world`, NOT a cheap
        ``+= delta`` translate of the previous value -- a housing
        ROTATION is modeled as a rotate-about-pivot POSITION push here
        too (see ``PJTHousing._update_angle2d`` -- a seated terminal has
        no ``angle2d`` of its own), so this fires for a rotate exactly
        the same way it fires for a plain move, and a plain translate-
        by-delta is only correct for the latter -- applying it to the
        former silently rotates the bracket/cylinder's own OFFSET from
        this terminal's anchor by nothing at all, leaving them pointing
        the pre-rotation direction (confirmed 2026-09-16: this is what
        let a wire's mandatory straight terminal-exit stub end up
        pointing back INTO the terminal after a housing move, since the
        stub direction is derived straight from these two points -- see
        ``wire_routing.reroute._terminal_exit_stub_point``).
        """

        with self._bracket_position:
            fresh = self._local_to_world(*self._geometry.bracket_position)
            self._bracket_position.x = fresh.x
            self._bracket_position.y = fresh.y
            self._bracket_position.z = fresh.z

        with self._cylinder_start:
            fresh = self._local_to_world(*self._geometry.cylinder_start)
            self._cylinder_start.x = fresh.x
            self._cylinder_start.y = fresh.y
            self._cylinder_start.z = fresh.z

        line = _line.Line(self._cylinder_start, self._wire_position)
        self._cylinder_angle = line.get_angle(self._cylinder_start)

        cylinder_length = line.length()
        self._cylinder_scale = _point.Point(1.0, 1.0, cylinder_length)

        with self._name_position:
            self._name_position.x = float(position.x)
            self._name_position.z = float(position.z)

        super()._update_position(position)

        # The inherited generic _update_position above only ever applies
        # a cheap in-place translate to self._obb/self._aabb (correct for
        # a pure move, wrong for a housing ROTATION-as-position-delta --
        # see objects_schematic/cavity.py's Cavity._update_position for
        # the identical reasoning) -- re-derive this terminal's own
        # hit-test box fresh from the owning housing's CURRENT position/
        # angle instead, same as Cavity does.
        self._compute_obb()
        self._compute_aabb()

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle):
        """
        Same reason/logic as :meth:`_update_position` -- a housing
        rotation pushes a new ``position2d`` for a seated terminal (see
        ``PJTHousing._update_angle2d``), not a new ``angle2d``, so this
        rarely fires from a housing rotate in practice -- included
        defensively anyway. Same full re-derivation via
        :meth:`_local_to_world` as :meth:`_update_position` too, rather
        than the previous undo-old-angle/apply-new-angle approach --
        simpler, and can't compound drift from whatever state
        ``_bracket_position``/``_cylinder_start`` happened to already be
        in.
        """

        with self._bracket_position:
            fresh = self._local_to_world(*self._geometry.bracket_position)
            self._bracket_position.x = fresh.x
            self._bracket_position.y = fresh.y
            self._bracket_position.z = fresh.z

        with self._cylinder_start:
            fresh = self._local_to_world(*self._geometry.cylinder_start)
            self._cylinder_start.x = fresh.x
            self._cylinder_start.y = fresh.y
            self._cylinder_start.z = fresh.z

        line = _line.Line(self._cylinder_start, self._wire_position)
        self._cylinder_angle = line.get_angle(self._cylinder_start)

        cylinder_length = line.length()
        self._cylinder_scale = _point.Point(1.0, 1.0, cylinder_length)

        # h_align is baked into the name Text's own vertex layout at
        # construction time -- unlike angle/position, render() can't
        # just swap it live -- so only rebuild when actually crossing
        # into/out of the 180 special case (see _is_180's own
        # docstring), not on every angle push.
        if _is_180(angle.y) != _is_180(self._o_angle.y):
            if _is_180(angle.y):
                name_h_align = build123d.TextAlign.RIGHT
            else:
                name_h_align = build123d.TextAlign.LEFT

            with self.parent.mainframe.editor2d.editor.context:
                self._vbo = _text.Text(self.db_obj.name, self._name_font_size,
                                       build123d.FontStyle.REGULAR,
                                       local_tilt=_text.TOP_DOWN_TILT,
                                       h_align=name_h_align,
                                       center_anchor=True)

        super()._update_angle(angle)

        # See _update_position's own comment -- same reasoning.
        self._compute_obb()
        self._compute_aabb()

    @property
    @_check_types.do
    def obb(self) -> np.ndarray:
        """The generic box until the housing is known, then the one worked
        out from the label (see :meth:`_compute_obb`)."""
        if self.housing is None:
            return super().obb

        if self._obb is None:
            self._compute_obb()
            self._compute_aabb()

        return self._obb

    @property
    @_check_types.do
    def aabb(self) -> np.ndarray:
        """See :attr:`obb`."""
        if self.housing is None:
            return super().aabb

        if self._obb is None:
            self._compute_obb()
            self._compute_aabb()

        return self._aabb

    def _label_angle(self) -> _angle.Angle:
        """The angle this terminal's name AND bracket are drawn at --
        the same one :meth:`render` uses.

        The owning HOUSING's own live angle, not this terminal's own
        ``self._angle`` (``db_obj.angle2d``) -- a seated terminal has no
        ``angle2d`` of its own that follows the housing's rotation (see
        :meth:`_update_angle`'s own docstring: a housing rotate pushes a
        new ``position2d`` here, never a new ``angle2d``), so reading
        ``self._angle`` left the name/bracket glyphs frozen at whatever
        angle they had when the terminal was first seated, un-rotated by
        any later housing rotation, even though the terminal's own
        POSITION tracked correctly the whole time -- confirmed
        2026-09-23 (Kevin) as the fix, mirroring
        ``objects_schematic/cavity.py``'s ``Cavity._label_angle`` (which
        already reads the housing's angle for exactly this reason).
        Falls back to this terminal's own angle only when the housing
        isn't resolvable yet (mirrors :meth:`_compute_obb`'s own guard).

        Except at exactly 180 degrees, where a full half-turn would
        render the glyph upside-down, so the angle is forced back to
        identity instead.
        """
        housing = self.housing
        if housing is None:
            live_angle = self._angle
        else:
            live_angle = housing.angle

        if _is_180(live_angle.y):
            return _NO_ROTATION

        return live_angle

    @_check_types.do
    def _compute_obb(self):
        """The label's own OBB (``Text.local_obb``) turned and moved to where
        the label is drawn. Nothing to do until the housing is known."""
        housing = self.housing
        if housing is None or self._vbo is None or self._name_position is None:
            return

        obb = self._vbo.local_obb.copy()
        obb @= self._label_angle()
        obb += self._name_position.as_numpy

        # the first time there is no array yet: it comes from the pool
        if self._obb is None:
            self._obb = self._obb_manager.read(self._obb_index)

        self._obb[:] = obb

    @_check_types.do
    def _compute_aabb(self):
        """The label's own AABB (``Text.local_aabb``) turned and moved to where
        the label is drawn, then ``utils.adjust_aabb`` so every min is in the
        min row and every max in the max row. Nothing to do until the housing
        is known."""
        housing = self.housing
        if housing is None or self._vbo is None or self._name_position is None:
            return

        local = self._vbo.local_aabb
        corners = _utils.compute_obb(
            _point.Point(*local[0].tolist()), _point.Point(*local[1].tolist()))

        corners @= self._label_angle()
        corners += self._name_position.as_numpy

        self._aabb[:] = _utils.adjust_aabb(corners)

    @_check_types.do
    def hit_test_step2(self, ray_origin, ray_direction):
        """Only the box is tested (see :meth:`hit_test_step3`)."""
        return _base_schematic.box_hit_test(self._obb, ray_origin, ray_direction)

    @_check_types.do
    def hit_test_step3(self, ray_origin, ray_dir):
        """A terminal is picked by its name's box -- the OBB -- not by the
        glyph triangles: the pool's own OBB test already said the ray is inside
        it, and nothing finer is wanted."""
        return _base_schematic.box_hit_test(self._obb, ray_origin, ray_dir)

    @_check_types.do
    def render(self, shaders):
        """
        Render the name line(s), the "(" bracket, and the wire-stub
        cylinder -- swapping ``self._vbo``/``self._angle``/
        ``self._scale``/``self._position`` for each piece in turn and
        delegating to the inherited pipeline -- the same
        swap-call-super()-restore idiom ``objects_3d/wire.py``'s
        ``Wire``/``objects_schematic/housing.py``'s ``Housing`` both
        already use.

        A ``Text`` piece (see its own "VBOHandlerBase-compatible
        interface" in ``shapes/text.py``) draws itself using whatever
        ``self._position``/``self._angle``/``self._scale`` this
        terminal has at the moment ``_render_geometry`` reads them
        (``Text`` tracks no position/angle of its own -- see
        ``Text.render()``'s own docstring), so those (not just
        ``self._vbo``) get swapped and restored around the name/bracket
        passes too -- same as the cylinder pass already does.

        Every world-space value used here (``_name_world_position``/
        ``_bracket_world_position``/``_cylinder_world_start``/
        ``_cylinder_world_angle``/``_cylinder_length``) is read straight
        off ``self`` -- NOT recomputed via ``_local_to_world``/the
        cylinder's own angle-from-direction math here, which this method
        used to do on every single call. :meth:`_rebuild_geometry`
        already recomputes all of those, but only when something that
        could actually change one of them fires (this terminal's own
        name, or -- via :meth:`_update_position`/:meth:`_update_angle`,
        both of which call it -- the owning housing's own live position/
        angle) -- a housing can carry thousands of terminals, and this
        method runs every frame, so redoing that rotation/angle math
        here unconditionally would repeat real, non-trivial work for
        (in the overwhelmingly common case) an unchanged result.
        """
        if not self.is_visible:
            return

        real_angle = self._angle
        real_position = self._position
        real_vbo = self._vbo
        real_scale = self._scale

        # The owning housing's own LIVE angle (see _label_angle's own
        # docstring for why: this terminal's own self._angle is never
        # updated by a housing rotate) -- used for BOTH the name and the
        # "(" bracket below, since both are flat glyphs meant to read
        # right-side-up with the housing the same way the housing's own
        # corner label and this cavity's own name already do.
        self._angle = self._label_angle()
        self._position = self._name_position

        super().render(shaders)

        if self._bracket is not None:
            # At 180 the mirrored layout needs a ")" -- see __init__'s
            # own comment on _bracket_close.
            # self._angle is _label_angle() here, which is the _NO_ROTATION
            # object itself at exactly 180 and never otherwise.
            if self._angle is _NO_ROTATION:
                self._vbo = self._bracket_close
            else:
                self._vbo = self._bracket

            self._position = self._bracket_position
            # self._angle is still label_angle from above -- the bracket
            # rotates with the housing exactly like the name does (and,
            # like the name, is not turned at all at 180).
            super().render(shaders)

            self._vbo = _cylinder.create_vbo()
            self._angle = self._cylinder_angle
            self._scale = self._cylinder_scale
            self._position = self._cylinder_start

            super().render(shaders)

            # A second (or later) wire attached to this terminal has already
            # pushed wire_position2d further out to make room for it (see
            # objects.terminal.Terminal._make_room_for_second_wire) -- mark
            # that fan-out point with a sphere, in its own distinct color, so
            # it reads as "several of this terminal's own wires meet here",
            # not a real splice. Purely visual -- not a separate object, not
            # its own click target; this terminal's own hit box (its name
            # label) is unaffected.
            if len(self.parent.wires) > 1:
                real_material = self._material

                self._vbo = _sphere.create_vbo()
                self._angle = _NO_ROTATION
                diameter = Config.object_sizes.splice.diameter
                self._scale = _point.Point(diameter, diameter, diameter)
                self._position = self._wire_position
                self._material = _WIRE_JUNCTION_MATERIAL

                super().render(shaders)

                self._material = real_material

        # Restored unconditionally -- not just inside the bracket branch
        # above -- so a bracket-less terminal (self._bracket is None)
        # doesn't leave self._position/self._angle pointed at the name
        # label's own values after render() returns.
        self._vbo = real_vbo
        self._angle = real_angle
        self._scale = real_scale
        self._position = real_position

    @_check_types.do
    def _delete(self):
        # self._name_cb.unbind()
        self._detach_extra_wires_at_wire_position2d()
        super()._delete()

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame",
        housing: _housing.Housing | None = None
    ) -> Union["_terminal.Terminal", None]:

        """
        Cavity-pick placement, schematic-native -- see
        add_handlers.editor_schematic.terminal's own module docstring
        for why there's no cursor-following preview here, unlike the 3D
        editor's own Terminal.start_add.
        """

        # avoid a cycle at import time
        from ...add_handlers.editor_schematic import terminal as _add_terminal
        from .. import terminal as _terminal_obj

        canvas = mainframe.editor2d.editor

        if housing is not None:
            initial_params = _terminal_3d.Terminal._search_params_for_housing(  # NOQA
                mainframe, housing)

        else:
            initial_params = None

        if housing is None:
            part_id = mainframe.editor_db.editor.terminals.GetSelection()
        else:
            part_id = None

        if part_id is None:
            dlg = _part_search.SearchDialog(mainframe, _editor_db.TerminalsPage,
                                            mainframe.global_db.terminals_table,
                                            'Add Terminal',
                                            initial_params=initial_params)

            if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()
            else:
                part_id = None

            dlg.deleteLater()

            if part_id is None:
                return None

        ptables = mainframe.project.ptables
        part = ptables.global_db.terminals_table[part_id]

        estimates, suggested = (
            _terminal_handler.estimate_dimensions(mainframe, part))

        ed = ensure_dimensions(
            mainframe, part, part.part_number, estimates, suggested)

        if not ed:
            return None

        name = f'{part.manufacturer.name} {part.part_number}'

        pos3d = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
        pos2d = ptables.pjt_points2d_table.insert(0.0, 0.0, 0.0)

        db_obj = ptables.pjt_terminals_table.insert(
            part_id, name, pos2d.db_id, pos3d.db_id, None)

        facade = _terminal_obj.Terminal(mainframe, db_obj)
        facade.obj3d.is_visible = False

        handler = _add_terminal.Terminal(canvas, facade, part, housing)
        facade.objschematic._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.objschematic

        return facade

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: _interaction.MouseInteraction, clicked_object
    ) -> bool:

        """
        Forwards to an active add-session (see start_add); falls back
        to BaseSchematic's own generic drag handling otherwise.
        """

        # avoid a cycle at import time
        from ...add_handlers.editor_schematic import terminal as _add_terminal

        if isinstance(self._active_handler, _add_terminal.Terminal):
            # A local reference, not another read of self._active_handler
            # below -- a CANCEL can delete this object's own facade,
            # whose generic delete() sees self._active_handler is this
            # same handler and clears it right there, before this call
            # even returns (see objects_3d.wire.Wire.handle_interaction).
            handler = self._active_handler
            handled = handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if handler.is_finished and self._active_handler is handler:
                self._active_handler = None

            return handled

        return super().handle_interaction(
            last_pos, current_pos, had_motion, interaction_type, clicked_object)

    @_check_types.do
    def get_context_menu(self):
        """
        Return this terminal's own right-click context menu (see
        ``ui/mainframe.py``'s ``_on_obj_right_click_2d``, which calls
        this on whatever ``objschematic`` was right-clicked) -- notably the
        entry point for drawing a wire from the schematic editor (see
        :meth:`TerminalMenu.on_add_wire`).
        """

        return TerminalMenu(self.editor2d.editor, self)

    @_check_types.do
    def _detach_extra_wires_at_wire_position2d(self):
        """
        Give every wire but the first one attached at this terminal's own
        ``wire_position2d`` its own new point at the same coordinates.

        Unlike 3D/peg board, a terminal has no per-wire clone of its own
        wire-attach point in the schematic view -- every wire attached here
        points ``start_position2d_id``/``stop_position2d_id`` straight at
        this SAME shared ``wire_position2d`` (see ``objects.terminal.
        Terminal.add_wire``'s own docstring -- distinct from
        ``position2d``, this terminal's own NAME anchor, which no wire ever
        attaches to), and seals aren't rendered in 2D at all, so there's
        nothing else to clean up here. Only the first wire found keeps the
        shared point (it becomes uniquely its own once the terminal row is
        gone); every additional wire would otherwise stay joined to it
        through a point that no longer represents a real connection.
        """

        ptables = self.mainframe.project.ptables
        point_id = self.db_obj.wire_position2d_id

        if point_id is None:
            return

        x, y, z = ptables.pjt_points2d_table[point_id].point.as_float
        seen_first = False

        for column in ('start_point2d_id', 'stop_point2d_id'):
            for row in ptables.pjt_wires_table.select('id', **{column: point_id}):
                wire_db = ptables.pjt_wires_table[row[0]]

                if not seen_first:
                    seen_first = True
                    continue

                new_point = ptables.pjt_points2d_table.insert(x, y, z)
                attr = column.replace('_point2d_id', '_position2d_id')
                setattr(wire_db, attr, new_point.db_id)


class TerminalMenu(QtWidgets.QMenu):
    """
    Represent a terminal menu in :mod:`harness_designer.objects.objects_schematic.terminal`.
    """

    @_check_types.do
    def __init__(self, canvas, selected):
        """
        Initialise the :class:`TerminalMenu` instance.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN

        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """

        QtWidgets.QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Wire')
        action.triggered.connect(self.on_add_wire)

        action = self.addAction('Add Wire Service Loop')
        action.triggered.connect(self.on_add_wire_service_loop)

        action = self.addAction('Add Seal')
        action.triggered.connect(self.on_add_seal)

        self.addSeparator()

        rotate_menu = _context_menus.Rotate2DMenu(canvas, selected)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror2DMenu(canvas, selected)
        self.addMenu(mirror_menu)

        self.addSeparator()
        action = self.addAction('Trace Circuit')
        action.triggered.connect(self.on_trace_circuit)

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
    def on_add_wire(self):
        """
        Start the interactive 2D wire-drawing flow (see
        add_handlers.editor_schematic.wire), pinned to this terminal as
        the start end.
        """

        mainframe = self.selected.mainframe
        terminal_obj = self.selected.parent

        @_check_types.do
        def _do():
            _wire_schematic.Wire.start_add(mainframe, terminal=terminal_obj)

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_wire_service_loop(self):
        """
        Handle the add wire service loop event.
        """

        pass

    @_check_types.do
    def on_add_seal(self):
        """
        Handle the add seal event.
        """

        pass

    @_check_types.do
    def on_trace_circuit(self):
        """
        Handle the trace circuit event.
        """

        pass

    @_check_types.do
    def on_select(self):
        """
        Handle the select event.
        """

        pass

    @_check_types.do
    def on_clone(self):
        """
        Handle the clone event.
        """

        pass

    @_check_types.do
    def on_delete(self):
        """
        Handle the delete event.
        """

        pass

    @_check_types.do
    def on_properties(self):
        """
        Handle the properties event.
        """

        pass
