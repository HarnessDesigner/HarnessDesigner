
import math
import numpy as np

from .. import utils as _utils

from ..gl import vbo as _vbo_handler

_vbo: _vbo_handler.VBOHandler = None


def create_vbo() -> _vbo_handler.VBOHandler:
    global _vbo

    if _vbo is None:
        vertices, faces = create(1.0, 1.0, 1.0)

        verts, nrmls, faces, count = _utils.compute_vbo_vertex_normals(vertices, faces)
        _vbo = _vbo_handler.VBOHandler('box', verts, nrmls, faces, count)

    return _vbo


def create(width, height, depth):

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
