import weakref
from typing import TYPE_CHECKING


import build123d
import math
from copy import deepcopy


from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal
from ... import gl_materials as _gl_materials
from . import base3d as _base3d
from .mixins import angle as _angle_mixin
from .mixins import move as _move_mixin

from ... import Config

if TYPE_CHECKING:
    from ... import editor_3d as _editor_3d
    from ...database.global_db import transition as _g_transition
    from ...database.project_db import pjt_transition as _pjt_transition
    from .. import transition as _transition
    from ...database.project_db import pjt_transition_branch as _pjt_transition_branch


Config = Config.editor3d


# TODO:
#       setting the angles
#       setting position
#       make branches accessable to wires and bundles
#       routing wire through transition
#       snap bundle to branch
#       snap wire to branch
#       changing between transition selection and branch selection
#       setting branch diameter
#       add agnostic for wires/bundles if transition is being dragged to move it


def _build_model(b_data: "_g_transition.Transition", points: list[_point.Point], sizes: list[_decimal]):
    model = None
    core_model = None
    has_bulb = False
    branch_models = []

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
            has_bulb = True

            if bulb_offset.x or bulb_offset.y:
                pl = build123d.Plane(origin=bulb_offset.as_float, z_dir=(1, 0, 0)).rotated((0, 0, float(angle)))
            else:
                pl = build123d.Plane(origin=offset.as_float, z_dir=(1, 0, 0)).rotated((0, 0, float(angle)))

            bulb = pl * build123d.extrude(build123d.Circle(float(max_dia / _decimal(2))), float(bulb_len))

            if model is None:
                model = bulb
                core_model = deepcopy(model)
            else:
                model += bulb
                core_model += bulb

            if bulb_offset.x or bulb_offset.y:
                pl = build123d.Plane(origin=bulb_offset.as_float, z_dir=(1, 0, 0))

                sphere = pl * build123d.Sphere(float(max_dia / _decimal(2)))

                model += sphere
                core_model += sphere

                pl = build123d.Plane(origin=(float(bulb_offset.x - bulb_len),
                                             float(bulb_offset.y), 0),
                                     z_dir=(1, 0, 0))

                sphere = pl * build123d.Sphere(float(max_dia / _decimal(2)))

                model += sphere
                core_model += sphere
            else:
                r = math.radians(angle)
                pos = _point.Point(bulb_len * _decimal(math.cos(r)),
                                   bulb_len * _decimal(math.sin(r)),
                                   _decimal(0.0)) + offset

                pl = build123d.Plane(origin=pos.as_float, z_dir=(1, 0, 0))

                sphere = pl * build123d.Sphere(float(max_dia / _decimal(2))).rotate(
                    build123d.Axis(origin=(0, 0, 0), direction=(1, 0, 0)), float(angle))

                model += sphere
                core_model += sphere

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
            core_model = deepcopy(model)
            branch_models.append(brnch)
        else:
            model += brnch
            brnch -= core_model
            branch_models.append(brnch)

        if branch_point is None:
            r = math.radians(float(angle))
            branch_point = _point.Point(length * _decimal(math.cos(r)),
                                        length * _decimal(math.sin(r)),
                                        _decimal(0.0))
            branch_point += offset

            points[branch_index] = branch_point

    return model, core_model, branch_models


