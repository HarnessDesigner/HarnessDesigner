# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Build the one bounding volume hierarchy the OpenCL kernel traverses.

``kernel.cl`` starts every ray at node 0 of a single hierarchy, so the whole
scene has to be in one tree. The tree is built by :mod:`.bvh`, a Cython
extension (``bvh.pyx``) that has to be compiled before this module can be
imported.
"""

import numpy as np

from . import bvh as _bvh
from .. import check_types as _check_types


LEAF_THRESHOLD = 4


@_check_types.do
def build_bvh(vertices: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build a BVH over world-space triangles.

    :param vertices: ``(N, 3)`` float32 vertex positions.
    :type vertices: numpy.ndarray
    :param faces: ``(M, 3)`` int32 vertex indices, one row per triangle.
    :type faces: numpy.ndarray
    :returns: ``(bounds, structure, indices)`` -- six floats and four ints per
        node, and the triangle order the leaves refer to.
    :rtype: tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray]
    :raises ValueError: When there are no triangles to build a tree from.
    """
    if not len(faces):
        raise ValueError('There is no geometry to build a BVH from')

    vertices = np.ascontiguousarray(vertices, dtype=np.float32)
    faces = np.ascontiguousarray(faces, dtype=np.int32)

    centroids = _bvh.calculate_centroids_parallel(vertices, faces)
    builder = _bvh.FastBVHBuilder(vertices, faces, centroids, leaf_threshold=LEAF_THRESHOLD)

    return builder.build()
