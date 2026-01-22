from typing import TYPE_CHECKING

import build123d

from ...geometry import point as _point
from ...geometry import line as _line
from ...geometry import angle as _angle
from ... import gl_materials as _gl_materials
from ...shapes import cylinder as _cylinder
from ...wrappers.decimal import Decimal as _decimal
from . import base3d as _base3d
from ... import Config


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire_marker as _pjt_wire_marker


Config = Config.editor3d


def _build_model(length: _decimal, diameter: _decimal, label):
    radius = diameter / _decimal(2.0)

    return _cylinder.create(float(radius), float(length)), None


class WireMarker(_base3d.Base3D):

    def __init__(self, parent, db_obj: "_pjt_wire_marker.PJTWireMarker"):
        super().__init__(parent)
        self._db_obj = db_obj
        self._part = db_obj.part
        self._position = db_obj.point3d.point
        self._wire = db_obj.wire
        self._wire_p1 = self._wire.start_point3d.point
        self._wire_p2 = self._wire.stop_point3d.point

        p1_distance = _line.Line(self._wire_p1, self._position).length()
        p2_distance = _line.Line(self._wire_p2, self._position).length()

        if p1_distance > p2_distance:
            self._distance = p1_distance
        else:
            self._distance = p2_distance
            self._wire_p1, self._wire_p2 = self._wire_p2, self._wire_p1

        self._angle = _angle.Angle.from_points(self._wire_p1, self._wire_p2)

        self._color = db_obj.part.color.ui
        self._material = _gl_materials.Plastic(self._color.rgba_scalar)
        self._label_material = _gl_materials.Plastic([0.05, 0.05, 0.05, 1.0])

        self._wire_p1.bind(self._update_position)
        self._wire_p2.bind(self._update_position)

        self._build()

    def _update_position(self, _):
        angle = _angle.Angle.from_points(self._wire_p1, self._wire_p2)
        delta = angle - self._angle
        self._angle = angle

        self._position -= self._wire_p1
        self._position @= delta
        self._position += self._wire_p1

        for renderer in self._triangles:
            data = renderer.data
            data[0][0] -= self._wire_p1
            data[0][0] @= delta
            data[0][0] -= self._wire_p1
            data[0][1] @= delta
            renderer.data = data

        tris = self._triangles[0].data[0][0]

        p1, p2 = self._compute_rect(tris)
        bb = self._compute_bb(p1, p2)
        self._bb[0] = bb
        self._rect[0] = [p1, p2]

    def _build(self):
        (vertices, faces), text_model = _build_model(self._part.length,
                                                     self._wire.part.od_mm + 0.0625,
                                                     self._db_obj.label)

        tris, nrmls, count = self._get_triangles(vertices, faces)

        tris += self._position
        tris -= self._wire_p1
        tris @= self._angle
        tris += self._wire_p1
        nrmls @= self._angle

        p1, p2 = self._compute_rect(tris)
        bb = self._compute_bb(p1, p2)
        self._rect = [[p1, p2]]
        self._bb = [bb]
        self._triangles = [
            _base3d.TriangleRenderer([[tris, nrmls, count]], self._material)]

        if text_model is not None:
            vertices, faces = self._convert_model_to_mesh(text_model)
            tris, nrmls, count = self._compute_vertex_normals(vertices, faces)

            tris += self._position
            tris -= self._wire_p1
            tris @= self._angle
            tris += self._wire_p1
            nrmls @= self._angle

            self._triangles.append(
                _base3d.TriangleRenderer([[tris, nrmls, count]], self._label_material))

    def _get_triangles(self, vertices, faces):
        if Config.modeling.smooth_markers:
            return self._compute_smoothed_vertex_normals(vertices, faces)
        else:
            return self._compute_vertex_normals(vertices, faces)


# raiders grave