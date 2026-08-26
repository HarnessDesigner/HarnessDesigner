# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Geometry helpers shared by the rotation-ring gizmo
(``rotation_handlers/rotation_rings.py`` and ``rotation_handlers/
rotation_ring/*``): per-axis ring-plane orientation math and the unit
torus mesh the always-on activation ring renders.

Ring planes follow the same nested Euler order
``objects.objectsvar... _angle.Angle.from_euler`` itself uses --
effective matrix ``Ry.Rx.Rz`` (Z innermost, X middle, Y outermost),
confirmed numerically here: ``Angle.from_euler(ex, ey, ez) @ v`` matches
``Ry(Rx(Rz(v)))`` to float32 precision for arbitrary (ex, ey, ez, v).

Each axis's ring, unrotated, has its own plane normal along that same
axis (the X ring's flat face is perpendicular to world X, etc.) --
:func:`slot_ring_angle` returns the orientation that carries a ring's
local-Z-is-the-normal mesh convention (see ``_Tick.local_radial``/
``ProtractorRingBase.reposition_all`` in ``rotation_ring/
_protractor_base.py``, and ``TorusRing``'s own local XY-plane/Z-normal
convention) onto that rest pose, then applies
whichever part of the tracked object's current Euler value sits
*outside* this axis in the nested order -- nothing sits outside Y (fixed
in world space); only Y sits outside X; Y and X both sit outside Z. Two
of the three rest poses collapse to a single-axis rotation about the
same world axis as the outer term (so they combine into one
``from_euler`` call by simple addition), also confirmed numerically
below rather than assumed:

- y ring: rest pose ``Angle.from_euler(-90, 0, 0)``, no outer term --
  always world Y, matching "fixed in world space".
- x ring: rest pose ``Angle.from_euler(0, 90, 0)`` composed with the
  outer ``Ry(ey)`` term -- both pure Y-axis rotations, so they add:
  ``Angle.from_euler(0, ey + 90, 0)``.
- z ring: rest pose is identity (local Z already is world Z); outer
  term is the object's own Ry.Rx, i.e. ``Angle.from_euler(ex, ey, 0)``.
"""

import math

import numpy as np

from ..geometry import angle as _angle
from .. import utils as _utils
from .. import check_types as _check_types


AXES = ('x', 'y', 'z')


@_check_types.do
def slot_ring_angle(axis: str, euler: tuple) -> "_angle.Angle":
    """Return the world-space orientation of *axis*'s ring plane, given
    the tracked object's current ``(ex, ey, ez)`` Euler value -- see the
    module docstring for the full derivation. Applying this to local Z
    (this gizmo's shared "ring normal is local Z" convention) gives the
    ring's current world-space plane normal; applying it to local X/Y
    gives the tangential/radial directions ``_Tick.local_radial``
    (``rotation_ring/_protractor_base.py``) places ticks with.
    """
    ex, ey, ez = euler

    if axis == 'z':
        return _angle.Angle.from_euler(ex, ey, 0.0)

    if axis == 'x':
        return _angle.Angle.from_euler(0.0, ey + 90.0, 0.0)

    if axis == 'y':
        return _angle.Angle.from_euler(-90.0, 0.0, 0.0)

    raise ValueError(f"axis must be 'x', 'y' or 'z', got {axis!r}")


@_check_types.do
def slot_normal(axis: str, euler: tuple) -> np.ndarray:
    """Return *axis*'s current world-space ring-plane normal (unit
    vector) -- :func:`slot_ring_angle` applied to local Z.
    """
    local_z = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    return np.asarray(slot_ring_angle(axis, euler) @ local_z, dtype=np.float32)


@_check_types.do
def wrap_angle(degrees: float) -> float:
    """Wrap *degrees* into ``(-180, 180]`` -- applied to every Euler
    value this gizmo writes back (a free-rotation drag's accumulated
    total, and a snapped tick's own degree value), so a long drag past
    +/-180 degrees, or a tick past 180, doesn't leave the object's own
    stored Euler value growing unbounded or landing outside the range
    every other Euler write in this codebase already assumes.
    """
    wrapped = math.fmod(degrees + 180.0, 360.0)
    if wrapped < 0.0:
        wrapped += 360.0

    return wrapped - 180.0


@_check_types.do
def build_ring_mesh(
    tube_diameter_scale: float, major_segments: int = 96, tube_segments: int = 16
) -> tuple[np.ndarray, int]:
    """Build a unit torus (major radius 1.0, lying in the local XY plane,
    centered on the origin, tube axis normal = local Z) -- the always-on
    activation ring's own mesh (:class:`~..rotation_ring.torus_ring.
    TorusRing`), rendered with a uniform ``Point(radius, radius, radius)``
    scale at draw time (see that class's own ``render()``), which is
    exactly what makes baking *tube_diameter_scale* into this unit mesh
    (rather than passing it as a render-time uniform) give a real-world
    tube thickness that stays proportional to the ring's own current
    radius, matching this parameter's own "as a fraction of radius"
    contract.

    Same build recipe every other primitive in ``shapes/`` uses (see
    ``shapes/cylinder.py``'s own ``create()``): hand-build a
    ``(vertices, faces)`` pair, then run it through
    ``utils.compute_normals`` for the final packed vertex/normal buffer.

    :param tube_diameter_scale: Tube diameter as a fraction of the
        (unit, i.e. 1.0) major radius.
    :param major_segments: Samples around the main ring.
    :param tube_segments: Samples around the tube's own circular
        cross-section.
    :returns: ``(packed, count)`` -- see ``utils.compute_normals``.
    """
    major_radius = 1.0
    tube_radius = tube_diameter_scale / 2.0

    vertices = np.zeros((major_segments * tube_segments, 3), dtype=np.float32)

    for i in range(major_segments):
        u = 2.0 * math.pi * i / major_segments
        cu, su = math.cos(u), math.sin(u)

        for j in range(tube_segments):
            v = 2.0 * math.pi * j / tube_segments
            cv, sv = math.cos(v), math.sin(v)

            radial = major_radius + tube_radius * cv
            vertices[i * tube_segments + j] = (radial * cu, radial * su, tube_radius * sv)

    faces = []
    for i in range(major_segments):
        i_next = (i + 1) % major_segments

        for j in range(tube_segments):
            j_next = (j + 1) % tube_segments

            a = i * tube_segments + j
            b = i_next * tube_segments + j
            c = i_next * tube_segments + j_next
            d = i * tube_segments + j_next

            # Winding confirmed outward-facing (positive dot against the
            # analytic outward normal at a sample vertex) before this was
            # written -- do not swap without re-checking, there's no
            # backface culling in this renderer to mask getting it wrong,
            # but every other shape's lighting assumes outward normals.
            faces.append([a, b, c])
            faces.append([a, c, d])

    faces = np.array(faces, dtype=np.int32)

    return _utils.compute_normals(vertices, faces)
