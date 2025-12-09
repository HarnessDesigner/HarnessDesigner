from typing import TYPE_CHECKING


import build123d
import math

from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal
from ...wrappers import color as _color
from ...geometry import angle as _angle
from ... import gl_materials as _gl_materials
from . import Base3D as _Base3D

if TYPE_CHECKING:
    from .. import Editor3D as _Editor3D
    from ...database.global_db import transition as _transition
    from ...database.project_db import pjt_transition as _pjt_transition


def build_model(center: _point.Point, b_data: "_transition.Transition", points: list[_point.Point], sizes: list[_decimal]):
    model = None

    hit_test_rects = []

    for branch in b_data.branches:
        branch_index = branch.idx
        branch_point = points[branch_index]
        set_dia = sizes[branch_index]

        if set_dia is None:
            set_dia = branch.min_dia

        max_dia = branch.max_dia
        length = branch.length
        bulb_len = branch.bulb_length
        angle = branch.angle
        bulb_offset = branch.bulb_offset
        offset = branch.offset

        if bulb_len:
            if bulb_offset.x or bulb_offset.y:
                pl = build123d.Plane(origin=bulb_offset.as_float, z_dir=(1, 0, 0)).rotated((0, 0, float(angle)))
            else:
                pl = build123d.Plane(origin=offset.as_float, z_dir=(1, 0, 0)).rotated((0, 0, float(angle)))

            bulb = pl * build123d.extrude(build123d.Circle(float(max_dia / _decimal(2))), float(bulb_len))

            if model is None:
                model = bulb
            else:
                model += bulb

            if bulb_offset.x or bulb_offset.y:
                pl = build123d.Plane(origin=bulb_offset.as_float, z_dir=(1, 0, 0))

                model += pl * build123d.Sphere(float(max_dia / _decimal(2)))

                pl = build123d.Plane(origin=(float(bulb_offset.x - bulb_len),
                                             float(bulb_offset.y), 0),
                                     z_dir=(1, 0, 0))

                model += pl * build123d.Sphere(float(max_dia / _decimal(2)))
            else:
                r = math.radians(angle)
                pos = _point.Point(bulb_len * _decimal(math.cos(r)),
                                   bulb_len * _decimal(math.sin(r)),
                                   _decimal(0.0)) + offset

                pl = build123d.Plane(origin=pos.as_float, z_dir=(1, 0, 0))
                model += pl * build123d.Sphere(float(max_dia / _decimal(2))).rotate(
                    build123d.Axis(origin=(0, 0, 0), direction=(1, 0, 0)), float(angle))

        # if 'flange_width' in branch:
        #     fw = branch['flange_width']
        #     fh = branch['flange_height']
        #
        #     pl = plane.rotated((0, 0, angle)).move(build123d.Location(position=(-length + 11, 0, 0)))
        #     model += (pl * build123d.extrude(build123d.Circle(min_dia / 2 + 15), fw))# .rotate(build123d.Axis(origin=(0, 0, 0), direction=(0, 1, 0)), angle)

        pl = build123d.Plane(origin=offset.as_float, z_dir=(1, 0, 0)).rotated((0, 0, float(angle)))

        brnch = pl * build123d.extrude(build123d.Circle(float(set_dia / _decimal(2))), float(length))

        if model is None:
            model = brnch
        else:
            model += brnch

        if branch_point is None:
            r = math.radians(float(angle))
            branch_point = _point.Point(length * _decimal(math.cos(r)),
                                        length * _decimal(math.sin(r)),
                                        _decimal(0.0))
            branch_point += offset
            branch_point += center

            points[branch_index] = branch_point

        set_radius = set_dia / _decimal(2)
        corner = _point.Point(_decimal(set_radius), _decimal(set_radius), _decimal(set_radius))

        hit_test_rects.append((branch_point - corner, branch_point + corner))

    bbox = model.bounding_box()
    corner1 = _point.Point(*(_decimal(float(item)) for item in bbox.min)) + center
    corner2 = _point.Point(*(_decimal(float(item)) for item in bbox.max)) + center

    hit_test_rects.append((corner1, corner2))

    return model, hit_test_rects


