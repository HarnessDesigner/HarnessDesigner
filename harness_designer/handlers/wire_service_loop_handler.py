# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for inserting wire service loops.

Started only from a wire segment's own context menu
(``objects.objects3d.wire.WireMenu.on_add_wire_service_loop``) -- the wire
is fixed at construction and never changes; there is no toolbar tool for
this and no way to jump to a different wire mid-placement. The wire is cut
live at construction time to make room for the loop (see
``_split_wire_for_loop``); hovering only slides the preview along that same
fixed line, and clicking finalises the placement in place.

Collision avoidance is not this handler's concern -- it lives entirely on
``objects.objects3d.wire_service_loop.WireServiceLoop`` (roll then slide,
mesh-accurate, bounded by the wire's own endpoints and any wire markers on
it) and runs automatically any time the loop's start point moves, which is
all this handler ever does (see ``_update_preview``).
"""

import numpy as np
from typing import TYPE_CHECKING

from . import handler_base as _handler_base
from . import wire_topology as _wire_topology
from ..geometry import point as _point
from ..geometry import angle as _angle
from ..geometry import line as _line
from ..objects import wire_service_loop as _wire_service_loop
from ..objects import wire_layout as _wire_layout
from ..objects import wire as _wire
from ..gl import materials as _materials
from .. import config as _config
from .. import color as _color


if TYPE_CHECKING:
    from .. import ui as _ui


Config = _config.Config.colors


def _wire_segments(wire: _wire.Wire):
    """Every (p1, p2) sub-segment of *wire*'s current 3D path, as numpy
    arrays -- start, through each interior waypoint in idx order, to
    stop. Mirrors handlers.wire_layout_handler's own _wire_segments (kept
    as a small local helper here rather than reaching into
    objects.objects3d.mixins.wire_type.WireTypeMixin._segments directly,
    matching this codebase's existing style for this exact duplication --
    see handlers.wire_topology._segment_index)."""
    points = [wire.obj3d.start_position.as_numpy]
    for waypoint in wire.db_obj.waypoints3d:
        points.append(waypoint.point.as_numpy)
    points.append(wire.obj3d.stop_position.as_numpy)

    return list(zip(points, points[1:]))


class _SplitState:
    """Snapshot of the wire that's been split to make room for the loop --
    everything needed to look up the current halves while the preview
    slides, and to fully reverse the split if it's abandoned (cancel).

    Much smaller than it used to be: handlers.wire_topology.split_wire_at_
    point/merge_wires now own the waypoint-slicing, marker-reassignment,
    and sibling-re-homing bookkeeping this class used to snapshot by hand.
    """
    wire1: _wire.Wire = None
    wire2: _wire.Wire = None
    layout1: _wire_layout.WireLayout = None
    layout2: _wire_layout.WireLayout = None
    # The endpoints of whichever single sub-segment of the *original*
    # wire's path the loop was placed on -- stable for the whole preview
    # session, unlike wire1/wire2's own start/stop, one of which is always
    # the loop's own live-dragged point (see _closest_point_on_line). Not
    # the wire's own overall start/stop: a bent wire's true path can have
    # any number of waypoints between them, and the loop -- a straight
    # helix insert -- can only ever slide within the one segment it was
    # placed on, not across a bend.
    line: _line.Line = None


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

class AddWireServiceLoopHandler(_handler_base.HandlerBase):
    """Handle interactive placement of a service loop on *wire*.

    The wire is fixed for the life of the handler -- constructable only
    from that wire's own context menu, never a toolbar tool, and it never
    jumps to a different wire. Hovering slides the preview along the wire;
    a click finalises the placement.
    """
    obj: _wire_service_loop.WireServiceLoop | None = None

    def __init__(
        self,
        mainframe: "_ui.MainFrame",
        wire: _wire.Wire,
        mouse_pos: _point.Point,
    ):
        """Cut *wire* and start the loop preview anchored at *mouse_pos*
        (the screen-space point that opened the wire's context menu).
        """
        super().__init__(mainframe, None)

        self._preview_material = _materials.Plastic(
            _color.Color(*Config.add_object.preview_color))

        self._split_state: _SplitState | None = None

        # get_closest_point already walks the wire's true path -- start,
        # through every interior waypoint, to stop -- and returns which
        # sub-segment the click landed on. Projecting onto the wire's
        # overall start/stop chord instead (as this used to) is only
        # correct for a wire with no bends; for a bent wire it can land
        # the loop off the actual wire path entirely and split the wrong
        # segment.
        position, wire_angle, seg_idx = wire.obj3d.get_closest_point(mouse_pos)

        with mainframe.editor3d.context:
            self._create_preview(wire, position, wire_angle, seg_idx)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _closest_point_on_line(
        self,
        line: _line.Line,
        mouse_pos: _point.Point,
    ) -> tuple[_point.Point, _angle.Angle] | tuple[None, None]:
        """Pin the hover position to *line* instead of a wire's own
        endpoints.

        Once split, wire1's stop / wire2's start IS the loop's own
        live-dragged point -- computing "closest point on the wire" against
        wire1/wire2 directly would feed the drag position back into its own
        input every frame, a feedback loop that skews the preview off the
        original line instead of sliding along it. *line* is built once
        from the original wire's real (never-moving) endpoints, so
        projecting onto it stays stable regardless of where the loop
        currently sits.
        """
        world_pos = self.camera.get_position_on_focal_plane(mouse_pos)
        position = line.project_to_line(world_pos)

        p1 = line.p1.as_numpy
        p2 = line.p2.as_numpy
        direction = p2 - p1
        length = np.linalg.norm(direction)

        if length < 0.001:
            return None, None

        direction = direction / length
        wire_angle = _angle.Angle.from_direction(direction)

        return position, wire_angle

    def _create_preview(
        self,
        wire: _wire.Wire,
        position: _point.Point,
        wire_angle: _angle.Angle,
        seg_idx: int,
    ):
        """Cut *wire* and build the loop preview at *position*, on sub-
        segment *seg_idx* of its current path. Called once, from
        __init__.

        *wire* is split *before* the WireServiceLoop 3D object is
        constructed: that object's own __init__ runs collision avoidance
        immediately (WireServiceLoop._resolve_collision), which relies on
        _attached_wires() already finding wire1/wire2 -- doing this the
        other way round would leave the original, not-yet-split wire as
        the only thing nearby, and the loop would "avoid" the very wire
        it's about to be spliced into.

        The stop point is inserted as a throwaway placeholder (same
        coordinates as the start) -- WireServiceLoop 3D's own __init__
        unconditionally re-derives it from the start position/angle/scale,
        so nothing here needs to get it right.
        """
        q_arr = np.array(wire_angle.as_quat_float, dtype=np.float64)

        p_start_db = self.ptables.pjt_points3d_table.insert(*position.as_float)
        p_stop_db = self.ptables.pjt_points3d_table.insert(*position.as_float)

        self.part = wire.db_obj.part

        name = f'{self.part.manufacturer.name} {self.part.part_number}'

        loop_db = self.ptables.pjt_wire_service_loops_table.insert(
            wire.db_obj.part_id, name,
            p_start_db.db_id, p_stop_db.db_id,
            wire.db_obj.circuit_id,
            True, q_arr)

        self._split_state = self._split_wire_for_loop(
            wire, p_start_db.db_id, p_stop_db.db_id, seg_idx)

        self.obj = _wire_service_loop.WireServiceLoop(self.mainframe, loop_db)
        self.obj.identify(self._preview_material)

        self.obj.set_siblings(self._split_state.wire1, self._split_state.wire2)
        self._split_state.wire1.set_sibling(self.obj, 'stop')
        self._split_state.wire2.set_sibling(self.obj, 'start')

        # The whole rest of this placement (every hover update until
        # commit or cancel) is one continuous move, in the same sense a
        # mouse drag is -- cache the collision-candidate list for it
        # instead of rebuilding on every _update_preview call (see
        # WireServiceLoop.begin_move_session). Paired with end_move_session
        # in release_capture/_teardown_preview.
        self.obj.obj3d.begin_move_session()

    def _update_preview(self, position: _point.Point):
        """Slide the existing preview to a new position on the same wire.

        Only the start point is moved -- WireServiceLoop 3D's own
        _update_position override derives the stop point from it, resolves
        any collision the move introduces, and (since wire1's stop /
        layout1's position are the same shared Point object as the loop's
        start; see _split_wire_for_loop) cascades the move to wire1/wire2/
        both layouts for free. Nothing else needs updating here.
        """
        if self.obj is None:
            return

        start_p = self.obj.obj3d.start_position
        start_p += position - start_p

    def _split_wire_for_loop(
        self,
        wire: _wire.Wire,
        start_point_id: int,
        stop_point_id: int,
        seg_idx: int,
    ) -> _SplitState:
        """Cut *wire* into two pieces around a gap spanning
        start_point_id/stop_point_id, and insert a WireLayout at each cut.

        Reuses handlers.wire_topology.split_wire_at_point twice (once per
        cut point) rather than reimplementing its waypoint-slicing/
        marker-reattachment/sibling-re-homing handling, then discards the
        middle segment the two calls leave behind -- the loop occupies
        that span, not a wire.
        """
        project = self.mainframe.project
        mainframe = self.mainframe

        state = _SplitState()
        # Captured now, while wire.obj3d is still the real, unsplit wire --
        # the endpoints of the one sub-segment (seg_idx) the loop was
        # placed on, never touched by the drag (only the loop's own start/
        # stop points move), so this stays valid and stable for the rest
        # of the preview session.
        seg_p1, seg_p2 = _wire_segments(wire)[seg_idx]
        state.line = _line.Line(_point.Point(*seg_p1), _point.Point(*seg_p2))

        wire_b, wire_a = _wire_topology.split_wire_at_point(
            project, wire, start_point_id)
        wire_d, wire_c = _wire_topology.split_wire_at_point(
            project, wire_b, stop_point_id)

        # wire_c spans start_point_id -> stop_point_id -- the loop lives
        # there instead of a wire; discard it with the same teardown
        # split_wire_at_point itself uses.
        if mainframe.get_selected() is wire_c:
            wire_c.set_selected(False)
        wire_c.delete()

        state.wire1, state.wire2 = wire_a, wire_d

        # Layouts are constructed only now that wire1/wire2 already
        # reference the shared points -- WireLayout.__init__ derives its
        # diameter/color from attached_wires, a live query against
        # pjt_wires, so it must find something before it falls back to the
        # hardcoded 3.0mm/gray default.
        layout1_db = self.ptables.pjt_wire_layouts_table.insert(start_point_id)
        layout2_db = self.ptables.pjt_wire_layouts_table.insert(stop_point_id)
        state.layout1 = _wire_layout.WireLayout(mainframe, layout1_db)
        state.layout2 = _wire_layout.WireLayout(mainframe, layout2_db)
        project.add_wire_layout(state.layout1)
        project.add_wire_layout(state.layout2)

        return state

    def _restore_wire_from_split(self, state: _SplitState) -> None:
        """Reverse _split_wire_for_loop: delete both layouts, then merge
        wire1/wire2 back into a single wire via handlers.wire_topology.
        merge_wires (waypoints, markers, and sibling re-homing all handled
        there)."""
        project = self.mainframe.project

        for layout_obj in (state.layout1, state.layout2):
            layout_obj.delete()

        _wire_topology.merge_wires(project, state.wire1, state.wire2)

        for layout_obj in (state.layout1, state.layout2):
            layout_obj.delete()

        for wire_obj in (state.wire1, state.wire2):
            if self.mainframe.get_selected() is wire_obj:
                wire_obj.set_selected(False)
            wire_obj.delete()

        # Not sure what this was but I had to comment it out to get the app to compile.
        # project.add_wire(restored_obj)

    def _teardown_preview(self) -> None:
        """Delete the live loop preview and restore the wire it split."""
        if self.obj is not None:
            self.obj.obj3d.end_move_session()
            self.obj.delete()
            self.obj = None

        if self._split_state is not None:
            with self.mainframe.editor3d.context:
                self._restore_wire_from_split(self._split_state)
            self._split_state = None

    # ------------------------------------------------------------------
    # Handler protocol
    # ------------------------------------------------------------------

    def hover(self, mouse_pos: _point.Point):
        """Slide the preview along the wire's own (fixed) line.

        The wire never changes for the life of this handler, so there's no
        picking or re-splitting to do here -- just moving the loop's
        shared start point, which cascades to the derived stop point,
        wire1/wire2, both layouts, and collision avoidance for free (see
        _update_preview).
        """
        if self._finalized:
            return
        if self._split_state is None or self.obj is None:
            return

        position, wire_angle = self._closest_point_on_line(self._split_state.line, mouse_pos)
        if position is None or wire_angle is None:
            return

        with self.mainframe.editor3d.context:
            self._update_preview(position)

    def release_capture(self):
        if self._finalized:
            return
        if self._captured_position is None:
            return
        if self._split_state is None or self.obj is None:
            return

        self._finalized = True
        state = self._split_state

        # Re-derive against the stable original line, same as hover() --
        # not wire1/wire2's own endpoints (see _closest_point_on_line).
        position, wire_angle = self._closest_point_on_line(state.line, self._captured_position)

        if position is None or wire_angle is None:
            self._teardown_preview()
            return

        with self.mainframe.editor3d.context:
            # Same move hover() makes -- WireServiceLoop 3D resolves
            # collision avoidance as part of it, so by the time this
            # returns the loop is already at its final, collision-resolved
            # position/angle. Nothing further to compute or apply.
            self._update_preview(position)
            self.obj.obj3d.end_move_session()

        self.obj.identify(None)
        self.mainframe.project.add_wire_service_loop(self.obj)
        self.obj = None
        self._split_state = None

    def cancel(self):
        self._teardown_preview()
