from typing import TYPE_CHECKING
import weakref

import wx

from ...widgets.context_menus import RotateMenu, MirrorMenu
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal
from . import base3d as _base3d
from .mixins import angle as _angle_mixin
from .mixins import move as _move_mixin


if TYPE_CHECKING:
    from ...database.project_db import pjt_boot as _pjt_boot
    from .. import boot as _boot

from ... import Config
from ... import gl_materials as _gl_materials

Config = Config.editor3d


class Boot(_base3d.Base3D, _angle_mixin.AngleMixin, _move_mixin.MoveMixin):
    _parent: "_boot.Boot" = None

    def __init__(self, parent: "_boot.Boot", db_obj: "_pjt_boot.PJTBoot"):
        _base3d.Base3D.__init__(self, parent)
        _angle_mixin.AngleMixin.__init__(self)
        _move_mixin.MoveMixin.__init__(self)

        self._db_obj: "_pjt_boot.PJTBoot" = db_obj

        self._part = db_obj.part

        self._position = db_obj.point3d.point
        self._o_position = self._position.copy()
        self._angle = db_obj.angle3d
        self._o_angle = self._angle.copy()

        self._color = self._part.color.ui

        self._position.bind(self._update_position)
        self._angle.bind(self._update_angle)

        self._material = _gl_materials.Rubber(self._color.rgba_scalar)

    def _build(self):
        model = self._part.model3d

        triangles = []

        if model is None:
            self._model = None
        else:
            self._model = model.model
            for verts, faces in self._model:
                tris, nrmls, count = self._get_triangles(verts, faces)
                tris @= self._angle
                nrmls @= self._angle
                tris += self._position

                p1, p2 = self._compute_rect(tris)
                # self._adjust_hit_points(p1, p2)
                bb = self._compute_bb(p1, p2)

                self._rect.append([p1, p2])
                self._bb.append(bb)
                triangles.append([tris, nrmls, count])

        self._triangles = [_base3d.TriangleRenderer(triangles, self._material)]

    def _get_triangles(self, vertices, faces):
        if Config.modeling.smooth_boots:
            return self._compute_smoothed_vertex_normals(vertices, faces)
        else:
            return self._compute_vertex_normals(vertices, faces)


class BootMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        rotate_menu = RotateMenu(canvas, selected)

        self.AppendSubMenu(rotate_menu, 'Rotate')

        mirror_menu = MirrorMenu(canvas, selected)
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
