
import math
import numpy as np

from .. import utils as _utils

from ..gl import vbo as _vbo_handler

_vbo: _vbo_handler.VBOHandler = None


def create_vbo() -> _vbo_handler.VBOHandler:
    global _vbo

    if _vbo is None:
        vertices, faces = create(0.5, 1.0, 360, 1)
        verts, nrmls, faces, count = _utils.compute_vbo_smoothed_vertex_normals(vertices, faces)
        _vbo = _vbo_handler.VBOHandler('cylinder', verts, nrmls, faces, count)

    return _vbo


def create(radius, length, resolution=None, split=None) -> tuple[np.ndarray, np.ndarray]:
    if resolution is None:
        resolution = int(max(15.0, _utils.remap(radius, 0.0, 2.0, 0.0, 20.0)))

    if split is None:
        split = int(max(1.0, _utils.remap(length, 0.0, 10.0, 0.0, 10.0)))

    count = resolution * (split + 1) + 2
    vertices = np.full((count, 3), [0.0, 0.0, 0.0], dtype=np.float64)

    vertices[0] = np.array([0.0, 0.0, length * 0.5], dtype=np.float64)
    vertices[1] = np.array([0.0, 0.0, -length * 0.5], dtype=np.float64)

    step = math.pi * 2.0 / float(resolution)
    h_step = length / float(split)

    for i in range(split + 1):
        for j in range(resolution):
            theta = float(step) * float(j)
            vertices[2 + resolution * i + j] = np.array(
                [math.cos(theta) * radius,
                 math.sin(theta) * radius,
                 length * 0.5 - h_step * i], dtype=np.float64)

    vertices += np.array([0.0, 0.0, length / 2.0], dtype=np.float64)

    faces = []
    for i in range(split):
        base1 = 2 + resolution * i
        base2 = base1 + resolution

        for j in range(resolution):
            j1 = int((j + 1) % resolution)
            faces.append([base2 + j, base1 + j1, base1 + j])
            faces.append([base2 + j, base2 + j1, base1 + j1])

    faces = np.array(faces, dtype=np.int32)
    
    return vertices, faces
