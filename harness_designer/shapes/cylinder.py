
import math
import numpy as np

from .. import utils as _utils
from ..import debug as _debug


@_debug.timeit
def create(radius=1.0, height=2.0):
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

    # // Triangles for top and bottom face.
    # for (int j = 0; j < resolution; j++) {
    #     int j1 = (j + 1) % resolution;
    #     int base = 2;
    #     mesh->triangles_.push_back(Eigen::Vector3i(0, base + j, base + j1));
    #     base = 2 + resolution * split;
    #     mesh->triangles_.push_back(Eigen::Vector3i(1, base + j1, base + j));
    # }

    # Triangles for cylindrical surface.

    vertices += np.array([0.0, 0.0, height / 2], dtype=np.float64)

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
