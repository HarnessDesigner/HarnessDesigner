from typing import TYPE_CHECKING

import wx
import wxOpenGL

from ...widgets.context_menus import RotateMenu, MirrorMenu
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal
from . import base3d as _base3d
from .mixins import angle as _angle_mixin
from .mixins import move as _move_mixin
from ...shapes import sphere as _sphere


if TYPE_CHECKING:
    from ...database.project_db import pjt_tpa_lock as _pjt_tpa_lock
    from .. import tpa_lock as _tpa_lock

from ... import Config


class TPALock(_base3d.Base3D, wxOpenGL.MeshModel, _angle_mixin.AngleMixin, _move_mixin.MoveMixin):
    _parent: "_tpa_lock.TPALock" = None

    def __init__(self, parent: "_tpa_lock.TPALock", db_obj: "_pjt_tpa_lock.PJTTPALock"):
        _base3d.Base3D.__init__(self, parent)
        _angle_mixin.AngleMixin.__init__(self)
        _move_mixin.MoveMixin.__init__(self)

        self._db_obj: "_pjt_tpa_lock.PJTTPALock" = db_obj

        self._part = db_obj.part

        position = db_obj.point3d.point
        
        self._color = self._part.color.ui

        material = wxOpenGL.RubberMaterial(self._color.rgba_scalar)
        selected_material = wxOpenGL.RubberMaterial(Config.selected_color)

        model = self._part.model3d
        if model is not None:
            file = model.path
            self._model_angle = model.angle
            self._o_model_angle = self._model_angle.copy()

            self._model_offset = model.offset
            self._o_model_offset = self._model_offset.copy()
            
            wxOpenGL.MeshModel.__init__(self, self.mainframe.editor3d.canvas,
                                        material, selected_material,
                                        Config.modeling.smooth_tpa_locks,
                                        file, self._model_offset, self._model_angle)

            self._model_angle.unbind(self._update_angle)
            self._model_offset.unbind(self._update_position)

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
                    self._adjust_hit_points(p1, p2)
                    rect.append([p1, p2])
                    
            self._rect = rect
            self._bb = bb

        else:
            vertices, faces = _sphere.create(3.0)
            angle = _angle.Angle()
            
            material = wxOpenGL.MetallicMaterial([0.6, 0.2, 0.2, 1.0])

            wxOpenGL.MeshGeneric.__init__(self, self.mainframe.editor3d.canvas,
                                          material, selected_material, True,
                                          [[vertices, faces]], position, angle)

    def _get_triangles(self, vertices, faces):
        if Config.modeling.smooth_tpa_locks:
            return self._compute_smoothed_vertex_normals(vertices, faces)
        else:
            return self._compute_vertex_normals(vertices, faces)


class TPALockMenu(wx.Menu):

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
