# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The peg-board rope-pull solver's single public entry point.

Prefers the compiled extension (:mod:`.rope_pull`) when it's been built,
falling back to the pure-Python reference (:mod:`.rope_pull_py`) when
it hasn't -- same pattern ``wire_routing.routing`` uses for ``astar``.
Both implementations take/return the exact same shapes; this module's
own :func:`solve_chain` is what translates the compiled extension's
plain ``(accepted, points)`` tuple (it has no Python-level objects at
its boundary at all, see :mod:`.rope_pull`'s own docstring) back into a
:class:`~.rope_pull_py.ChainResult`, so every caller sees one consistent
return type regardless of which implementation actually ran.
"""

from . import rope_pull_py as _rope_pull_py
from .rope_pull_py import ChainResult, DragEnd  # NOQA -- re-exported, this module is the public surface


try:
    from . import rope_pull as _rope_pull_ext
except ImportError:
    # The compiled extension hasn't been built in this environment -- the
    # pure Python one (same rules, same results, much slower) takes over.
    _rope_pull_ext = None


_DRAG_END_TO_INT = {
    DragEnd.START: 0,
    DragEnd.STOP: 1,
    DragEnd.WAYPOINT: 2,
}


def solve_chain(
    start: tuple[float, float],
    stop: tuple[float, float],
    required_length: float,
    drag_end: DragEnd,
    target: tuple[float, float],
    height_cap_fraction: float,
    min_height_mm: float,
    tolerance: float = 1e-6,
) -> ChainResult:
    """See :func:`~.rope_pull_py.solve_chain` for the full contract --
    same wire-or-bundle peg-board chain, same inputs/outputs. Runs the
    compiled extension when available, the pure-Python reference
    otherwise.
    """
    if _rope_pull_ext is None:
        return _rope_pull_py.solve_chain(
            start, stop, required_length, drag_end, target,
            height_cap_fraction, min_height_mm, tolerance)

    accepted, points = _rope_pull_ext.solve_chain(
        start, stop, required_length, _DRAG_END_TO_INT[drag_end], target,
        height_cap_fraction, min_height_mm, tolerance)

    return ChainResult(accepted, points)
