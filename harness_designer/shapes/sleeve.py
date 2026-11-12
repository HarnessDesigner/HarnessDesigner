# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Solder sleeve mesh: a hollow tube with a WALL (real depth), its ends tapered down onto the cable.

A solder sleeve (a cable shield terminator, see ``SHIELD_SLEEVE_DESIGN.md`` in the repo root) is a heat shrink tube with a ring of
solder inside. The tube is what this primitive is; the ring (the coloured stripe seen through it) is drawn with
:mod:`.cylinder`, which sits UNDER (inside) this mesh.

Like :mod:`.cylinder` the mesh is built once at unit size and is scaled by whoever uses it, so it fits any cable: its OUTER diameter is
1.0 and its length 1.0, running along local +Z from the origin (``z = 0``, the base end) to ``z = 1`` (the tip), so a caller
scales it by ``(D, D, L)`` and places its base the way a cylinder's is placed. The wall and the taper are fractions of the diameter and
so scale with it.

The revolved profile, ``(radius, z)``:

* outside: from the tip radius at ``z = 0`` it swells over ``TAPER`` of the length to the full radius 0.5 (a smooth step, so the taper
  reads as the tube shrunk down onto the cable), stays there, and comes back down at the other end;
* the end rings join the outside to the inside wall;
* inside: a plain cylinder of radius ``0.5 - WALL``, which is the cable's radius at the unit scale.

