# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_pegboard as _base_pegboard
from . import chain_edges as _chain_edges
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl import materials as _materials
from ...gl.canvas_base import interaction as _interaction
from ...shapes import sphere as _sphere
from ... import color as _color
from ... import check_types as _check_types
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire_layout as _pjt_wire_layout
    from .. import wire_layout as _wire_layout
    from .. import wire as _wire_facade
    from ... import ui as _ui


Config = _config.Config.editor_pegboard


class WireLayout(_base_pegboard.BasePegboard):
    """
    Peg-board representation of a wire layout (grab handle) -- a small
    sphere marker at a bend along its wire's path, sized/colored from
    the wire's own catalog part. Mirrors
    ``objects_3d.wire_layout.WireLayout`` exactly (same diameter/color
    fallback, same ``_pick_priority``/``can_rotate`` override) -- built
    fresh here rather than borrowed from ``obj3d``, same reasoning as
    ``objects_pegboard.wire.Wire`` (see that class's own docstring).

    A bare position with no vbo of its own (the previous version of this
    class) can never be rendered (``BaseVar.render()`` no-ops without
    one) NOR picked (``_compute_obb``/``_compute_aabb`` both require a
    real vbo too, so ``.obb`` stays ``None`` forever --
    ``gl.object_picker._pick_candidates_at_mouse`` skips any object
    whose ``.obb`` is ``None`` outright) -- a waypoint built that way was
    silently invisible and unselectable in the peg-board view.
    """
    _parent: "_wire_layout.WireLayout" = None
    db_obj: "_pjt_wire_layout.PJTWireLayout"

    # Sits on the wire's own centerline, inside its OBB by design --
    # mirrors objects_3d.wire_layout.WireLayout._pick_priority.
    _pick_priority = 1

    @_check_types.do
    def __init__(self, parent: "_wire_layout.WireLayout",
                 db_obj: "_pjt_wire_layout.PJTWireLayout"):
        """Initialise the :class:`WireLayout` instance.

        :param parent: Parent object.
        :type parent: :class:`_wire_layout.WireLayout`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_layout.PJTWireLayout`
        """
        # A PJTWireLayout row is exclusive to exactly one view (see the
        # class docstring on PJTWireLayout itself) -- the facade always
        # builds all three view wrappers unconditionally for every row
        # (objects.wire_layout.WireLayout.__init__), regardless of which
        # one it actually belongs to. So this branch is the normal,
        # expected case for a row placed in the 3D or schematic view --
        # no vbo/angle/scale/material at all, mirroring
        # base_pegboard.BasePegboard.__init__'s "no rendering presence"
        # contract exactly (can_drag()/drag()/render()/picking all
        # already no-op gracefully on a None position).
        if db_obj.position_pegboard_id is None:
            super().__init__(parent, db_obj, position=None)
            self.point3d_id = None
            return

        wires = db_obj.attached_wires
        if wires:
            diameter = wires[0].part.od_mm
            color = wires[0].part.color.ui
        else:
            diameter = 3.0
            color = _color.Color(0.5, 0.5, 0.5, 1.0)

        material = _materials.Plastic(color)
        scale = _point.Point(diameter, diameter, diameter)
        angle = _angle.Angle()
        position = db_obj.position_pegboard

        with parent.mainframe.editor_pegboard.context:
            vbo = _sphere.create_vbo()
            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

        self.point3d_id = db_obj.position_pegboard_id

    @_check_types.do
    def can_rotate(self) -> bool:
        """A layout waypoint has no independent orientation of its own
        (its ``_angle`` above is a fresh, never-synced dummy purely to
        satisfy ``BaseVar``'s constructor) -- mirrors
        objects_3d.wire_layout.WireLayout.can_rotate exactly.
        """
        return False

    @_check_types.do
    def can_drag(self) -> bool:
        """A layout waypoint sitting at a terminal's or cavity's own
        housing-derived wire-routing point (``terminal.wire_position_
        pegboard``/``terminal.attach_position_pegboard``/``cavity.
        wire_position_pegboard`` -- see ``objects.terminal.Terminal.
        add_wire``, which drops a real ``WireLayout`` at each) must not
        be independently draggable -- its position is derived from the
        housing; the user has to move the housing itself instead
        (confirmed 2026-09-13, the same rule ``objects_pegboard.wire.
        Wire.is_housing_attached``'s own docstring already documented
        for the wire's own segment-drag, but this ``BaseVar.can_drag``
        override -- documented for exactly this case, never previously
        used by any class -- had never actually been wired up for the
        waypoint's own independent single-point drag).

        Reuses ``WireDragMixin.is_anchor_point`` -- the exact same test
        already used to keep the wire's own segment-drag from moving
        these points, so this can never drift out of sync with that
        rule.
        """
        if self.point3d_id is None:
            return super().can_drag()

        from ...drag_handlers.editor_pegboard import wire as _wire_pegboard  # NOQA -- avoid a cycle at import time

        project = self.parent.mainframe.project
        if _wire_pegboard.Wire.is_anchor_point(project, self.point3d_id):
            return False

        return super().can_drag()

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_wires

        return smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @_check_types.do
    def touching_budgets(self) -> list:
        """Return the length budget(s) for the wire segment(s) touching
        this waypoint -- always two (previous/next), since a wire-layout
        point is always strictly interior to its wire's chain.

        Resolves this waypoint's own row (``pjt_points_pegboard``) to
        find which wire it belongs to, then delegates the actual chain
        walk to that wire's own
        ``objects.objects_pegboard.wire.Wire.touching_edges``.
        """
        if self.point3d_id is None:
            return []

        project = self.parent.mainframe.project
        waypoint_row = project.ptables.pjt_points_pegboard_table[self.point3d_id]

        if waypoint_row.wire_id is None:
            return []

        wire_db_obj = project.ptables.pjt_wires_table[waypoint_row.wire_id]
        return _chain_edges.touching_edges(wire_db_obj, self.point3d_id)

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame", wire: "_wire_facade.Wire",
        initial_pos: _point.Point | None = None
    ) -> "_wire_layout.WireLayout":
        """Interactive placement of a new waypoint on *wire*'s own
        pegboard chain, pinned to it for the whole session -- see
        add_handlers.editor_pegboard.wire_layout's own module docstring.
        *initial_pos* seeds the live preview's starting pegboard
        position (the point that was right-clicked to open the "Add
        Waypoint" menu item, when available).
        """
        canvas = mainframe.editor_pegboard.editor
        ptables = mainframe.project.ptables

        if initial_pos is None:
            initial_pos = _point.Point(0.0, 0.0, 0.0)

        pos_db = ptables.pjt_points_pegboard_table.insert(0.0, 0.0, 0.0)
        layout_db = ptables.pjt_wire_layouts_table.insert(point_pegboard_id=pos_db.db_id)

        from .. import wire_layout as _wire_layout_facade

        facade = _wire_layout_facade.WireLayout(mainframe, layout_db)
        facade.objpegboard.is_visible = False

        pos = facade.objpegboard.position
        pos += initial_pos - pos

        from ...add_handlers.editor_pegboard import wire_layout as _add_wire_layout

        handler = _add_wire_layout.WireLayout(canvas, facade, wire)
        facade.objpegboard._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.objpegboard

        return facade

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: _interaction.MouseInteraction, clicked_object
    ) -> bool:
        """Forwards to an active add-session (see start_add); falls back
        to BasePegboard's own generic drag handling otherwise.
        """
        from ...add_handlers.editor_pegboard import wire_layout as _add_wire_layout  # NOQA -- avoid a cycle at import time

        if isinstance(self._active_handler, _add_wire_layout.WireLayout):
            handled = self._active_handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if self._active_handler.is_finished:
                self._active_handler = None

            return handled

        return super().handle_interaction(
            last_pos, current_pos, had_motion, interaction_type, clicked_object)
