# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Wire-into-skeleton drag-and-drop UI mechanics -- BUNDLE_PLACEMENT.md
section 12. Read that section in full before touching this module. Sits
between the GL mouse-event dispatch (``drag_handlers.editor_3d/
editor_pegboard.wire_route``, ``objects.objects_3d/objects_pegboard.
wire``) and the pure routing engine (``handlers.wire_routing_handler``).

**What lives here:**

- :func:`compute_eligible_targets` -- the drag-start eligibility scan
  (every bundle free end / transition free branch the dragged wire's own
  diameter fits into, per ``handlers.bundle_diameter.wire_fits_bundle``/
  ``wire_fits_branch``).
- The two-tier highlight (:func:`highlight_eligible`/
  :func:`clear_eligible_highlights`/:func:`set_hover_highlight`) -- every
  eligible target is recolored the moment the set is computed, and
  whichever one is currently under the cursor is further brightened
  (user, 2026-10-03: "Branch/bundles that are able to fit the wire
  should be identified by changing it's color when the drag operation
  starts," then, clarifying: "once the mouse hovers over that branch/
  bundle we can have it change color to indicate that a drop can
  occur there").
- :class:`WireRouteMixin` -- mixed into each view's own concrete
  ``WireRoute`` drag-handler subclass (alongside that view's ordinary
  ``Wire`` drag handler) to add eligibility-scan-on-arm and hover-
  tracking-on-move on top of the UNCHANGED ordinary bend-drag behavior
  (user: "when the wire section is dragged the wire should move as
  usual"). Same shared-mixin/thin-per-view-glue shape as
  ``handlers.wire_drag_base.WireDragMixin`` itself.
- :class:`RouteSession` -- the click-driven continuation once the
  initial drag lands mid-skeleton at a transition (user: "the user
  would then need to click on the branch the wire should exit the
  transition out of... This process will continue until the wire exits
  either from a transition branch that doesn't have a bundle or from a
  bundle end not attached to a transition."). Installed as a Wire view
  object's own ``_active_handler``, dispatched via the same
  ``__call__(last_pos, current_pos, had_motion, interaction_type,
  clicked_object)`` contract ``add_handlers.base.AddHandlerBase``/
  ``add_handlers.editor_3d.wire.Wire`` already use for a multi-step
  session -- see ``objects.objects_3d/objects_pegboard.wire.Wire.
  handle_interaction``'s own isinstance dispatch, which this module's
  caller must add a branch for (mirroring the existing one for
  ``add_handlers.editor_3d.wire.Wire`` exactly).
- :func:`begin_route` -- the one entry point ``handle_interaction``'s
  LEFT_UP branch calls once a :class:`WireRouteMixin` drag is dropped on
  a valid target: constructs the ``wire_routing_handler.RouteWalk``,
  commits immediately if it already finished (a free end with no
  transition in the way), or returns a :class:`RouteSession` to install
  as the new ``_active_handler`` otherwise.

**Splices are out of scope here** (user, 2026-10-03: "we will get to how
to handle splices a little bit later") -- a transition reached with no
free, fitting branch to continue down simply has nothing to click; the
session stays armed showing no eligible branches until the user gives up
(right-click to cancel) or a differently-sized wire is tried. Not
designed around yet, not expected to be the common case.

Not run against the live app (no GL context outside the real app -- same
ceiling as everything else in this area); verified so far only at the
level ``wire_routing_handler.py``'s own ``RouteWalk``/``route_wire`` are
(pure-logic scripts against fake DB objects) -- the object_picker/camera/
material calls in this module specifically have not been exercised.
"""

from typing import TYPE_CHECKING, Union as _Union

from . import bundle_diameter as _bundle_diameter
from . import transition_handler as _transition_handler
from . import wire_routing_handler as _wire_routing_handler
from ..gl import object_picker as _object_picker
from ..gl.canvas_base import interaction as _interaction
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..geometry import point as _point
    from ..objects import project as _project
    from ..objects import bundle as _bundle_obj
    from ..objects import transition as _transition_obj
    from ..objects import wire as _wire_obj
    from ..gl.canvas_base import canvas_base as _canvas_base


# Reuse the existing fit/hover materials from transition_handler.py
# rather than declaring near-duplicate ones -- same green-means-eligible,
# blue-means-hovered-now visual language already used for bundle/
# transition placement (BUNDLE_PLACEMENT.md section 12's own open item
# on this, resolved this way: no dedicated new colors).
_ELIGIBLE = _transition_handler._BRANCH_FIT
_HOVERED = _transition_handler._HOVER_HIGHLIGHT

# A "hit" is one of:
#   ('bundle', bundle_facade, end)         end is 'start'/'stop'
#   ('branch', transition_facade, branch)  branch is the view-level Branch
# or None.


@_check_types.do
def _view_transition(t_obj: "_transition_obj.Transition", view: str):
    return t_obj.obj3d if view == '3d' else t_obj.objpegboard


@_check_types.do
def compute_eligible_targets(
    project: "_project.Project", wire_od: float, view: str,
) -> tuple[list, list]:
    """Every bundle free end / transition free branch *wire_od* fits
    into, for *view* (``'3d'``/``'pegboard'``) -- BUNDLE_PLACEMENT.md
    section 12's drag-start eligibility scan.

    Freeness/occupancy (``_is_bundle_end_free``, ``branch.bundle``) are
    project-wide topology facts, checked the same way regardless of
    *view* (see ``handlers.wire_drag_base.wire_end_anchors``'s own
    docstring on why -- the same convention applies here); only WHICH
    objects are shown in a given view (``is_in_3dview``/
    ``is_in_pegboardview``) and which of a transition's two facades
    (``obj3d``/``objpegboard``) supplies ``.branches`` depend on *view*.

    :returns: ``(eligible_ends, eligible_branches)`` -- a list of
        ``(bundle_facade, end)`` and a list of
        ``(transition_facade, branch)`` tuples respectively.
    """
    _wire_routing_handler._check_view(view)

    eligible_ends = []
    for bndl in project.bundles:
        is_in_view = bndl.is_in_3dview if view == '3d' else bndl.is_in_pegboardview
        if not is_in_view:
            continue

        for end in ('start', 'stop'):
            if not _transition_handler._is_bundle_end_free(project.ptables, bndl, end):
                continue
            if _bundle_diameter.wire_fits_bundle(wire_od, bndl.db_obj):
                eligible_ends.append((bndl, end))

    eligible_branches = []
    for t_obj in project.transitions:
        is_in_view = t_obj.is_in_3dview if view == '3d' else t_obj.is_in_pegboardview
        if not is_in_view:
            continue

        for branch in _view_transition(t_obj, view).branches:
            if branch.db_obj is None or branch.db_obj.bundle is not None:
                continue  # unplaced preview branch, or already occupied
            if _bundle_diameter.wire_fits_branch(wire_od, branch.db_obj):
                eligible_branches.append((t_obj, branch))

    return eligible_ends, eligible_branches


@_check_types.do
def highlight_eligible(eligible_ends: list, eligible_branches: list, view: str) -> None:
    """Apply :data:`_ELIGIBLE` to every target in the precomputed set --
    called once, the moment a set is computed (drag-start, or a
    transition newly reached mid-:class:`RouteSession`)."""
    for bndl, _end in eligible_ends:
        bndl.identify(_ELIGIBLE)
    for t_obj, branch in eligible_branches:
        _view_transition(t_obj, view).highlight_branch(branch, _ELIGIBLE)


@_check_types.do
def clear_eligible_highlights(eligible_ends: list, eligible_branches: list, view: str) -> None:
    """Undo :func:`highlight_eligible` for every target in the set --
    called on teardown (drag/session cancelled or finished)."""
    for bndl, _end in eligible_ends:
        bndl.identify(None)
    for t_obj, branch in eligible_branches:
        _view_transition(t_obj, view).clear_branch_highlight(branch)


@_check_types.do
def find_drop_hit(
    canvas: "_canvas_base.CanvasBase", mouse_pos: "_point.Point",
    eligible_ends: list, eligible_branches: list, view: str,
) -> _Union[tuple, None]:
    """Whatever's under *mouse_pos* right now, restricted to the
    precomputed eligible sets -- ``None`` if the cursor is over nothing
    eligible (an ineligible object, empty space, or a non-eligible
    bundle/branch). Checks bundles (real pickable ``Base3D``/
    ``BasePegboard`` objects, via ``gl.object_picker.find_object``)
    before branches (not separately pickable -- a direct ray-sphere test
    per transition, same as every other branch-pick site in this
    codebase, e.g. ``add_handlers.editor_3d.transition.Transition.
    hover``).
    """
    camera = canvas.camera

    picked = _object_picker.find_object(mouse_pos, camera, canvas)
    if picked is not None:
        from ..objects import bundle as _bundle_obj
        if isinstance(picked, _bundle_obj.Bundle):
            for bndl, end in eligible_ends:
                if bndl is picked:
                    return 'bundle', bndl, end

    origin, direc = _object_picker._build_ray(mouse_pos, camera)  # NOQA -- same private helper every branch-pick site uses
    if origin is not None:
        for t_obj, branch in eligible_branches:
            candidate = _view_transition(t_obj, view).hit_test_branch_ray(origin, direc)
            if candidate is branch:
                return 'branch', t_obj, branch

    return None


@_check_types.do
def same_hit(a: _Union[tuple, None], b: _Union[tuple, None]) -> bool:
    """Whether *a* and *b* (each a hit tuple or ``None``, see module
    docstring) name the same target -- identity on the object, not
    equality, since facades/view objects have no meaningful ``__eq__``.
    """
    if a is None or b is None:
        return a is b

    return a[0] == b[0] and a[1] is b[1] and a[2] is b[2]


@_check_types.do
def set_hover_highlight(hit: _Union[tuple, None], material, view: str) -> None:
    """Apply *material* to *hit* (``_ELIGIBLE`` to un-hover it,
    ``_HOVERED`` to hover it) -- a no-op for ``None``."""
    if hit is None:
        return

    kind, obj, extra = hit
    if kind == 'bundle':
        obj.identify(material)
    else:
        _view_transition(obj, view).highlight_branch(extra, material)


class WireRouteMixin:
    """Mixed into each view's own concrete ``WireRoute`` drag-handler
    subclass (``drag_handlers.editor_3d/editor_pegboard.wire_route.
    WireRoute``), alongside that view's own ordinary ``Wire`` drag
    handler -- adds the eligibility scan, two-tier highlight, and
    drop-target tracking on top of the inherited ordinary bend-drag
    behavior, which is called unchanged (BUNDLE_PLACEMENT.md section 12:
    "the wire should move as usual"). A concrete subclass must set
    ``_view`` at class level and call :meth:`_arm_routing` right after
    arming the ordinary drag, :meth:`_update_hover` on every move (after
    the ordinary move-delta), and :meth:`_disarm_routing` right before
    disarming the ordinary drag -- see either concrete subclass for the
    exact three-line wiring. Same shared-mixin/thin-per-view-glue shape
    as ``handlers.wire_drag_base.WireDragMixin`` itself; never call
    ``super()`` here for the same reason that module's docstring gives.
    """

    _view: str = None  # '3d' or 'pegboard' -- set by the concrete subclass

    drop_hit = None
    _eligible_ends = None
    _eligible_branches = None

    @_check_types.do
    def _is_routing_eligible(self) -> bool:
        """BUNDLE_PLACEMENT.md section 12's entry precondition: the
        dragged pair must be two of the wire's own REAL waypoints, never
        the wire's own start or stop -- a single moving point (a true
        end, or an anchored pair collapsed to one survivor) is never
        eligible, full stop.
        """
        if self.end is not None or self._moving is None or len(self._moving) != 2:
            return False

        view_obj = self._get_view_object(self.target)
        start_id = view_obj.start_position.db_id
        stop_id = view_obj.stop_position.db_id

        for point in self._moving:
            if point.db_id in (start_id, stop_id):
                return False

        return True

    @_check_types.do
    def _arm_routing(self) -> None:
        """Call once, right after the ordinary drag's own ``_arm_drag``.
        Scans and highlights the eligible set; leaves both lists empty
        (so :meth:`_update_hover` is a no-op and :meth:`is_finished`
        -style drop handling never fires) when :meth:`_is_routing_eligible`
        says no -- the drag then behaves exactly like an ordinary bend.
        """
        self._eligible_ends = []
        self._eligible_branches = []
        self.drop_hit = None

        if not self._is_routing_eligible():
            return

        project = self.target.mainframe.project
        wire_od = self.target.db_obj.part.od_mm
        self._eligible_ends, self._eligible_branches = compute_eligible_targets(
            project, wire_od, self._view)
        highlight_eligible(self._eligible_ends, self._eligible_branches, self._view)

    @_check_types.do
    def _update_hover(self, mouse_pos: "_point.Point") -> None:
        """Call on every move, after the ordinary move-delta has already
        been applied."""
        if not self._eligible_ends and not self._eligible_branches:
            return

        new_hit = find_drop_hit(
            self.canvas, mouse_pos, self._eligible_ends, self._eligible_branches, self._view)

        if same_hit(new_hit, self.drop_hit):
            return

        set_hover_highlight(self.drop_hit, _ELIGIBLE, self._view)
        set_hover_highlight(new_hit, _HOVERED, self._view)
        self.drop_hit = new_hit

    @_check_types.do
    def _disarm_routing(self) -> None:
        """Call right before the ordinary drag's own ``_disarm_drag`` --
        always safe to call even when :meth:`_arm_routing` found nothing
        eligible (clearing two empty lists is a no-op)."""
        clear_eligible_highlights(self._eligible_ends or [], self._eligible_branches or [], self._view)
        self._eligible_ends = []
        self._eligible_branches = []
        self.drop_hit = None


class RouteSession:
    """Click-driven continuation of a ``wire_routing_handler.RouteWalk``
    that's paused at a transition -- see this module's own docstring.
    Shaped like ``add_handlers.base.AddHandlerBase`` (same ``canvas``/
    ``target`` attributes, same ``__call__`` signature, same
    ``is_finished`` contract) so it can be installed as a Wire view
    object's own ``_active_handler`` and dispatched the same way an
    ``add_handlers.editor_3d.wire.Wire`` placement session already is --
    not a subclass of it, since it isn't constructed via any object's
    own ``start_add``, but the calling contract is what
    ``handle_interaction`` actually needs.
    """

    @_check_types.do
    def __init__(
        self, canvas: "_canvas_base.CanvasBase", wire_obj: "_wire_obj.Wire",
        walk: "_wire_routing_handler.RouteWalk", wire_od: float, view: str,
    ) -> None:
        self.canvas = canvas
        self.target = wire_obj
        self._walk = walk
        self._wire_od = wire_od
        self._view = view
        self._finished = False
        self._eligible_branches: list = []
        self._hovered_branch = None
        self._highlight_current_transition()

    @_check_types.do
    def _current_transition_view_obj(self):
        transition_db = self._walk.pending_transition
        return _view_transition(transition_db.get_object(), self._view)

    @_check_types.do
    def _highlight_current_transition(self) -> None:
        view_transition = self._current_transition_view_obj()
        self._eligible_branches = []

        for branch in view_transition.branches:
            if branch.db_obj is None or branch.db_obj.bundle is not None:
                continue
            if not _bundle_diameter.wire_fits_branch(self._wire_od, branch.db_obj):
                continue

            view_transition.highlight_branch(branch, _ELIGIBLE)
            self._eligible_branches.append(branch)

        self._hovered_branch = None

    @_check_types.do
    def _clear_current_highlights(self) -> None:
        view_transition = self._current_transition_view_obj()
        for branch in self._eligible_branches:
            view_transition.clear_branch_highlight(branch)

        self._eligible_branches = []
        self._hovered_branch = None

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finished

    @_check_types.do
    def delete(self) -> None:
        """Clear whatever highlights the current ``pending_transition``
        still carries -- called by :meth:`__call__` itself at both a
        normal finish and an outright cancel, mirroring
        ``add_handlers.base.AddHandlerBase.delete``'s own "called exactly
        once, on both a normal finish and a cancel" contract (nothing
        external calls this for a :class:`RouteSession`, same as for
        ``add_handlers.editor_3d.wire.Wire`` -- see
        ``objects.objects_3d.wire.Wire.handle_interaction``'s own
        dispatch, which never calls ``.delete()`` for either). Guarded so
        a second call (there shouldn't be one) is a harmless no-op.
        """
        if self._eligible_branches:
            self._clear_current_highlights()

    @_check_types.do
    def __call__(
        self, last_pos: "_point.Point", current_pos: "_point.Point", had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object: object,
    ) -> bool:
        if interaction_type is _interaction.MouseInteraction.MOVE:
            view_transition = self._current_transition_view_obj()
            origin, direc = _object_picker._build_ray(current_pos, self.canvas.camera)  # NOQA
            hit = None
            if origin is not None:
                candidate = view_transition.hit_test_branch_ray(origin, direc)
                if candidate in self._eligible_branches:
                    hit = candidate

            if hit is not self._hovered_branch:
                if self._hovered_branch is not None:
                    view_transition.highlight_branch(self._hovered_branch, _ELIGIBLE)
                if hit is not None:
                    view_transition.highlight_branch(hit, _HOVERED)
                self._hovered_branch = hit

            return True

        if interaction_type is _interaction.MouseInteraction.LEFT_UP:
            if self._hovered_branch is None:
                return False  # click missed every eligible branch -- stay armed

            branch = self._hovered_branch
            self.delete()
            self._walk.choose(_wire_routing_handler.ContinueBranch(branch.db_obj))

            if self._walk.is_finished:
                self._walk.commit()
                self._finished = True
            else:
                self._highlight_current_transition()

            return True

        if interaction_type is _interaction.MouseInteraction.RIGHT_UP:
            # Cancel outright -- nothing has been written to pjt_wire_paths
            # yet (RouteWalk only writes on .commit()), so there is
            # nothing to roll back beyond the highlights themselves.
            self.delete()
            self._finished = True
            return True

        return False


@_check_types.do
def begin_route(
    canvas: "_canvas_base.CanvasBase", wire_obj: "_wire_obj.Wire",
    grabbed_position, hit: tuple, view: str,
) -> _Union["RouteSession", None]:
    """Call from ``handle_interaction``'s LEFT_UP branch once a
    :class:`WireRouteMixin` drag's own ``drop_hit`` is non-``None`` at
    release. Constructs the engine's ``RouteWalk`` from *hit*
    (``('bundle', bundle, end)`` or ``('branch', t_obj, branch)``) and
    *grabbed_position*; commits immediately and returns ``None`` if the
    walk already reached a free end (no transition in the way), or
    returns a :class:`RouteSession` to install as the new
    ``_active_handler`` otherwise.
    """
    project = wire_obj.mainframe.project
    ptables = project.ptables
    wire_od = wire_obj.db_obj.part.od_mm

    kind = hit[0]
    if kind == 'bundle':
        _kind, bundle, end = hit
        entry = _wire_routing_handler.EnterBundle(bundle.db_obj, end)
    else:
        _kind, _t_obj, branch = hit
        entry = _wire_routing_handler.EnterBranch(branch.db_obj)

    walk = _wire_routing_handler.RouteWalk(ptables, wire_obj, grabbed_position, entry, view)

    if walk.is_finished:
        walk.commit()
        return None

    return RouteSession(canvas, wire_obj, walk, wire_od, view)
