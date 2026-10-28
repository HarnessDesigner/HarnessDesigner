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

import numpy as np
from PySide6 import QtCore, QtWidgets

from . import bundle_diameter as _bundle_diameter
from . import rope_pull_handler as _rope_pull_handler
from . import transition_handler as _transition_handler
from . import wire_routing_handler as _wire_routing_handler
from ..gl import object_picker as _object_picker
from ..gl.canvas_base import interaction as _interaction
from .. import check_types as _check_types
from .. import logger as _logger
from ..objects import bundle as _bundle_obj


if TYPE_CHECKING:
    from .. import objects as _objects
    from ..objects.objectsvar import base_var as _base_var
    from ..gl import materials as _materials
    from ..objects.objects_3d import transition as _transition_3d
    from ..objects.objects_pegboard import transition as _transition_pegboard
    from ..objects.objects_3d import bundle as _bundle_3d
    from ..objects.objects_pegboard import bundle as _bundle_pegboard
    from ..geometry import point as _point
    from ..objects import project as _project
    from ..objects import transition as _transition_obj
    from ..objects import wire as _wire_obj
    from ..gl.canvas_base import canvas_base as _canvas_base


# Reuse the existing fit/hover materials from transition_handler.py
# rather than declaring near-duplicate ones -- same green-means-eligible,
# blue-means-hovered-now visual language already used for bundle/
# transition placement (BUNDLE_PLACEMENT.md section 12's own open item
# on this, resolved this way: no dedicated new colors).
_ELIGIBLE = _transition_handler.BRANCH_FIT
_HOVERED = _transition_handler.HOVER_HIGHLIGHT

# A "hit" is one of:
#   ('bundle', bundle_facade, end_position)   end_position is the actual Point
#   ('branch', transition_facade, branch)  branch is the view-level Branch
# or None.


@_check_types.do
def _view_transition(t_obj: "_transition_obj.Transition", view: str) -> _Union["_transition_3d.Transition", "_transition_pegboard.Transition"]:
    return t_obj.obj3d if view == '3d' else t_obj.objpegboard


@_check_types.do
def _view_bundle(bndl: "_bundle_obj.Bundle", view: str) -> _Union["_bundle_3d.Bundle", "_bundle_pegboard.Bundle"]:
    return bndl.obj3d if view == '3d' else bndl.objpegboard



@_check_types.do
def _closest_bundle_end(
    start_pos: "_point.Point", stop_pos: "_point.Point", waypoint: "_point.Point",
) -> "_point.Point":
    """Whichever of *start_pos*/*stop_pos* is geometrically nearer
    *waypoint* -- plain straight-line distance, nothing else (user,
    2026-10-12: "feed in the end points of the bundle and one of the 2
    waypoints that make up the section... whichever is the shorter
    straight line distance, return that bundle end"). Returns the
    winning Point itself, not a 'start'/'stop' label. View-agnostic by
    construction: the caller already resolved both positions in
    whichever view it cares about, and *waypoint* is already real
    world-space coordinates -- nothing here reads a view, a bundle, or
    an eligibility list.
    """
    start_dist_sq = float(np.sum((waypoint.as_numpy - start_pos.as_numpy) ** 2))
    stop_dist_sq = float(np.sum((waypoint.as_numpy - stop_pos.as_numpy) ** 2))
    return start_pos if start_dist_sq <= stop_dist_sq else stop_pos


@_check_types.do
def _refresh_committed_wire(wire_obj: "_wire_obj.Wire", view: str) -> None:
    """Resync *wire_obj*'s own *view* object with the ``pjt_wire_paths``
    rows a ``wire_routing_handler.RouteWalk.commit()`` call just wrote --
    without this, the wire's cached waypoint list (and the hidden-segment
    cache ``_segment_transforms`` reads, see ``handlers.wire_topology.
    hidden_waypoint_ids``) would keep showing the pre-route geometry
    until something else happened to call ``refresh_waypoints`` later."""
    view_obj = wire_obj.obj3d if view == '3d' else wire_obj.objpegboard
    view_obj.refresh_waypoints()


@_check_types.do
def _refresh_routed_bundle_diameters(walk: "_wire_routing_handler.RouteWalk") -> None:
    """Recompute and apply the wire-driven diameter of every bundle
    *walk* just routed the wire through -- without this, a free bundle
    with no wires yet stays at its catalog minimum diameter forever,
    even once wires are routed through it, since nothing else triggers
    ``handlers.bundle_diameter.refresh_diameter`` for a plain drag-and-
    drop commit (it was previously only called from
    ``objects.bundle.Bundle.set_sibling``, i.e. transition attach).
    """
    for bundle_db in walk.touched_bundles:
        _bundle_diameter.refresh_diameter(bundle_db.get_object())


