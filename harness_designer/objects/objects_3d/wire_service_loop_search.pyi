# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import numpy as np


KIND_BOX: int
"""The candidate's real shape is its box (another loop, a marker)."""

KIND_CYLINDER: int
"""The candidate's real shape is the cylinder inscribed in its box along the
box's z axis (a wire section)."""


class LoopSearch:
    """See the module docstring of ``wire_service_loop_search.pyx``.

    One instance per move session: it holds every box the loop can hit and
    answers each ``WireServiceLoop._resolve_collision`` of that session. A
    candidate collides only when its box overlaps the loop's box AND the
    loop's mesh touches its real shape.
    """

    def __init__(
        self,
        boxes: np.ndarray | list[np.ndarray],
        kinds: list[int] | np.ndarray,
        local_obb: np.ndarray,
        scale: np.ndarray,
        loop_vertices: np.ndarray
    ):
        """
        :param boxes: Every box the loop can hit, ``(K, 8, 3)`` or a list of
            ``(8, 3)`` arrays, in the bounds pool's corner order (0 = min
            corner, 1 toggles x, 3 toggles y, 4 toggles z); may be empty.
        :param kinds: ``K`` ints, ``KIND_BOX`` or ``KIND_CYLINDER``, one per
            box.
        :param local_obb: The loop mesh's own ``(8, 3)`` OBB, unscaled.
        :param scale: The loop's ``(3,)`` scale; must be uniform.
        :param loop_vertices: The loop mesh's points, unscaled, ``(M, 3)``
            (a triangle soup is fine).
        """
        ...

    def pose_at(
        self,
        p1: np.ndarray,
        p2: np.ndarray,
        pivot: np.ndarray,
        axis: np.ndarray,
        q0: np.ndarray,
        t: float,
        theta_deg: float
    ) -> tuple[tuple[float, float, float, float], tuple[float, float, float], tuple[float, float, float]]:
        """``(angle, start, stop)`` after rolling by *theta_deg* about *axis*
        through *pivot*, having slid *t* along it: the rigid rotation of the
        mesh and of the start/stop points, with the angle the OBJECT needs
        for it (``q_roll (x) q0``, since the object turns about its own
        origin). *p1* / *p2* are the current start and stop points, *q0* the
        current angle ``[w, x, y, z]``."""
        ...

    def is_clear(
        self,
        position: np.ndarray,
        w: float,
        x: float,
        y: float,
        z: float
    ) -> bool:
        """Whether the loop with its start point at *position* and rotation
        ``[w, x, y, z]`` touches nothing."""
        ...

    def contact(
        self,
        position: np.ndarray,
        w: float,
        x: float,
        y: float,
        z: float
    ) -> int:
        """How many of the loop's mesh vertices are inside the candidates at
        this pose (0 = clear)."""
        ...

    def boxes_overlap(
        self,
        position: np.ndarray,
        w: float,
        x: float,
        y: float,
        z: float
    ) -> list[int]:
        """Indices of the candidates whose BOX overlaps the loop's box at this
        pose: stage one only, the hit list ``is_clear`` goes on to refine."""
        ...

    def search(
        self,
        p1: np.ndarray,
        p2: np.ndarray,
        pivot: np.ndarray,
        axis: np.ndarray,
        q0: np.ndarray,
        t0: float,
        pos_limit: float,
        neg_limit: float,
        slide_step: float,
        roll_deg: float,
        slide_roll_deg: float
    ) -> tuple[
        float, float, tuple[float, float, float, float], tuple[float, float, float], tuple[float, float, float]
    ] | None:
        """The nearest clear pose, as ``(t, theta_deg, angle, start, stop)``
        (the object's new angle ``[w, x, y, z]`` and the new start and stop
        points), or ``None``.

        *p1* / *p2* are the loop's current start and stop points, *q0* its
        current angle, *axis* the direction of the wire and *pivot* the point
        on it the roll turns about. Tries the roll that is clear nearest the
        current angle at slide offset *t0* (steps of *roll_deg*); failing
        that, slides away from *t0* in both directions in *slide_step*
        increments, never past *pos_limit* / *neg_limit* (their offsets along
        *axis*), scanning the full turn at *slide_roll_deg* at each, and keeps
        the clear spot closest to *t0* (the positive side wins a tie).
        """
        ...
