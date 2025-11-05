
from typing import TYPE_CHECKING


from ..editor_3d.shapes import cylinder as _cylinder
from ..editor_3d.shapes import hemisphere as _hemisphere
from ..geometry import point as _point
from ..wrappers.decimal import Decimal as _decimal


from . import base as _base


if TYPE_CHECKING:
    from .. import editor_2d as _editor2d
    from .. import editor_3d as _editor3d
    from ..database.project_db import pjt_transition as _pjt_transition
    from ..database.global_db import transition_branch as _transition_branch


class Branch:

    def __init__(self, transition: "Transition",  bulb_offset_apex: _decimal,
                 origin: _point.Point, branch: "_transition_branch.TransitionBranch",
                 branch_point: _point.Point):

        length = branch.length
        offset = branch.offset
        angle = branch.angle

        min_dia = branch.min_dia
        max_dia = branch.max_dia

        bulb_length = branch.bulb_length
        bulb_offset = branch.bulb_offset
        # flange_height = branch.flange_height
        # flange_width = branch.flange_width
        color = transition.part.color

        self._transition = transition
        self._origin = origin

        if bulb_length:
            if bulb_offset_apex is not None:
                cyl_1_p1 = _point.Point(bulb_offset_apex - (max_dia * _decimal(0.75)),
                                        _decimal(0.0), _decimal(0.0))

                factor = bulb_length / length
                b_length = (
                    length - bulb_offset_apex + (max_dia / _decimal(2.0)) * factor)

            else:
                cyl_1_p1 = bulb_offset.copy()
                b_length = bulb_length

            if offset.x or offset.y:
                cyl_1_p1 += offset

            cyl_1_p1 += origin

            cyl1 = _cylinder.Cylinder(cyl_1_p1, b_length - (max_dia / _decimal(2.0)),
                                      max_dia, transition.part.color, None)
            self.cyl1 = cyl1
            if bulb_offset.x or bulb_offset.y:
                h_sphere1 = _hemisphere.Hemisphere(cyl1.p1, max_dia,
                                                   color, _decimal(0.0))

                self.h_sphere1 = h_sphere1

                h_sphere1.set_y_angle(_decimal(90.0), h_sphere1.center)

                if bulb_offset_apex is None:
                    apex = h_sphere1.center.copy()
                    apex += _point.Point(h_sphere1.diameter / _decimal(2.0),
                                         _decimal(0.0), _decimal(0.0))

                    self.bulb_offset_apex = apex.x
                else:
                    self.bulb_offset_apex = bulb_offset_apex
            else:
                self.bulb_offset_apex = bulb_offset_apex
                self.h_sphere1 = None

            if branch.idx == 0:
                cyl1.set_z_angle(angle, cyl1.p1)
            else:
                cyl1.set_z_angle(angle, origin)

            h_sphere2 = _hemisphere.Hemisphere(cyl1.p2, max_dia, color, min_dia)
            self.h_sphere2 = h_sphere2

            h_sphere2.set_y_angle(_decimal(90.0), h_sphere2.center)
            h_sphere2.set_z_angle(angle, h_sphere2.center)

            cyl2 = _cylinder.Cylinder(h_sphere2.hole_center,
                                      length - bulb_length + (max_dia / _decimal(2.0)),
                                      min_dia, color, None)
            self.cyl2 = cyl2

            cyl2.set_z_angle(angle, cyl2.p1)
        else:
            cyl_1_p1 = origin.copy()

            if offset.x or offset.y:
                cyl_1_p1 += offset

            cyl_1_p1 += origin

            cyl2 = _cylinder.Cylinder(cyl_1_p1, length, min_dia,
                                      transition.part.color, None)

            cyl2.set_z_angle(angle, cyl2.p1)

            self.cyl2 = cyl2
            self.cyl1 = None
            self.h_sphere1 = None
            self.h_sphere2 = None

        self.cyl2.p2 = branch_point
        self._branch = branch
        self._dia = branch.min_dia

    def add_to_plot(self, axes):
        self.cyl2.add_to_plot(axes)

        if self.cyl1 is not None:
            self.cyl1.add_to_plot(axes)
        if self.h_sphere1 is not None:
            self.h_sphere1.add_to_plot(axes)
        if self.h_sphere2 is not None:
            self.h_sphere2.add_to_plot(axes)

    def set_py_data(self, data):
        self.cyl2.set_py_data(data)

        if self.cyl1 is not None:
            self.cyl1.set_py_data(data)
        if self.h_sphere1 is not None:
            self.h_sphere1.set_py_data(data)
        if self.h_sphere2 is not None:
            self.h_sphere2.set_py_data(data)

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, origin: _point.Point):
        self.cyl2.set_angles(x_angle, y_angle, z_angle, origin)

        if self.cyl1 is not None:
            self.cyl1.set_angles(x_angle, y_angle, z_angle, origin)
        if self.h_sphere1 is not None:
            self.h_sphere1.set_angles(x_angle, y_angle, z_angle, origin)
        if self.h_sphere2 is not None:
            self.h_sphere2.set_angles(x_angle, y_angle, z_angle, origin)

    @property
    def name(self):
        return self._branch.name

    def remove(self):
        pass

    def on_move(self, point):
        pass

    def set_diameter(self, dia):
        if self._branch.max_dia < dia:
            return False
        elif self._branch.min_dia > dia:
            return False
        self._dia = dia


class Transition(_base.ObjectBase):

    def __init__(self, db_obj: "_pjt_transition.PJTTransition", editor_3d: "_editor3d.Editor3D", editor_2d: "_editor2d.Editor2D"):
        super().__init__(db_obj, editor_3d, editor_2d)
        self._branches = []

        origin = db_obj.center.point
        bulb_offset_apex = None

        part = db_obj.part

        # part.model3d
        # part.model3d_type

        for i, branch in enumerate(part.branches):
            if i == 0:
                bp = db_obj.branch1.point
            elif i == 1:
                bp = db_obj.branch2.point
            elif i == 2:
                bp = db_obj.branch3.point
            elif i == 3:
                bp = db_obj.branch4.point
            elif i == 4:
                bp = db_obj.branch5.point
            elif i == 5:
                bp = db_obj.branch6.point
            else:
                raise RuntimeError('sanity check')

            bp.add_object(self)
            branch = Branch(self, bulb_offset_apex, origin, branch, bp)
            bulb_offset_apex = branch.bulb_offset_apex

            self._branches.append(branch)

        for branch in self._objs:
            branch.set_angles(db_obj.x_angle, db_obj.y_angle, db_obj.z_angle, origin)
            branch.add_to_plot(editor_3d.axes)
            branch.set_py_data(self)

        self.origin = origin
