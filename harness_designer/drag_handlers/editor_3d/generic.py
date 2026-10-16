# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Generic single-position drag for the 3D editor.

Applies to: housing, transition, splice, wire service loops, bundle
layouts, wire layouts -- anything whose entire position is the one thing
a drag ever needs to move (contrast :mod:`~.wire`/:mod:`~.bundle`, which
move a specific point/segment along a path instead).

Eligibility for the two starred cases below is decided on the object
itself (``can_drag()`` -- see
``harness_designer.objects.objectsvar.base_var.BaseVar``), not here:

- A bundle layout that's shared with a boot or a transition is not
  draggable.
- A wire layout that shares its position with a cavity, terminal, or
  splice is not draggable.

Ported from :class:`~harness_designer.gl.canvas_3d.dragging.base.DragObject`
(proven, working code from before this package existed).

**Peg-board length realization.** Moving ANY of these six (not just a
``BundleLayout``/``WireLayout`` marker) changes the real ``length_mm``
(derived live from the 3D path) of every bundle/wire anchored at
whichever of this object's own 3D point(s) actually moved -- per
``BUNDLE_PLACEMENT.md`` section 6's decided rule, a 3D length change
must be realized in the peg-board view. Every frame this moves such an
object, :meth:`Generic.__call__` re-solves every chain attached to it
(``handlers.rope_pull_handler.realize_length_change``/``realize_3d_move``)
immediately afterward -- this chain's own peg-board start anchor never
actually moves (nothing here drags it), but its own far end, and now
whatever THAT cascades into (another Transition, a Housing, and so on
-- see ``rope_pull_handler``'s own module docstring), can, if this
chain's own slack alone can't absorb the new length. A ``BundleLayout``/
``WireLayout`` marker's own point is an INTERIOR waypoint, found via
``PJTBundleLayout.attached_bundles``/``PJTWireLayout.attached_wires``;
every other type's own point(s) are genuine chain ANCHORS (a Housing has
one; a Splice/WireServiceLoop has two, its own start/stop; a Transition
has one PER BRANCH -- moving the transition moves every branch's own
point by the same rigid delta, and a bundle is anchored at a branch's
own point, never the transition's own center -- confirmed missing
entirely in an earlier pass after a live report that dragging a
transition in 3D wasn't lengthening its attached bundle's peg-board
chain at all), found via :func:`~harness_designer.handlers.
rope_pull_handler.realize_3d_move`'s own start/stop point-id scan. Each
matched chain starts its own independent cascade -- unlike the
peg-board-drag side's single shared resolve, there is no "everyone must
agree" step tying separate matched chains together here.
"""

from typing import TYPE_CHECKING

from .. import editor_3d as _editor_3d
from ...handlers import rope_pull_handler as _rope_pull_handler
from ...handlers import wire_routing_handler as _wire_routing_handler
from ...geometry import point as _point
from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ... import objects as _objects


class Generic(_editor_3d.DragHandler3D):
    """Generic single-position drag -- moves ``obj3d.position`` directly."""

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase") -> None:
        super().__init__(canvas, target)

        # Last object world Point used for incremental moves.
        self.last_pos = target.obj3d.position.copy()

        # Only WireServiceLoop3D needs this (see its own begin_move_session
        # docstring) -- caches its collision-candidate list for the whole
        # drag instead of rebuilding it on every one of the many position
        # updates a drag produces.
        if target.is_wire_service_loop:
            target.obj3d.begin_move_session()

        # Open the move gesture for this drag's whole lifetime (WRITE_DESIGN.md
        # section 4.12): every database write this drag triggers -- the
        # housing/transition position cascade included -- defers into each
        # table's cache instead of touching the database, until delete()
        # below closes it and the outermost close flushes once. Last
        # statement in __init__ on purpose: if anything above raised, this
        # object was never fully constructed and delete() will never be
        # called on it, so a gesture opened earlier would leak open forever.
        canvas.mainframe.project.begin_gesture()

    @_check_types.do
    def delete(self) -> None:
        try:
            # One final, real (in_progress=False) reconcile before the
            # gesture closes below -- every per-frame call from
            # __call__ ran with in_progress=True while this drag was
            # open, which pins every touched chain's own waypoint COUNT
            # at whatever it already was (repositioning only); without
            # this, that count would never catch up to what the final
            # position actually needs. Still batched into the same
            # flush as everything else, since the gesture is still open
            # here -- see _realize_pegboard_length's own comment.
            self._realize_pegboard_length(in_progress=False)

            if self.target.is_wire_service_loop:
                self.target.obj3d.end_move_session()

            super().delete()
        finally:
            # Close the gesture last, whichever way this exits -- see
            # __init__ above. A gesture that never closes would silently
            # defer every later write app-wide until something else
            # happened to close it, so this must run even if the cleanup
            # above raises.
            self.canvas.mainframe.project.end_gesture()

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta: _point.Point, mouse_pos: _point.Point) -> None:  # NOQA -- mouse_pos unused, part of the shared contract
        position = self.target.obj3d.position

        delta3d = self._axis_locked_delta3d(
            position, self.last_pos, delta, self.target.obj3d.aabb)
        if delta3d is None:
            return

        position += delta3d
        self.last_pos = position.copy()

        self._realize_pegboard_length()

    @_check_types.do
    def _realize_pegboard_length(self, in_progress: bool | None = None) -> None:
        """See the module docstring's "Peg-board length realization"
        section. A no-op for any target type not listed there.

        :param in_progress: Explicit override for this one call. Every
            per-frame call from ``__call__`` leaves this ``None``,
            deriving it from whether a gesture is currently open (cheap,
            count-preserving while this drag's own gesture is still
            open). ``delete()``'s own final call passes ``False``
            explicitly to force the real, count-correcting reconcile
            exactly once, while the gesture is still open so it still
            batches into the same flush as everything else.
        """
        target = self.target
        mainframe = self.canvas.mainframe
        ptables = mainframe.project.ptables

        if in_progress is None:
            in_progress = ptables.gesture_depth > 0

        if target.is_bundle_layout:
            layout_point_id = target.db_obj.position3d_id

            for bundle_db_obj in target.db_obj.attached_bundles:
                _rope_pull_handler.realize_length_change(
                    mainframe, bundle_db_obj, in_progress=in_progress)

                # This waypoint moving changes the bundle's own SHAPE, not
                # just its length -- if it's the waypoint nearest an end
                # (first/last in the bundle's own list), that end's own
                # outward tangent can have changed too, so any guard
                # there needs repositioning, not just translating (user,
                # 2026-10-10: bundle waypoint drags are one of the cases
                # that change a stub's direction, not only its position).
                waypoints = bundle_db_obj.waypoints3d
                if waypoints:
                    if waypoints[0].db_id == layout_point_id:
                        _wire_routing_handler.reposition_guards_for_bundle_end(
                            ptables, bundle_db_obj, bundle_db_obj.start_position3d, '3d')
                    if waypoints[-1].db_id == layout_point_id:
                        _wire_routing_handler.reposition_guards_for_bundle_end(
                            ptables, bundle_db_obj, bundle_db_obj.stop_position3d, '3d')
            return

        if target.is_wire_layout:
            for wire_db_obj in target.db_obj.attached_wires:
                _rope_pull_handler.realize_length_change(
                    mainframe, wire_db_obj, in_progress=in_progress)
            return

        if target.is_housing:
            point_ids = [target.db_obj.position3d_id]
        elif target.is_transition:
            point_ids = []
            for branch in target.db_obj.branches:
                point_id = branch.position3d_id
                point_ids.append(point_id)

                # A branch moves rigidly with its own transition, but a
                # bundle plugged into it is anchored ONLY at this one
                # point -- the rest of the bundle (and its guard at the
                # OTHER end) does not move with the transition, so this
                # end's own outward tangent can change even though the
                # far end's does not (user, 2026-10-10: the bundle's own
                # end points being draggable -- via whatever moves
                # them, here a dragged transition -- is the other case
                # that needs a guard reposition, not just a translation).
                if point_id is None:
                    continue

                bundle_db_obj = branch.bundle
                if bundle_db_obj is None:
                    continue

                is_start = bundle_db_obj.start_position3d_id == point_id
                end_position = (
                    bundle_db_obj.start_position3d if is_start else bundle_db_obj.stop_position3d)
                _wire_routing_handler.reposition_guards_for_bundle_end(
                    ptables, bundle_db_obj, end_position, '3d')
        elif target.is_splice or target.is_wire_service_loop:
            point_ids = [target.db_obj.start_position3d_id, target.db_obj.stop_position3d_id]
        else:
            return

        _rope_pull_handler.realize_3d_move(
            mainframe, [point_id for point_id in point_ids if point_id is not None],
            in_progress=in_progress)