_OTHER_VIEW = {'3d': 'pegboard', 'pegboard': '3d'}


@_check_types.do
def _companion_entry(
    entry: _Union["_wire_routing_handler.EnterBundle", "_wire_routing_handler.EnterBranch"],
    companion_view: str,
) -> _Union["_wire_routing_handler.EnterBundle", "_wire_routing_handler.EnterBranch"]:
    """A fresh entry terminus for *companion_view*, naming the SAME
    physical bundle free end / transition branch *entry* does.

    ``EnterBranch`` needs no translation -- ``branch`` is the same row
    in both views, and ``RouteWalk`` resolves its own point from
    ``view`` internally (``_branch_point_id``). But ``EnterBundle.point``
    is NOT view-translated by ``RouteWalk``: ``__init__`` takes it as
    ``self._current_point`` verbatim, however it was built. Reusing the
    ORIGINAL view's ``EnterBundle`` unchanged therefore silently fed the
    companion ``RouteWalk`` a point from the WRONG view's table --
    confirmed live, 2026-10-28: `commit()` raised ``IndexError`` the
    moment it tried to look that point up in *companion_view*'s own
    point table. Fixed by building a new ``EnterBundle`` wrapping the
    same bundle but the companion view's own end point.

    ``Point``'s own singleton-by-``db_id`` contract (``geometry/
    point.py``) is what makes the ``is`` identity check below reliable
    regardless of which view *entry* was originally built from.
    """
    if isinstance(entry, _wire_routing_handler.EnterBranch):
        return entry

    bundle = entry.bundle
    is_start = (
        entry.point is bundle.start_position3d
        or entry.point is bundle.start_position_pegboard)

    if companion_view == '3d':
        point = bundle.start_position3d if is_start else bundle.stop_position3d
    else:
        point = bundle.start_position_pegboard if is_start else bundle.stop_position_pegboard

    return _wire_routing_handler.EnterBundle(bundle, point)


@_check_types.do
def _entry_position(
    entry: _Union["_wire_routing_handler.EnterBundle", "_wire_routing_handler.EnterBranch"],
    view: str,
) -> np.ndarray:
    """*entry*'s own terminus position in *view* -- *entry* must
    already be valid for *view* (see :func:`_companion_entry`), so this
    is a real position to feed ``wire_routing_handler.RouteWalk`` as
    its *grabbed_position* for a view with no actual drag/drop of its
    own (see :func:`_route_companion_view`), not a guess.
    """
    if isinstance(entry, _wire_routing_handler.EnterBundle):
        return entry.point.as_numpy

    branch = entry.branch
    point = branch.position3d if view == '3d' else branch.position_pegboard
    return point.as_numpy


@_check_types.do
def _route_companion_view(
    wire_obj: "_wire_obj.Wire",
    entry: _Union["_wire_routing_handler.EnterBundle", "_wire_routing_handler.EnterBranch"],
    hops: list, view: str,
) -> None:
    """Mirror a route that was just committed in *view* into
    *wire_obj*'s OTHER view too (user, 2026-10-28: dropping a wire onto
    a bundle in either the 3D or the peg-board view must route it
    through that same bundle in BOTH views). *entry* is the
    view-agnostic terminus the original drag resolved (wraps a real
    ``PJTBundle``/``PJTTransitionBranch`` row, shared by both views);
    *hops* is every ``ContinueBranch`` the user clicked through to get
    there, in order -- replayed here unchanged, since whether a
    transition's branch already has a bundle plugged in is a
    project-wide topology fact, not a per-view one (see
    ``compute_eligible_targets``'s own docstring). *view* is whichever
    view the caller already routed and committed; this only handles the
    other one.

    An ``EndAtSplice`` hop is refused rather than guessed at -- splices
    are not wired into this feature at all yet (module docstring), so
    one can never actually appear in *hops* today; this only guards
    against silently mis-routing if that ever changes.

    Always finishes with ``rope_pull_handler.realize_length_change`` so
    the peg-board side's length conforms to the 3D side's, regardless
    of which view the user actually dragged in (user, 2026-10-28:
    peg-board is adjusted either way, never the other direction -- same
    rule BUNDLE_PLACEMENT.md section 6 already uses for every other
    peg-board/3D interaction).
    """
    for hop in hops:
        if isinstance(hop, _wire_routing_handler.EndAtSplice):
            _logger.warning(
                'wire_routing_drag: companion-view routing skipped -- '
                'EndAtSplice is not supported across views yet')
            return

    ptables = wire_obj.mainframe.project.ptables
    companion_view = _OTHER_VIEW[view]
    companion_entry = _companion_entry(entry, companion_view)
    grabbed_position = _entry_position(companion_entry, companion_view)

    companion_walk = _wire_routing_handler.RouteWalk(
        ptables, wire_obj, grabbed_position, companion_entry, companion_view)

    for hop in hops:
        if companion_walk.is_finished:
            break
        companion_walk.choose(hop)

    if not companion_walk.is_finished:
        _logger.warning(
            'wire_routing_drag: companion-view route did not finish -- '
            'skeleton topology disagreed between views, leaving the '
            'companion view unrouted')
        return

    companion_walk.commit()
    _refresh_committed_wire(wire_obj, companion_view)
    _refresh_routed_bundle_diameters(companion_walk)

    _rope_pull_handler.realize_length_change(
        wire_obj.mainframe, wire_obj.db_obj, in_progress=False)


