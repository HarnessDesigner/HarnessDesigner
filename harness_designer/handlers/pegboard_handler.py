# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for adding peg-board waypoints along an
existing bundle strand.

Mirrors ``handlers.bundle_layout_handler.AddBundleLayoutHandler``'s
``hover``/``capture_position``/``release_capture``/``cancel`` shape (see
``HandlerBase``), adapted for the peg board's own 2D top-down camera
instead of the 3D editor's -- ``HandlerBase.__init__`` hardcodes
``self.camera = mainframe.editor3d.camera``, which is wrong here, so
:class:`AddWaypointHandler` overrides ``self.camera`` right after calling
``super().__init__`` to the peg-board canvas's own ``Camera2D``.

Unlike every other ``HandlerBase`` subclass in this codebase, this one is
not driven by ``mainframe``'s generic ``_obj_handler``/editor3d-mouse-event
dispatch chain (``ui/mainframe.py``'s ``_on_tool_mode_change``/the ~25
``if self._obj_handler is not None: ...`` call sites) -- there is no
peg-board equivalent of that dispatch table yet, since the peg board
editor's dock/toolbar wiring is explicitly out-of-scope "later task" work
throughout this feature's plan (``tranquil-orbiting-spindle.md``). Instead
it is driven directly by
:class:`~harness_designer.gl.canvas_pegboard.mouse_handler.MouseHandlerPegBoard`,
which is the concrete, testable entry point today
(:meth:`~harness_designer.gl.canvas_pegboard.mouse_handler.MouseHandlerPegBoard.start_add_waypoint`).
A future peg-board toolbar action can activate this exactly the way
``mainframe._on_tool_mode_change`` instantiates every other ``Add*Handler``
on a toolbar id -- the handler class itself doesn't need to change either
way.
"""

from typing import TYPE_CHECKING

from . import handler_base as _handler_base
from ..geometry import point as _point


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..gl.canvas_pegboard import canvas as _canvas
    from ..gl.canvas_pegboard import layout_graph as _layout_graph
    from ..database.project_db.pjt_point_peg import PJTPointPeg


# Snap threshold for "close enough to a strand" hit-testing, world units
# (mm) -- mirrors bundle_layout_handler._SNAP_THRESHOLD's role (that one is
# 3D/world-units against real bundle cylinders; this is the 2D peg-board
# equivalent against PegboardEdge segments).
_SNAP_THRESHOLD_MM = 5.0
_SNAP_THRESHOLD_SQ = _SNAP_THRESHOLD_MM ** 2


def _find_edge_at_point(edges: list, world_pos: "_point.Point"):
    """Return the closest :class:`PegboardEdge` to *world_pos*, within
    :data:`_SNAP_THRESHOLD_MM`, via point-to-segment nearest-distance --
    the same technique as
    ``handlers.bundle_layout_handler._find_bundle``'s closest-point math,
    applied in the peg board's 2D (x, z) plane against edge endpoints
    instead of 3D bundle cylinders.

    :param edges: Every currently live edge (``Canvas.edges``).
    :type edges: list[:class:`_layout_graph.PegboardEdge`]
    :param world_pos: Click position in world coordinates (``.y`` stands
        in for world Z, same convention used throughout
        ``gl.canvas_pegboard``).
    :type world_pos: :class:`_point.Point`
    :returns: ``(edge_index, edge, ratio, clicked_x, clicked_z)`` for the
        closest edge within the snap threshold, or ``None``. *ratio* is
        the clicked point's fractional position from ``edge.node_a`` to
        ``edge.node_b`` (0.0 at ``node_a``, 1.0 at ``node_b``).
    :rtype: tuple | None
    """
    best = None
    best_dist_sq = _SNAP_THRESHOLD_SQ

    for index, edge in enumerate(edges):
        x1, z1 = edge.node_a.x, edge.node_a.z
        x2, z2 = edge.node_b.x, edge.node_b.z

        dx, dz = x2 - x1, z2 - z1
        seg_len_sq = dx * dx + dz * dz
        if seg_len_sq < 1e-8:
            continue

        t = ((world_pos.x - x1) * dx + (world_pos.y - z1) * dz) / seg_len_sq
        t = max(0.0, min(1.0, t))

        cx, cz = x1 + t * dx, z1 + t * dz
        dist_sq = (world_pos.x - cx) ** 2 + (world_pos.y - cz) ** 2

        if dist_sq < best_dist_sq:
            best_dist_sq = dist_sq
            best = (index, edge, t, cx, cz)

    return best


def _insert_waypoint_on_edge(
    project,
    edge: "_layout_graph.PegboardEdge",
    x: float,
    z: float,
) -> "PJTPointPeg":
    """Insert a new ``pjt_points_peg`` bundle-waypoint row splitting *edge*.

    No length-budget bookkeeping happens here at all: each edge's
    ``max_length_mm`` is computed live, proportionally, the next time the
    graph is rebuilt (see ``layout_graph._build_chain_edges``) --
    :meth:`AddWaypointHandler.release_capture` already triggers that
    rebuild (``Canvas.load_project()``) immediately after calling this, so
    there's nothing to split/correct here up front any more.

    Index handling: *edge* may sit anywhere in its bundle's chain, not
    just at the end. If ``edge.node_b`` is itself an existing waypoint
    (i.e. this edge is *not* the last one before the stop node), the new
    row is inserted right before it; otherwise (``node_b`` is the
    bundle's stop node) it's simply appended at the end. Every existing
    waypoint from the insertion point onward has its ``idx`` incremented
    by 1 to make room, walked in *reverse* order (highest ``idx`` first)
    purely so no two rows are ever briefly holding the same ``idx`` value
    mid-loop, even though ``pjt_points_peg`` has no uniqueness constraint
    on it today -- cheap insurance against a future schema change adding
    one.

    :param project: The currently open project (``mainframe.project``).
    :type project: :class:`harness_designer.objects.project.Project`
    :param edge: The edge being split.
    :type edge: :class:`_layout_graph.PegboardEdge`
    :param x: Peg-board X coordinate for the new waypoint.
    :type x: float
    :param z: Peg-board Z coordinate for the new waypoint (stored as the
        row's ``y`` field -- see ``pjt_point_peg.py``).
    :type z: float
    :returns: The newly created waypoint row.
    :rtype: :class:`PJTPointPeg`
    """
    points_table = project.ptables.pjt_points_peg_table
    bundle_id = edge.bundle_id
    existing = points_table.for_bundle(bundle_id)

    if edge.node_b.waypoint_id is not None:
        insert_index = next(
            i for i, row in enumerate(existing)
            if row.db_id == edge.node_b.waypoint_id)
    else:
        # node_b is the bundle's stop node -- this is the last edge in the
        # chain, so the new waypoint simply appends at the end.
        insert_index = len(existing)

    for row in reversed(existing[insert_index:]):
        row.idx = row.idx + 1

    return points_table.insert(x, z, bundle_id=bundle_id, idx=insert_index)


class AddWaypointHandler(_handler_base.HandlerBase):
    """Handle interactive creation of a peg-board waypoint by clicking
    along an existing bundle strand.

    A single click (mouse-down) both creates the new
    ``pjt_points_peg`` bundle-waypoint row (:meth:`release_capture`) and hands off
    directly into the peg board's own continuous-drag mechanism (via
    ``Canvas.arm_waypoint_drag``), so the same press-drag-release gesture
    that placed the waypoint can also fine-tune its position before
    release -- exactly like
    ``handlers.bundle_layout_handler.AddBundleLayoutHandler`` does for 3D
    bundle layouts. See :meth:`gl.canvas_pegboard.mouse_handler.
    MouseHandlerPegBoard.on_left_down` for the exact call sequence
    (``hover`` -> ``capture_position`` -> ``release_capture``, all within
    one mouse-down).
    """

    def __init__(self, mainframe: "_ui.MainFrame", canvas: "_canvas.Canvas"):
        """Initialise the :class:`AddWaypointHandler` instance.

        :param mainframe: Main application frame that owns the project.
        :type mainframe: "_ui.MainFrame"
        :param canvas: The peg board canvas this click happened on.
        :type canvas: :class:`_canvas.Canvas`
        """
        super().__init__(mainframe, None)

        # HandlerBase.__init__ sets self.camera to the 3D editor's camera
        # -- wrong for this 2D top-down interaction. Override with the peg
        # board's own Camera2D right after.
        self.canvas = canvas
        self.camera = canvas.camera

        self._hit_edge_index: int = None

    def hover(self, mouse_pos: "_point.Point"):
        """Hit-test *mouse_pos* (screen coordinates) against every live
        edge on the peg board (:func:`_find_edge_at_point`), recording the
        closest hit (if any) for :meth:`release_capture`.

        :param mouse_pos: Mouse position, screen coordinates.
        :type mouse_pos: :class:`_point.Point`
        """
        world_pos = self.camera.screen_to_world(mouse_pos)
        hit = _find_edge_at_point(self.canvas.edges, world_pos)

        if hit is None:
            self._hit_edge_index = None
            return

        index, _edge, _ratio, _cx, _cz = hit
        self._hit_edge_index = index

    def release_capture(self) -> None:
        """Finalize placement: insert the new waypoint row at the
        captured position and hand off into a continuous drag.

        No-op (but still finalized) when the captured click never landed
        near any strand -- mirrors
        ``AddBundleLayoutHandler.release_capture``'s own "nothing snapped,
        do nothing" guard.
        """
        if self._finalized:
            return

        if self._captured_position is None:
            return

        self._finalized = True

        if self._hit_edge_index is None:
            return

        project = self.mainframe.project
        edge = self.canvas.edges[self._hit_edge_index]

        world_pos = self.camera.screen_to_world(self._captured_position)
        if self.canvas.config.grid.snap:
            world_pos = self.canvas.snap_to_grid(world_pos)

        new_row = _insert_waypoint_on_edge(
            project, edge, float(world_pos.x), float(world_pos.y))

        # Discrete, infrequent action (not a per-frame drag update) -- a
        # full rebuild here is fine, unlike during a live drag. Rebuilds
        # self.canvas's live node/edge/strand-draw state so the newly
        # split bundle renders correctly and the new waypoint has a
        # matching live PegboardNode to hand off the drag to below.
        self.canvas.load_project(project)

        new_node = None
        for node in self.canvas.nodes:
            if node.waypoint_id == new_row.db_id:
                new_node = node
                break

        if new_node is not None:
            self.canvas.arm_waypoint_drag(new_node)

    def cancel(self):
        """Cancel placement.

        Overrides ``HandlerBase.cancel``'s default (``self.obj.delete()``)
        since this handler never creates a preview ``self.obj`` -- there
        is nothing to clean up beyond forgetting the last hit-test.
        """
        self._hit_edge_index = None
