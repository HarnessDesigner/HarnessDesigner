# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>


def solve_chain(
    start: tuple[float, float],
    stop: tuple[float, float],
    required_length: float,
    drag_end: int,
    target: tuple[float, float],
    diameter_mm: float,
    zigzag_length_factor: float,
    threshold_factor: float,
    tolerance: float = 1e-6,
) -> tuple[bool, list[tuple[float, float]]]:
    """See ``rope_pull.rope_pull_py.solve_chain`` -- identical behavior;
    *drag_end* is ``0`` (start anchor), ``1`` (stop anchor) or ``2``
    (interior waypoint) instead of a
    :class:`~rope_pull.rope_pull_py.DragEnd`.

    :returns: ``(accepted, points)`` -- *points* is a list of
        ``(x, z)`` float tuples, meaningful only when *accepted* is
        ``True``.
    """
    ...
