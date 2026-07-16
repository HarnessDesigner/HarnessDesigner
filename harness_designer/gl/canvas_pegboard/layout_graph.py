# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Peg board bundle-graph collection -- nodes/edges/strands for the bundle
strand and bare-wire rendering + drag-clamp/pull-mode system.

Anchor collection (housing/splice/transition/bare-terminal placement) used
to live in this module (``PegboardAnchor``/``build_anchors``/the per-type
``_housing_anchors``/``_splice_anchors``/``_transition_anchors``/
``_bare_terminal_anchors`` builders, plus the ``_pegboard_xz``/
``_pegboard_rotation``/``_apply_user_spin``/``_footprint`` helpers they used)
-- that has moved to :mod:`harness_designer.objects.objectspeg`
(``basepeg.py``'s ``BasePeg`` base class -- live ``position``/``angle``/
``aabb`` properties, immediate DB writes via bound ``Point``/``Angle`` --
plus each anchor type's own dedicated ``housing.py``/``splice.py``/
``transition.py``/``terminal.py`` subclass, constructed directly in that
type's ``ObjectBase`` subclass ``__init__`` -- e.g. ``objects.housing.
Housing.__init__``'s ``self.objpeg = ...`` -- alongside ``obj2d``/``obj3d``,
not via a separate factory function), as part of folding peg-board anchors
into ``ObjectBase`` as a real ``objpeg`` sibling to ``obj2d``/``obj3d``
(replacing the throwaway ``PegboardAnchor`` dataclass/bulk-rebuild model
with a persistent per-object wrapper). Every other ``ObjectBase`` subclass
gets its own dedicated do-nothing ``objectspeg`` class too (never a single
shared stub) -- see ``objects.objectspeg.basepeg.BasePeg``'s docstring.
Everything below this module's
scope -- the bundle-graph/waypoint/drag-clamp/pull-mode system -- is
unchanged by that refactor: a rendered strand spans a graph edge between two
nodes that may be peg-board-only waypoints with no ``ObjectBase`` at all, so
"one ``ObjectBase`` = one board anchor" doesn't apply here. The only change
this module needed was how ``_resolve_chain_endpoint``/``build_bundle_graph``
resolve "does this ``point3d_id`` have a live anchor" -- callers now pass a
dict built from ``gl.canvas_pegboard.canvas.Canvas._anchors`` (the
incrementally-maintained live anchor list) instead of a dict built from this
module's former ``build_anchors()`` return value; the dict shape
(``{point3d_id: anchor}``) and every function below is otherwise unchanged.
"""

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ... import color as _color


if TYPE_CHECKING:
    from ...objects import project as _project


@dataclass
class BundleStrand:
    """One renderable bundle-cover strand segment.

    ``x1``/``z1``/``x2``/``z2`` are a one-time snapshot of the segment's
    endpoints at build time (from :func:`build_bundle_strands_for_edges`,
    the function actually used by ``Canvas`` -- the older, independent
    :func:`build_bundle_strands` is unused dead code, superseded when
    Phase 3 added waypoints/drag). ``Canvas._render_bundle_strands``
    reads ``width``/``color`` from this dataclass but gets *position*
    live from the corresponding :class:`PegboardEdge`'s own node x/z
    instead (always current, drag or not) -- so these four fields go
    stale the moment a drag moves anything, by design; nothing reads them
    after construction.
    """

    x1: float
    z1: float
    x2: float
    z2: float
    width: float
    color: "_color.Color"


@dataclass
class BareWireStrand:
    """One renderable thin bare-wire strand (Phase 2).

    Drawn from the nearest endpoint of the owning bundle segment to the
    bare terminal's own anchor position -- see :func:`build_bare_wire_strands`.
    """

    x1: float
    z1: float
    x2: float
    z2: float
    width: float
    color: "_color.Color"


@dataclass
class PegboardNode:
    """One point in a bundle's peg-board path (Phase 3).

    Either an anchor (housing/splice/transition/bare-terminal, has a real
    ``point3d_id`` via its own ``objects.objectspeg.basepeg.BasePeg``
    subclass) or a peg-board-only waypoint (no 3D counterpart, backed by a
    ``pjt_points_peg`` row with a non-``NULL`` ``bundle_id``) -- exactly
    one of ``anchor``/``waypoint_id`` is set, the other is ``None``.
    """

    x: float
    z: float
    anchor: object
    waypoint_id: "int | None"


@dataclass
class PegboardEdge:
    """One straight segment between two consecutive :class:`PegboardNode`\\ s
    along a bundle's peg-board chain (Phase 3).

    ``max_length_mm`` is this edge's length budget -- computed live (never
    persisted) as the bundle's own
    :attr:`~harness_designer.database.project_db.pjt_bundle.PJTBundle.length_mm`
    split proportionally by this edge's current 2D distance against the
    chain's total 2D distance (see :func:`_build_chain_edges`) -- so
    summing every edge's ``max_length_mm`` for one bundle always equals
    ``bundle.length_mm`` exactly. The drag-clamp system depends on this
    invariant.
    """

    node_a: PegboardNode
    node_b: PegboardNode
    max_length_mm: float
    bundle_id: int


# Phase 2 bundle-strand/bare-wire-strand fallback constants -- see
# build_bundle_strands()/build_bare_wire_strands() docstrings for why each
# of these exists (all work around known, out-of-scope pre-existing bugs
# or fill in for data that legitimately may not be easily derivable yet).
_DEFAULT_BUNDLE_WIDTH_MM = 5.0
_MIN_SANE_BUNDLE_WIDTH_MM = 1.0
_MAX_SANE_BUNDLE_WIDTH_MM = 100.0

_DEFAULT_BARE_WIRE_WIDTH_MM = 1.5
_MIN_SANE_WIRE_WIDTH_MM = 0.05
_MAX_SANE_WIRE_WIDTH_MM = 50.0

_FALLBACK_STRAND_COLOR_RGB = (128, 128, 128)


def _fallback_strand_color() -> "_color.Color":
    """Mid-gray fallback used whenever a strand's real color can't be
    resolved (missing catalog part, missing color field, etc.)."""
    r, g, b = _FALLBACK_STRAND_COLOR_RGB
    return _color.Color(r, g, b)


def _safe_bundle_width(bundle) -> float:
    """Return a safe strand width (mm) for *bundle*.

    ``PJTBundle.diameter`` has a known, separately-tracked pre-existing bug
    (see ``pjt_bundle.py``): its getter does
    ``pjt_concentrics_table.select('id', bundle_id=...)`` -- selecting the
    concentric row's own database id, not any real diameter column -- so it
    returns a nonsensical number (or raises, depending on data state). This
    function is a **local, Phase-2-only workaround**, not a fix: it tries
    ``bundle.diameter`` and falls back to a fixed default whenever the call
    raises or the result isn't a sane physical diameter, so a bad value
    never produces an invisible (0/negative) or absurdly-huge strand.
    Do NOT change ``PJTBundle.diameter`` itself to "fix" this.
    """
    try:
        value = float(bundle.diameter)
    except Exception:  # NOQA
        return _DEFAULT_BUNDLE_WIDTH_MM

    if not (_MIN_SANE_BUNDLE_WIDTH_MM <= value <= _MAX_SANE_BUNDLE_WIDTH_MM):
        return _DEFAULT_BUNDLE_WIDTH_MM

    return value


def _bundle_strand_color(bundle) -> "_color.Color":
    """Return *bundle*'s cover color, falling back to mid-gray.

    Falls back whenever ``bundle.part`` (the catalog ``BundleCover`` row)
    or its ``.color`` (``ColorMixin``) can't be resolved -- never crashes
    the render for a data gap.
    """
    try:
        part = bundle.part
    except Exception:  # NOQA
        return _fallback_strand_color()

    if part is None:
        return _fallback_strand_color()

    try:
        color = part.color
    except Exception:  # NOQA
        return _fallback_strand_color()

    if color is None:
        return _fallback_strand_color()

    return color


def _resolve_chain_endpoint(
    point3d_id: int,
    anchors_by_point3d_id: dict,
    project: "_project.Project",
) -> "PegboardNode":
    """Resolve one bundle endpoint (``start_position3d_id``/
    ``stop_position3d_id``) to a :class:`PegboardNode`.

    If an already-built anchor claims this ``point3d_id`` (the endpoint is
    a housing/splice/transition/bare-terminal), the node wraps that anchor
    and reuses its (already persistence-aware) ``.x``/``.z`` position.
    Otherwise this is a plain inline point with nothing else referencing it
    (e.g. a mid-chain ``PJTBundle`` split with no ``PJTBundleLayout``/anchor
    at the shared point) -- fall back to the raw ``pjt_points3d`` row's own
    ``.x``/``.z`` directly; no anchor, no waypoint.

    :param point3d_id: The endpoint's ``pjt_points3d`` row id.
    :type point3d_id: int
    :param anchors_by_point3d_id: Every currently live anchor, keyed by its
        own ``point3d_id`` -- see
        ``gl.canvas_pegboard.canvas.Canvas._anchors``.
    :type anchors_by_point3d_id: dict[int, :class:`~harness_designer.objects.objectspeg.basepeg.BasePeg`]
    :param project: The currently open project (``mainframe.project``).
    :type project: :class:`harness_designer.objects.project.Project`
    :returns: The resolved endpoint node.
    :rtype: :class:`PegboardNode`
    """
    anchor = anchors_by_point3d_id.get(point3d_id)
    if anchor is not None:
        return PegboardNode(
            x=anchor.position.x, z=anchor.position.z, anchor=anchor, waypoint_id=None)

    point_row = project.ptables.pjt_points3d_table[point3d_id]
    return PegboardNode(x=float(point_row.x), z=float(point_row.z),
                         anchor=None, waypoint_id=None)


def build_bundle_chain(
    bundle,
    anchors_by_point3d_id: dict,
    project: "_project.Project",
) -> list["PegboardNode"]:
    """Build the ordered node chain for one :class:`PJTBundle` row.

    ``[start_node, *waypoint_nodes_in_sequence_order, stop_node]`` --
    start/stop resolved via :func:`_resolve_chain_endpoint`; waypoints
    from ``pjt_points_peg_table.for_bundle()`` (already sorted by
    ``.idx``), one :class:`PegboardNode` each (``anchor=None``, since a
    waypoint has no 3D counterpart by definition).

    :param bundle: The bundle row whose chain to build.
    :type bundle: :class:`~harness_designer.database.project_db.pjt_bundle.PJTBundle`
    :param anchors_by_point3d_id: Every currently live anchor, keyed by its
        own ``point3d_id`` (see
        ``gl.canvas_pegboard.canvas.Canvas._anchors``).
    :type anchors_by_point3d_id: dict[int, :class:`~harness_designer.objects.objectspeg.basepeg.BasePeg`]
    :param project: The currently open project (``mainframe.project``).
    :type project: :class:`harness_designer.objects.project.Project`
    :returns: The bundle's full ordered node chain.
    :rtype: list[:class:`PegboardNode`]
    """
    start_node = _resolve_chain_endpoint(
        bundle.start_position3d_id, anchors_by_point3d_id, project)
    stop_node = _resolve_chain_endpoint(
        bundle.stop_position3d_id, anchors_by_point3d_id, project)

    waypoint_rows = project.ptables.pjt_points_peg_table.for_bundle(bundle.db_id)
    waypoint_nodes = [
        PegboardNode(x=float(row.x), z=float(row.z), anchor=None, waypoint_id=row.db_id)
        for row in waypoint_rows
    ]

    return [start_node, *waypoint_nodes, stop_node]


_MIN_CHAIN_DISTANCE_MM = 1e-9


def _build_chain_edges(
    bundle,
    nodes: list["PegboardNode"],
) -> list["PegboardEdge"]:
    """Build the length-budgeted edges between every consecutive pair of
    *nodes* in one bundle's chain (see :func:`build_bundle_chain`).

    Each edge's ``max_length_mm`` is computed live, never persisted -- the
    bundle's own real total length (``bundle.length_mm``, itself computed
    live from the real 3D start/stop points) split proportionally by this
    edge's *current* 2D distance against the sum of every edge's current
    2D distance in the chain. A waypoint has no 3D position at all, so
    there's no independent 3D distance to derive a per-edge sub-length
    from directly -- this proportional split is the substitute, recomputed
    fresh every time the graph is rebuilt (:func:`build_bundle_graph`,
    called from ``Canvas.load_project()``) rather than stored anywhere.

    Deliberately NOT recomputed mid-drag (only at a full graph rebuild) --
    doing so continuously would make the edge touching the very node being
    dragged chase its own tail (its own budget growing right along with
    the distance it's supposed to be constraining), defeating the whole
    point of the clamp.

    Zero interior waypoints falls out of the same formula with no special
    case: a single edge spanning the whole chain is also its own entire
    denominator, so it gets exactly 100% of ``bundle.length_mm``.

    :param bundle: The bundle row these edges belong to.
    :type bundle: :class:`~harness_designer.database.project_db.pjt_bundle.PJTBundle`
    :param nodes: This bundle's chain, as built by :func:`build_bundle_chain`.
    :type nodes: list[:class:`PegboardNode`]
    :returns: One :class:`PegboardEdge` per consecutive node pair.
    :rtype: list[:class:`PegboardEdge`]
    """
    total_length_mm = bundle.length_mm
    pairs = list(zip(nodes[:-1], nodes[1:]))

    distances = [
        math.hypot(node_b.x - node_a.x, node_b.z - node_a.z)
        for node_a, node_b in pairs
    ]
    total_distance = sum(distances)

    if total_distance < _MIN_CHAIN_DISTANCE_MM:
        # Degenerate (every node coincident) -- split the real length
        # evenly rather than dividing by zero.
        even_share = total_length_mm / len(pairs)
        return [
            PegboardEdge(node_a=node_a, node_b=node_b,
                        max_length_mm=even_share, bundle_id=bundle.db_id)
            for node_a, node_b in pairs
        ]

    return [
        PegboardEdge(
            node_a=node_a, node_b=node_b,
            max_length_mm=total_length_mm * (distance / total_distance),
            bundle_id=bundle.db_id,
        )
        for (node_a, node_b), distance in zip(pairs, distances)
    ]


def build_bundle_graph(
    project: "_project.Project",
    anchors_by_point3d_id: dict,
) -> tuple[list["PegboardNode"], list["PegboardEdge"]]:
    """Build the full peg-board node/edge graph for every bundle in *project*.

    Shared, top-level entry point for rendering (see
    :func:`build_bundle_strands`) and the drag-clamp task (Phase 3,
    ``gl.canvas_pegboard.canvas.Canvas``/``mouse_handler.py``) -- walks every
    :class:`PJTBundle` row via :func:`build_bundle_chain`/
    :func:`_build_chain_edges`.

    :param project: The currently open project (``mainframe.project``).
    :type project: :class:`harness_designer.objects.project.Project`
    :param anchors_by_point3d_id: Every currently live anchor, keyed by its
        own ``point3d_id`` -- built from
        ``gl.canvas_pegboard.canvas.Canvas._anchors`` (the incrementally-
        maintained live anchor list; this parameter is required, unlike
        before this refactor, since there is no longer a
        ``build_anchors()`` this function can fall back to building
        internally).
    :type anchors_by_point3d_id: dict[int, :class:`~harness_designer.objects.objectspeg.basepeg.BasePeg`]
    :returns: ``(all_nodes, all_edges)`` across every bundle.
    :rtype: tuple[list[:class:`PegboardNode`], list[:class:`PegboardEdge`]]
    """
    all_nodes = []
    all_edges = []

    for bundle in project.ptables.pjt_bundles_table:
        if bundle.start_position3d is None or bundle.stop_position3d is None:
            continue

        nodes = build_bundle_chain(bundle, anchors_by_point3d_id, project)
        edges = _build_chain_edges(bundle, nodes)

        all_nodes.extend(nodes)
        all_edges.extend(edges)

    return all_nodes, all_edges


def build_bundle_strands(
    project: "_project.Project",
    anchors_by_point3d_id: dict,
) -> list["BundleStrand"]:
    """Build one flat :class:`BundleStrand` per peg-board graph edge.

    Phase 3 upgrade from Phase 2's single straight start->stop segment: a
    bundle with waypoints now produces one strand per :class:`PegboardEdge`
    in its chain (see :func:`build_bundle_chain`/:func:`_build_chain_edges`),
    so a 2-waypoint bundle becomes 3 straight segments forming a bent
    polyline. Every segment of the same bundle reuses the same width/color
    (:func:`_safe_bundle_width`/:func:`_bundle_strand_color`) -- same
    workarounds as Phase 2, unchanged.

    :param project: The currently open project (``mainframe.project``).
    :type project: :class:`harness_designer.objects.project.Project`
    :param anchors_by_point3d_id: Every currently live anchor, keyed by its
        own ``point3d_id`` (see
        ``gl.canvas_pegboard.canvas.Canvas._anchors``).
    :type anchors_by_point3d_id: dict[int, :class:`~harness_designer.objects.objectspeg.basepeg.BasePeg`]
    :returns: One :class:`BundleStrand` per edge, across every bundle.
    :rtype: list[:class:`BundleStrand`]
    """
    strands = []

    for bundle in project.ptables.pjt_bundles_table:
        if bundle.start_position3d is None or bundle.stop_position3d is None:
            continue

        width = _safe_bundle_width(bundle)
        color = _bundle_strand_color(bundle)

        nodes = build_bundle_chain(bundle, anchors_by_point3d_id, project)
        edges = _build_chain_edges(bundle, nodes)

        for edge in edges:
            strands.append(BundleStrand(
                x1=edge.node_a.x, z1=edge.node_a.z,
                x2=edge.node_b.x, z2=edge.node_b.z,
                width=width,
                color=color,
            ))

    return strands


def build_bundle_strands_for_edges(
    project: "_project.Project",
    edges: list["PegboardEdge"],
) -> list["BundleStrand"]:
    """Build one :class:`BundleStrand` per already-built *edge*, in the same
    order (Phase 3).

    Unlike :func:`build_bundle_strands` (which independently re-walks every
    bundle's chain/edges from scratch), this takes an *edges* list the
    caller already has -- e.g. from :func:`build_bundle_graph` -- and
    produces exactly one strand per edge, at the same index. This 1:1
    index correspondence is what lets
    ``gl.canvas_pegboard.canvas.Canvas`` cheaply map "which edge is
    touching a dragged node" to "which strand-draw VBO to
    :meth:`~harness_designer.gl.vbo.NonPooledVBOHandler.update`" without
    rebuilding the whole graph on every mouse-move.

    Each edge's own ``bundle_id`` is used to look up its owning
    :class:`~harness_designer.database.project_db.pjt_bundle.PJTBundle`
    row (cached per call, since a multi-waypoint bundle contributes
    several edges that all share one bundle) for width/color -- same
    :func:`_safe_bundle_width`/:func:`_bundle_strand_color` workarounds as
    :func:`build_bundle_strands`, unchanged.

    :param project: The currently open project (``mainframe.project``).
    :type project: :class:`harness_designer.objects.project.Project`
    :param edges: Every edge to build a strand for, e.g. the second element
        of :func:`build_bundle_graph`'s return value.
    :type edges: list[:class:`PegboardEdge`]
    :returns: One :class:`BundleStrand` per edge, same order/length as
        *edges*.
    :rtype: list[:class:`BundleStrand`]
    """
    strands = []
    bundle_cache: dict = {}

    for edge in edges:
        bundle = bundle_cache.get(edge.bundle_id)
        if bundle is None:
            bundle = project.ptables.pjt_bundles_table[edge.bundle_id]
            bundle_cache[edge.bundle_id] = bundle

        width = _safe_bundle_width(bundle)
        color = _bundle_strand_color(bundle)

        strands.append(BundleStrand(
            x1=edge.node_a.x, z1=edge.node_a.z,
            x2=edge.node_b.x, z2=edge.node_b.z,
            width=width,
            color=color,
        ))

    return strands


def _safe_bare_wire_width(wire) -> float:
    """Return a safe strand width (mm) for a bare-terminated *wire*.

    Tries the wire's own catalog part's ``od_mm`` (outer diameter, mm --
    an existing, easy-to-find field on ``global_db.wire.Wire``, not a new
    derivation). Falls back to a small fixed default whenever the part/
    field is missing or the value isn't a sane physical wire diameter --
    this is a deliberately simple Phase-2 approximation, not an attempt to
    derive OD from conductor size/insulation wall thickness.
    """
    try:
        part = wire.part
    except Exception:  # NOQA
        part = None

    if part is not None:
        try:
            value = part.od_mm
        except Exception:  # NOQA
            value = None

        if value is not None:
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = None

            if value is not None and _MIN_SANE_WIRE_WIDTH_MM <= value <= _MAX_SANE_WIRE_WIDTH_MM:
                return value

    return _DEFAULT_BARE_WIRE_WIDTH_MM


def _bare_wire_strand_color(wire) -> "_color.Color":
    """Return *wire*'s own insulation color, falling back to mid-gray."""
    try:
        part = wire.part
    except Exception:  # NOQA
        return _fallback_strand_color()

    if part is None:
        return _fallback_strand_color()

    try:
        color = part.color
    except Exception:  # NOQA
        return _fallback_strand_color()

    if color is None:
        return _fallback_strand_color()

    return color


def build_bare_wire_strands(project: "_project.Project") -> list["BareWireStrand"]:
    """Build one thin :class:`BareWireStrand` per bare-terminated wire end.

    Implements the plan's visibility-filtering "bundle-with-bare-terminal-
    exception" rule (``visibility.py`` section): for every :class:`PJTBundle`,
    for every wire inside it (``PJTBundle.wires``), for every terminal that
    wire resolves to (``PJTWire.terminals`` -- looks the wire's
    ``start_position3d_id``/``stop_position3d_id`` up against
    ``pjt_terminals.wire_point3d_id``, i.e. "which terminal, if any, is
    attached to each end of this wire"), a terminal with ``cavity_id is
    None`` is bare/not-seated. For each such bare end, draws a strand from
    whichever of the bundle's own ``start_position3d``/``stop_position3d``
    is geometrically nearer (straight-line XZ distance) to the bare
    terminal's own ``position3d``, out to that terminal's position --
    i.e. "the individual wire exiting the bundle to reach its bare
    terminal". Wires with no bare end contribute nothing. Standalone wires
    never added to any bundle are out of scope (per the plan).

    :param project: The currently open project (``mainframe.project``).
    :type project: :class:`harness_designer.objects.project.Project`
    :returns: One :class:`BareWireStrand` per bare-terminated wire end.
    :rtype: list[:class:`BareWireStrand`]
    """
    strands = []

    for bundle in project.ptables.pjt_bundles_table:
        b_p1 = bundle.start_position3d
        b_p2 = bundle.stop_position3d
        if b_p1 is None or b_p2 is None:
            continue

        b_x1, b_z1 = float(b_p1.x), float(b_p1.z)
        b_x2, b_z2 = float(b_p2.x), float(b_p2.z)

        try:
            wires = bundle.wires
        except Exception:  # NOQA
            continue

        for wire in wires:
            try:
                terminals = wire.terminals
            except Exception:  # NOQA
                continue

            for terminal in terminals:
                if terminal.cavity_id is not None:
                    continue

                term_pos = terminal.position3d
                if term_pos is None:
                    continue

                tx, tz = float(term_pos.x), float(term_pos.z)

                dist1 = math.hypot(tx - b_x1, tz - b_z1)
                dist2 = math.hypot(tx - b_x2, tz - b_z2)

                if dist1 <= dist2:
                    anchor_x, anchor_z = b_x1, b_z1
                else:
                    anchor_x, anchor_z = b_x2, b_z2

                width = _safe_bare_wire_width(wire)
                color = _bare_wire_strand_color(wire)

                strands.append(BareWireStrand(
                    x1=anchor_x, z1=anchor_z,
                    x2=tx, z2=tz,
                    width=width,
                    color=color,
                ))

    return strands
