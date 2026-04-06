import weakref
from typing import TYPE_CHECKING

import numpy as np
import wx
import build123d
import math
from copy import deepcopy

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base3d as _base3d
from ...shapes import sphere as _sphere
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ... import config as _config
from ... import utils as _utils
from ... import color as _color

if TYPE_CHECKING:
    from ...database.global_db import transition as _g_transition
    from ...database.project_db import pjt_transition as _pjt_transition
    from .. import transition as _transition
    from ...database.project_db import pjt_transition_branch as _pjt_transition_branch


Config = _config.Config.editor3d


# TODO:
#       setting the angles
#       setting position
#       make branches accessable to wires and bundles
#       routing wire through transition
#       snap bundle to branch
#       snap wire to branch
#       changing between transition selection and branch selection
#       setting branch diameter


def _build_model(b_data: "_g_transition.Transition", branches: list["Branch"], update_points=False):
    model = None

    for branch in b_data.branches:
        branch_index = branch.idx
        brnch = branches[branch_index]

        branch_point = brnch.position
        set_dia = brnch.diameter

        if set_dia is None:
            set_dia = branch.min_dia
            brnch.diameter = set_dia

        max_dia = branch.max_dia
        length = branch.length
        bulb_len = branch.bulb_length
        angle = branch.angle
        bulb_offset = branch.bulb_offset
        offset = branch.offset

        if bulb_len:
            if bulb_offset.x or bulb_offset.y:
                pl = build123d.Plane(origin=bulb_offset.as_float, z_dir=(1, 0, 0)).rotated((0, 0, angle))
            else:
                pl = build123d.Plane(origin=offset.as_float, z_dir=(1, 0, 0)).rotated((0, 0, angle))

            bulb = pl * build123d.extrude(build123d.Circle(max_dia / 2.0), bulb_len)

            if model is None:
                model = bulb
            else:
                model += bulb

            if bulb_offset.x or bulb_offset.y:
                pl = build123d.Plane(origin=bulb_offset.as_float, z_dir=(1, 0, 0))

                sphere = pl * build123d.Sphere(max_dia / 2.0)

                model += sphere

                pl = build123d.Plane(origin=(bulb_offset.x - bulb_len, bulb_offset.y, 0),
                                     z_dir=(1, 0, 0))

                sphere = pl * build123d.Sphere(max_dia / 2.0)

                model += sphere
            else:
                r = math.radians(angle)
                pos = _point.Point(bulb_len * math.cos(r), bulb_len * math.sin(r), 0.0) + offset

                pl = build123d.Plane(origin=pos.as_float, z_dir=(1, 0, 0))

                sphere = pl * build123d.Sphere(max_dia / 2.0).rotate(
                    build123d.Axis(origin=(0, 0, 0), direction=(1, 0, 0)), angle)

                model += sphere

        # if 'flange_width' in branch:
        #     fw = branch['flange_width']
        #     fh = branch['flange_height']
        #
        #     pl = plane.rotated((0, 0, angle)).move(build123d.Location(position=(-length + 11, 0, 0)))
        #     model += (pl * build123d.extrude(build123d.Circle(min_dia / 2 + 15), fw))# .rotate(build123d.Axis(origin=(0, 0, 0), direction=(0, 1, 0)), angle)

        pl = build123d.Plane(origin=offset.as_float, z_dir=(1, 0, 0)).rotated((0, 0, angle))

        brch = pl * build123d.extrude(build123d.Circle(set_dia / 2.0), length)

        if model is None:
            model = brch
        else:
            model += brch

        if branch_point.as_float == (0.0, 0.0, 0.0) or update_points:
            r = math.radians(float(angle))
            with branch_point:
                branch_point.x = length * math.cos(r)
                branch_point.y = length * math.sin(r)
                branch_point.z = 0.0
                branch_point += offset

    return model


