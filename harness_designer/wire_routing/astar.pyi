# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import numpy as np


def build_tables(
    xs: np.ndarray,
    zs: np.ndarray,
    rects: np.ndarray,
    h_lanes: np.ndarray,
    v_lanes: np.ndarray,
    limit: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    For every node of the grid, whether the step to its left / right /
    down / up neighbour is allowed -- ``(ok_left, ok_right, ok_down,
    ok_up)``, each a flat ``uint8`` array indexed ``i * len(zs) + j``.

    A step is allowed when its destination isn't strictly inside an
    obstacle rect, the edge doesn't cut through one, and the edge doesn't
    run within ``limit`` of, and over a real stretch of, another wire's run.

    All coordinates are ``int64``, scaled by 10 ** 6 (see
    ``wire_routing.routing._SCALE``).

    :param xs: Grid columns, ascending.
    :param zs: Grid rows, ascending.
    :param rects: ``(R, 4)`` -- ``min_x, min_z, max_x, max_z``.
    :param h_lanes: ``(H, 3)`` -- ``z, lo, hi`` of each horizontal run.
    :param v_lanes: ``(V, 3)`` -- ``x, lo, hi`` of each vertical run.
    :param limit: Lane spacing, less its tolerance.
    """
    ...


def astar(
    xs: np.ndarray,
    zs: np.ndarray,
    si: int,
    sj: int,
    gi: int,
    gj: int,
    ok_left: np.ndarray,
    ok_right: np.ndarray,
    ok_down: np.ndarray,
    ok_up: np.ndarray,
    limit: int,
    bend_cost: int,
    forbid_start: int,
    forbid_goal: int
) -> np.ndarray | None:
    """
    4-directional A* from grid node ``(si, sj)`` to ``(gi, gj)``.

    The search state is ``(node, direction of arrival)`` and a path also
    carries its own straight runs, so a route can't turn and run too close
    and parallel to an earlier stretch of itself.

    :param ok_left: Allowed-step tables from :func:`build_tables`.
    :param limit: How close a run may come to another parallel run of the
        same path (the lane spacing, less its tolerance).
    :param bend_cost: Extra cost of every bend.
    :param forbid_start: Step the very first move may not take
        (``0`` left, ``1`` right, ``2`` down, ``3`` up), or ``-1``.
    :param forbid_goal: Step the last move into the goal may not take, or ``-1``.

    :returns: The node indices ``i * len(zs) + j`` of the cheapest path, start
        to goal inclusive, as an ``int32`` array -- or ``None`` if the goal
        can't be reached.
    """
    ...


class Router:
    """
    One drag frame's routing grid, shared by every wire routed in it.

    Holds the grid lines, how many obstacles / other wires' runs block each
    step (as counts, so painting is reversible), and the search buffers --
    all built once, so routing wire after wire only has to paint the wire
    that just settled. See ``wire_routing.routing.RoutingFrame``.

    All coordinates are ``int64``, scaled by 10 ** 6.
    """

    last_pops: int
    """How many states the most recent :meth:`search` expanded."""

    def __init__(self, xs: np.ndarray, zs: np.ndarray, limit: int):
        """
        :param xs: Grid columns, ascending, unique.
        :param zs: Grid rows, ascending, unique.
        :param limit: Lane spacing, less its tolerance.
        """
        ...

    @property
    def shape(self) -> tuple[int, int]:
        ...

    def paint_rects(self, rects: np.ndarray, delta: int) -> None:
        """Add (``delta`` 1) or take back (``-1``) obstacle rects -- ``(R, 4)``
        of ``min_x, min_z, max_x, max_z``."""
        ...

    def paint_lanes(self, h_lanes: np.ndarray, v_lanes: np.ndarray, delta: int) -> None:
        """Add (``delta`` 1) or take back (``-1``) other wires' runs --
        ``(H, 3)`` of ``z, lo, hi`` and ``(V, 3)`` of ``x, lo, hi``."""
        ...

    def paint_pack(self, h_lanes: np.ndarray, v_lanes: np.ndarray, delta: int) -> None:
        """Add (``delta`` 1) or take back (``-1``) sibling runs to PACK against
        -- same layout as :meth:`paint_lanes`. They block nothing: once any are
        painted, a step that is not one lane spacing beside one costs an extra
        sixteenth of its length, so a route hugs its siblings where it can."""
        ...

    def search(
        self,
        si: int,
        sj: int,
        gi: int,
        gj: int,
        bend_cost: int,
        forbid_start: int,
        forbid_goal: int,
        use_lanes: bool
    ) -> np.ndarray | None:
        """
        A* from grid node ``(si, sj)`` to ``(gi, gj)`` over what is currently
        painted -- see :func:`astar`.

        :param use_lanes: ``False`` ignores the wire-lane counts (housings
            still block) -- the last-resort retry.

        :returns: Node indices ``i * nz + j``, start to goal, as ``int32`` --
            or ``None`` if unreachable.
        """
        ...
