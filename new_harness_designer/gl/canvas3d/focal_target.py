from typing import TYPE_CHECKING

import math
import numpy as np

from ... import utils as _utils
from ...objects import generic as _generic
from ...gl import materials as _materials
from ...geometry import angle as _angle
from ...geometry import point as _point
from ... import color as _color

from ... import config as _config

if TYPE_CHECKING:
    from . import canvas as _canvas


Config = _config.Config.editor3d


class FocalPoint(_generic.Generic):

    def __init__(self, canvas: "_canvas.Canvas"):
        _generic.Generic.__init__(self, canvas)

        self.canvas = canvas
        self.obj3d = FocalPoint3D(self)


class FocalPoint3D(_generic.Generic3D):

    def __init__(self, parent: "FocalPoint"):
        self.canvas = parent.canvas

        color = _color.Color(*parent.canvas.config.focal_target.color)

        material = _materials.Metallic(color)
        angle = _angle.Angle()
        scale = _point.Point(1.0, 1.0, 1.0)
        position = parent.canvas.camera.focal_position
        data = self._build_point(Config.focal_target.radius)

        _generic.Generic3D.__init__(self, parent.canvas, None, angle, position, scale, material, data)

    @staticmethod
    def _build_point(radius=1.0):
        resolution = int(max(20.0, _utils.remap(radius, 0.35, 19.0, 20.0, 30.0)))

        count = 2 * resolution * (resolution - 1) + 2
        vertices = np.full((count, 3), [0.0, 0.0, 0.0], dtype=np.float64)

        vertices[0] = np.array([0.0, 0.0, radius], dtype=np.float64)
        vertices[1] = np.array([0.0, 0.0, -radius], dtype=np.float64)

        step = math.pi / float(resolution)

        for i in range(1, resolution, 1):
            alpha = step * i
            base = int(2 + 2 * resolution * (i - 1))
            for j in range(2 * resolution):
                theta = step * j

                alpha_sin = math.sin(alpha)
                alpha_cos = math.cos(alpha)
                theta_sin = math.sin(theta)
                theta_cos = math.cos(theta)

                vertices[base + j] = np.array(
                    [alpha_sin * theta_cos,
                     alpha_sin * theta_sin,
                     alpha_cos], dtype=np.float64) * radius

        # Triangles for poles.
        faces = []

        for j in range(2 * resolution):
            j1 = (j + 1) % (2 * resolution)
            base = 2
            faces.append([0, base + j, base + j1])
            base = 2 + 2 * resolution * (resolution - 2)
            faces.append([1, base + j1, base + j])

        # Triangles for non-polar region.
        for i in range(1, resolution - 1, 1):
            base1 = 2 + 2 * resolution * (i - 1)
            base2 = base1 + 2 * resolution
            for j in range(2 * resolution):
                j1 = int((j + 1) % (2 * resolution))
                faces.append([base2 + j, base1 + j1, base1 + j])
                faces.append([base2 + j, base2 + j1, base1 + j1])

        faces = np.array(faces, dtype=np.int32)
        vertices = vertices.reshape(-1, 3)

        return list(_utils.compute_smoothed_vertex_normals(vertices, faces))
