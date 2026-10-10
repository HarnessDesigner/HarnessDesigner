"""Explicit per-axis access for the rotation handlers.

Each handler works on one of the three Euler axes by name. These helpers
map the name to the matching attribute with plain branches, so no
``getattr``/``setattr`` is needed and an unknown axis fails loudly.
"""

from typing import Any


def get_axis(angle: Any, axis: str) -> float:
    """Read one Euler component (``'x'``, ``'y'`` or ``'z'``) of *angle*."""
    if axis == 'x':
        return angle.x
    if axis == 'y':
        return angle.y
    if axis == 'z':
        return angle.z

    raise ValueError(f'unknown axis {axis!r}')


def set_axis(angle: Any, axis: str, value: float) -> None:
    """Write one Euler component (``'x'``, ``'y'`` or ``'z'``) of *angle*."""
    if axis == 'x':
        angle.x = value
    elif axis == 'y':
        angle.y = value
    elif axis == 'z':
        angle.z = value
    else:
        raise ValueError(f'unknown axis {axis!r}')


def axis_color(ring_config: Any, axis: str) -> list[float]:
    """The configured RGBA colour for one axis's ring."""
    if axis == 'x':
        return ring_config.x_color
    if axis == 'y':
        return ring_config.y_color
    if axis == 'z':
        return ring_config.z_color

    raise ValueError(f'unknown axis {axis!r}')