class Transition(_Base3D):

    _db_obj: "_pjt_transition.PJTTransition" = None

    def __init__(self, editor3d: "_Editor3D", transition_db: "_pjt_transition.PJTTransition"):
        super().__init__(editor3d)

        self.__update_disabled_count = 0
        self._part = transition_db.part

        self._color = self._part.color
        self._center = transition_db.center.point
        self._center.add_object(self)

        self._angle = transition_db.angle
        self._name = transition_db.name
        self._db_obj = transition_db

        branch_count = self._part.branch_count

        branch_points = []
        branch_diams = []
        if branch_count >= 1:
            branch_points.append(transition_db.branch1.point)
            branch_diams.append(transition_db.branch1dia)
        if branch_count >= 2:
            branch_points.append(transition_db.branch2.point)
            branch_diams.append(transition_db.branch2dia)
        if branch_count >= 3:
            branch_points.append(transition_db.branch3.point)
            branch_diams.append(transition_db.branch3dia)
        if branch_count >= 4:
            branch_points.append(transition_db.branch4.point)
            branch_diams.append(transition_db.branch4dia)
        if branch_count >= 5:
            branch_points.append(transition_db.branch5.point)
            branch_diams.append(transition_db.branch5dia)
        if branch_count >= 6:
            branch_points.append(transition_db.branch6.point)
            branch_diams.append(transition_db.branch6dia)

        for bp in branch_points:
            bp.add_object(self)

        self._model, self._hit_test_points = build_model(self._center, self._part, branch_points, branch_diams)
        self._branch_points = branch_points
        self._branch_diams = branch_diams
        self._ui_color = self._color.ui
        self._ui_color.Bind(self._update)
        self._material = _gl_materials.Rubber(self._ui_color.rgba_scalar)
        self._triangles = None
        self._normals = None
        self._triangle_count = 0

    def hit_test(self, point: _point.Point) -> bool:
        for p1, p2 in self._hit_test_points:
            if p1 <= point <= p2:
                return True

        return False

    def draw(self, renderer):
        if self._triangles is None:
            self._normals, self._triangles, self._triangle_count = self._get_triangles(self._model)

            self._triangles @= self._angle
            self._triangles += self._center.as_numpy

        renderer.draw_triangles(self._normals, self._triangles, self._triangle_count, self._ui_color.rgb_scalar)

    def get_branch_index(self, point: _point.Point) -> int:
        for i, (p1, p2) in self._hit_test_points[:-1]:
            if p1 <= point <= p2:
                return i

        return -1

    def get_branch_min_max_dia(self, index: int) -> tuple[_decimal, _decimal]:
        branch = self._part.branches[index]
        return branch.min_dia, branch.max_dia

    def set_branch_dia(self, index: int, dia: _decimal):
        self._branch_diams[index] = dia
        setattr(self._db_obj, f'branch{index + 1}dia', dia)

        model, hit_test_points = build_model(self._center, self._part, self._branch_points, self._branch_diams)
        self._hit_test_points = hit_test_points
        self._model = model
        self._triangles = None

    def _update_color(self, *_):
        self._material = _gl_materials.Rubber(self._ui_color.rgba_scalar)
        self.editor3d.canvas.Refresh(False)

    @property
    def color(self) -> _color.Color:
        return self._ui_color

    @color.setter
    def color(self, value: _color.Color):
        self._ui_color.Unbind(self._update)
        self._ui_color = value
        self._ui_color.Bind(self._update)
        # TODO: Finish
        # self._db_obj.table

    @property
    def angle(self) -> _angle.Angle:
        return self._angle

    @angle.setter
    def angle(self, value: _angle.Angle):
        angle_diff = value - self._angle

        self._angle += angle_diff

        for p1, p2 in self._hit_test_points:
            p1 -= self._center
            p1 @= angle_diff
            p1 += self._center

            p2 -= self._center
            p2 @= angle_diff
            p2 += self._center

        if self._triangles is None:
            self._normals, self._triangles, self._triangle_count = self._get_triangles(self._model)
            self._triangles @= self._angle
            self._triangles += self._center.as_numpy
        else:
            self._triangles -= self._center.as_numpy
            self._triangles @= angle_diff
            self._triangles += self._center.as_numpy

        with self:
            for p in self._branch_points:
                with p:
                    p -= self._center
                    p @= angle_diff
                    p += self._center

                for obj in p.objects:
                    obj.recalculate()

    def __enter__(self):
        self.__update_disabled_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__update_disabled_count -= 1

    def _update(self, *_):
        if self.__update_disabled_count:
            return

        self.editor3d.Refresh(False)

    def move(self, point: _point.Point) -> None:
        with self:
            for p1, p2 in self._hit_test_points:
                p1 += point
                p2 += point

            for bp in self._branch_points:
                bp += point

            self._center += point

        self._update()