class Transition(_base3d.Base3D, _angle_mixin.AngleMixin, _move_mixin.MoveMixin):
    _parent: "_transition.Transition" = None

    def __init__(self, parent: "_transition.Transition",
                 db_obj: "_pjt_transition.PJTTransition"):

        _base3d.Base3D.__init__(self, parent)
        _angle_mixin.AngleMixin.__init__(self)
        _move_mixin.MoveMixin.__init__(self)
        self._db_obj: "_pjt_transition.PJTTransition" = db_obj

        self._part = db_obj.part
        self._position = db_obj.point3d.point
        self._angle = db_obj.angle3d
        self._color = self._part.color.ui

        self._material = _gl_materials.Rubber(self._color.rgba_scalar)
        branch_count = self.branch_count = self._part.branch_count

        branch_points = []
        branch_diams = []
        branches = []

        if branch_count >= 1:
            branch = db_obj.branch1
            branches.append(branch)

            if branch.point3d is None:
                branch_points.append(None)
            else:
                branch_points.append(branch.point3d.point)

            branch_diams.append(branch.diameter)
        if branch_count >= 2:
            branch = db_obj.branch2
            branches.append(branch)

            if branch.point3d is None:
                branch_points.append(None)
            else:
                branch_points.append(branch.point3d.point)

            branch_diams.append(branch.diameter)
        if branch_count >= 3:
            branch = db_obj.branch3
            branches.append(branch)

            if branch.point3d is None:
                branch_points.append(None)
            else:
                branch_points.append(branch.point3d.point)

            branch_diams.append(branch.diameter)
        if branch_count >= 4:
            branch = db_obj.branch4
            branches.append(branch)

            if branch.point3d is None:
                branch_points.append(None)
            else:
                branch_points.append(branch.point3d.point)

            branch_diams.append(branch.diameter)
        if branch_count >= 5:
            branch = db_obj.branch5
            branches.append(branch)

            if branch.point3d is None:
                branch_points.append(None)
            else:
                branch_points.append(branch.point3d.point)

            branch_diams.append(branch.diameter)
        if branch_count >= 6:
            branch = db_obj.branch6
            branches.append(branch)

            if branch.point3d is None:
                branch_points.append(None)
            else:
                branch_points.append(branch.point3d.point)

            branch_diams.append(branch.diameter)

        self._branches = branches
        self._branch_points = branch_points
        self._branch_diams = branch_diams

        self._model = None
        self._hit_test_points = None
        self._material = None
        self._position.bind(self._update_position)
        self._angle.bind(self._update_angle)

    def _build(self):
        model, core_model, branch_models = _build_model(self._part, self._branch_points, self._branch_diams)

        for i, branch in enumerate(self._branches):

            if branch.point3d is None:
                point = self._branch_points[i]

                point @= self._angle
                point += self._position
                x, y, z = point
                point = self._db_obj.table.db.pjt_points3d_table.insert(x, y, z)
                branch.point3d_id = point.db_id
                self._branch_points[i] = point.point

            branch.diameter = self._branch_diams[i]

        del self._stored_branches[:]

        for i, model in enumerate(branch_models):
            vertices, faces = self._convert_model_to_mesh(model)
            tris, nrmls, count = self._get_triangles(vertices, faces)

            tris @= self._angle
            nrmls @= self._angle
            tris += self._position

            p1, p2 = self._compute_rect(tris)
            bb = self._compute_bb(p1, p2)
            Branch(tris, nrmls, count, [p1, p2], bb, self._branch_points[i])

    def _get_triangles(self, vertices, faces):
        if Config.modeling.smooth_transitions:
            return self._compute_smoothed_vertex_normals(vertices, faces)
        else:
            return self._compute_vertex_normals(vertices, faces)

    def get_branch_index(self, point: _point.Point) -> int:
        for i, (p1, p2) in self._hit_test_points[:-1]:
            if p1 <= point <= p2:
                return i

        return -1

    def get_branch_min_max_dia(self, index: int) -> tuple[_decimal, _decimal]:
        branch = self._part.branches[index]
        return branch.min_dia, branch.max_dia


class Branch:

    def __init__(self, db_obj: "_pjt_transition_branch.PJTTransitionBranch"):
        self.db_obj = db_obj
        self.triangles = None
        self.normals = None
        self.count = 0
        self.rect = []
        self.bb = None
        self.point = None
        self._color = None
        self._wires = []

        self.is_selected = False
        self.is_target = False
        self.is_target_locked = False

        self._target_material = _gl_materials.Rubber([1.0, 0.3, 0.3, 1.0])
        self._target_locked_material = _gl_materials.Rubber([0.3, 1.0, 0.3, 1.0])
        self._material = None

    def __remove_wire(self, ref):
        if ref in self._wires:
            self._wires.remove(ref)

    def add_wire(self, wire):
        ref = weakref.ref(wire, self.__remove_wire)
        self._wires.append(ref)

        # point = self.
        # self.db_obj.concentric.

    def remove_wire(self, wire):
        for ref in self._wires[:]:
            w = ref()
            if w is None or w == wire:
                self._wires.remove(ref)

    @property
    def material(self):
        if self.is_target_locked:
            return self._target_locked_material

        if self.is_target:
            return self._target_material

        return self._material

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self._color = value
        self._material = _gl_materials.Rubber(value)
