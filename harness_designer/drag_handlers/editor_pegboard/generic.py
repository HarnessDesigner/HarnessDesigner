# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Generic locked-X/Z drag for the Peg Board Editor.

Applies to: transitions, housings, wire layouts, bundle layouts, and
terminals (not in a cavity) -- anything whose entire position is the one
thing a drag ever needs to move (no per-segment/rope mechanics, unlike
wire/bundle -- see :mod:`~.wire`/:mod:`~.bundle`).

No directional-arrows gizmo, no axis lock (see the package's own
``__init__`` docstring) -- the camera's locked top-down orthographic
projection already maps the cursor to an unambiguous world X/Z position
every frame.

**Movement is gated by the rope-pull solver** (``handlers.
rope_pull_handler.resolve_rigid_move``, see its own module docstring for
the full design), not the older per-edge length-budget clamp
(:meth:`~harness_designer.drag_handlers.editor_pegboard.
DragHandlerPegboard._apply_local_clamp`) -- this handler bypasses that
entirely (see :meth:`Generic.__init__`), since this object's own peg-board
point id is exactly what a wire/bundle's start/stop anchor OR an
interior ``BundleLayout``/``WireLayout`` waypoint IS (there is no
separate "drag the end" object, see ``BUNDLE_PLACEMENT.md`` section 6's
own implementation notes). Every touching chain must accept the SAME
candidate fraction of the drag's own full delta before anything moves at
that fraction -- see :func:`resolve_rigid_move`'s own docstring for why
this is resolved as a line from the drag's fixed starting point(s)
rather than a per-frame hard refuse (revised 2026-10-01 after a live
"stuck transition" report).

**:meth:`Generic.__init__` caches every real peg-board point this drag
could ever move, each at its OWN position when the drag began.**
:func:`resolve_rigid_move` must measure its candidate fraction from a
FIXED starting point every frame, never a "current" position re-derived
each call -- re-deriving it was exactly what caused the dragged object
to get stuck exactly where the last accepted frame left it (the next
frame's delta was computed against that now-stale position instead of
the drag's own real start). This object's own point (``point3d_id``
below, despite the name -- see
``objects_pegboard.transition.Transition.__init__``) is cached alongside,
for a Transition, every branch's own peg-board point -- a bundle is
never anchored at a transition's own CENTER point, only at one of its
BRANCHES, each with its own separate peg-board point that moves by the
exact same rigid delta the center does. :meth:`Generic.__call__` computes
one ``full_delta`` (current mouse target minus the CENTER's cached
start) and hands every cached point -- center and every branch alike --
to :func:`~harness_designer.handlers.rope_pull_handler.resolve_rigid_move`
together, since they all move by that same delta at once -- confirmed
necessary after a live report that dragging a transition in the
peg-board view wasn't being constrained by its attached bundle's length
at all (it was only ever checking the center point, which no bundle
references).
"""

from typing import TYPE_CHECKING

from .. import editor_pegboard as _editor_pegboard
from .. import base as _base
from ...handlers import rope_pull_handler as _rope_pull_handler
from ...geometry import point as _point
from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_pegboard import canvas as _canvas
    from ... import objects as _objects


class Generic(_editor_pegboard.DragHandlerPegboard):
    """Generic locked-X/Z drag -- see the module docstring."""

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase") -> None:
        # Bypass DragHandlerPegboard.__init__ -- it caches
        # target.objpegboard.touching_budgets() for the older per-edge
        # clamp this handler no longer uses at all (see the module
        # docstring); that cache would just be wasted work here now,
        # same reasoning drag_handlers.editor_pegboard.bundle.Bundle's
        # own segment-drag __init__ already applies for the same reason.
        _base.DragHandlerBase.__init__(self, canvas, target)

        # Every real peg-board point this drag could ever move, each at
        # ITS OWN position right now (the drag's start) -- see the module
        # docstring's own "caches every real peg-board point" section for
        # why this must never be re-derived from a "current" position on
        # a later frame.
        objpegboard = target.objpegboard
        point_id = objpegboard.point3d_id

        self._point_starts: list[tuple[bytes, _point.Point]] = []
        if point_id is not None:
            self._point_starts.append((point_id, objpegboard.position.copy()))

            if target.is_transition:
                for branch in target.db_obj.branches:
                    branch_point_id = branch.position_pegboard_id
                    if branch_point_id is not None:
                        self._point_starts.append(
                            (branch_point_id, branch.position_pegboard.copy()))

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta: object, mouse_pos: _point.Point) -> None:  # NOQA -- delta unused, the locked ortho camera gives an absolute world position directly
        objpegboard = self.target.objpegboard

        world_pos = self.canvas.camera.screen_to_world(mouse_pos)
        target_pos = _point.Point(float(world_pos.x), 0.0, float(world_pos.z))

        if self._point_starts:
            center_start = self._point_starts[0][1]
            full_delta = (
                float(target_pos.x) - float(center_start.x),
                float(target_pos.z) - float(center_start.z))

            t = _rope_pull_handler.resolve_rigid_move(
                self.canvas.mainframe, self._point_starts, full_delta)

            target_pos = _point.Point(
                float(center_start.x) + full_delta[0] * t, 0.0,
                float(center_start.z) + full_delta[1] * t)

        current = objpegboard.position
        world_delta = _point.Point(
            float(target_pos.x) - float(current.x), 0.0,
            float(target_pos.z) - float(current.z))

        objpegboard.drag(world_delta)
