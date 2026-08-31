# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math

import numpy as np
import build123d
from PySide6.QtWidgets import QMenu

from . import base_schematic as _base_schematic
from ...ui.widgets import context_menus as _context_menus
from ... import config as _config
from ... import color as _color
from ...gl import materials as _materials
from ...gl.canvas_base import interaction as _interaction
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...shapes import text as _text
from ...shapes import cylinder as _cylinder
from ... import utils as _utils
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_terminal as _pjt_terminal
    from .. import terminal as _terminal
    from . import housing as _housing_schematic
    from .. import housing as _housing_facade
    from ... import ui as _ui


Config = _config.Config.editor_schematic


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
    db_obj: "_pjt_terminal.PJTTerminal"

    @_check_types.do
    def __init__(self, parent: "_terminal.Terminal",
                 db_obj: "_pjt_terminal.PJTTerminal"):
        """Initialise the :class:`Terminal` instance.

        :param parent: Parent object.
        :type parent: :class:`_terminal.Terminal`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_terminal.PJTTerminal`
        """
        self._part = db_obj.part
        self.db_obj = db_obj

        self._name_lines: list = []
        self._name_local_positions: list = []

        position = db_obj.position2d
        angle = db_obj.angle2d
        scale = _point.Point(1.0, 1.0, 1.0)
        material = _materials.Generic(_color.Color(*Config.colors.label))

        with parent.mainframe.editor2d.editor.context:
            # No vbo of its own -- render() swaps self._vbo between the
            # name line(s), the "(" bracket, and the wire-stub cylinder
            # in turn (see the class docstring).
            super().__init__(parent, db_obj, None, angle, position, scale, material)
            self._rebuild_geometry()

        self._name_cb = self.db_obj.bind(self._rebuild, 'name')

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
    def housing(self):
        """This terminal's own seated cavity's owning ``Housing2D``, or
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
        math as ``objects_schematic/housing.py``'s own ``_place_child``/
        ``_world_offset``. Called fresh every :meth:`render`, so this
        always reflects the housing's current transform without needing
        its own change-tracking.
        """
        housing = self.housing

        points = np.array([[local_x, 0.0, local_z]], dtype=np.float32)
        wx, wy, wz = _base_schematic._rotate_about_y(points, housing.angle.y)[0]  # NOQA

        return _point.Point(
            housing.position.x + float(wx),
            housing.position.y + float(wy),
            housing.position.z + float(wz))

    @_check_types.do
    def _rebuild_geometry(self):
        """(Re)build the name line(s), "(" bracket, and wire-stub
        cylinder -- their own vbos and housing-LOCAL transforms (world
        conversion happens later, live, in :meth:`render`/
        :meth:`_compute_obb`/:meth:`_compute_aabb` via
        :meth:`_local_to_world`) -- from scratch.

        No-ops if :attr:`housing` isn't resolvable yet (this terminal's
        own construction time -- the owning housing may not be fully
        linked yet, mirroring ``objects_schematic/cavity.py``'s Cavity's
        own ``housing`` property docstring) -- a later
        :meth:`_update_position`/:meth:`_update_angle` (fired once the
        housing actually lays this terminal out) picks up the rebuild
        then instead.
        """
        housing = self.housing
        if housing is None:
            return

        cavity = self.db_obj.cavity

        cavity_aabb = housing.get_cavity_aabb(cavity)
        padding = Config.object_sizes.pin_edge_padding

        pin_local_x = float(cavity_aabb[0][0])
        slot_top = float(cavity_aabb[0][2])

        name_min_x = pin_local_x + padding
        name_max_x = float(cavity_aabb[1][0]) - padding
        name_min_z = slot_top + padding
        name_max_z = float(cavity_aabb[1][2]) - padding

        avail_width = max(0.0, name_max_x - name_min_x)
        avail_height = max(0.0, name_max_z - name_min_z)

        # --- Name: shrink-to-fit, possibly multi-line (assumes explicit
        # newlines in the name string -- no auto-wrap). ---
        max_font_size = Config.object_sizes.terminal.name_font_size
        lines = self.db_obj.name.split('\n') if self.db_obj.name else ['']

        built = [
            _text.Text(line, max_font_size, build123d.FontStyle.REGULAR,
                       local_tilt=_text.TOP_DOWN_TILT)
            for line in lines
        ]
        max_line_width = max((t.width for t in built), default=0.0)
        total_height = len(built) * _text.CHARACTER_HEIGHT * max_font_size

        width_scale = 1.0
        if max_line_width > avail_width > 0.0:
            width_scale = avail_width / max_line_width

        height_scale = 1.0
        if total_height > avail_height > 0.0:
            height_scale = avail_height / total_height

        name_font_size = max_font_size * min(width_scale, height_scale, 1.0)

        if name_font_size != max_font_size:
            built = [
                _text.Text(line, name_font_size, build123d.FontStyle.REGULAR,
                           local_tilt=_text.TOP_DOWN_TILT)
                for line in lines
            ]

        self._name_lines = built

        line_height = _text.CHARACTER_HEIGHT * name_font_size
        # LEFT/TOP-anchored within the padded box -- each line's own
        # baseline sits one more line_height down from the box's own
        # top edge (a Text's local z=0 is already its own baseline).
        self._name_local_positions = [
            (name_min_x, name_min_z + (i + 1) * line_height)
            for i in range(len(built))
        ]

        # --- "(" bracket: fully separate size/position from the name. ---
        cavity_font_size = Config.object_sizes.cavity.name_font_size
        cavity_char_height = _text.CHARACTER_HEIGHT * cavity_font_size
        remaining_height = max(0.0, housing.cavity_height - cavity_char_height)
        bracket_font_size = remaining_height / _text.CHARACTER_HEIGHT

        self._bracket = _text.Text(
            '(', bracket_font_size, build123d.FontStyle.REGULAR,
            local_tilt=_text.TOP_DOWN_TILT)

        # Independently pin_edge - padding -- lands at the same X as the
        # cavity name's own right edge (see the class docstring), not
        # because it's aligned to it.
        bracket_right_x = pin_local_x - padding
        bracket_left_x = bracket_right_x - self._bracket.width

        # Starts exactly at the cavity name's own baseline (rendered
        # below it), extends down by its own full height.
        bracket_top_z = slot_top + cavity_char_height
        bracket_bottom_z = bracket_top_z + remaining_height

        self._bracket_local_position = (bracket_left_x, bracket_bottom_z)

        # --- Wire-stub cylinder. ---
        max_cavity_name_width = housing.get_max_cavity_name_width()
        cylinder_z = (bracket_top_z + bracket_bottom_z) / 2.0

        self._cylinder_local_start = (bracket_left_x, cylinder_z)
        self._cylinder_local_stop = (
            bracket_right_x - max_cavity_name_width, cylinder_z)

        # Keep this terminal's own persisted 2D wire attachment point
        # (database/project_db/pjt_terminal.py's PJTTerminal.wire_position2d
        # -- where a wire actually connects in the schematic, distinct
        # from position2d, this terminal's own name anchor) in sync with
        # the cylinder's own stop point -- that property already lazily
        # creates the row (at the origin) on first access, "the caller
        # repositions it immediately" per its own docstring; this is
        # that repositioning, done unconditionally every rebuild (not
        # just once) so a housing move/rotate or another cavity's name
        # changing (shifting the shared stop X for every terminal in
        # the housing) keeps this point current too.
        stop_world = self._local_to_world(*self._cylinder_local_stop)
        wire_point = self.db_obj.wire_position2d
        with wire_point:
            wire_point.x = stop_world.x
            wire_point.z = stop_world.z

        self._compute_obb()
        self._compute_aabb()

    @_check_types.do
    def _local_bounds(self) -> tuple:
        """``(min_x, min_z, max_x, max_z)``, housing-local, encompassing
        the name line(s), the "(" bracket, and the wire-stub cylinder --
        used for :meth:`_compute_obb`/:meth:`_compute_aabb`.
        """
        xs = []
        zs = []

        for line, (local_x, local_z) in zip(self._name_lines, self._name_local_positions):
            xs.extend([local_x, local_x + line.width])
            zs.extend([local_z - line.height, local_z])

        bracket_x, bracket_z = self._bracket_local_position
        xs.extend([bracket_x, bracket_x + self._bracket.width])
        zs.extend([bracket_z - self._bracket.height, bracket_z])

        start_x, start_z = self._cylinder_local_start
        stop_x, stop_z = self._cylinder_local_stop
        xs.extend([start_x, stop_x])
        zs.extend([start_z, stop_z])

        return min(xs), min(zs), max(xs), max(zs)

    @_check_types.do
    def _compute_obb(self):
        """Derive this object's OBB from :meth:`_local_bounds`, rotated
        by the owning housing's own current angle (this terminal's own
        ``self._angle`` plays no part -- see the class docstring)."""
        if not self._name_lines:
            return

        housing = self.housing
        if housing is None:
            return

        min_x, min_z, max_x, max_z = self._local_bounds()

        local = np.array([
            [min_x, 0.0, min_z], [min_x, 0.0, max_z],
            [max_x, 0.0, min_z], [max_x, 0.0, max_z],
        ], dtype=np.float32)

        local @= housing.angle
        self._obb = local + housing.position

    @_check_types.do
    def _compute_aabb(self):
        """Same bounds as :meth:`_compute_obb` -- see its docstring."""
        if not self._name_lines:
            return

        housing = self.housing
        if housing is None:
            return

        min_x, min_z, max_x, max_z = self._local_bounds()

        corners = np.array([
            [min_x, 0.0, min_z], [min_x, 0.0, max_z],
            [max_x, 0.0, min_z], [max_x, 0.0, max_z],
        ], dtype=np.float32)

        corners @= housing.angle
        corners += housing.position.as_numpy

        aabb = _utils.adjust_aabb(corners)

        for i in range(2):
            for j in range(3):
                self._aabb[i][j] = aabb[i][j]

    @_check_types.do
    def _update_position(self, position: _point.Point):
        super()._update_position(position)
        self._rebuild_geometry()

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle):
        super()._update_angle(angle)
        self._rebuild_geometry()

    @_check_types.do
    def render(self, shaders):
        """Render the name line(s), the "(" bracket, and the wire-stub
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
        """
        if not self.is_visible:
            return

        real_vbo, real_angle, real_scale, real_position = (
            self._vbo, self._angle, self._scale, self._position)
        identity_angle = _angle.Angle()

        for line, (local_x, local_z) in zip(self._name_lines, self._name_local_positions):
            self._vbo = line
            self._angle = identity_angle
            self._scale = real_scale
            self._position = self._local_to_world(local_x, local_z)
            super().render(shaders)

        if hasattr(self, '_bracket'):
            bracket_x, bracket_z = self._bracket_local_position
            self._vbo = self._bracket
            self._angle = identity_angle
            self._scale = real_scale
            self._position = self._local_to_world(bracket_x, bracket_z)
            super().render(shaders)

        self._angle, self._scale, self._position = real_angle, real_scale, real_position

        if hasattr(self, '_cylinder_local_start'):
            start_x, start_z = self._cylinder_local_start
            stop_x, stop_z = self._cylinder_local_stop
            dx = stop_x - start_x
            dz = stop_z - start_z
            length = math.hypot(dx, dz)

            if length > 1e-6:
                real_angle, real_scale, real_position = self._angle, self._scale, self._position

                housing = self.housing
                local_cylinder_angle = _angle.Angle.from_euler(
                    0.0, math.degrees(math.atan2(dx, dz)), 0.0)

                self._vbo = _cylinder.create_vbo()
                self._angle = local_cylinder_angle + housing.angle
                self._scale = _point.Point(
                    Config.object_sizes.wire.diameter,
                    Config.object_sizes.wire.diameter, length)
                self._position = self._local_to_world(start_x, start_z)

                super().render(shaders)

                self._angle, self._scale, self._position = real_angle, real_scale, real_position

        self._vbo = real_vbo

    @_check_types.do
    def _rebuild(self, _entry=None):
        """Rebuild everything (see :meth:`_rebuild_geometry`) from this
        terminal's current name. Bound to fire whenever this terminal's
        own name changes.
        """
        with self.editor2d.editor.context:
            self._rebuild_geometry()

        self.editor2d.Refresh()

    @_check_types.do
    def _delete(self):
        self._name_cb.unbind()
        self._detach_extra_wires_at_position2d()
        super()._delete()

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame", housing: "_housing_facade.Housing | None" = None
    ) -> "_terminal.Terminal | None":
        """Cavity-pick placement, schematic-native -- see
        add_handlers.editor_schematic.terminal's own module docstring
        for why there's no cursor-following preview here, unlike the 3D
        editor's own Terminal.start_add.
        """
        from ...objects.objects_3d import terminal as _terminal_3d
        from ...ui.dialogs import part_search as _part_search
        from ...ui import editor_db as _editor_db
        from ...add_handlers.editor_schematic import terminal as _add_terminal
        from .. import terminal as _terminal_facade
        from PySide6.QtWidgets import QDialog

        canvas = mainframe.editor2d.editor

        compat_ids = (
            _terminal_3d.Terminal._get_housing_compat_pns(mainframe, housing)  # NOQA
            if housing is not None else [])

        part_id = mainframe.editor_db.editor.terminals.GetSelection() if housing is None else None

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.TerminalsPage, title='Add Terminal',
                table=mainframe.global_db.terminals_table, initial_results=compat_ids)
            part_id = dlg.GetValue() if dlg.exec() == QDialog.DialogCode.Accepted else None
            dlg.deleteLater()

            if part_id is None:
                return None

        ptables = mainframe.project.ptables
        part = ptables.global_db.terminals_table[part_id]

        from ...handlers import terminal_handler as _terminal_handler
        from ...ui.dialogs.dimensions_dialog import ensure_dimensions
        estimates, suggested = _terminal_handler.estimate_dimensions(mainframe, part)
        if not ensure_dimensions(mainframe, part, part.part_number, estimates, suggested):
            return None

        name = f'{part.manufacturer.name} {part.part_number}'

        pos3d = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
        pos2d = ptables.pjt_points2d_table.insert(0.0, 0.0)

        db_obj = ptables.pjt_terminals_table.insert(part_id, name, pos2d.db_id, pos3d.db_id, None)

        facade = _terminal_facade.Terminal(mainframe, db_obj)
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
        """Forwards to an active add-session (see start_add); falls back
        to BaseSchematic's own generic drag handling otherwise.
        """
        from ...add_handlers.editor_schematic import terminal as _add_terminal  # NOQA -- avoid a cycle at import time

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
        """Return this terminal's own right-click context menu (see
        ``ui/mainframe.py``'s ``_on_obj_right_click_2d``, which calls
        this on whatever ``objschematic`` was right-clicked) -- notably the
        entry point for drawing a wire from the schematic editor (see
        :meth:`TerminalMenu.on_add_wire`).
        """
        return TerminalMenu(self.editor2d.editor, self)

    @_check_types.do
    def _detach_extra_wires_at_position2d(self):
        """Give every wire but the first one attached at this terminal's
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


class TerminalMenu(QMenu):
    """Represent a terminal menu in :mod:`harness_designer.objects.objects_schematic.terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas, selected):
        """Initialise the :class:`TerminalMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
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
        """Start the interactive 2D wire-drawing flow (see
        add_handlers.editor_schematic.wire), pinned to this terminal as
        the start end.
        """
        from PySide6.QtCore import QTimer
        from . import wire as _wire_schematic

        mainframe = self.selected.mainframe
        terminal_obj = self.selected.parent

        @_check_types.do
        def _do():
            _wire_schematic.Wire.start_add(mainframe, terminal=terminal_obj)

        QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_wire_service_loop(self):
        """Handle the add wire service loop event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_add_seal(self):
        """Handle the add seal event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_trace_circuit(self):
        """Handle the trace circuit event.

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
