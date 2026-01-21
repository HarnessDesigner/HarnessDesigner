
import numpy as np

from ..import debug as _debug


@_debug.timeit
def create(width=1.0, height=1.0, depth=1.0):

    depth /= 2.0
    height /= 2.0
    width /= 2.0

    vertices = np.full((8, 3), [0.0, 0.0, 0.0], dtype=np.float64)
    vertices[0] = np.array([width, height, depth], dtype=np.float64)
    vertices[1] = np.array([width, height, -depth], dtype=np.float64)
    vertices[2] = np.array([width, -height, depth], dtype=np.float64)
    vertices[3] = np.array([width, -height, -depth], dtype=np.float64)

    vertices[4] = np.array([-width, height, depth], dtype=np.float64)
    vertices[5] = np.array([-width, height, -depth], dtype=np.float64)
    vertices[6] = np.array([-width, -height, depth], dtype=np.float64)
    vertices[7] = np.array([-width, -height, -depth], dtype=np.float64)

    # Triangles.
    faces = np.array([[4, 7, 5], [4, 6, 7], [0, 2, 4], [2, 6, 4],
                      [0, 1, 2], [1, 3, 2], [1, 5, 7], [1, 7, 3],
                      [2, 3, 7], [2, 7, 6], [0, 4, 1], [1, 4, 5]], dtype=np.int32)

    return vertices, faces
