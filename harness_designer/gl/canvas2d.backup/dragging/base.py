# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ....geometry import point as _point
from ....geometry import line as _line
from .... import debug as _debug
from .... import check_types as _check_types


if TYPE_CHECKING:
    from .. import canvas as _canvas
    from .... import objects as _objects
    from ....objects import bundle as _bundle_object


# Number of drag events to let pass before locking in the dominant axis.
# The first event(s) right after button-down are dominated by mouse-down
# jitter (worse on high-resolution mice), which picks the wrong axis far
# more often than a settled delta does.
_AXIS_LOCK_SETTLE_EVENTS = 2


class DragObjectBase:
    """Shared screen-projection / axis-lock mechanics for every drag object.

    Subclasses each track their own notion of "anchor" (the point projected
    to screen space and incrementally updated every call) and decide what a
    computed world-space delta actually moves -- this base only owns the
    math that's identical regardless of what's being dragged.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas"):
        self.canvas = canvas
        self.axis_lock = _point.Point(0, 0, 0)

        self.pick_offset = None
        self._settle_events = 0

    @_check_types.do
    def delete(self):
       pass


class DragObject(DragObjectBase):
    """Generic single-position drag -- moves ``obj3d.position`` directly.

    Used for anything that isn't a Wire (see dragging.wire.WireDragObject)
    or a Bundle (see PathDragObject below) -- a plain object whose entire
    position is the one thing a drag ever needs to move.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", selected: "_objects.ObjectBase"):
        super().__init__(canvas)
        self.selected = selected

        # last object world _point.Point used for incremental moves
        self.last_pos = selected.obj2d.position.copy()

        # Duck-typed: only WireServiceLoop 3D defines this (see its own
        # begin_move_session docstring) -- caches its collision-candidate
        # list for the whole drag instead of rebuilding it on every one of
        # the many position updates a drag produces.
        if hasattr(selected.obj2d, 'begin_move_session'):
            selected.obj2d.begin_move_session()

    @_check_types.do
    def delete(self):
        if hasattr(self.selected.obj2d, 'end_move_session'):
            self.selected.obj2d.end_move_session()

        super().delete()

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta):
        position = self.selected.obj3d.position

        delta3d = self._axis_locked_delta3d(
            position, self.last_pos, delta, self.selected.obj3d.aabb)

        if delta3d is None:
            return

        position += delta3d
        self.last_pos = position.copy()


class PathDragObject(DragObjectBase):
    """Rigid-translate drag for a Bundle: moves the start point, every
    interior waypoint, and the stop point together by the same world-space
    delta, anchored on whichever point of the bundle's own true path was
    actually under the mouse when the drag began.

    Wire used to share this class too, back when a fully free-standing wire
    (neither end anchored) only ever moved as one rigid body regardless of
    where it was grabbed -- see dragging.wire.WireDragObject for the wire-
    specific replacement (segment-local dragging + snapping), used for
    every Wire drag now instead. Bundles have no comparable per-segment
    concept -- no anchor semantics (a bundle's own end can only ever attach
    to a Transition, never a Housing directly -- see
    objects.bundle.Bundle.set_sibling) and nothing to snap onto -- so a
    Bundle always still moves as a single rigid body no matter where it's
    grabbed.

    Anchoring on the straight start-to-stop chord's midpoint (as this used
    to, before bundles could have bends of their own) is wrong once there
    are any waypoints: that point may not even sit on the bundle's actual
    path, and only translating start/stop while leaving interior waypoints
    in place tears its shape apart mid-drag instead of moving it as one
    rigid body -- see WireTypeMixin.get_closest_point, which already walks
    the true (waypoint-aware) path and is used here for both concerns:
    which point to anchor on, and (via obj3d.db_obj.waypoints3d below)
    which points to move.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas",
                 selected: "_bundle_object.Bundle",
                 mouse_pos: _point.Point):
        super().__init__(canvas)
        self.selected = selected

        obj3d = selected.obj3d
        anchor, _angle, _seg_idx = obj3d.get_closest_point(mouse_pos)
        if anchor is None:
            # Degenerate (zero-length) bundle -- nothing meaningful on its
            # own path to anchor on; the straight chord's midpoint is at
            # least a stable fallback.
            line = _line.Line(obj3d.start_position, obj3d.stop_position)
            anchor = line.point_from_start(line.length() / 2.0)

        # A fresh, unregistered Point (no db_id) -- purely a local
        # screen-projection anchor, tracked incrementally below, never
        # itself persisted.
        self._anchor = anchor
        self.last_pos = self._anchor.copy()

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta):
        delta3d = self._axis_locked_delta3d(
            self._anchor, self.last_pos, delta, self.selected.obj3d.aabb)
        if delta3d is None:
            return

        obj3d = self.selected.obj3d

        start_position = obj3d.start_position
        stop_position = obj3d.stop_position

        start_position += delta3d
        for waypoint in obj3d.db_obj.waypoints3d:
            point = waypoint.point
            point += delta3d
        stop_position += delta3d

        self._anchor += delta3d
        self.last_pos = self._anchor.copy()
