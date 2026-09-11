# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union

import build123d
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
from ...shapes import text as _text
from ...shapes import cylinder as _cylinder
from ...handlers import terminal_handler as _terminal_handler


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
    return round(degrees) % 360 == 180


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
                    name_x, cavity_geometry.position[1])

                db_obj.position2d_id = position2d.db_id
                position = db_obj.position2d

                with position:
                    position @= housing.angle2d

                position += housing.position2d

                position2d = cavity.table.db.pjt_points2d_table.insert(
                    *cavity_geometry.cylinder_stop)

                db_obj.wire_position2d_id = position2d.db_id

                wire_position = db_obj.wire_position2d
                with wire_position:
                    wire_position @= housing.angle2d

                wire_position += housing.position2d
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
            self._bracket = _text.Text('(', cavity_geometry.bracket_font_size,
                                       build123d.FontStyle.REGULAR,
                                       local_tilt=_text.TOP_DOWN_TILT,
                                       center_anchor=True)

            bracket_position = _point.Point(
                cavity_geometry.bracket_position[0],
                0.0, cavity_geometry.bracket_position[1])

            with bracket_position:
                bracket_position @= self.housing.angle
                bracket_position += housing.position2d

            cylinder_start = _point.Point(
                cavity_geometry.cylinder_start[0],
                0.0, cavity_geometry.cylinder_start[1])

            with cylinder_start:
                cylinder_start @= self.housing.angle
                cylinder_start += housing.position2d

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
    def _update_position(self, position: _point.Point):
        """
        Re-derive the "(" bracket's own world position and the
        wire-stub cylinder's own world start/angle/scale from this
        cavity's own precomputed housing-local geometry, rotated and
        translated by the owning housing's CURRENT position/angle --
        mirrors the same bracket/cylinder math ``__init__`` runs once
        at construction. Needed because a housing move pushes a new
        ``position2d`` here (see
        ``database/project_db/pjt_housing.py``'s
        ``PJTHousing._update_position2d``), but the bracket/cylinder
        aren't bound to that Point themselves -- unlike this
        terminal's own name label (``self._position``), they'd
        otherwise go stale.
        """

        delta = position - self._o_position

        with self._bracket_position:
            self._bracket_position += delta

        with self._cylinder_start:
            self._cylinder_start += delta

        line = _line.Line(self._cylinder_start, self._wire_position)
        self._cylinder_angle = line.get_angle(self._cylinder_start)

        cylinder_length = line.length()
        self._cylinder_scale = _point.Point(1.0, 1.0, cylinder_length)

        super()._update_position(position)

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle):
        """
        Same reason/logic as :meth:`_update_position` -- a housing
        rotation pushes a new ``position2d`` for a seated terminal (see
        ``PJTHousing._update_angle2d``), not a new ``angle2d``, so this
        rarely fires from a housing rotate in practice -- included
        defensively anyway.
        """

        inverse_angle = self._o_angle.inverse
        housing = self.housing

        with self._bracket_position:
            self._bracket_position -= housing.position
            self._bracket_position @= inverse_angle
            self._bracket_position @= angle
            self._bracket_position += housing.position

        with self._cylinder_start:
            self._cylinder_start -= housing.position
            self._cylinder_start @= inverse_angle
            self._cylinder_start @= angle
            self._cylinder_start += housing.position

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

            self._vbo = _text.Text(self.db_obj.name, self._name_font_size,
                                   build123d.FontStyle.REGULAR,
                                   local_tilt=_text.TOP_DOWN_TILT,
                                   h_align=name_h_align,
                                   center_anchor=True)

        super()._update_angle(angle)

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

        # Follows this terminal's own angle2d at 0/90/270, same as
        # always -- except at 180, where a full half-turn would render
        # the name glyph upside-down, so the angle is forced back to
        # identity instead (see _is_180's own docstring -- __init__/
        # _update_angle already flip this same Text's own h_align to
        # compensate, whenever this last crossed into/out of 180).
        if _is_180(real_angle.y):
            self._angle = _angle.Angle()

        super().render(shaders)

        self._angle = real_angle

        if self._bracket is not None:
            real_vbo, real_scale, real_position = (
                self._vbo, self._scale, self._position)

            self._vbo = self._bracket
            self._position = self._bracket_position
            super().render(shaders)

            self._vbo = _cylinder.create_vbo()
            self._angle = self._cylinder_angle
            self._scale = self._cylinder_scale
            self._position = self._cylinder_start

            super().render(shaders)

            self._vbo = real_vbo
            self._angle = real_angle
            self._scale = real_scale
            self._position = real_position

    @_check_types.do
    def _delete(self):
        # self._name_cb.unbind()
        self._detach_extra_wires_at_position2d()
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
        pos2d = ptables.pjt_points2d_table.insert(0.0, 0.0)

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
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:

        """
        Forwards to an active add-session (see start_add); falls back
        to BaseSchematic's own generic drag handling otherwise.
        """

        # avoid a cycle at import time
        from ...add_handlers.editor_schematic import terminal as _add_terminal

        if isinstance(self._active_handler, _add_terminal.Terminal):
            handled = self._active_handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if self._active_handler.is_finished:
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
    def _detach_extra_wires_at_position2d(self):
        """
        Give every wire but the first one attached at this terminal's
        own 2D point its own new point at the same coordinates.

        Unlike 3D, a terminal has no separate crimp/layout-point chain
        in the schematic view -- wires attach directly to the
        terminal's own position2d, and seals aren't rendered in 2D at
        all, so there's nothing else to clean up here. Only the first
        wire found keeps the shared point (it becomes uniquely its own
        once the terminal row is gone); every additional wire would
        otherwise stay joined to it through a point that no longer
        represents a real connection.
        """

        ptables = self.mainframe.project.ptables
        point_id = self.db_obj.position2d_id

        if point_id is None:
            return

        x, y, _ = ptables.pjt_points2d_table[point_id].point.as_float
        seen_first = False

        for column in ('start_point2d_id', 'stop_point2d_id'):
            for row in ptables.pjt_wires_table.select('id', **{column: point_id}):
                wire_db = ptables.pjt_wires_table[row[0]]

                if not seen_first:
                    seen_first = True
                    continue

                new_point = ptables.pjt_points2d_table.insert(x, y)
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