Every surface has its own vertices, so the edges between them stay sharp while each surface is shaded smooth.
"""

import math
import numpy as np

from .. import utils as _utils
from ..gl import vbo as _vbo_handler
from .. import check_types as _check_types


# the wall of the tube, as a fraction of its outer diameter
WALL = 0.10

# how much of the length each end takes to swell from the tip radius to the full radius
TAPER = 0.22

# the radius of the tip, as a fraction of the way from the inside wall (0) to the outside (WALL): the shrunk ends are thin
TIP = 0.35

# The length of the sleeve as it is drawn: a sleeve on a cable is a RECOVERED (heat shrunk) one, and it gets shorter as it shrinks. TE's
# catalog "Product Length" (35 of the 72 sleeves have one: 8.5 to 55 mm, mostly about 30) is the length as supplied, so the drawn
# length is RECOVERED_LENGTH of it. A part with no length gets one from the cable's diameter: DEFAULT_LENGTH_BASE_MM plus
# DEFAULT_LENGTH_PER_MM for each mm of it, kept between DEFAULT_LENGTH_MIN_MM and DEFAULT_LENGTH_MAX_MM (13 mm for a 4 mm cable).
RECOVERED_LENGTH = 0.8
DEFAULT_LENGTH_BASE_MM = 3.0
DEFAULT_LENGTH_PER_MM = 2.5
DEFAULT_LENGTH_MIN_MM = 10.0
DEFAULT_LENGTH_MAX_MM = 24.0

# The pigtail a catalog sleeve comes with is this long, measured from the MIDDLE of the sleeve to the end of the lead (user, 2026-11-11:
# 150 mm for every sleeve with a pre-installed lead, from TE's drawings). It is also the most that lead may be made to measure.
# A pigtail the user adds to a sleeve has no such limit.
PIGTAIL_LENGTH_MM = 150.0

# The solder ring seen through the (translucent) tube: its length as a fraction of the sleeve's, and its diameter as a fraction of
# the way from the inside of the tube to its outside, so it lies INSIDE the wall.
RING_LENGTH = 0.34
RING_DEPTH = 0.5

_vbo: _vbo_handler.PooledVBOHandler = None


def sizes(cable_diameter: float, min_dia: float = 0.0, max_dia: float = 0.0, length: float = 0.0) -> dict[str, float]:
    """The scale of a sleeve on a cable and of the solder ring on it.

    The unit mesh has an outer diameter of 1.0 and its inside wall at ``1 - 2 * WALL``, so a sleeve that fits a cable of diameter *d* is
    ``d / (1 - 2 * WALL)`` across. The cable is taken as the part's range allows (a cable thicker than the expanded diameter does not
    fit, which the caller checks with ``Splice.fits_cable``; here it is only clamped so that a mesh is always built).

    :param cable_diameter: The cable's outside diameter, mm (0 or less when there is no cable yet: the part's expanded diameter is used).
    :param min_dia: The part's recovered inside diameter, mm (0.0 = not known).
    :param max_dia: The part's expanded inside diameter, mm (0.0 = not known).
    :param length: The part's length as supplied, mm (0.0 = not known: the length comes from the cable's diameter). The sleeve is
        drawn recovered, ``RECOVERED_LENGTH`` of it.
    :returns: ``diameter`` and ``length`` of the sleeve, ``ring_diameter``, ``ring_length`` and ``ring_offset`` (from the sleeve's base
        along its axis to the ring's base) of the solder ring.
    """
    if cable_diameter <= 0.0:
        cable_diameter = max_dia if max_dia > 0.0 else 3.0

    if max_dia > 0.0:
        cable_diameter = min(cable_diameter, max_dia)

    if min_dia > 0.0:
        cable_diameter = max(cable_diameter, min_dia)

    diameter = cable_diameter / (1.0 - 2.0 * WALL)
    if length > 0.0:
        length *= RECOVERED_LENGTH
    else:
        length = min(max(DEFAULT_LENGTH_BASE_MM + DEFAULT_LENGTH_PER_MM * cable_diameter, DEFAULT_LENGTH_MIN_MM), DEFAULT_LENGTH_MAX_MM)

    ring_length = length * RING_LENGTH

    # inside the wall: between the inside of the tube (1 - 2 * WALL of its diameter) and its outside
    ring_diameter = diameter * (1.0 - 2.0 * WALL * (1.0 - RING_DEPTH))

    return {
        'diameter': diameter, 'length': length,
        'ring_diameter': ring_diameter, 'ring_length': ring_length,
        'ring_offset': (length - ring_length) / 2.0,
    }


@_check_types.do
def create_vbo() -> _vbo_handler.PooledVBOHandler:
    """Create or return the cached sleeve VBO.

    :returns: Cached VBO data for the unit solder sleeve mesh.
    :rtype: :class:`harness_designer.gl.vbo.PooledVBOHandler`
    """
    global _vbo

    if _vbo is None:
        vertices, faces = create()

        packed, count = _utils.compute_normals(vertices, faces)

        unpacked_verts = packed[:count * 3].reshape(-1, 3)
        aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
        aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
        obb = _utils.compute_obb(aabb1, aabb2)

        _vbo = _vbo_handler.PooledVBOHandler(
            'sleeve', packed, count, aabb=aabb, obb=obb,
            arena_kind=_vbo_handler.VBO_TYPE_PRIMITIVE)

    return _vbo


def _smooth_step(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def profile(wall: float = WALL, taper: float = TAPER, tip: float = TIP, steps: int = 4) -> dict[str, list[tuple[float, float]]]:
    """The ``(radius, z)`` points of the four surfaces of the unit sleeve, each in the order the closed profile runs (outside going
    up, the top ring going in, the inside going down, the bottom ring going out), which is counter-clockwise in the (radius, z) plane.

    :param wall: Wall thickness as a fraction of the outer diameter (1.0).
    :param taper: Part of the length each end takes to swell to the full radius.
    :param tip: Where the radius of the tip lies between the inside wall (0) and the outside (1).
    :param steps: Number of rings in each taper.
    :returns: ``{'outer': [...], 'top': [...], 'inner': [...], 'bottom': [...]}``.
    """
    outer_r = 0.5
    inner_r = outer_r - wall
    tip_r = inner_r + wall * tip

    outer = []
    for i in range(steps + 1):
        t = _smooth_step(i / steps)
        outer.append((tip_r + (outer_r - tip_r) * t, taper * i / steps))

    for i in range(steps + 1):
        t = _smooth_step(1.0 - i / steps)
        outer.append((tip_r + (outer_r - tip_r) * t, 1.0 - taper + taper * i / steps))

    return {
        'outer': outer,
        'top': [(tip_r, 1.0), (inner_r, 1.0)],
        'inner': [(inner_r, 1.0), (inner_r, 0.0)],
        'bottom': [(inner_r, 0.0), (tip_r, 0.0)],
    }


@_check_types.do
def create(resolution: int = 48, wall: float = WALL, taper: float = TAPER, tip: float = TIP) -> tuple[np.ndarray, np.ndarray]:
    """Create the vertices and faces of the unit solder sleeve.

    :param resolution: Number of samples around each ring.
    :type resolution: int
    :param wall: Wall thickness as a fraction of the outer diameter.
    :type wall: float
    :param taper: Part of the length each end takes to swell to the full radius.
    :type taper: float
    :param tip: Where the radius of the tip lies between the inside wall (0) and the outside (1).
    :type tip: float
    :returns: Vertex and triangle index arrays; the triangles are wound counter-clockwise seen from outside.
    :rtype: tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`]
    """
    angles = [math.pi * 2.0 * j / resolution for j in range(resolution)]
    cos = [math.cos(a) for a in angles]
    sin = [math.sin(a) for a in angles]

    vertices: list[list[float]] = []
    faces: list[list[int]] = []

    for rings in profile(wall, taper, tip).values():
        first = len(vertices)

        for radius, z in rings:
            for j in range(resolution):
                vertices.append([cos[j] * radius, sin[j] * radius, z])

        for i in range(len(rings) - 1):
            a = first + i * resolution
            b = a + resolution

            for j in range(resolution):
                j1 = (j + 1) % resolution
                faces.append([a + j, a + j1, b + j1])
                faces.append([a + j, b + j1, b + j])

    vertices_array = np.array(vertices, dtype=np.float32)
    faces_array = np.array(faces, dtype=np.int32)

    # Wound the same way for every segment of the closed profile; which way that is depends on the order above, so look at the sign
    # of the volume the faces enclose and flip them all when it is inside out.
    triangles = vertices_array[faces_array]
    volume = float(np.einsum('ij,ij->i', triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])).sum()) / 6.0

    if volume < 0.0:
        faces_array = faces_array[:, ::-1].copy()

    return vertices_array, faces_array
