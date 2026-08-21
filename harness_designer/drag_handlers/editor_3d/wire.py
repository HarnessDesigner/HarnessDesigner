# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Segment-local drag for a Wire in the 3D editor.

A wire always has two endpoints, each either free, seated in a cavity,
attached to a bare terminal, attached to a wire service loop, or
attached to a splice -- plus zero or more ordered waypoints between
them. What a click-and-drag on the wire's body actually moves depends on
where along that path the click landed:

- A click near a free end drags just that end.
- A click near an end that's anchored (cavity/terminal/splice/wire
  service loop) never drags that end -- see :func:`is_anchor_point`.
- A click on a plain 2-point wire's body (no waypoints) with both ends
  free drags the whole wire (both ends move together).
- A click before the first waypoint or after the last, with that
  bounding end free, drags only that free end.
- A click between two waypoints drags both waypoints bounding that
  segment together.

All of this planning happens once, at drag-start, in
:func:`plan_wire_drag` -- see :class:`WireDragPlan`. Any click
configuration that resolves to nothing draggable (e.g. both ends of the
nearest segment are anchored) returns ``None``, and the caller should
treat the click as a camera-pan instead of starting a no-op drag.

Directional arrows and axis-locking (see
:mod:`~harness_designer.drag_handlers.editor_3d`) apply here exactly
like every other 3D drag -- the axis lock is derived from the first
couple of settled mouse-delta samples after the click, same as any other
object.

