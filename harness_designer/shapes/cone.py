import math
import numpy as np

from .. import utils as _utils
from ..import debug as _debug

from ..gl import vbo as _vbo_handler

_vbo: _vbo_handler.VBOHandler = None


def create_vbo() -> _vbo_handler.VBOHandler:
    global _vbo

    if _vbo is None:
        vertices, faces = create(0.5, 1.0, 360, 1)
        verts, nrmls, faces, count = _utils.compute_vbo_smoothed_vertex_normals(vertices, faces)
        edges = _utils.compute_edges(faces)

        _vbo = _vbo_handler.VBOHandler('cone', verts, edges, nrmls, faces, count)

    return _vbo


@_debug.timeit
def create(radius=1.0, height=2.0, resolution=None, split=None):
    if resolution is None:
        resolution = int(max(20.0, _utils.remap(radius, 0.0, 1.0, 0.0, 20.0)))

    if split is None:
        split = int(max(3.0, _utils.remap(height, 0.0, 2.0, 0.0, 10.0)))

    count = resolution * split + 2
    vertices = np.full((count, 3), [0.0, 0.0, 0.0], dtype=np.float64)

    vertices[0] = np.array([0.0, 0.0, 0.0], dtype=np.float64)
    vertices[1] = np.array([0.0, 0.0, height], dtype=np.float64)

    step = math.pi * 2.0 / float(resolution)
    h_step = height / float(split)
    r_step = radius / float(split)

    for i in range(split):
        base = 2 + resolution * i
        r = r_step * (split - i)
        for j in range(resolution):
            theta = step * j
            vertices[base + j] = np.array(
                [math.cos(theta) * r,
                 math.sin(theta) * r,
                 h_step * i], dtype=np.float64)

    faces = []
    for j in range(resolution):
        j1 = int((j + 1) % resolution)
        # Triangles for bottom surface.
        # int base = 2;
        # mesh->triangles_.push_back(Eigen::Vector3i(0, base + j1, base + j));

        # Triangles for top segment of conical surface.
        base = 2 + resolution * (split - 1)
        faces.append([1, base + j, base + j1])

    # Triangles for conical surface other than top-segment.
    for i in range(split - 1):
        base1 = 2 + resolution * i
        base2 = base1 + resolution
        for j in range(resolution):
            j1 = int((j + 1) % resolution)
            faces.append([base2 + j1, base1 + j, base1 + j1])
            faces.append([base2 + j1, base2 + j, base1 + j])

    faces = np.array(faces, dtype=np.int32)

    return vertices, faces
