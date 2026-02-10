from typing import TYPE_CHECKING

import wx

from ...widgets.context_menus import RotateMenu, MirrorMenu
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal
from . import base3d as _base3d
from .mixins import angle as _angle_mixin
from .mixins import move as _move_mixin
from ...shapes import sphere as _sphere
from ...ui.editor_3d import vbo_handler as _vbo_handler
from ...wrappers import materials as _materials
from ... import config as _config
from ... import utils as _utils


if TYPE_CHECKING:
    from ...database.project_db import pjt_boot as _pjt_boot
    from .. import boot as _boot


Config = _config.Config.editor3d


class Boot(_base3d.Base3D, _angle_mixin.AngleMixin, _move_mixin.MoveMixin):
    _parent: "_boot.Boot" = None

    def __init__(self, parent: "_boot.Boot", db_obj: "_pjt_boot.PJTBoot"):
        _base3d.Base3D.__init__(self, parent)
        _angle_mixin.AngleMixin.__init__(self)
        _move_mixin.MoveMixin.__init__(self)

        self._db_obj: "_pjt_boot.PJTBoot" = db_obj

        self._part = db_obj.part

        position = db_obj.point3d.point

        self._color = self._part.color.ui

        self._material = _materials.RubberMaterial(self._color.rgba_scalar)
        self._selected_material = _materials.RubberMaterial(Config.selected_color)

        model = self._part.model3d
        if model is not None:
            uuid = model.uuid

            if uuid in _vbo_handler.VBOHandler:
                self._vbo = _vbo_handler.VBOHandler(uuid, [])
            else:
                data = model.load()

                triangles = []

                for vertices, faces in data:
                    if Config.renderer.smooth_boots:
                        verts, nrmls, faces, count = _utils.compute_unique_smoothed_vertex_normals(vertices, faces)
                    else:
                        verts, nrmls, faces, count = _utils.compute_unique_vertex_normals(vertices, faces)

                    triangles.append([verts, nrmls, faces, count])

                self._vbo = _vbo_handler.VBOHandler(uuid, triangles)

            self._position = position
            self._o_position = self._position.copy()

            self._angle = db_obj.angle3d
            self._o_angle = self._angle.copy()

            self._position.bind(self._update_position)
            self._angle.bind(self._update_angle)

            rect = []
            bb = []

            for renderer in self._triangles:
                data = renderer.data

                for i, (tris, nrmls, count) in enumerate(data):
                    tris @= self._angle
                    nrmls @= self._angle

                    tris += self._position

                    p1, p2 = self._compute_rect(tris)
                    bb.append(self._compute_bb(p1, p2))
                    rect.append([p1, p2])

            self._rect = rect
            self._bb = bb

        else:
            vertices, faces = _sphere.create(3.0)
            material = _materials.MetallicMaterial([0.6, 0.2, 0.2, 1.0])



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
