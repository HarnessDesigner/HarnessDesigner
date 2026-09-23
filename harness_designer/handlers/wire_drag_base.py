# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Shared segment-local wire drag, used identically by the 3D and
peg-board editors.

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

When the plan's moving point is a true wire end (snap-eligible -- see
:attr:`WireDragPlan.snap_end`), the drag also builds an invisible
snap-probe set (see :mod:`~harness_designer.handlers.wire_snap`) at
every terminal's own back point, every splice's own branch point, and
every other open, same-part wire end, and hit-tests the REAL cursor
position against them on every move. Landing within a probe teleports
the dragged point exactly onto it instead of following the mouse;
``snapped_kind``/``snapped_target`` are read by the mouse handler's
button-up handling to commit the connection once the mouse releases. A
hard AWG/cross-section mismatch is purely informational here -- never
blocks the snap itself, only shows a warning overlay (confirmed
2026-08-06: "always allow a snap to occur and the connection to be
made... the user can resolve that issue after").

**:class:`WireDragMixin` defines no constructor -- on purpose, and this
is a hard rule, not a style preference** (confirmed 2026-09-13, matching
the same discipline already used throughout
``database.project_db.mixins``): a mixin's whole value is that it can
be combined with any base class *in either order* without changing
behavior, and the only way to guarantee that is for it to never define
``__init__``/``delete`` (or any other method the "real" base class --
``DragHandler3D``/``DragHandlerPegboard`` -- also defines and expects
to run via cooperative ``super()`` chaining). A method that exists on
both sides of a multiple-inheritance combination has its resolution
decided by base-class order -- reversing ``class Wire(WireDragMixin,
DragHandler3D)`` to ``class Wire(DragHandler3D, WireDragMixin)`` then
silently changes which one runs, or skips one of them entirely (traced
concretely, both directions, on 2026-09-13 -- reversing it either
raises a straight ``TypeError`` at construction, once "fixed" past
that, or silently drops the mixin's own setup entirely). Something as
simple as base-class order must never be able to break the code.

So every method this mixin provides is either (a) uniquely named --
``_arm_drag``/``_disarm_drag``/``__call__``/``_raw_move_delta``/
``_move_delta`` -- nothing else in the hierarchy defines these, so
which class "wins" is never in question regardless of order, or (b) a
plain classmethod that never calls ``super()`` at all
(``is_anchor_point``/``wire_end_anchors``/``plan_wire_drag``). Each
concrete ``Wire`` (``drag_handlers.editor_3d.wire.Wire``/
``drag_handlers.editor_pegboard.wire.Wire``) keeps single, ordinary
inheritance from its own ``DragHandler3D``/``DragHandlerPegboard``, and
writes its own explicit ``__init__``/``delete``/``__call__``, each
calling its real base by name -- ``DragHandler3D.__init__(self, ...)``/
``DragHandler3D.delete(self)``/``DragHandler3D.__call__`` (or the
``DragHandlerPegboard`` equivalents), never ``super()`` -- alongside this
mixin's own ``_arm_drag``/``_disarm_drag``/``__call__`` (reached the same
explicit way). ``__call__`` needs the same explicit treatment as
``__init__``/``delete``: both ``DragHandlerBase`` (this mixin's sibling's
own ancestor) and this mixin define ``__call__``, so plain inheritance
resolves it via MRO order rather than intent -- confirmed live, 2026-09-13,
when ``DragHandlerBase.__call__``'s unconditional ``NotImplementedError``
silently won over this mixin's real logic in both concrete ``Wire``
classes until each added its own explicit override.

**Known gap (2026-09-13, narrowed):** the snap-COMMIT side of this
feature (``wire_snap.commit_snap``) is still 3D-only for a snap onto a
TERMINAL or SPLICE (``Terminal.add_wire``/``Splice.add_wire`` and
``commit_snap``'s own splice branch write only ``*_position3d``/
``*_position2d`` columns) -- ``SnapProbeSet`` already supports per-view
concrete subclasses (probes built at ``*_position_pegboard`` for
peg-board), so the LIVE in-drag teleport-onto-a-probe this module drives
works for peg-board there too, but finalizing THAT specific case into a
real connection on mouse-up does not yet. A snap onto another WIRE's own
dangling end is no longer part of this gap: :meth:`WireDragMixin.
merge_wire_into` merges peg-board geometry too now (full interior-
waypoint reindexing, matching 3D), whenever both wires actually have
peg-board geometry.
"""

from typing import TYPE_CHECKING

import numpy as np

from ..geometry import point as _point
from ..gl import object_picker as _object_picker
from .. import debug as _debug
from .. import check_types as _check_types
from . import wire_snap as _wire_snap
from . import snap_probe_set as _snap_probe_set


if TYPE_CHECKING:
    from ..gl.canvas_base import canvas_base as _canvas_base
    from .. import objects as _objects
    from ..objects import project as _project
    from ..objects import wire as _wire_object


class WireDragPlan:
    """
    What a click on a Wire's body should drag -- computed once at
    drag-start by :func:`plan_wire_drag`, consumed by
    :meth:`WireDragMixin._arm_drag`.

    :ivar moving: The 1-2 live Point objects to translate together.
    :ivar anchor: The path point nearest the click, used as the
        screen-projection anchor (see :meth:`WireDragMixin.
        _raw_move_delta`).
    :ivar snap_end: 'start'/'stop' when *moving* is a single point that is
        also the wire's own true end (snap-eligible) -- None otherwise
        (a moving pair, or a single non-end point, never snaps; the
        general rule guarantees a lone moving point is always a true end
        though, see :func:`plan_wire_drag`).
    """

    __slots__ = ('moving', 'anchor', 'snap_end')

    def __init__(self, moving: list, anchor: _point.Point, snap_end: str | None):
        self.moving = moving
        self.anchor = anchor
        self.snap_end = snap_end


class WireDragMixin:
    """
    Shared segment-local wire drag behavior -- see the module
    docstring for the hard rule this class follows (no ``__init__``/
    ``delete``, ever) and why. Concrete per-view classes
    (``drag_handlers.editor_3d.wire.Wire``/``drag_handlers.
    editor_pegboard.wire.Wire``) mix this in alongside their own
    ``DragHandler3D``/``DragHandlerPegboard`` -- in either order, it
    makes no difference -- and MUST override every accessor below
    (never ``getattr``/duck-typing, so IDE navigation and static type-
    checking keep working).
    """

    # Class-level placeholders -- document what a concrete class's own
    # __init__ must establish (via _arm_drag) before this mixin's other
    # methods are usable. Same convention objects.mixins.wire.
    # WireTypeMixin already uses for the same reason.
    canvas = None
    target = None
    _moving = None
    _anchor = None
    last_pos = None
    end = None
    _snap_probes = None
    _overlay = None
    snapped_kind = None
    snapped_target = None
    pick_offset = None

    # ------------------------------------------------------------------
    # View-specific accessors -- every concrete subclass MUST override
    # every one of these. Never getattr/duck-typing, so IDE navigation
    # and static type-checking keep working across the whole hierarchy.
    # ------------------------------------------------------------------

    @staticmethod
    def _get_view_object(obj: "_objects.ObjectBase"):
        """
        Return *obj*'s own view-specific wrapper for this editor --
        ``obj.obj3d`` or ``obj.objpegboard``.
        """

        raise NotImplementedError

    @staticmethod
    def _get_editor(mainframe):
        """
        Return this view's own INNER GL canvas widget (``mainframe.editorX.
        editor._canvas`` -- not the wrapper, ``mainframe.editorX.editor``
        itself, which is un-offset and usually smaller: see
        gl.canvas_base.canvas_window_base.CanvasWindowBase.objects_in_window's
        own docstring on why the two differ) -- used to parent a
        :class:`~harness_designer.handlers.wire_snap.SnapOverlay`, whose
        ``show_message`` moves it using mouse positions measured against
        that same inner canvas.
        """

        raise NotImplementedError

    @staticmethod
    def _points_table(project: "_project.Project"):
        """
        This view's own peg-board/3D points table (``pjt_points3d_table``
        / ``pjt_points_pegboard_table``), used to resolve a point id's own
        ``parent_point_id`` in :meth:`is_anchor_point`.
        """

        raise NotImplementedError

    @staticmethod
    def _waypoints(wire_db_obj):
        """
        This wire's own ordered interior waypoints for this view
        (``wire_db_obj.waypoints3d`` / ``waypoints_pegboard``).
        """

        raise NotImplementedError

    @staticmethod
    def _wire_position_id_raw(obj) -> bytes | None:
        """
        A cavity's or terminal's own ``wire_position*_id_raw`` column
        for this view (see :meth:`is_anchor_point`).
        """

        raise NotImplementedError

    @staticmethod
    def _attach_position_id_raw(obj) -> bytes | None:
        """
        A terminal's own ``attach_position*_id_raw`` column for this
        view (see :meth:`is_anchor_point`).
        """

        raise NotImplementedError

    @staticmethod
    def _get_start_position_id(wire_db_obj) -> bytes | None:
        """
        This view's own ``start_position*_id`` column on a wire's DB
        row (see :meth:`merge_wire_into`).
        """

        raise NotImplementedError

    @staticmethod
    def _set_start_position_id(wire_db_obj, value: bytes | None) -> None:
        raise NotImplementedError

    @staticmethod
    def _get_stop_position_id(wire_db_obj) -> bytes | None:
        """
        This view's own ``stop_position*_id`` column on a wire's DB
        row (see :meth:`merge_wire_into`).
        """

        raise NotImplementedError

    @staticmethod
    def _set_stop_position_id(wire_db_obj, value: bytes | None) -> None:
        raise NotImplementedError

    @staticmethod
    def _layout_position_id(layout_db_obj) -> bytes | None:
        """
        This view's own ``position*_id`` column on a WireLayout's DB
        row (see :meth:`wire_layout_end_wire`).
        """

        raise NotImplementedError

    @staticmethod
    def _is_in_view(obj: "_objects.ObjectBase") -> bool:
        """
        This view's own ``is_in_3dview``/``is_in_pegboardview`` check
        on a facade object (see :meth:`wire_layout_end_wire`).
        """

        raise NotImplementedError

    # _SnapProbeSet: this view's own concrete snap_probe_set.SnapProbeSet
    # subclass, living in that view's own drag_handlers.editor_*.wire_snap
    # module -- every concrete Wire class MUST set this at class level.
    _SnapProbeSet: _snap_probe_set.SnapProbeSetType | None = None

    # ------------------------------------------------------------------
    # Shared planning -- classmethods so they can run before any
    # instance exists (mirrors gl.object_picker.find_object's own
    # `get_view` parameter style: an explicit callable, never getattr).
    # Never call super() -- plain classmethods, no lifecycle role, so
    # they're exempt from this mixin's own "no constructor" rule (that
    # rule is specifically about methods that would otherwise collide
    # with DragHandler3D/DragHandlerPegboard's own; nothing there
    # defines these names either).
    # ------------------------------------------------------------------

    @classmethod
    @_check_types.do
    def is_anchor_point(cls, project: "_project.Project", point_id: bytes) -> bool:
        """
        True when *point_id* is rigidly tied to a cavity's or
        terminal's own wire-routing point -- not something a drag should
        ever move directly.

        A point attached to a terminal/splice/cavity that can carry more
        than one wire gets its own cloned row for the 2nd+ wire (one
        point can only carry a single wire_id/idx tag at a time -- see
        ``Terminal._own_or_cloned_point_id``), with its own
        ``parent_point_id`` set to the real/canonical anchor point's id.
        So the clone's own raw id never equals the terminal's/cavity's
        own routing point id directly -- resolve up to the canonical id
        first (a no-op when the point isn't a clone).
        """

        points_table = cls._points_table(project)

        point_row = points_table[point_id]
        parent_id = point_row.parent_point_id

        if parent_id is not None:
            check_id = parent_id
        else:
            check_id = point_id

        for cavity in project.cavities:
            if cls._wire_position_id_raw(cavity.db_obj) == check_id:
                return True

        for terminal in project.terminals:
            if check_id in (
                cls._wire_position_id_raw(terminal.db_obj),
                cls._attach_position_id_raw(terminal.db_obj),
            ):
                return True

        return False

    @classmethod
    @_check_types.do
    def wire_end_anchors(cls, project: "_project.Project",
                         wire_obj: "_wire_object.Wire") -> tuple[bool, bool]:

        """
        Return (start_anchored, stop_anchored) for *wire_obj*.

        An end is "anchored" when it sits at a cavity's or terminal's
        own wire-routing point -- that end's position is derived from
        the cavity/terminal's own placement, not something a drag
        should move directly. An end that is NOT anchored is always
        safe to drag freely even when another wire's endpoint happens
        to share the exact same live Point (a plain junction) -- moving
        a shared Point via its own ``+=`` already propagates to
        everything else bound to it for free.

        Whether an end is anchored is a project-wide topology fact, not
        a per-view rendering detail -- callers that need a view-agnostic
        answer (``handlers.wire_snap.SnapProbeSet.__init__``,
        ``handlers.wire_handler._pick_free_end``) call this via
        ``drag_handlers.editor_3d.wire.Wire`` specifically, always, even
        when the calling code itself is peg-board-side -- never bare on
        ``WireDragMixin`` (every accessor is abstract there, so it just
        raises ``NotImplementedError`` -- confirmed live, 2026-09-13).
        """

        view_obj = cls._get_view_object(wire_obj)
        start_id = view_obj.start_position.db_id[:-2]
        stop_id = view_obj.stop_position.db_id[:-2]

        return (cls.is_anchor_point(project, start_id),
                cls.is_anchor_point(project, stop_id))

    @classmethod
    @_check_types.do
    def plan_wire_drag(cls, project: "_project.Project", wire_obj: "_wire_object.Wire",
                       mouse_pos: _point.Point) -> WireDragPlan | None:

        """
        Work out what a click on *wire_obj*'s body at *mouse_pos*
        should drag, per the confirmed rule:

        1. If the click lands near the wire's own true start or stop
           (see the view object's own ``get_closest_endpoint`` -- the
           wire's own diameter or 5mm, whichever is larger), the single
           moving point is that true end.
        2. Otherwise, find the segment nearest the click (see the view
           object's own ``get_closest_point``) -- the two points
           bounding that segment (true end or interior waypoint on
           either side) are the moving pair. This also covers a plain
           2-point wire (no interior waypoints): the "segment" is the
           whole wire, so a mid-body click moves both ends together.
        3. Either way, drop any point that is anchored
           (:meth:`is_anchor_point`) -- anything beyond the two bounding
           points never moves, regardless of what's past them.
        4. If nothing is left after that filtering, return ``None`` --
           the caller pans the camera instead of starting a no-op drag.

        Snap-testing only ever applies when exactly one point ends up
        moving -- a lone moving point is always a true end, a moving
        pair never is.
        """

        view_obj = cls._get_view_object(wire_obj)

        _pos, is_endpoint, end_name = view_obj.get_closest_endpoint(mouse_pos)

        if is_endpoint:
            if end_name == 'start':
                moving_point = view_obj.start_position
            else:
                moving_point = view_obj.stop_position

            point_id = moving_point.db_id[:-2]

            if cls.is_anchor_point(project, point_id):
                return None

            return WireDragPlan(moving=[moving_point],
                                anchor=moving_point.copy(),
                                snap_end=end_name)

        closest_point, _angle, seg_idx = view_obj.get_closest_point(mouse_pos)
        if closest_point is None:
            return None

        waypoints = cls._waypoints(wire_obj.db_obj)
        chain = ([view_obj.start_position] +
                 [wp.point for wp in waypoints] +
                 [view_obj.stop_position])

        last_idx = len(chain) - 1
        bounding = (seg_idx, seg_idx + 1)

        moving = []
        for idx in bounding:
            point = chain[idx]
            if not cls.is_anchor_point(project, point.db_id[:-2]):
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

        return WireDragPlan(moving=[point for _idx, point in moving],
                            anchor=closest_point.copy(),
                            snap_end=snap_end)

    # ------------------------------------------------------------------
    # Shared wire-topology lookups -- also plain classmethods, resolved
    # through cls's own accessors, moved here from handlers.wire_handler
    # (2026-09-13): that module is for view-agnostic code only, and these
    # three were hardcoded to 3D despite peg-board's own WireMenu already
    # calling pick_free_end (silently wrong there whenever both ends were
    # free -- it fed a peg-board-space click position through 3D ray-
    # casting) and peg-board's own drag-commit needing merge_wire_into
    # (see wire_snap.commit_snap). Never call super() -- see the module
    # docstring's own hard rule; same as is_anchor_point/wire_end_anchors/
    # plan_wire_drag above.
    # ------------------------------------------------------------------

    @classmethod
    @_check_types.do
    def wire_layout_end_wire(cls, wire_layout_obj, project: "_project.Project",
                             part_id: bytes | None):

        """
        Return (wire, endpoint) if *wire_layout_obj* sits at one
        endpoint of a wire with matching *part_id*, in THIS view.

        Returns (None, None) when the layout is mid-wire (split point,
        two wires share it) or when no wire with the given part_id is
        attached.
        """

        if part_id is None:
            return None, None

        layout_pos_id = cls._layout_position_id(wire_layout_obj.db_obj)
        matching = []

        for w in project.wires:
            if not cls._is_in_view(w):
                continue

            view_obj = cls._get_view_object(w)
            start_str = view_obj.start_position.db_id
            stop_str = view_obj.stop_position.db_id
            if start_str and start_str[:-2] == layout_pos_id:
                matching.append((w, 'start'))
            elif stop_str and stop_str[:-2] == layout_pos_id:
                matching.append((w, 'stop'))

        if len(matching) == 1:
            w, ep = matching[0]
            if w.db_obj.part_id == part_id:
                return w, ep

        return None, None

    @classmethod
    @_check_types.do
    def pick_free_end(cls, mainframe, wire_obj: "_wire_object.Wire",
                      click_pos: _point.Point | None = None) -> str | None:

        """
        Return ``'start'``/``'stop'`` -- whichever end of *wire_obj* is
        free to extend/add onto (see ``objects.objects_3d.wire.WireMenu``/
        ``objects.objects_pegboard.wire.WireMenu``'s Extend Wire/Add to
        Wire actions) -- or ``None`` if both ends are anchored to a
        terminal/cavity (those menu actions are disabled in that case).

        Exactly one free end wins outright; with both free, whichever is
        closer to *click_pos* (where the context menu was opened, in
        THIS view's own screen space) wins, using the same closest-
        point-on-path technique :meth:`plan_wire_drag` already uses to
        decide "which end did the user mean" elsewhere.
        """

        project = mainframe.project
        start_anchored, stop_anchored = cls.wire_end_anchors(project, wire_obj)

        if start_anchored and stop_anchored:
            return None

        if start_anchored:
            return 'stop'

        if stop_anchored:
            return 'start'

        view_obj = cls._get_view_object(wire_obj)

        if click_pos is None:
            return 'stop'

        closest_point, _angle, _seg_idx = view_obj.get_closest_point(click_pos)
        if closest_point is None:
            return 'stop'

        start_dist = float(np.linalg.norm(
            closest_point.as_numpy - view_obj.start_position.as_numpy))

        stop_dist = float(np.linalg.norm(
            closest_point.as_numpy - view_obj.stop_position.as_numpy))

        if start_dist <= stop_dist:
            return 'start'

        return 'stop'

    @staticmethod
    def _view_merge_geometry(get_view_object, get_waypoints, wire_obj,
                             other_wire, own_end: str, other_end: str):

        """
        This view's own seam point id, reindexed own/other waypoint
        chains, and this view's own start/stop ids for the merged wire --
        identical bookkeeping regardless of which view, just fed that
        view's own :meth:`_get_view_object`/:meth:`_waypoints` pair (see
        :meth:`merge_wire_into`).
        """

        own_view = get_view_object(wire_obj)
        other_view = get_view_object(other_wire)

        if own_end == 'start':
            # Mirror image of the 'stop' case below: wire_obj's own far/
            # outer end is now its stop (own_end is the seam), so its own
            # waypoints need reversing to still walk outer-end-toward-seam
            # in the merged wire's own start->stop order.
            seam_point_id = own_view.start_position.db_id[:-2]
            own_waypoints = list(reversed(get_waypoints(wire_obj.db_obj)))
            start_id = own_view.stop_position.db_id[:-2]
        else:
            seam_point_id = own_view.stop_position.db_id[:-2]
            own_waypoints = list(get_waypoints(wire_obj.db_obj))
            start_id = own_view.start_position.db_id[:-2]

        if other_end == 'start':
            stop_id = other_view.stop_position.db_id[:-2]

            # already start->stop order
            other_waypoints = list(get_waypoints(other_wire.db_obj))
        else:
            stop_id = other_view.start_position.db_id[:-2]
            other_waypoints = list(reversed(get_waypoints(other_wire.db_obj)))

        return seam_point_id, own_waypoints, other_waypoints, start_id, stop_id

    @classmethod
    @_check_types.do
    def merge_wire_into(cls, project: "_project.Project",
                        wire_obj: "_wire_object.Wire",
                        other_wire: "_wire_object.Wire",
                        other_end: str, own_end: str = 'stop'):

        """
        Join *wire_obj*'s own dangling *own_end* ('start' or 'stop';
        default 'stop' -- the two-click preview flow's own always-growing
        end, the only case that existed before this took an own_end
        parameter) to *other_wire*'s dangling *other_end*, merging them
        into a single row -- part_id must already match (checked by the
        caller). Also the commit path for a snapped wire-to-wire endpoint
        drag (see handlers.wire_snap.commit_snap) -- own_end there is
        whichever end was actually dragged, which can be either one.

        Every view a wire has geometry in gets merged together, not just
        the view this call happened to be reached through -- a wire's own
        3D and peg-board points are independent, parallel geometry for
        the SAME logical connection (see ``StartStopPosition3DMixin``/
        ``StartStopPositionPegboardMixin`` both living on ``PJTWire`` at
        once), so a merged wire must keep all of them, not just whichever
        one the triggering click/drag happened to be in. 3D is always
        present (every wire has 3D geometry) and is the one view
        ``pjt_wires_table.insert`` itself accepts columns for; peg-board
        is merged the same way -- full interior-waypoint reindexing, not
        just a start/stop id carryover -- whenever both wires actually
        have peg-board geometry (confirmed 2026-09-13: peg-board wires
        support user-placed interior waypoints the same way 3D does, so a
        merge should treat them the same way, not like 2D's current
        lighter start/stop-only treatment, which this leaves unchanged).

        *wire_obj*'s own current *own_end* point becomes a permanent
        interior waypoint marking the seam (a WireLayout is dropped there
        for each view that got merged), same as an ordinary bend;
        *other_wire*'s own waypoints follow, reversed first if joining to
        its start (so the merged chain still reads start->stop in one
        consistent direction), renumbered to continue. circuit_id is
        inherited from whichever of the two already had one set, not
        required to match. Both original rows are deleted; returns the
        new merged wire.
        """

        from ..drag_handlers.editor_3d import wire as _wire_3d  # NOQA
        from ..drag_handlers.editor_pegboard import wire as _wire_pegboard  # NOQA
        from ..objects import wire as _wire_object_mod  # NOQA
        from ..objects import wire_layout as _wire_layout_mod  # NOQA

        ptables = project.ptables
        mainframe = project.mainframe

        (seam_id_3d, own_wp_3d,
         other_wp_3d, start_id_3d,
         stop_id_3d) = cls._view_merge_geometry(_wire_3d.Wire._get_view_object,  # NOQA
                                                _wire_3d.Wire._waypoints,  # NOQA
                                                wire_obj, other_wire,
                                                own_end, other_end)

        if own_end == 'start':
            start_id_2d = wire_obj.db_obj.stop_position2d_id

        else:
            start_id_2d = wire_obj.db_obj.start_position2d_id

        if other_end == 'start':
            stop_id_2d = other_wire.db_obj.stop_position2d_id
        else:
            stop_id_2d = other_wire.db_obj.start_position2d_id

        # Both wires need COMPLETE peg-board geometry (both ends), not
        # just one end on one side -- a wire only partly present in
        # peg-board has nothing coherent there to merge.
        pegboard_present = (
            _wire_pegboard.Wire._get_start_position_id(wire_obj.db_obj) is not None and  # NOQA
            _wire_pegboard.Wire._get_stop_position_id(wire_obj.db_obj) is not None and  # NOQA
            _wire_pegboard.Wire._get_start_position_id(other_wire.db_obj) is not None and  # NOQA
            _wire_pegboard.Wire._get_stop_position_id(other_wire.db_obj) is not None)  # NOQA

        if pegboard_present:
            (seam_id_pegboard, own_wp_pegboard,
             other_wp_pegboard, start_id_pegboard,
             stop_id_pegboard) = cls._view_merge_geometry(_wire_pegboard.Wire._get_view_object,  # NOQA
                                                          _wire_pegboard.Wire._waypoints,  # NOQA
                                                          wire_obj, other_wire,
                                                          own_end, other_end)
        else:
            seam_id_pegboard = own_wp_pegboard = other_wp_pegboard = None
            start_id_pegboard = stop_id_pegboard = None

        part_id = wire_obj.db_obj.part_id
        name = wire_obj.db_obj.name

        circuit_id = wire_obj.db_obj.circuit_id
        if circuit_id is None:
            circuit_id = other_wire.db_obj.circuit_id

        layer_id = wire_obj.db_obj.layer_id
        layer_view_point_id = wire_obj.db_obj.layer_view_position_id
        is_filler_wire = wire_obj.db_obj.is_filler_wire
        is_visible3d = wire_obj.db_obj.is_visible3d
        is_visible2d = wire_obj.db_obj.is_visible2d

        if own_end == 'start':
            orig_start_sibling = wire_obj.stop_sibling
        else:
            orig_start_sibling = wire_obj.start_sibling

        if other_end == 'start':
            other_stop_sibling = other_wire.stop_sibling
        else:
            other_stop_sibling = other_wire.start_sibling

        merged_db = ptables.pjt_wires_table.insert(
            part_id, name, circuit_id,
            start_id_3d, stop_id_3d,
            start_id_2d, stop_id_2d,
            is_visible3d, is_visible2d,
            layer_view_point_id, layer_id, is_filler_wire)

        for i, wp in enumerate(own_wp_3d):
            wp.wire_id = merged_db.db_id
            wp.idx = i

        seam_point_3d = ptables.pjt_points3d_table[seam_id_3d]
        seam_point_3d.wire_id = merged_db.db_id
        seam_point_3d.idx = len(own_wp_3d)

        for i, wp in enumerate(other_wp_3d):
            wp.wire_id = merged_db.db_id
            wp.idx = len(own_wp_3d) + 1 + i

        if pegboard_present:
            _wire_pegboard.Wire._set_start_position_id(merged_db, start_id_pegboard)  # NOQA
            _wire_pegboard.Wire._set_stop_position_id(merged_db, stop_id_pegboard)  # NOQA
            merged_db.is_visible_pegboard = wire_obj.db_obj.is_visible_pegboard

            pegboard_points_table = _wire_pegboard.Wire._points_table(project)  # NOQA

            for i, wp in enumerate(own_wp_pegboard):
                wp.wire_id = merged_db.db_id
                wp.idx = i

            seam_point_pegboard = pegboard_points_table[seam_id_pegboard]
            seam_point_pegboard.wire_id = merged_db.db_id
            seam_point_pegboard.idx = len(own_wp_pegboard)

            for i, wp in enumerate(other_wp_pegboard):
                wp.wire_id = merged_db.db_id
                wp.idx = len(own_wp_pegboard) + 1 + i

        merged_obj = _wire_object_mod.Wire(mainframe, merged_db)

        layout_db = ptables.pjt_wire_layouts_table.insert(seam_id_3d)
        layout_obj = _wire_layout_mod.WireLayout(mainframe, layout_db)
        project.add_wire_layout(layout_obj)

        if pegboard_present:
            layout_db = ptables.pjt_wire_layouts_table.insert(
                point_pegboard_id=seam_id_pegboard)

            layout_obj = _wire_layout_mod.WireLayout(mainframe, layout_db)
            project.add_wire_layout(layout_obj)

        if orig_start_sibling is not None:
            merged_obj.set_sibling(orig_start_sibling, 'start')
            orig_start_sibling.replace_wire(wire_obj, merged_obj)

        if other_stop_sibling is not None:
            merged_obj.set_sibling(other_stop_sibling, 'stop')
            other_stop_sibling.replace_wire(other_wire, merged_obj)

        project.add_wire(merged_obj)

        # wire_markers remain 3D-only, unchanged -- a separate,
        # not-yet-view-agnostic feature (see objects.objects_3d.
        # wire_marker), out of scope for this pass.
        old_ids = (wire_obj.db_obj.db_id, other_wire.db_obj.db_id)
        for marker in project.wire_markers:
            if marker.db_obj.wire_id in old_ids:
                marker.db_obj.wire_id = merged_db.db_id
                marker.obj3d.rebind_wire(merged_db)

        for w in (wire_obj, other_wire):
            if mainframe.get_selected() is w:
                w.set_selected(False)

            w.delete()

        return merged_obj

    @_check_types.do
    def _raw_move_delta(self, anchor: _point.Point,
                        last_pos: _point.Point, delta) -> _point.Point:

        """
        Project *anchor* to screen space, add the raw mouse *delta*,
        unproject back to world space, and return the resulting raw
        (un-locked) world-space delta this frame implies. Ported from
        ``drag_handlers.editor_3d.DragHandler3D._delta3d`` -- identical
        math, moved here since it's genuinely view-agnostic camera
        projection, not 3D-specific.
        """

        anchor_screen = self.canvas.camera.ProjectPoint(anchor)
        depth = anchor_screen.z

        screen_new = anchor_screen + delta
        screen_new.z = depth

        world_hit = self.canvas.camera.UnprojectPoint(screen_new)
        pick_world = self.canvas.camera.UnprojectPoint(anchor_screen)

        if self.pick_offset is None:
            self.pick_offset = anchor - pick_world

        world_hit += self.pick_offset

        return world_hit - last_pos

    @_check_types.do
    def _move_delta(self, anchor: _point.Point,
                    last_pos: _point.Point, delta, aabb):

        """
        The delta actually applied this frame. Default: the raw,
        unlocked projection delta, as-is -- correct for a view whose
        camera never needs axis disambiguation OR a hard axis floor.
        Neither concrete view actually uses this default unmodified
        today: the 3D view overrides it to lock to whichever axis
        dominated once the first few events have settled (see
        ``DragHandler3D._axis_locked_delta3d``, which it delegates to),
        since its free-orbit camera makes a raw screen delta ambiguous;
        the peg-board view overrides it to hard-clamp Y to exactly 0
        every frame (see ``drag_handlers.editor_pegboard.wire.Wire.
        _move_delta``'s own docstring) -- its locked top-down ortho
        camera never needs to CHOOSE an axis the way 3D does, but still
        needs a hard floor against float32 depth-precision drift
        compounding across a drag (confirmed 2026-09-13: the actual
        mechanism behind a live "wire drops below the floor" bug).
        Uniquely named -- no collision risk; a concrete ``Wire``'s own
        override always wins outright regardless of base order, since
        nothing else in the hierarchy defines this name at all.
        """

        return self._raw_move_delta(anchor, last_pos, delta)

    @_check_types.do
    def _apply_budget_clamp(self, moving_points: list,  # NOQA
                            delta: _point.Point) -> _point.Point:

        """
        Clamp *delta* so dragging never stretches a touching wire/
        bundle segment past its remaining length budget -- a peg-board-
        only concept (see ``drag_handlers.editor_pegboard``'s own module
        docstring: "it will not pull the things that are at the other
        ends"). Default (used as-is by the 3D view, which has no such
        constraint): no-op, returns *delta* unchanged.

        **Not yet implemented for peg-board** -- the existing peg-board
        segment-drag (``drag_handlers.editor_pegboard.wire``'s own
        ``Wire._max_scale_within_budget``) computes this per-point
        against ``chain_edges.touching_edges``, but that logic assumes
        the old, always-two-points segment-only plan; generalizing it to
        also cover this shared algorithm's single-point (true-end) case
        is follow-up work, not done here.
        """

        return delta

    @_check_types.do
    def _arm_drag(self, canvas: "_canvas_base.CanvasBase",
                  target: "_wire_object.Wire",  plan: WireDragPlan) -> None:

        """
        Populate this instance's own drag state from *plan*, and
        build the snap-probe set + overlay when the plan's moving point
        is snap-eligible. Call this from the concrete class's own
        ``__init__``, after its own ``super().__init__()`` has already
        run -- this is NOT a constructor itself.
        """

        self.canvas = canvas
        self.target = target

        self._moving = plan.moving
        self._anchor = plan.anchor
        self.last_pos = self._anchor.copy()
        self.end = plan.snap_end

        self._snap_probes = None
        self._overlay = None
        self.snapped_kind = None
        self.snapped_target = None
        self.pick_offset = None

        if self.end is not None:
            wire_part = target.db_obj.part
            if wire_part is not None:
                self._snap_probes = self._SnapProbeSet(
                    canvas.mainframe, wire_part, exclude_wire=target)

                self._overlay = _wire_snap.SnapOverlay(
                    self._get_editor(canvas.mainframe))

    @_check_types.do
    def _disarm_drag(self) -> None:
        """
        Tear down whatever :meth:`_arm_drag` acquired. Call this
        from the concrete class's own ``delete``, before its own
        ``super().delete()`` -- this is NOT ``delete`` itself.
        """

        if self._snap_probes is not None:
            self._snap_probes.close()
            self._snap_probes = None

        if self._overlay is not None:
            self._overlay.deleteLater()
            self._overlay = None

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta, mouse_pos: _point.Point) -> None:
        if self._snap_probes is not None:
            # Hit-test against the real cursor position, not a position
            # reconstructed from the (possibly axis-locked) dragged
            # point's own screen projection -- once axis-locking has
            # engaged, the dragged point's screen position only ever
            # moves along the locked axis, so it drifts further and
            # further from where the mouse actually is.
            picked = _object_picker.find_object(mouse_pos, self.canvas.camera, self.canvas)

            kind, target = _wire_snap.get_snap_info(picked)

            if kind is not None:
                # Purely informational -- never gates the snap/commit,
                # even for a genuine AWG-range mismatch (confirmed
                # 2026-08-06): always allow the connection, just flag a
                # potential issue for the user to resolve afterward.
                wire_part = self.target.db_obj.part
                if kind == 'terminal':
                    _ok, block_msg, warning_msg = (
                        _wire_snap.check_terminal_compat(target, wire_part))

                elif kind == 'splice':
                    _ok, block_msg, warning_msg = (
                        _wire_snap.check_splice_compat(target, wire_part))

                else:
                    block_msg, warning_msg = None, None

                if block_msg:
                    self._overlay.show_message(
                        mouse_pos, block_msg, blocking=True)

                elif warning_msg:
                    self._overlay.show_message(
                        mouse_pos, warning_msg, blocking=False)

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

        move_delta = self._move_delta(
            self._anchor, self.last_pos, delta,
            self._get_view_object(self.target).aabb)

        if move_delta is None:
            return

        move_delta = self._apply_budget_clamp(self._moving, move_delta)

        for point in self._moving:
            point += move_delta

        self._anchor += move_delta
        self.last_pos = self._anchor.copy()