When the plan's moving point is a true wire end (snap-eligible -- see
:attr:`WireDragPlan.snap_end`), the drag also builds an invisible
snap-probe set (see ``handlers.wire_snap``) at every terminal's own back
point, every splice's own branch point, and every other open, same-part
wire end, and hit-tests the REAL cursor position against them on every
move -- not the dragged point's own (possibly axis-locked) screen
position. Axis-locking only ever lets the dragged point move along one
world axis, so its screen projection drifts further from the actual
cursor the longer the lock has been engaged; probing near the dragged
point instead of the cursor made snapping onto anything off the locked
axis nearly impossible. Landing within a probe teleports the dragged
point exactly onto it (bypasses the axis lock entirely -- a partial-axis
move could never land exactly on the target) instead of following the
mouse; ``snapped_kind``/``snapped_target`` are read by the mouse
handler's button-up handling to commit the connection once the mouse
releases. A hard AWG/cross-section mismatch is purely informational here
-- never blocks the snap itself, only shows a warning overlay (confirmed
2026-08-06: "always allow a snap to occur and the connection to be
made... the user can resolve that issue after").

Ported from :class:`~harness_designer.gl.canvas_3d.dragging.wire.WireDragObject`
(proven, working code from before this package existed) -- only import
paths and the base class changed; the algorithm itself is unchanged.
"""

from typing import TYPE_CHECKING

from ...geometry import point as _point
from ...gl import object_picker as _object_picker
from .. import editor_3d as _editor_3d
from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ...objects import project as _project
    from ...objects import wire as _wire_object


@_check_types.do
def is_anchor_point(project: "_project.Project", point_id: bytes) -> bool:
    """True when *point_id* is rigidly tied to a cavity's or terminal's own
    wire-routing point -- not something a drag should ever move directly.

    A point attached to a terminal/splice/cavity that can carry more than
    one wire gets its own cloned row for the 2nd+ wire (one point can only
    carry a single wire_id/idx tag at a time -- see
    Terminal._own_or_cloned_point_id), with its own ``parent_point_id`` set
    to the real/canonical anchor point's id. So the clone's own raw id never
    equals the terminal's/cavity's own routing point id directly -- resolve
    up to the canonical id first (a no-op when the point isn't a clone;
    ``parent_point_id`` is None for the terminal's/cavity's own first-wire
    point, and always None for a wire's own true attach point, which is
    shared directly by every wire on that terminal rather than cloned).
    """
    point_row = project.ptables.pjt_points3d_table[point_id]
    parent_id = point_row.parent_point_id
    check_id = parent_id if parent_id is not None else point_id

    for cavity in project.cavities:
        if cavity.db_obj.wire_position3d_id_raw == check_id:
            return True

    for terminal in project.terminals:
        if check_id in (terminal.db_obj.wire_position3d_id_raw, terminal.db_obj.attach_position3d_id_raw):
            return True

    return False


@_check_types.do
def wire_end_anchors(project: "_project.Project", wire_obj: "_wire_object.Wire") -> tuple[bool, bool]:
    """Return (start_anchored, stop_anchored) for *wire_obj*.

    An end is "anchored" when it sits at a cavity's or terminal's own
    wire-routing point (Cavity.wire_position3d, Terminal.wire_position3d/
    attach_position3d) -- that end's position is derived from the
    cavity/terminal's own placement, not something a drag should move
    directly. Deliberately kept here rather than as a method on the Wire
    object itself -- this is purely a drag/move-handling decision, not
    something the object needs to know about itself; see
    handlers.wire_snap.SnapProbeSet, its only remaining caller (segment-
    local drag planning uses is_anchor_point directly -- see
    plan_wire_drag below).

    An end that is NOT anchored is always safe to drag freely even when
    another wire's endpoint happens to share the exact same live Point
    (a plain junction, not a cavity/terminal routing point) -- moving a
    shared Point via its own `+=` already propagates to everything else
    bound to it for free (see geometry.point.Point), so no separate
    "is another wire attached here" check is needed: only the cavity/
    terminal case requires special handling (leaving that end fixed).
    """
    obj3d = wire_obj.obj3d
    start_id = obj3d.start_position.db_id[:-2]
    stop_id = obj3d.stop_position.db_id[:-2]

    return is_anchor_point(project, start_id), is_anchor_point(project, stop_id)


class WireDragPlan:
    """What a click on a Wire's body should drag -- computed once at
    drag-start by plan_wire_drag(), consumed by :class:`Wire`.

    :ivar moving: The 1-2 live Point objects to translate together.
    :ivar anchor: The path point nearest the click, used as the
        screen-projection anchor (see DragHandler3D._axis_locked_delta3d).
    :ivar snap_end: 'start'/'stop' when *moving* is a single point that is
        also the wire's own true end (snap-eligible) -- None otherwise
        (a moving pair, or a single non-end point, never snaps; the
        general rule guarantees a lone moving point is always a true end
        though, see plan_wire_drag).
    """

    __slots__ = ('moving', 'anchor', 'snap_end')

    def __init__(self, moving: list, anchor: _point.Point, snap_end: str | None):
        self.moving = moving
        self.anchor = anchor
        self.snap_end = snap_end


@_check_types.do
def plan_wire_drag(project: "_project.Project", wire_obj: "_wire_object.Wire",
                    mouse_pos: _point.Point) -> WireDragPlan | None:
    """Work out what a click on *wire_obj*'s body at *mouse_pos* should
    drag, per the confirmed rule:

    1. If the click lands near the wire's own true start or stop (see
       WireTypeMixin.get_closest_endpoint's own tolerance -- the wire's own
       diameter or 5mm, whichever is larger), the single moving point is
       that true end.
    2. Otherwise, find the segment nearest the click (see
       WireTypeMixin.get_closest_point) -- the two points bounding that
       segment (true end or interior waypoint on either side) are the
       moving pair. This also covers a plain 2-point wire (no interior
       waypoints): the "segment" is the whole wire, so a mid-body click
       moves both ends together, same as it always visually looked like a
       whole-wire move.
    3. Either way, drop any point that is anchored (is_anchor_point) --
       anything beyond the two bounding points never moves, regardless of
       what's past them (another waypoint, an anchor, or a free end).
    4. If nothing is left after that filtering, return None -- the caller
       (mouse_handler.py) pans the camera instead of starting a no-op drag.

    Snap-testing only ever applies when exactly one point ends up moving --
    which, by construction, only happens via case 1 above (a true end) or
    case 2 collapsing to one surviving point after anchor filtering (also
    always a true end, since an interior waypoint is only ever a member of
    a still-two-point pair, never chosen alone) -- so a lone moving point is
    always snap-eligible; a moving pair never is.
    """
    obj3d = wire_obj.obj3d

    _pos, is_endpoint, end_name = obj3d.get_closest_endpoint(mouse_pos)

    if is_endpoint:
        moving_point = obj3d.start_position if end_name == 'start' else obj3d.stop_position
        point_id = moving_point.db_id[:-2]

        if is_anchor_point(project, point_id):
            return None

        return WireDragPlan(moving=[moving_point], anchor=moving_point.copy(), snap_end=end_name)

    closest_point, _angle, seg_idx = obj3d.get_closest_point(mouse_pos)
    if closest_point is None:
        return None

    chain = [obj3d.start_position] + [wp.point for wp in wire_obj.db_obj.waypoints3d] + [obj3d.stop_position]

    last_idx = len(chain) - 1
    bounding = (seg_idx, seg_idx + 1)

    moving = []
    for idx in bounding:
        point = chain[idx]
        if not is_anchor_point(project, point.db_id[:-2]):
            moving.append((idx, point))

    if not moving:
        return None

    snap_end = None
    if len(moving) == 1:
        idx, _point_obj = moving[0]
        if idx == 0:
            snap_end = 'start'
        elif idx == last_idx:
            snap_end = 'stop'

    return WireDragPlan(
        moving=[point for _idx, point in moving],
        anchor=closest_point.copy(),
        snap_end=snap_end)


class Wire(_editor_3d.DragHandler3D):
    """Segment-local drag for a Wire -- moves only the one or two path
    points (true end or interior waypoint) bounding the segment nearest the
    click, computed once at construction time by plan_wire_drag(); nothing
    else on the wire's path ever moves, and a drag never creates a new
    waypoint -- only a snap commit on mouse release can do that (see
    handlers.wire_snap.commit_snap).

    Also builds an invisible snap-probe set (see handlers.wire_snap) when
    the plan's moving point is snap-eligible (its own true start/stop) --
    one probe at every terminal's own back point, every splice's own branch
    point, and every OTHER open, same-part wire end -- and hit-tests the
    dragged point against them on every move. When within one, that point
    teleports exactly onto it (bypassing the axis lock entirely, since a
    partial-axis move could never land exactly on the target) instead of
    following the mouse; see ``snapped_kind``/``snapped_target``, read by
    mouse_handler.py's on_left_up to commit the connection once the mouse
    releases.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_wire_object.Wire",
                 plan: WireDragPlan):
        super().__init__(canvas, target)

        self._moving = plan.moving
        self._anchor = plan.anchor
        self.last_pos = self._anchor.copy()
        self.end = plan.snap_end

        self._snap_probes = None
        self._overlay = None
        self.snapped_kind: str | None = None
        self.snapped_target = None

        if self.end is not None:
            wire_part = target.db_obj.part
            if wire_part is not None:
                from ...handlers import wire_snap as _wire_snap  # NOQA -- avoid a cycle at import time

                self._snap_probes = _wire_snap.SnapProbeSet(
                    canvas.mainframe, wire_part, exclude_wire=target)
                self._overlay = _wire_snap.SnapOverlay(canvas.mainframe.editor3d.editor)

    @_check_types.do
    def delete(self) -> None:
        if self._snap_probes is not None:
            self._snap_probes.close()
            self._snap_probes = None

        if self._overlay is not None:
            self._overlay.deleteLater()
            self._overlay = None

        super().delete()

    def _get_view_object(self, obj):  # NOQA
        return obj.obj3d

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta, mouse_pos: _point.Point) -> None:
        if self._snap_probes is not None:
            from ...handlers import wire_snap as _wire_snap  # NOQA -- avoid a cycle at import time

            # Hit-test against the real cursor position, not a position
            # reconstructed from the (possibly axis-locked) dragged
            # point's own screen projection -- once axis-locking has
            # engaged, the dragged point's screen position only ever
            # moves along the locked axis, so it drifts further and
            # further from where the mouse actually is; probing near it
            # instead of the real cursor made snapping nearly impossible
            # whenever the snap target wasn't along the locked axis.
            picked = _object_picker.find_object(
                mouse_pos, self.canvas.camera.objects_in_view,
                self.canvas.camera, self._get_view_object)

            kind, target = _wire_snap.get_snap_info(picked)

            if kind is not None:
                # Purely informational -- never gates the snap/commit, even
                # for a genuine AWG-range mismatch (confirmed 2026-08-06):
                # always allow the connection, just flag a potential issue
                # for the user to resolve afterward (a future design-rules
                # checker is the real enforcement point, not this).
                wire_part = self.target.db_obj.part
                if kind == 'terminal':
                    _ok, block_msg, warning_msg = _wire_snap.check_terminal_compat(target, wire_part)
                elif kind == 'splice':
                    _ok, block_msg, warning_msg = _wire_snap.check_splice_compat(target, wire_part)
                else:
                    block_msg, warning_msg = None, None

                if block_msg:
                    self._overlay.show_message(mouse_pos, block_msg, blocking=True)
                elif warning_msg:
                    self._overlay.show_message(mouse_pos, warning_msg, blocking=False)
                elif self._overlay is not None:
                    self._overlay.hide_message()

                target_point = _wire_snap.snap_point(kind, target)

                moving_point = self._moving[0]
                moving_point += target_point - moving_point

                self.snapped_kind = kind
                self.snapped_target = target

                # A copy -- never the live target Point itself, which the
                # next drag event (or a snap-to-something-else) would
                # otherwise mutate in place via the arithmetic above.
                self._anchor = target_point.copy()
                self.last_pos = self._anchor.copy()
                return

            if self._overlay is not None:
                self._overlay.hide_message()

            self.snapped_kind = None
            self.snapped_target = None

        delta3d = self._axis_locked_delta3d(
            self._anchor, self.last_pos, delta, self.target.obj3d.aabb)
        if delta3d is None:
            return

        for point in self._moving:
            point += delta3d

        self._anchor += delta3d
        self.last_pos = self._anchor.copy()
