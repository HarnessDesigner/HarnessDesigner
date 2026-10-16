# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""A per-wire safety net for peg-board/3D slack and rope-pull reconcile.

Every existing trigger for ``rope_pull_handler.realize_length_change``
(``drag_handlers.editor_3d.generic.Generic._realize_pegboard_length``,
``resolve_rigid_move``, and so on) is an explicit call made by whichever
drag handler happens to be moving a point that matters to a wire. Each
one of those has to correctly enumerate every point that could matter --
confirmed live, 2026-10-12, that at least one of them (a housing drag)
didn't, letting a wire stretch straight past its real length with
nothing ever pulling back.

:class:`WireSlackHandler` closes that gap from the other direction: one
instance is owned by each ``objects.wire.Wire`` facade, and it binds its
own callback directly onto every one of that wire's own points, in both
views, so ANY move of ANY of them -- however it happens, from wherever,
enumerated by the mover or not -- re-runs this wire's own reconcile. It
is a supplement to the existing explicit call sites, not a replacement
for them: a bound callback only ever fires AFTER a point has already
moved, so it can reshape this wire's own interior/slack to match, but it
can never retroactively stop an anchor from having been dragged too far
in the first place -- that still has to be prevented at the mover's own
call site (see ``drag_handlers.editor_pegboard.generic.Generic.__init__``'s
own ``_point_starts`` enumeration for exactly this kind of fix).
"""

from typing import TYPE_CHECKING

import weakref

from . import rope_pull_handler as _rope_pull_handler
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..objects import wire as _wire_obj


class WireSlackHandler:
    """Binds this handler's own callbacks onto every one of a wire's
    start/stop/waypoint points, in both the 3D and peg-board views --
    see the module docstring.

    Holds no reference to any ``Point``: each ``Point.bind()`` call
    stores only a weak reference back to this handler's own bound
    method, so a point dropped from the route (replaced, deleted)
    simply stops mattering on its own -- nothing here ever needs to
    unbind. This handler's own lifetime is tied to whatever holds IT
    (the owning ``Wire`` facade, as a plain attribute); once that's
    gone, every one of those weak references dies too, and the
    bindings quietly stop firing.
    """

    # Shared by EVERY instance -- deliberately a class attribute, not
    # set per-instance in __init__ -- see _reconcile's own comment on
    # why a guard scoped to just one wire isn't enough to stop a
    # housing move from recursing through several different wires'
    # own handlers, each nested inside the last.
    _reconciling_any = False

    @_check_types.do
    def __init__(self, wire: "_wire_obj.Wire") -> None:
        self._wire = wire

        # What register_3d()/register_pegboard() bound LAST time, as weak
        # refs -- not strong refs, so this still holds no Point reference
        # (see the class docstring) -- purely so the next call can unbind
        # from exactly those points before rebinding the current set. A
        # point that's gone (dropped from the route, GC'd) just yields a
        # dead ref, skipped on unbind.
        self._bound_3d_refs: list[weakref.ref] = []
        self._bound_pegboard_refs: list[weakref.ref] = []

        self.register_3d()
        self.register_pegboard()

    @staticmethod
    @_check_types.do
    def _rebind(refs: list[weakref.ref], points: list, callback) -> list[weakref.ref]:  # NOQA -- points/callback: no clean static type here
        """Unbind *callback* from whatever *refs* points to, then bind it
        to every one of *points*, returning the new tracked ref list.

        Mirrors ``objects_3d.wire.Wire._bind_waypoints``'s own
        unbind-then-rebind idiom. Without the unbind half, re-registering
        on every call (this runs on every ``refresh_waypoints()``,
        including a bare mid-drag reposition that never actually adds or
        removes a waypoint -- see ``rope_pull_handler._apply_mid_drag``)
        piles up one extra duplicate binding per call on whichever points
        stay the same across calls (start/stop, almost always) -- confirmed
        live, 2026-10-13: a drag with only two wires went "amazingly slow"
        and visibly corrupted point positions, both symptoms of this same
        unbounded per-point callback-list growth (each one still only
        fires once per update thanks to ``CallbackMixin``'s own dedup, but
        the list it has to scan to find that out keeps growing every
        single frame of the drag).
        """
        for ref in refs:
            point = ref()
            if point is not None:
                point.unbind(callback)

        for point in points:
            point.bind(callback)

        return [weakref.ref(point) for point in points]

    @_check_types.do
    def register_3d(self) -> None:
        """(Re-)bind to the wire's current 3D start/stop/waypoints.

        Safe to call again after the waypoint list changes -- unbinds
        from whatever was bound last time first (see :meth:`_rebind`), so
        a point no longer part of the route stops mattering immediately
        rather than accumulating a stale binding. Called from
        ``objects_3d.wire.Wire.refresh_waypoints``, the same place that
        already re-binds that view's own ``_update_position`` callback
        whenever the route changes.
        """
        obj3d = self._wire.obj3d
        points = [obj3d.start_position, obj3d.stop_position]
        points.extend(waypoint.point for waypoint in self._wire.db_obj.waypoints3d)

        self._bound_3d_refs = self._rebind(self._bound_3d_refs, points, self._on_3d_changed)

    @_check_types.do
    def register_pegboard(self) -> None:
        """Peg-board mirror of :meth:`register_3d` -- called from
        ``objects_pegboard.wire.Wire.refresh_waypoints``.
        """
        objpegboard = self._wire.objpegboard
        points = [objpegboard.start_position, objpegboard.stop_position]
        points.extend(waypoint.point for waypoint in self._wire.db_obj.waypoints_pegboard)

        self._bound_pegboard_refs = self._rebind(
            self._bound_pegboard_refs, points, self._on_pegboard_changed)

    @_check_types.do
    def unregister_pegboard(self) -> None:
        """Unbind from every currently-tracked peg-board point, with no
        rebind -- see :meth:`_reconcile`'s own use of this, right
        before it runs the calculation that repositions those same
        points.
        """
        for ref in self._bound_pegboard_refs:
            point = ref()
            if point is not None:
                point.unbind(self._on_pegboard_changed)

        self._bound_pegboard_refs = []

    @_check_types.do
    def _on_3d_changed(self, point) -> None:  # NOQA -- point unused, Point.bind's own callback contract
        self._reconcile()

    @_check_types.do
    def _on_pegboard_changed(self, point) -> None:  # NOQA -- point unused
        self._reconcile()

    @_check_types.do
    def _reconcile(self) -> None:
        """Re-run this wire's own slack/rope-pull reconcile.

        Guarded against re-entry by :attr:`_reconciling_any` -- shared
        by every ``WireSlackHandler`` instance, not just this wire's
        own, because a per-wire guard alone isn't enough: a housing
        move cascades through several DIFFERENT wires' own points
        (``PJTHousing._update_position_pegboard`` touches a seated
        terminal's attach point, its own wire-stub point, and its
        cavity's wire-stub point for every terminal on that housing,
        each a separate ``Point.bind()`` callback), and the rope-pull
        cascade this triggers (``_node_for_point``'s own Housing
        recognition) can ALSO reposition another wire's own waypoints
        while reconciling THIS one. That second wire's own handler
        then fires too -- a per-wire-only guard would wave it through
        (it's a different wire, its OWN flag is still ``False``),
        nesting a second, third, sometimes more full reconcile calls
        on top of the first, all still on the same call stack. One of
        those wires' own geometry recalculation along the way
        (``objects_pegboard.wire.Wire._recalculate_geometry`` ->
        ``_ensure_stripe_capacity``) creates/resizes a real GL VBO --
        confirmed live, 2026-10-14: nested three deep this way, that
        VBO creation came back ``GLError 1282 invalid operation``,
        since OpenGL's own per-context state (bound buffer, pending
        error flag) was never designed to tolerate being mutated
        reentrantly like that. Skipping a nested call for a different
        wire here does not leave it incorrectly un-reconciled: the
        SAME cascade that moved its points in the first place already
        reconciles it for real, through ``rope_pull_handler``'s own
        ``_evaluate_points``/``_commit_points`` entries for that wire's
        own chain -- this handler firing on top of that is always a
        redundant safety-net call, never the only place it happens.

        ``realize_length_change`` ALSO repositions this same wire's
        own peg-board waypoints one at a time
        (``rope_pull_handler._reconcile_interior``/``_apply_mid_drag``),
        which is why peg-board points are unbound first
        (:meth:`unregister_pegboard`) rather than relying on the guard
        alone -- nothing those repositions touch can reach ANY
        handler's ``_on_pegboard_changed`` while they're unbound,
        re-registered in ``finally`` so a raised exception can't leave
        this wire permanently unbound. Only the peg-board side needs
        this: this calculation never touches a 3D point (peg-board
        only, see the module docstring), so there is nothing to unbind
        there.

        ``in_progress`` mirrors every other drag-frame call into this
        same machinery (see ``realize_length_change``'s own docstring):
        while a gesture is open, this only repositions -- it never
        creates/destroys a real ``WireLayout`` on every single frame a
        point happens to move.
        """
        # A commit (rope_pull_handler._commit_points) already reconciles
        # every chain its own cascade touched, and the points it moves
        # fire this very callback synchronously -- re-entering here ran a
        # second _apply_mid_drag on the SAME overlay/offline store while
        # the outer one was mid-loop, corrupting the far-end stub entries
        # of a wire attached at both ends. See rope_pull_handler.
        # is_committing(). The class-level flag alone only covers a
        # reconcile started by this handler, not one started by a drag or
        # 3D call site.
        if WireSlackHandler._reconciling_any or _rope_pull_handler.is_committing():
            return

        WireSlackHandler._reconciling_any = True
        try:
            self.unregister_pegboard()

            mainframe = self._wire.mainframe
            in_progress = mainframe.project.ptables.gesture_depth > 0
            _rope_pull_handler.realize_length_change(
                mainframe, self._wire.db_obj, in_progress=in_progress)
        finally:
            self.register_pegboard()
            WireSlackHandler._reconciling_any = False