class Transition(_base3d.Base3D):
    parent: "_transition.Transition" = None
    db_obj: "_pjt_transition.PJTTransition" = None

    def __init__(self, parent: "_transition.Transition",
                 db_obj: "_pjt_transition.PJTTransition"):

        self._part = db_obj.part
        position = db_obj.position3d
        angle = db_obj.angle3d
        color = self._part.color.ui
        inverse_angle = -angle

        material = _materials.Rubber(color)
        branch_count = self.branch_count = self._part.branch_count

        branch_points = []
        branch_diams = []
        branches = []

        if branch_count >= 1:
            branch = db_obj.branch1

            b_position = branch.position3d
            if b_position.as_float != (0.0, 0.0, 0.0):
                with b_position:
                    b_position -= position
                    b_position @= inverse_angle

            branches.append(Branch(parent, branch, branch.diameter, b_position))

        if branch_count >= 2:
            branch = db_obj.branch2

            b_position = branch.position3d
            if b_position.as_float != (0.0, 0.0, 0.0):
                with b_position:
                    b_position -= position
                    b_position @= inverse_angle

            branches.append(Branch(parent, branch, branch.diameter, b_position))

        if branch_count >= 3:
            branch = db_obj.branch3

            b_position = branch.position3d
            if b_position.as_float != (0.0, 0.0, 0.0):
                with b_position:
                    b_position -= position
                    b_position @= inverse_angle

            branches.append(Branch(parent, branch, branch.diameter, b_position))

        if branch_count >= 4:
            branch = db_obj.branch4

            b_position = branch.position3d
            if b_position.as_float != (0.0, 0.0, 0.0):
                with b_position:
                    b_position -= position
                    b_position @= inverse_angle

            branches.append(Branch(parent, branch, branch.diameter, b_position))

        if branch_count >= 5:
            branch = db_obj.branch5

            b_position = branch.position3d
            if b_position.as_float != (0.0, 0.0, 0.0):
                with b_position:
                    b_position -= position
                    b_position @= inverse_angle

            branches.append(Branch(parent, branch, branch.diameter, b_position))

        if branch_count >= 6:
            branch = db_obj.branch6

            b_position = branch.position3d
            if b_position.as_float != (0.0, 0.0, 0.0):
                with b_position:
                    b_position -= position
                    b_position @= inverse_angle

            branches.append(Branch(parent, branch, branch.diameter, b_position))

        self._model = _build_model(self._part, branches)

        self._vertices, self._faces = _utils.convert_model_to_mesh(self._model)
        tris, normals, count = _utils.compute_smoothed_vertex_normals(self._vertices, self._faces)

        for branch in branches:
            with branch.position:
                branch.position @= angle

            branch.position += position

        tris @= angle
        normals @= angle
        tris += position

        self._branches = branches
        self._branch_points = branch_points
        self._branch_diams = branch_diams

        scale = _point.Point(1.0, 1.0, 1.0)
        _base3d.Base3D.__init__(self, parent, db_obj, None, angle, db_obj.position3d,
                                scale, material, [tris, normals, count])

    def build(self):
        inverse_angle = -self._angle

        for branch in self._branches:
            with branch.position:
                branch.position -= self._position
                branch.position @= inverse_angle

        self._model = _build_model(self._part, self._branches, update_points=True)

        for branch in self._branches:
            with branch.position:
                branch.position @= self._angle

            branch.position += self._position

        self._vertices, self._faces = _utils.convert_model_to_mesh(self._model)
        tris, normals, count = _utils.compute_smoothed_vertex_normals(self._vertices, self._faces)

        tris @= self._angle
        normals @= self._angle
        tris += self._position

        self._data = [tris, normals, count]

        self.editor3d.Refresh(False)

    def _update_angle(self, angle: _angle.Angle):
        delta = angle - self._o_angle
        for branch in self._branches:
            with branch.position:
                branch.position -= self._position
                branch.position @= delta

            branch.position += self._position

        super()._update_angle(angle)

    def _update_position(self, position: _point.Point):
        delta = position - self._o_position

        for branch in self._branches:
            branch.position += delta

        super()._update_position(position)

    def get_branch(self, point: _point.Point) -> int:
        for branch in self._branches:
            if branch.position.db_id == point.db_id:
                return branch

    def get_context_menu(self):
        return TransitionMenu(self.mainframe.editor3d.editor, self)


class Branch(_base3d.Base3D):
    _parent: "_transition.Transition" = None
    db_obj: "_pjt_transition_branch.PJTTransitionBranch"

    def __init__(self, parent: "_transition.Transition", db_obj: "_pjt_transition_branch.PJTTransitionBranch",
                 diameter: float, position: _point.Point):

        self._diameter = diameter

        vbo = _sphere.create_vbo()
        scale = _point.Point(diameter, diameter, diameter)
        angle = _angle.Angle()

        color = _color.Color(1.0, 0.3, 0.3, 1.0)
        material = _materials.Rubber(color)

        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, position,
                                scale, material)

        color = _color.Color(0.3, 1.0, 0.3, 1.0)
        self._selected_material = _materials.Rubber(color)

    @property
    def diameter(self) -> float:
        return self._diameter

    @diameter.setter
    def diameter(self, value: float):
        self._diameter = value
        self.db_obj.diameter = value
        self._parent.obj3d.build()

    @property
    def min_diameter(self) -> float:
        branch = self.db_obj.transition.part.branches[self.db_obj.branch_id]
        return branch.min_dia

    @property
    def max_diameter(self) -> float:
        branch = self.db_obj.transition.part.branches[self.db_obj.branch_id]
        return branch.max_dia


class TransitionMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        rotate_menu = _context_menus.Rotate3DMenu(canvas, selected)
        self.AppendSubMenu(rotate_menu, 'Rotate')

        mirror_menu = _context_menus.Mirror3DMenu(canvas, selected)
        self.AppendSubMenu(mirror_menu, 'Mirror')

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Select')
        canvas.Bind(wx.EVT_MENU, self.on_select, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Clone')
        canvas.Bind(wx.EVT_MENU, self.on_clone, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Delete')
        canvas.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Properties')
        canvas.Bind(wx.EVT_MENU, self.on_properties, id=item.GetId())

    def on_select(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_clone(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_properties(self, evt: wx.MenuEvent):
        evt.Skip()