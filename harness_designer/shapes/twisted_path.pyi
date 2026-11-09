# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import numpy as np


def build_path(
    starts: np.ndarray,
    rotations: np.ndarray,
    quats: np.ndarray,
    lengths: np.ndarray,
    joined: np.ndarray,
    bend_radius: float,
    rounded: bool,
    rate: float,
    outer_radius: float,
    start_phase: float,
    bend_step: float,
    samples_per_turn: int,
    max_rings: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """The pieces of a bent wire with everything needed to draw them; see the module docstring of ``twisted_path.pyx``.

    *starts* ``(n, 3)``, *rotations* ``(n, 3, 3)``, *quats* ``(n, 4)`` and *lengths* ``(n,)`` are float64 and C-contiguous,
    *joined* ``(n,)`` is uint8.

    :returns: ``(positions (m, 3), quats (m, 4), lengths (m,), phases (m,), start mitres (m, 4), end mitres (m, 4),
        rings (m,), sources (m,), matrices (m, 3, 3))``, one row per piece in path order; *sources* is the input segment a piece
        is cut from, or -1 for a chord of a rounded corner.
    """
    ...
