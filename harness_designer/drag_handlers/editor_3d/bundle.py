# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Rigid-translate drag for a Bundle in the 3D editor.

Moves the start point, every interior waypoint, and the stop point
together by the same world-space delta, anchored on whichever point of
the bundle's own true path was actually under the mouse when the drag
began.

Wire used to share this same rigid-body drag too, back when a fully
free-standing wire (neither end anchored) only ever moved as one rigid
body regardless of where it was grabbed -- see :mod:`~.wire` for the
wire-specific replacement (segment-local dragging + snapping), used for
every Wire drag now instead. Bundles have no comparable per-segment
concept -- no anchor semantics (a bundle's own end can only ever attach
to a Transition, never a Housing directly -- see
``objects.bundle.Bundle.set_sibling``) and nothing to snap onto -- so a
Bundle always still moves as a single rigid body no matter where it's
grabbed, and (unlike :mod:`~.wire`) never needs the real cursor position
for anything -- there's no snap probe to hit-test against.

Anchoring on the straight start-to-stop chord's midpoint (as this used
to, before bundles could have bends of their own) is wrong once there
are any waypoints: that point may not even sit on the bundle's actual
path, and only translating start/stop while leaving interior waypoints
in place tears its shape apart mid-drag instead of moving it as one
rigid body -- see ``WireTypeMixin.get_closest_point``, which already
walks the true (waypoint-aware) path and is used here for both concerns:
which point to anchor on, and (via ``obj3d.db_obj.waypoints3d`` below)
which points to move.

Ported from :class:`~harness_designer.gl.canvas_3d.dragging.base.PathDragObject`
(proven, working code from before this package existed).
"""

from typing import TYPE_CHECKING

from ...geometry import point as _point
from ...geometry import line as _line
from .. import editor_3d as _editor_3d
from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ...objects import bundle as _bundle_object


class Bundle(_editor_3d.DragHandler3D):
    """Rigid-translate drag for a Bundle -- see the module docstring."""

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_bundle_object.Bundle",
                 mouse_pos: _point.Point):
        super().__init__(canvas, target)

        obj3d = target.obj3d
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
    def __call__(self, delta, mouse_pos: _point.Point) -> None:  # NOQA -- mouse_pos unused, nothing to snap onto
        delta3d = self._axis_locked_delta3d(
            self._anchor, self.last_pos, delta, self.target.obj3d.aabb)
        if delta3d is None:
            return

        obj3d = self.target.obj3d

        start_position = obj3d.start_position
        stop_position = obj3d.stop_position

        start_position += delta3d
        for waypoint in obj3d.db_obj.waypoints3d:
            point = waypoint.point
            point += delta3d
        stop_position += delta3d

        self._anchor += delta3d
        self.last_pos = self._anchor.copy()
