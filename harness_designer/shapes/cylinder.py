
import math
import numpy as np

from .. import utils as _utils

from ..ui.editor_3d import vbo_handler as _vbo_handler

_vbo: _vbo_handler.VBOHandler = None


def create_vbo() -> _vbo_handler.VBOHandler:
    global _vbo

    if _vbo is None:
        count = 360 * 2 + 2
        vertices = np.full((count, 3), [0.0, 0.0, 0.0], dtype=np.float64)

        vertices[0] = np.array([0.0, 0.0, 0.5], dtype=np.float64)
        vertices[1] = np.array([0.0, 0.0, -0.5], dtype=np.float64)

        step = math.pi * 2.0 / 200.0

        for i in range(2):
            for j in range(200):
                theta = float(step) * float(j)
                cos = math.cos(theta)
                sin = math.sin(theta)
                vertices[2 + 200 * i + j] = np.array(
                    [cos * 0.5, sin * 0.5, 0.5 - i], dtype=np.float64)

        vertices += np.array([0.0, 0.0, 0.5], dtype=np.float64)

        faces = []

        for j in range(360):
            j1 = int((j + 1) % 360)
            faces.append([362 + j, 2 + j1, 2 + j])
            faces.append([362 + j, 362 + j1, 2 + j1])

        faces = np.array(faces, dtype=np.int32)
        verts, nrmls, faces, count = _utils.compute_vbo_smoothed_vertex_normals(vertices, faces)
        _vbo = _vbo_handler.VBOHandler('cylinder', [[verts, nrmls, faces, count]])

        verts, nrmls, faces, count = _utils.compute_vbo_vertex_normals(vertices, faces)
        
        _vbo = _vbo_handler.VBOHandler('cylinder', [[verts, nrmls, faces, count]])

    return _vbo


def create(radius=0.5, height=1.0) -> tuple[np.ndarray, np.ndarray]:
    resolution = int(max(15.0, _utils.remap(radius, 0.0, 2.0, 0.0, 20.0)))
    split = int(max(1.0, _utils.remap(height, 0.0, 10.0, 0.0, 10.0)))

    count = resolution * (split + 1) + 2
    vertices = np.full((count, 3), [0.0, 0.0, 0.0], dtype=np.float64)

    vertices[0] = np.array([0.0, 0.0, height * 0.5], dtype=np.float64)
    vertices[1] = np.array([0.0, 0.0, -height * 0.5], dtype=np.float64)

    step = math.pi * 2.0 / float(resolution)
    h_step = height / float(split)

    for i in range(split + 1):
        for j in range(resolution):
            theta = float(step) * float(j)
            vertices[2 + resolution * i + j] = np.array(
                [math.cos(theta) * radius,
                 math.sin(theta) * radius,
                 height * 0.5 - h_step * i], dtype=np.float64)

    vertices += np.array([0.0, 0.0, height / 2.0], dtype=np.float64)

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
