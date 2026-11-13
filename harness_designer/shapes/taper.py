# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Taper (cone frustum) mesh generation helpers.

The taper is the short 45 degree step a shield wire makes in the schematic from the full wire size down to the thickness of the dashed shield
ring (user, 2026-11-12): a hollow frustum, base-anchored along +Z like :mod:`~harness_designer.shapes.cylinder`, built at unit size (base
diameter 1, length 1) and scaled by ``(D, D, length)``. Its far end is :data:`END_RATIO` of the base.
"""

import math
import numpy as np

from .. import utils as _utils
from ..gl import vbo as _vbo_handler
from .. import check_types as _check_types


# The thickness a shield wire and the dashes of its ring have, as a part of an ordinary wire's: the frustum's far end is this part of its base.
END_RATIO = 0.3

_vbo: _vbo_handler.PooledVBOHandler = None


@_check_types.do
def length(diameter: float) -> float:
    """The length of a 45 degree taper from *diameter* down to ``diameter * END_RATIO``: the radius changes by as much as the length."""
    return diameter * (1.0 - END_RATIO) / 2.0


@_check_types.do
def create_vbo() -> _vbo_handler.PooledVBOHandler:
    """Create or return the cached taper VBO (base diameter 1 at Z = 0, ``END_RATIO`` at Z = 1)."""
    global _vbo

    if _vbo is None:
        vertices, faces = create(0.5, 0.5 * END_RATIO, 1.0, 360)

        packed, count = _utils.compute_normals(vertices, faces)

        unpacked_verts = packed[:count * 3].reshape(-1, 3)
        aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
        aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
        obb = _utils.compute_obb(aabb1, aabb2)

        _vbo = _vbo_handler.PooledVBOHandler(
            'taper', packed, count, aabb=aabb, obb=obb,
            arena_kind=_vbo_handler.VBO_TYPE_PRIMITIVE)

    return _vbo


@_check_types.do
def create(radius: float, end_radius: float, height: float, resolution: int = 360) -> tuple[np.ndarray, np.ndarray]:
    """Create vertices and faces for the side wall of a frustum, from *radius* at Z = 0 to *end_radius* at Z = *height* (no end caps).

    :param radius: Radius of the base.
    :param end_radius: Radius of the far end.
    :param height: Length along +Z.
    :param resolution: Number of samples around each ring.
    :returns: Vertex and triangle index arrays.
    """
    count = resolution * 2 + 2
    vertices = np.zeros((count, 3), dtype=np.float32)

    # the two axis points are kept (as the cylinder's are) so the vertex layout is the same
    vertices[0] = (0.0, 0.0, height)
    vertices[1] = (0.0, 0.0, 0.0)

    step = math.pi * 2.0 / float(resolution)

    for i, (r, z) in enumerate(((end_radius, height), (radius, 0.0))):
        for j in range(resolution):
            theta = step * j
            vertices[2 + resolution * i + j] = (math.cos(theta) * r, math.sin(theta) * r, z)

    faces = []
    base1 = 2
    base2 = base1 + resolution

    # the same winding as the cylinder's: ring 0 is the far end
    for j in range(resolution):
        j1 = (j + 1) % resolution
        faces.append([base2 + j, base1 + j1, base1 + j])
        faces.append([base2 + j, base2 + j1, base1 + j1])

    return vertices, np.array(faces, dtype=np.int32)