@_check_types.do
def compute_eligible_targets(
    project: "_project.Project", wire_od: float, view: str,
) -> tuple[list, list]:
    """Every bundle free end / transition free branch *wire_od* fits
    into, for *view* (``'3d'``/``'pegboard'``) -- BUNDLE_PLACEMENT.md
    section 12's drag-start eligibility scan.

    Freeness/occupancy (``is_bundle_end_free``, ``branch.bundle``) are
    project-wide topology facts, checked the same way regardless of
    *view* (see ``handlers.wire_drag_base.wire_end_anchors``'s own
    docstring on why -- the same convention applies here); only WHICH
    objects are shown in a given view (``is_in_3dview``/
    ``is_in_pegboardview``) and which of a transition's two facades
    (``obj3d``/``objpegboard``) supplies ``.branches`` depend on *view*.

    :returns: ``(eligible_ends, eligible_branches)`` -- a list of
        ``(bundle_facade, end_position)`` and a list of
        ``(transition_facade, branch)`` tuples respectively.
    """
    _wire_routing_handler.check_view(view)

    eligible_ends = []
    for bndl in project.bundles:
        is_in_view = bndl.is_in_3dview if view == '3d' else bndl.is_in_pegboardview
        if not is_in_view:
            continue

        view_obj = _view_bundle(bndl, view)
        for end, point in (('start', view_obj.start_position), ('stop', view_obj.stop_position)):
            if not _transition_handler.is_bundle_end_free(project.ptables, bndl, end):
                continue
            if _bundle_diameter.wire_fits_bundle(wire_od, bndl.db_obj):
                eligible_ends.append((bndl, point))

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
    eligible_ends: list, eligible_branches: list, view: str, moving: list["_point.Point"],
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

    *moving* is the dragged section's own two waypoints (``self.moving``
    on the drag handler) -- needed to pick the right END when a picked
    bundle has more than one eligible end (see :func:`_closest_bundle_end`).
    """
    camera = canvas.camera

    picked = _object_picker.find_object(mouse_pos, camera, canvas)
    if picked is not None:
        if isinstance(picked, _bundle_obj.Bundle):
            candidates = [point for bndl, point in eligible_ends if bndl is picked]
            if len(candidates) == 1:
                return 'bundle', picked, candidates[0]
            if candidates:
                view_obj = _view_bundle(picked, view)
                end_position = _closest_bundle_end(view_obj.start_position, view_obj.stop_position, moving[0])
                return 'bundle', picked, end_position

    origin, direc = _object_picker.build_ray(mouse_pos, camera)
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
def set_hover_highlight(hit: _Union[tuple, None], material: "_materials.GLMaterial", view: str) -> None:
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

    _view: str | None = None  # '3d' or 'pegboard' -- set by the concrete subclass

    drop_hit = None
    _eligible_ends = None
    _eligible_branches = None

    # Class-level placeholders for everything this mixin reads but never
    # sets itself -- established by WireDragMixin (mixed in alongside
    # this one, on the concrete WireRoute subclass's OTHER base,
    # handlers.wire_drag_base.WireDragMixin), never by this mixin's own
    # __init__ (it has none -- see this mixin's own docstring on why).
    # WireRouteMixin has no inheritance relationship to WireDragMixin --
    # they only meet on the concrete subclass -- so without these,
    # static analysis has no way to know self.canvas/self.target/
    # self.snap_point/self.moving/self._get_view_object are ever going to
    # exist. Same convention WireDragMixin itself follows for its own
    # ``canvas``/``target``/etc. placeholders, for the identical reason.
    canvas = None
    target = None
    snap_point = None
    moving = None

    @staticmethod
    @_check_types.do
    def _get_view_object(obj: "_objects.ObjectBase") -> "_base_var.BaseVar":
        """Established by WireDragMixin -- see that class's own
        docstring. Declared here only so static analysis can resolve
        ``self._get_view_object(...)`` inside this mixin's own methods;
        never actually called through this placeholder at runtime (the
        concrete subclass's MRO always resolves to WireDragMixin's real
        per-view override instead).
        """
        raise NotImplementedError

    @_check_types.do
    def _is_routing_eligible(self) -> bool:
        """BUNDLE_PLACEMENT.md section 12's entry precondition: the
        dragged pair must be two of the wire's own REAL waypoints, never
        the wire's own start or stop -- a single moving point (a true
        end, or an anchored pair collapsed to one survivor) is never
        eligible, full stop.
        """
        if self.snap_point is not None or self.moving is None or len(self.moving) != 2:
            return False

        view_obj = self._get_view_object(self.target)
        start_id = view_obj.start_position.db_id
        stop_id = view_obj.stop_position.db_id

        for point in self.moving:
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
            self.canvas, mouse_pos, self._eligible_ends, self._eligible_branches, self._view,
            self.moving)

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
        entry: _Union["_wire_routing_handler.EnterBundle", "_wire_routing_handler.EnterBranch"],
    ):
        self.canvas = canvas
        self.target = wire_obj
        self._walk = walk
        self._wire_od = wire_od
        self._view = view
        self._entry = entry
        self._hops: list = []
        self._finished = False
        self._eligible_branches: list = []
        self._hovered_branch = None
        self._highlight_current_transition()

    @_check_types.do
    def _current_transition_view_obj(self) -> _Union["_transition_3d.Transition", "_transition_pegboard.Transition"]:
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
        interaction_type: "_interaction.MouseInteraction", clicked_object: _Union["_objects.ObjectBase", None],
    ) -> bool:
        """BUNDLE_PLACEMENT.md section 12: "the only left click with no
        motion that will be accepted as a click on anything is when a
        branch on the transition is clicked... a right click with no
        motion will cancel the operation. All other mouse interactions
        that move the camera are allowed to take place." Two things
        follow, both fixed 2026-10-10 (previously every MOVE/LEFT_UP/
        RIGHT_UP was swallowed unconditionally, which silently blocked
        camera orbit/pan/truck while a session was armed and cancelled
        the whole route on a right-drag camera release):

        - MOVE only updates the branch hover highlight while no mouse
          button is actually held -- a camera-move drag (whichever
          button the user's own config binds to orbit/pan/truck) is
          declined outright so ``on_mouse_motion``'s own fallback
          button-delta handling runs instead of being pre-empted here.
        - LEFT_UP/RIGHT_UP only act when *had_motion* is False, mirroring
          ``add_handlers.base``'s own "a click-type event with motion was
          actually a drag release, let it fall through" convention --
          see e.g. ``add_handlers.editor_3d.wire.Wire.__call__``.
        """
        if interaction_type is _interaction.MouseInteraction.MOVE:
            if QtWidgets.QApplication.mouseButtons() != QtCore.Qt.MouseButton.NoButton:
                return False

            view_transition = self._current_transition_view_obj()
            origin, direc = _object_picker.build_ray(current_pos, self.canvas.camera)
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

        if had_motion:
            # A camera-move drag's own release (orbit/pan/truck, whatever
            # button it used) -- never a branch pick or a cancel.
            return False

        if interaction_type is _interaction.MouseInteraction.LEFT_UP:
            if self._hovered_branch is None:
                return False  # click missed every eligible branch -- stay armed

            branch = self._hovered_branch
            self.delete()
            hop = _wire_routing_handler.ContinueBranch(branch.db_obj)
            self._hops.append(hop)
            self._walk.choose(hop)

            if self._walk.is_finished:
                self._walk.commit()
                _refresh_committed_wire(self.target, self._view)
                _refresh_routed_bundle_diameters(self._walk)
                _route_companion_view(self.target, self._entry, self._hops, self._view)
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
    grabbed_position: "np.ndarray", hit: tuple, view: str,
) -> _Union["RouteSession", None]:
    """Call from ``handle_interaction``'s LEFT_UP branch once a
    :class:`WireRouteMixin` drag's own ``drop_hit`` is non-``None`` at
    release. Constructs the engine's ``RouteWalk`` from *hit*
    (``('bundle', bundle, end_position)`` or ``('branch', t_obj, branch)``) and
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
        _kind, bundle, end_position = hit
        entry = _wire_routing_handler.EnterBundle(bundle.db_obj, end_position)
    else:
        _kind, _t_obj, branch = hit
        entry = _wire_routing_handler.EnterBranch(branch.db_obj)

    walk = _wire_routing_handler.RouteWalk(ptables, wire_obj, grabbed_position, entry, view)

    if walk.is_finished:
        walk.commit()
        _refresh_committed_wire(wire_obj, view)
        _refresh_routed_bundle_diameters(walk)
        _route_companion_view(wire_obj, entry, [], view)
        return None

    return RouteSession(canvas, wire_obj, walk, wire_od, view, entry)
