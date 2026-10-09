# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Transition placement for the 3D editor -- rewritten (2026-09-27) to
match `BUNDLE_PLACEMENT.md` section 4's decided design, replacing the
previous bundle-snap-only implementation (which `BUNDLE_PLACEMENT.md`
section 8 already called out for full replacement, and which in fact
crashed the moment it actually found a bundle -- it called a
``utils.get_closest_point_on_wire_endpoint`` function that has never
existed anywhere in this codebase).

Two placement modes, decided in section 4:

- **Free placement** -- the transition follows the mouse (on the
  camera's focal plane) and is always visible; a click commits it at the
  current position/angle, with every branch left free (no bundle
  attached) and its peg-board position seeded from the 3D one
  (``objects_pegboard.transition.Transition.__init__``'s own existing
  x/z-projection seed already does this automatically, the same way a
  housing's does).
- **Snapped to a bundle's free end** -- found by ``handlers.
  transition_handler._find_free_bundle_end`` (an ENDPOINT only, never a
  mid-span point -- section 4's "no mid-bundle placement" rule; the old
  mid-bundle-split-on-commit code this replaces is gone entirely, since
  there is no longer a mid-span case to handle). Every branch is shown
  (the transition is positioned at the bundle end, all six/however-many
  branches visible); hovering over a specific branch (2026-09-28: a real
  ray-sphere test, ``Transition.hit_test_branch_ray``, against each
  branch's own end position/diameter -- branches are no longer separate
  pickable ``Base3D`` objects the generic canvas picker can resolve to,
  see ``objects_3d.transition``'s own module docstring) highlights it
  green/orange by diameter fit (``Transition.branch_fits``/
  ``highlight_branch``, reusing ``handlers.transition_handler.
  RouteThroughTransitionHandler._diameter_of`` and the
  ``BRANCH_FIT``/``BRANCH_NO_FIT`` materials already defined there).
  Clicking while a branch is highlighted (and
  fits) commits: the chosen branch's own position becomes the SAME point
  row as the bundle's end (section 5's "the bundle's start/stop point and
  the branch's position point are the same row"), rotated so that
  branch's own local direction points back along the bundle (section 4:
  "the branch's outward axis points back along the bundle, so the bundle
  runs straight into the branch mouth"), and every OTHER branch is left
  free. **No wire assignment, no per-branch concentric rows, no new wire
  rows are ever created here** -- section 4's own "PROPOSED -- All wire
  assignment is REMOVED from placement... A new transition has all
  branches free," now actually true of this code, not just the design
  doc.

Right-click (``CANCEL``) deletes the in-progress preview and aborts, same
as before.

Known simplifications, not yet resolved by this pass (see
`BUNDLE_PLACEMENT.md`'s own open questions):
- The attached branch's diameter is left at the catalog's own `min_dia`,
  same as every other (free) branch -- section 4b's own "what the branch
  diameter follows... is undecided" is still undecided; this does not
  attempt to derive it from the bundle.
- A free-space transition's default orientation is whatever
  `Transition.start_add` seeds it at (identity) -- section 4's own
  "OPEN -- Orientation of a transition placed in free space" is still
  open; the user can rotate it afterward with the existing gizmo.
"""

from typing import TYPE_CHECKING, Union as _Union

from ...gl.canvas_base import interaction as _interaction
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...objects import bundle as _bundle
from .. import base as _base
from ... import check_types as _check_types
from ...handlers import transition_handler as _transition_handler
from ...gl import object_picker as _object_picker

if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ... import objects as _objects
    from ...gl import materials as _materials
    from ...database.global_db import transition as _glb_transition
    from ...objects.objects_3d import transition as _transition_3d


class Transition(_base.AddHandlerBase):
    """
    Free or bundle-end-snapping transition placement -- see the module
    docstring.
    """

    @_check_types.do
    def __init__(
        self,
        canvas: "_canvas.Canvas",
        target: "_objects.ObjectBase",
        part_id: bytes,
        part: "_glb_transition.Transition",
        highlight_material: "_materials.GLMaterial"
    ) -> None:

        super().__init__(canvas, target)

        self.mainframe = canvas.mainframe
        self.camera = canvas.camera

        self._part_id = part_id
        self._part = part
        self._highlight_material = highlight_material
        self._snapped_bundle: _bundle.Bundle | None = None
        self._snapped_endpoint: str | None = None
        self._hovered_branch = None
        self._finalized = False

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    @_check_types.do
    def __call__(self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
                 interaction_type: _interaction.MouseInteraction,
                 clicked_object: _Union["_objects.ObjectBase", None]) -> bool:

        if self._finalized:
            return False

        if interaction_type is _interaction.MouseInteraction.CANCEL:
            self._finalized = True
            self.cancel()
            return True

        if interaction_type is _interaction.MouseInteraction.MOVE:
            self.hover(current_pos)
            return True

        if (
            interaction_type is _interaction.MouseInteraction.LEFT_UP and
            not had_motion
        ):
            self._on_click(current_pos)
            return True

        return False

    # -- hover: free-follow, or snapped-to-a-bundle-end with branch pick --

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
        bundle_end = _transition_handler._find_free_bundle_end(  # NOQA
            mouse_pos, self.camera, self.mainframe.project)

        if bundle_end is None:
            self._clear_bundle_hover()

            self._move_target_to(
                self.camera.get_position_on_focal_plane(mouse_pos))

            self.target.obj3d.is_visible = True

            return

        bundle, endpoint = bundle_end

        if bundle is not self._snapped_bundle:
            self._clear_bundle_hover()
            bundle.identify(self._highlight_material)
            self._snapped_bundle = bundle
            self._snapped_endpoint = endpoint

        if endpoint == 'start':
            end_position = bundle.obj3d.start_position
        else:
            end_position = bundle.obj3d.stop_position

        self._move_target_to(end_position)
        self.target.obj3d.is_visible = True

        # Real ray-sphere test (Transition.hit_test_branch_ray), not the
        # generic canvas object picker -- a branch is no longer its own
        # pickable Base3D object (2026-09-28), so find_object can't
        # resolve it any more; the transition itself now owns hit-
        # testing its own branches directly.
        origin, direc = _object_picker.build_ray(mouse_pos, self.camera)

        if origin is None:
            selected = None
        else:
            selected = self.target.obj3d.hit_test_branch_ray(origin, direc)

        if selected is not self._hovered_branch:
            self._clear_branch_hover()

            if selected is not None:
                diameter = _transition_handler.RouteThroughTransitionHandler._diameter_of(bundle)  # NOQA
                fits = self.target.obj3d.branch_fits(selected, diameter)

                if fits:
                    mat = _transition_handler.BRANCH_FIT
                else:
                    mat = _transition_handler.BRANCH_NO_FIT

                self.target.obj3d.highlight_branch(selected, mat)
                self._hovered_branch = selected

    @_check_types.do
    def _move_target_to(self, position: _point.Point) -> None:
        pos = self.target.obj3d.position
        pos += position - pos

    @_check_types.do
    def _clear_bundle_hover(self) -> None:
        if self._snapped_bundle is not None:
            self._snapped_bundle.identify(None)
            self._snapped_bundle = None
            self._snapped_endpoint = None

        self._clear_branch_hover()

    @_check_types.do
    def _clear_branch_hover(self) -> None:
        if self._hovered_branch is not None:
            self.target.obj3d.clear_branch_highlight(self._hovered_branch)
            self._hovered_branch = None

    # -- click: commit free, or commit attached to the hovered branch --

    @_check_types.do
    def _on_click(self, _mouse_pos: _point.Point) -> None:
        if self._snapped_bundle is None:
            self._commit_free()

            return

        if self._hovered_branch is None:
            # Snapped to a bundle end, but the user hasn't picked a
            # branch yet -- section 4: "the user then SELECTS the branch
            # they want to attach to the end." Stay in placement mode.
            return

        diameter = _transition_handler.RouteThroughTransitionHandler._diameter_of(  # NOQA
            self._snapped_bundle)

        if not self.target.obj3d.branch_fits(self._hovered_branch, diameter):
            return  # highlighted orange (no fit) -- refuse the pick, stay active

        self._commit_attached(self._snapped_bundle,
                              self._snapped_endpoint,
                              self._hovered_branch)

    @_check_types.do
    def _commit_free(self) -> None:
        """
        Place with nothing attached -- section 4's "DECIDED -- free
        placement." Every branch is free; peg-board position is seeded
        automatically from the 3D one by ``objects_pegboard.transition.
        Transition.__init__``'s own existing x/z-projection seed, the
        same as it already does for every fresh transition.
        """

        from ...objects import transition as _transition

        project = self.mainframe.project
        ptables = project.ptables

        pos = self.target.obj3d.position
        px, py, pz = float(pos.x), float(pos.y), float(pos.z)

        current_angle = self.target.obj3d.angle
        ax, ay, az = current_angle.as_euler_float

        # Set before self.target.delete(), not after -- that delete tears
        # down self.target.obj3d, which (Base3D._delete) finds its own
        # _active_handler is still this same handler and calls THIS
        # object's delete() again, re-entrantly, while we're still inside
        # this call. That delete() only cancels (deleting self.target a
        # second time, onto rows this method's own insert()s below haven't
        # even created yet) when _finalized is still False, so it has to
        # already be True before the delete below ever runs.
        self._finalized = True

        self.target.delete()
        self.target = None

        center_db = ptables.pjt_points3d_table.insert(px, py, pz)
        init_angle = _angle.Angle.from_euler(ax, ay, az)
        name = f'{self._part.manufacturer.name} {self._part.part_number}'

        transition_db = ptables.pjt_transitions_table.insert(
            self._part_id, name, center_db.db_id, init_angle)

        for branch_id in range(1, self._part.branch_count + 1):
            g_br = self._part.branches[branch_id - 1]
            pt_db = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)

            ptables.pjt_transition_branches_table.insert(
                g_br.db_id, transition_db.db_id, pt_db.db_id,
                branch_id, float(g_br.min_dia))

            # No concentric row, no wires -- section 4's "a new transition
            # has all branches free," and see TRANSITION_EDITOR_DIALOG.md
            # section 7.10 for why a transition branch needs neither at
            # all any more.

        transition_obj = _transition.Transition(self.mainframe, transition_db)
        project.add_transition(transition_obj)

    @_check_types.do
    def _commit_attached(
        self,
        bundle: _bundle.Bundle,
        endpoint: str,
        branch: "_transition_3d.Branch"
    ) -> None:

        """
        Place with the chosen branch attached to *bundle*'s free
        *endpoint* -- section 4's "DECIDED -- placement at the end of a
        bundle" and section 5's "the bundle's start/stop point and the
        branch's position point are the same row." Every OTHER branch is
        left free, same as the free-placement case.
        """

        from ...objects import transition as _transition

        project = self.mainframe.project
        ptables = project.ptables

        # branch is one of self.target.obj3d's own objects_3d.transition.
        # Branch instances (built from part.branches, one per catalog
        # idx) -- branch_id (1-based) is that PJTTransitionBranch's own
        # slot, which lines up with the catalog's own 0-based idx as
        # branch_id - 1 (now correct after fixing global_db.Transition.
        # branches' off-by-one, see TRANSITION_DESIGN.md section 6/7).
        branch_id = branch.db_obj.branch_id
        catalog_branch = self._part.branches[branch_id - 1]
        local_direction = _transition_handler._branch_local_direction(catalog_branch)  # NOQA

        if endpoint == 'start':
            end_point_id = bundle.db_obj.start_position3d_id
            end_position = bundle.obj3d.start_position
        else:
            end_point_id = bundle.db_obj.stop_position3d_id
            end_position = bundle.obj3d.stop_position

        ex, ey, ez = end_position.as_float

        bundle.identify(None)
        self._clear_branch_hover()

        # See _commit_free's own comment -- same re-entrancy, same reason
        # this has to be set before self.target.delete(), not after.
        self._finalized = True

        self.target.delete()
        self.target = None

        center_db = ptables.pjt_points3d_table.insert(ex, ey, ez)
        init_angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)
        name = f'{self._part.manufacturer.name} {self._part.part_number}'

        transition_db = ptables.pjt_transitions_table.insert(
            self._part_id, name, center_db.db_id, init_angle)

        for i in range(1, self._part.branch_count + 1):
            g_br = self._part.branches[i - 1]
            if i == branch_id:
                # Shared point -- this branch's own position row IS the
                # bundle's existing endpoint row, not a new one.
                point_id = end_point_id
            else:
                point_id = ptables.pjt_points3d_table.insert(
                    0.0, 0.0, 0.0).db_id

            ptables.pjt_transition_branches_table.insert(
                g_br.db_id, transition_db.db_id,
                point_id, i, float(g_br.min_dia))

            # No concentric row, no wires -- see _commit_free's own comment.

        _transition_handler._align_branch_to_bundle(  # NOQA
            transition_db, local_direction, bundle, endpoint)

        transition_obj = _transition.Transition(self.mainframe, transition_db)
        transition_obj.add_bundle(bundle, endpoint, branch_id)
        project.add_transition(transition_obj)

    @_check_types.do
    def cancel(self) -> None:
        self._clear_bundle_hover()

        if self.target is not None:
            self.target.delete()
            self.target = None

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self._finalized = True
            self.cancel()
