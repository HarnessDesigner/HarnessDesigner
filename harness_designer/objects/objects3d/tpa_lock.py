from typing import TYPE_CHECKING

import wx

# from ...widgets.context_menus import RotateMenu, MirrorMenu
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
    from ...database.project_db import pjt_tpa_lock as _pjt_tpa_lock
    from .. import tpa_lock as _tpa_lock

Config = _config.Config.editor3d


class TPALock(_base3d.Base3D):
    _parent: "_tpa_lock.TPALock" = None
    db_obj: "_pjt_tpa_lock.PJTTPALock"

    def __init__(self, parent: "_tpa_lock.TPALock", db_obj: "_pjt_tpa_lock.PJTTPALock"):
        self._part = db_obj.part

        model = self._part.model3d
        if model is not None:
            uuid = model.uuid
            scale = _point.Point(1.0, 1.0, 1.0)
            color = self._part.color.ui
            material = _materials.Plastic(color)
            angle = db_obj.angle3d

            if uuid in _vbo.VBOHandler:
                vbo = _vbo.VBOHandler(uuid)
            else:
                vertices, faces = model.load()

                if Config.renderer.smooth_tpa_locks:
                    verts, nrmls, faces, count = _utils.compute_vbo_smoothed_vertex_normals(vertices, faces)
                else:
                    verts, nrmls, faces, count = _utils.compute_vbo_vertex_normals(vertices, faces)

                vbo = _vbo.VBOHandler(uuid, verts, nrmls, faces, count)
        else:
            vbo = _sphere.create_vbo()
            scale = _point.Point(3.0, 3.0, 3.0)
            angle = _angle.Angle()

            color = _color.Color(0.6, 0.2, 0.6, 1.0)

            material = _materials.Metallic(color)

        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, db_obj.position3d, scale, material)

#
# class TPALockMenu(wx.Menu):
#
#     def __init__(self, canvas, selected):
#         wx.Menu.__init__(self)
#         self.canvas = canvas
#         self.selected = selected
#
#         rotate_menu = RotateMenu(canvas, selected)
#
#         self.AppendSubMenu(rotate_menu, 'Rotate')
#
#         mirror_menu = MirrorMenu(canvas, selected)
#         self.AppendSubMenu(mirror_menu, 'Mirror')
#
#         self.AppendSeparator()
#         item = self.Append(wx.ID_ANY, 'Select')
#         canvas.Bind(wx.EVT_MENU, self.on_select, id=item.GetId())
#
#         item = self.Append(wx.ID_ANY, 'Clone')
#         canvas.Bind(wx.EVT_MENU, self.on_clone, id=item.GetId())
#
#         self.AppendSeparator()
#         item = self.Append(wx.ID_ANY, 'Delete')
#         canvas.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())
#
#         self.AppendSeparator()
#         item = self.Append(wx.ID_ANY, 'Properties')
#         canvas.Bind(wx.EVT_MENU, self.on_properties, id=item.GetId())
#
#     def on_select(self, evt: wx.MenuEvent):
#         evt.Skip()
#
#     def on_clone(self, evt: wx.MenuEvent):
#         evt.Skip()
#
#     def on_delete(self, evt: wx.MenuEvent):
#         evt.Skip()
#
#     def on_properties(self, evt: wx.MenuEvent):
#         evt.Skip()
