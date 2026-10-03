# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Skeleton-first bundle placement for the 3D editor -- BUNDLE_PLACEMENT.md
section 3, replacing the old wire-snapping flow entirely (a bundle no
longer spans an existing wire end to end; it is placed free, in empty
space or attached to transition branches, and starts empty -- wires are
routed onto it afterwards, once wire routing exists).

One state machine, mirroring ``add_handlers.editor_3d.wire.Wire`` (named
in the design doc as "the model to follow"), simplified for bundles'
narrower snap surface (only transition branches, never terminals/
splices/other bundles/wire layouts):

- **Phase 0** (placing the START point): the growing point is
  ``target.obj3d.start_position``. Hover free-follows the camera focal
  plane, or -- when a real ray-sphere hit lands on a FREE transition
  branch (``handlers.transition_handler._find_free_branch_ray``) --
  snaps onto that branch's own tip and highlights it green/orange by
  diameter fit. A left click on empty space (or a fitting branch) locks
  the start there and moves to phase 1; a click on a non-fitting branch
  is ignored (stays in phase 0).
- **Phase 1** (growing the STOP point, one section at a time): the
  growing point is ``target.obj3d.stop_position``. A left click on empty
  space commits the current point as an interior waypoint (a
  ``BundleLayout``, exactly the mechanics ``handlers.
  bundle_layout_handler._create_bundle_layout_on_bundle`` already uses
  for "Add Handle") and keeps growing; a left click on a fitting free
  branch attaches the bundle there and ENDS the placement; a right click
  either cancels outright (no waypoint committed yet -- section 3:
  "Right click after only the first click: the whole placement is
  canceled") or removes the last committed waypoint and promotes its
  point to be the bundle's free end (one or more waypoints already
  committed -- "the last layout is removed and its point becomes the
  bundle's END point").

Diameter-range narrowing (section 3's initial-diameter rule, generalized
to both ends per the section's own OPEN suggestion): a session tracks
``(_diameter_lo, _diameter_hi)`` starting at the cover part's own
``(min_dia, max_dia)``; each branch attach raises the lower bound to
that branch's own minimum and tightens the upper bound to its maximum,
so a second branch attach is only offered (highlighted green) when it
still overlaps whatever the first attach already narrowed the range to.
The final diameter is always ``_diameter_lo`` -- ``part.min_dia`` if
neither end ever attaches (section 3: "free click = the bundle's
minimum diameter"), otherwise the largest minimum of every branch
attached. Every attached branch's own diameter is raised to match (the
bundle and every branch it touches always agree), and a ``BundleLayout``
marker is dropped exactly on the shared joint point so it renders like a
real fitting there -- its own diameter/color derive automatically from
the bundle (``PJTBundleLayout.attached_bundles``).

Peg-board seeding (section 10's implementation-order item 1, "with
peg-board start/stop seeded") happens once, at the very end of a
successful placement -- see :func:`_seed_pegboard`'s own docstring for
the length-preserving unfold and its one known gap (the peg-board chain
solver, section 6b, that will eventually absorb the length mismatch a
BOTH-ends-pinned bundle can produce, is not built yet).
"""

from typing import TYPE_CHECKING, Union as _Union

import numpy as np

from ...gl.canvas_base import interaction as _interaction
from ...gl import object_picker as _object_picker
from ...geometry import point as _point
from ...handlers import transition_handler as _transition_handler
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ... import objects as _objects
    from ...objects import transition as _transition_obj
    from ...objects.objects_3d import transition as _transition_3d
    from ...objects import bundle_layout as _bundle_layout_facade


@_check_types.do
def drop_joint_layout(
    mainframe, branch: "_transition_3d.Branch"
) -> "_bundle_layout_facade.BundleLayout":
    """
    Create a ``BundleLayout`` marker exactly on *branch*'s own shared
    point -- used at every branch attach (phase 0's start attach, phase
    1's end attach, and :meth:`objects.objects_3d.bundle.Bundle.
    start_add_from_branch`'s own pre-attached start, all three going
    through this one function so they can't drift apart). Its own
    diameter/color derive automatically from whatever bundle now sits on
    that same point the moment it's constructed (``PJTBundleLayout.
    attached_bundles`` / ``objects_3d.bundle_layout.BundleLayout.
    __init__``) -- no separate diameter/color plumbing needed here.
    """

    from ...objects import bundle_layout as _bundle_layout

    ptables = mainframe.project.ptables
    layout_db = ptables.pjt_bundle_layouts_table.insert(point3d_id=branch.db_obj.position3d_id)
    layout = _bundle_layout.BundleLayout(mainframe, layout_db)
    mainframe.project.add_bundle_layout(layout)

    return layout


class Bundle(_base.AddHandlerBase):
    """
    Skeleton-first bundle placement session -- see the module
    docstring.
    """

    @_check_types.do
    def __init__(
        self,
        canvas: "_canvas.Canvas",
        target: "_objects.ObjectBase",
        part,
        phase: int,
        diameter_lo: float,
        diameter_hi: float,
        start_branch: tuple | None = None,
        start_branch_orig_diameter: float | None = None,
        start_layout: "_bundle_layout_facade.BundleLayout | None" = None
    ):
        super().__init__(canvas, target)

        self.mainframe = canvas.mainframe
        self.camera = canvas.camera
        self.ptables = self.mainframe.project.ptables

        self._part = part
        self._phase = phase
        self._diameter_lo = diameter_lo
        self._diameter_hi = diameter_hi

        # (transition_facade, Branch) once an end has attached -- start
        # can be pre-populated by start_add_from_branch (phase starts at
        # 1 directly, skipping phase 0 entirely); stop is only ever set
        # by this session's own _finish_attached.
        self._start_branch = start_branch
        self._start_branch_orig_diameter = start_branch_orig_diameter
        self._start_layout = start_layout
        self._stop_branch = None

        self._hovered_branch = None
        self._committed_layouts = []
        self._has_committed_waypoint = False
        self._session_waypoint_count = 0
        self._finalized = False

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    @_check_types.do
    def __call__(
        self,
        last_pos,
        current_pos,
        had_motion: bool,
        interaction_type: _interaction.MouseInteraction, clicked_object
    ) -> bool:
        if self._finalized:
            return False

        if interaction_type is _interaction.MouseInteraction.CANCEL:
            self.cancel()
            self._finalized = True
            return True

        if interaction_type is _interaction.MouseInteraction.MOVE:
            self.hover(current_pos)
            return True

        if not had_motion:
            if interaction_type is _interaction.MouseInteraction.LEFT_UP:
                if self._phase == 0:
                    self._handle_first_click(current_pos)
                else:
                    self._handle_later_click(current_pos)

                return True

            if interaction_type is _interaction.MouseInteraction.RIGHT_UP:
                self.finalize_at_last_point()
                return True

        return False

    # ------------------------------------------------------------------
    # Growing-end plumbing -- 'start' during phase 0, 'stop' from phase 1
    # on (a bundle, unlike a wire, never grows from its own stop end).
    # ------------------------------------------------------------------

    @property
    @_check_types.do
    def _growing_point(self) -> _point.Point:
        if self._phase == 0:
            return self.target.obj3d.start_position

        return self.target.obj3d.stop_position

    @_check_types.do
    def _set_growing_position3d_id(self, point_id: bytes) -> None:
        if self._phase == 0:
            self.target.db_obj.start_position3d_id = point_id
        else:
            self.target.db_obj.stop_position3d_id = point_id

    @_check_types.do
    def _set_growing_obj3d_position(self, point: _point.Point) -> None:
        if self._phase == 0:
            self.target.obj3d.set_start_position(point)
        else:
            self.target.obj3d.set_stop_position(point)

    @_check_types.do
    def _move_growing_point(self, position) -> None:
        if not isinstance(position, _point.Point):
            position = _point.Point(*position)

        growing = self._growing_point
        growing += position - growing

    @_check_types.do
    def _apply_diameter(self, diameter: float) -> None:
        self.target.obj3d._diameter = diameter  # NOQA
        self.target.obj3d.scale.x = diameter
        self.target.obj3d.scale.y = diameter

        # The peg-board Bundle view is built the moment the facade is
        # constructed (start_add/start_add_from_branch), seeded from the
        # SAME part.min_dia the 3D side starts at -- but nothing else ever
        # touches it afterward, so without this it stays pinned at that
        # original value forever while obj3d above tracks every branch
        # attach's narrowing. Peg-board layouts don't have this problem
        # (they're only created in _seed_pegboard, at the very end, after
        # narrowing is already final) -- only the bundle's own peg-board
        # cylinder does.
        self.target.objpegboard._diameter = diameter  # NOQA
        self.target.objpegboard.scale.x = diameter
        self.target.objpegboard.scale.y = diameter

    # ------------------------------------------------------------------
    # Hover
    # ------------------------------------------------------------------

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
        with self.mainframe.editor3d.context:
            if self._start_branch is not None:
                exclude_transition = self._start_branch[0]
            else:
                exclude_transition = None

            origin, direc = _object_picker._build_ray(mouse_pos, self.camera)  # NOQA
            hit = None
            if origin is not None:
                hit = _transition_handler._find_free_branch_ray(  # NOQA
                    origin, direc, self.mainframe.project,
                    exclude_transition=exclude_transition)

            if hit is not None:
                t_obj, branch = hit

                if hit != self._hovered_branch:
                    self._clear_branch_hover()
                    fits = self._branch_fits(branch)

                    if fits:
                        mat = _transition_handler._BRANCH_FIT   # NOQA
                    else:
                        mat = _transition_handler._BRANCH_NO_FIT  # NOQA

                    t_obj.obj3d.highlight_branch(branch, mat)  # NOQA
                    self._hovered_branch = hit

                self._move_growing_point(branch.tip_point)
            else:
                self._clear_branch_hover()
                self._move_growing_point(
                    self.camera.get_position_on_focal_plane(mouse_pos))

            self.target.obj3d.is_visible = True

    @_check_types.do
    def _clear_branch_hover(self) -> None:
        if self._hovered_branch is not None:
            t_obj, branch = self._hovered_branch
            t_obj.obj3d.clear_branch_highlight(branch)
            self._hovered_branch = None

    @_check_types.do
    def _branch_fits(self, branch: "_transition_3d.Branch") -> bool:
        return (self._diameter_lo <= branch.max_diameter and
                self._diameter_hi >= branch.min_diameter)

    # ------------------------------------------------------------------
    # Clicks
    # ------------------------------------------------------------------

    @_check_types.do
    def _handle_first_click(self, mouse_pos: _point.Point | None) -> None:  # NOQA
        """
        Lock the start point wherever hover last left it (free, or a
        fitting branch's own tip) and move on to phase 1. A click while
        hovering a NON-fitting branch is ignored -- stays in phase 0.

        *mouse_pos* is unused -- everything this needs was already
        decided by the last :meth:`hover` call (``self._hovered_branch``)
        -- which is exactly why ``objects_3d.bundle.Bundle.
        start_add_from_branch`` can call this directly with ``None`` to
        replay a synthetic "click" on a branch it already knows about,
        reusing this method's own real attach path instead of a second
        copy of it.
        """

        if self._hovered_branch is not None:
            t_obj, branch = self._hovered_branch

            if not self._branch_fits(branch):
                return

            self._start_branch_orig_diameter = branch.diameter
            self._attach_growing_end_to_branch(branch)
            t_obj.add_bundle(self.target, 'start', branch.db_obj.branch_id)
            self._start_branch = (t_obj, branch)
            self._narrow_diameter_range(branch)
            self._start_layout = drop_joint_layout(self.mainframe, branch)

        self._clear_branch_hover()
        self._phase = 1

    @_check_types.do
    def _handle_later_click(self, mouse_pos: _point.Point) -> None:  # NOQA
        """
        A click on a fitting free branch attaches the stop end there
        and ends the whole placement; any other click (empty space, or a
        non-fitting branch, ignored the same way phase 0 ignores one)
        commits the current growing point as an interior waypoint and
        keeps the session going.
        """

        if self._hovered_branch is not None:
            t_obj, branch = self._hovered_branch

            if self._branch_fits(branch):
                self._finish_attached(t_obj, branch)

            return

        self._commit_waypoint()

    @_check_types.do
    def _attach_growing_end_to_branch(
        self,
        branch: "_transition_3d.Branch"
    ) -> None:

        stale_id = self._growing_point.db_id[:-2]

        self._set_growing_obj3d_position(branch.db_obj.position3d)
        self._set_growing_position3d_id(branch.db_obj.position3d_id)

        self.ptables.pjt_points3d_table[stale_id].delete()

    @_check_types.do
    def _narrow_diameter_range(self, branch: "_transition_3d.Branch") -> None:
        self._diameter_lo = max(self._diameter_lo, branch.min_diameter)
        self._diameter_hi = min(self._diameter_hi, branch.max_diameter)
        self._apply_diameter(self._diameter_lo)

        branch.set_diameter(self._diameter_lo)
        if self._start_branch is not None:
            self._start_branch[1].set_diameter(self._diameter_lo)

        # Every layout dropped/committed so far was built reading the
        # bundle's diameter AT THAT MOMENT (objects_3d.bundle_layout.
        # BundleLayout.__init__ caches it once, from PJTBundleLayout.
        # attached_bundles) -- a later attach that narrows the range
        # further (e.g. the stop end snapping to a branch with a smaller
        # max_diameter than the start end already settled on) would
        # otherwise leave every earlier layout showing the bundle's OLD,
        # now-stale diameter forever. Refresh them all to the new value.
        if self._start_layout is not None:
            self._start_layout.obj3d.set_diameter(self._diameter_lo)

        for layout_obj in self._committed_layouts:
            layout_obj.obj3d.set_diameter(self._diameter_lo)

    @_check_types.do
    def _finish_attached(
        self,
        t_obj: "_transition_obj.Transition",
        branch: "_transition_3d.Branch"
    ) -> None:

        self._attach_growing_end_to_branch(branch)
        t_obj.add_bundle(self.target, 'stop', branch.db_obj.branch_id)
        self._stop_branch = (t_obj, branch)
        self._narrow_diameter_range(branch)
        drop_joint_layout(self.mainframe, branch)

        self._finish_common()

    # ------------------------------------------------------------------
    # Waypoint commit
    # ------------------------------------------------------------------

    @_check_types.do
    def _commit_waypoint(self) -> None:
        from ...objects import bundle_layout as _bundle_layout

        self._has_committed_waypoint = True

        growing_point_id = self._growing_point.db_id[:-2]
        growing_pos = self._growing_point

        bundle_id = self.target.db_obj.db_id

        self.ptables.pjt_bundle_paths_table.append(
            bundle_id, '3d', growing_point_id)

        layout_db = self.ptables.pjt_bundle_layouts_table.insert(
            point3d_id=growing_point_id)

        layout_obj = _bundle_layout.BundleLayout(self.mainframe, layout_db)
        self.mainframe.project.add_bundle_layout(layout_obj)
        self._committed_layouts.append(layout_obj)
        self._session_waypoint_count += 1

        new_point_db = self.ptables.pjt_points3d_table.insert(
            float(growing_pos.x), float(growing_pos.y), float(growing_pos.z))

        self._set_growing_position3d_id(new_point_db.db_id)
        self._set_growing_obj3d_position(new_point_db.point)
        self.target.obj3d.refresh_waypoints()

    # ------------------------------------------------------------------
    # Finishing early / cancellation
    # ------------------------------------------------------------------

    @_check_types.do
    def finalize_at_last_point(self) -> None:
        if self._finalized or self._phase == 0:
            return

        if not self._has_committed_waypoint:
            self.cancel()
            self._finalized = True
            return

        self._promote_last_committed()
        self._finish_common()

    @_check_types.do
    def _promote_last_committed(self) -> None:
        stale_id = self._growing_point.db_id[:-2]

        last_waypoint = self.target.db_obj.waypoints3d[-1]
        last_point = last_waypoint.point

        self.ptables.pjt_bundle_paths_table.remove(
            self.target.db_obj.db_id, '3d', last_waypoint.db_id)

        self._set_growing_obj3d_position(last_point)
        self._set_growing_position3d_id(last_waypoint.db_id)

        self.ptables.pjt_points3d_table[stale_id].delete()

        self._session_waypoint_count -= 1

        if self._committed_layouts:
            last_layout = self._committed_layouts.pop()
            last_layout.delete()

        self.target.obj3d.refresh_waypoints()

    @_check_types.do
    def _finish_common(self) -> None:
        self._clear_branch_hover()
        self.target.identify(None)
        self._seed_pegboard()
        self.mainframe.project.add_bundle(self.target)
        self._finalized = True

    @_check_types.do
    def cancel(self) -> None:
        self._clear_branch_hover()

        for layout_obj in reversed(self._committed_layouts):
            layout_obj.delete()

        self._committed_layouts = []

        if self._start_branch is not None:
            _t_obj, branch = self._start_branch
            branch.set_diameter(self._start_branch_orig_diameter)

            if self._start_layout is not None:
                self._start_layout.delete()

            self._start_branch = None

        if self.target is not None:
            self.target.delete()
            self.target = None

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self.cancel()
            self._finalized = True

    # ------------------------------------------------------------------
    # Peg-board seeding
    # ------------------------------------------------------------------

    @_check_types.do
    def _drop_joint_layout_pegboard(
        self,
        branch: "_transition_3d.Branch"
    ) -> None:

        """
        Peg-board counterpart of :func:`drop_joint_layout` -- a branch
        attach needs its own marker in EACH view (a ``BundleLayout`` row
        is exclusive to one view, section 2.5), so the 3D joint layout
        created by :func:`drop_joint_layout` does not cover the peg-board
        side at all; this drops the peg-board one, at the branch's own
        peg-board position, from :meth:`_seed_pegboard`.
        """

        from ...objects import bundle_layout as _bundle_layout

        layout_db = self.ptables.pjt_bundle_layouts_table.insert(
            point_pegboard_id=branch.db_obj.position_pegboard_id)

        layout_facade = _bundle_layout.BundleLayout(self.mainframe, layout_db)
        self.mainframe.project.add_bundle_layout(layout_facade)

    @_check_types.do
    def _seed_pegboard(self) -> None:
        """
        Give the freshly placed bundle a non-degenerate peg-board
        presence (BUNDLE_PLACEMENT.md section 10 item 1) by unfolding its
        3D path into the peg-board plane: walk from the peg-board start,
        stepping each 3D segment's own REAL length along that segment's
        own X/Z-projected direction (a vertical segment reuses the
        previous segment's own direction, or +X for the very first) --
        one new peg-board waypoint per interior 3D waypoint, seeded 1:1
        at creation time (section 6 item 1: "the peg-board waypoints are
        its own" -- they only need to start out matching, not stay that
        way). Each interior waypoint and each branch attach also gets its
        own peg-board ``BundleLayout`` marker (a row is exclusive to one
        view, so these are separate rows from the 3D joint layouts
        :func:`drop_joint_layout` already drops -- see
        :meth:`_drop_joint_layout_pegboard`), matching the same diameter/
        color the bundle's 3D layouts get.

        This keeps the peg-board bundle's total length EXACTLY equal to
        the 3D one whenever at most one end is pinned to a branch (the
        free/free and free/branch cases: the walk's own final point IS
        the peg-board stop, by construction). When BOTH ends are pinned,
        the peg-board stop is instead forced onto the stop branch's own
        already-fixed peg-board position (section 6 question 7: "in
        peg-board the two ends are then moved to coincide") regardless of
        where the walk itself lands -- the resulting length mismatch is
        real and NOT corrected here. Absorbing it (bowing a waypoint, or
        adding one) is the peg-board chain solver's own job
        (BUNDLE_PLACEMENT.md section 6b), not yet built.

        The bundle's own peg-board start/stop points already exist by
        the time this runs -- ``objects_pegboard.bundle.Bundle.__init__``
        (built the moment the facade was constructed, back in
        ``objects_3d.bundle.Bundle.start_add``/``start_add_from_branch``)
        reads ``db_obj.start/stop_position_pegboard``, and that mixin
        lazily creates a (0, 0, 0) row the first time it's ever read, same
        as the 3D mixin does. So the free case MOVES that existing point
        in place (``+=``, which also persists it -- never creates a
        second row the first is then abandoned next to), and the
        branch-attach case SWAPS to the branch's own point the same way
        the 3D attach does (``set_start/stop_position`` + deleting the
        now-stale lazy one).
        """

        ptables = self.ptables
        db = self.target.db_obj
        obj_peg = self.target.objpegboard

        if self._start_branch is not None:
            stale_id = obj_peg.start_position.db_id[:-2]
            branch = self._start_branch[1]
            obj_peg.set_start_position(branch.db_obj.position_pegboard)
            db.start_position_pegboard_id = branch.db_obj.position_pegboard_id
            ptables.pjt_points_pegboard_table[stale_id].delete()
            self._drop_joint_layout_pegboard(branch)
        else:
            p = db.start_position3d
            start_pos = obj_peg.start_position
            start_pos += _point.Point(float(p.x), 0.0, float(p.z)) - start_pos

        points3d = [db.start_position3d,
                    *(w.point for w in db.waypoints3d),
                    db.stop_position3d]

        start_peg = obj_peg.start_position
        current_np = np.array(
            [float(start_peg.x), 0.0, float(start_peg.z)], dtype=np.float64)

        prev_dir = np.array([1.0, 0.0], dtype=np.float64)

        walked_points = []
        for a, b in zip(points3d[:-1], points3d[1:]):
            seg = b.as_numpy - a.as_numpy
            length = float(np.linalg.norm(seg))
            if length < 1e-9:
                continue

            planar = np.array([seg[0], seg[2]], dtype=np.float64)
            planar_len = float(np.linalg.norm(planar))
            if planar_len > 1e-9:
                direction = planar / planar_len
                prev_dir = direction
            else:
                direction = prev_dir

            current_np = current_np + np.array(
                [direction[0] * length, 0.0, direction[1] * length],
                dtype=np.float64)

            walked_points.append(current_np.copy())

        walked_stop_np = walked_points.pop() if walked_points else current_np

        from ...objects import bundle_layout as _bundle_layout

        for pos_np in walked_points:
            peg = ptables.pjt_points_pegboard_table.insert(
                float(pos_np[0]), 0.0, float(pos_np[2]))

            ptables.pjt_bundle_paths_table.append(
                db.db_id, 'pegboard', peg.db_id)

            layout_db = ptables.pjt_bundle_layouts_table.insert(
                point_pegboard_id=peg.db_id)

            layout_facade = _bundle_layout.BundleLayout(
                self.mainframe, layout_db)

            self.mainframe.project.add_bundle_layout(layout_facade)

        if self._stop_branch is not None:
            stale_id = obj_peg.stop_position.db_id[:-2]
            branch = self._stop_branch[1]
            obj_peg.set_stop_position(branch.db_obj.position_pegboard)
            db.stop_position_pegboard_id = branch.db_obj.position_pegboard_id
            ptables.pjt_points_pegboard_table[stale_id].delete()
            self._drop_joint_layout_pegboard(branch)
        else:
            stop_pos = obj_peg.stop_position
            target_pos = _point.Point(float(walked_stop_np[0]), 0.0, float(walked_stop_np[2]))
            stop_pos += target_pos - stop_pos

        self.target.objpegboard.refresh_waypoints()
