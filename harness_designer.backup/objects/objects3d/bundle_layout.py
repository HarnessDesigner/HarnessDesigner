
from typing import TYPE_CHECKING

import wxOpenGL
import wx


from ...geometry import point as _point
from ...geometry import angle as _angle

from ...wrappers.decimal import Decimal as _decimal
from . import base3d as _base3d
from ...shapes import sphere as _sphere
from ... import Config
from .mixins import move as _move_mixin


if TYPE_CHECKING:
    from ...database.project_db import pjt_bundle_layout as _pjt_bundle_layout
    from .. import bundle_layout as _bundle_layout


Config = Config.editor3d


class BundleLayout(_base3d.Base3D, wxOpenGL.MeshGeneric, _move_mixin.MoveMixin):
    _parent: "_bundle_layout.BundleLayout" = None

    def __init__(self, parent: "_bundle_layout.BundleLayout",
                 db_obj: "_pjt_bundle_layout.PJTBundleLayout"):

        _base3d.Base3D.__init__(self, parent)
        _move_mixin.MoveMixin.__init__(self)

        self._db_obj: "_pjt_bundle_layout.PJTBundleLayout" = db_obj

        position = db_obj.point3d.point
        angle = _angle.Angle()

        self._is_deleted = False
        self._is_dragging = False

        bundles = db_obj.attached_bundles

        bundle = bundles[-1]
        layers = bundle.concentric.layers
        self._diameter = layers[-1].diameter

        material = wxOpenGL.RubberMaterial(self._color.rgba_scalar)
        selected_material = wxOpenGL.RubberMaterial(Config.selected_color)

        vertices, faces = _sphere.create(float(self._diameter) / 2.0)

        wxOpenGL.MeshGeneric.__init__(self, self.editor3d.canvas, material, selected_material,
                                      Config.modeling.smooth_bundles, [[vertices, faces]], position, angle)

    def _get_triangles(self, vertices, faces):
        if Config.modeling.smooth_bundles:
            return self._compute_smoothed_vertex_normals(vertices, faces)
        else:
            return self._compute_vertex_normals(vertices, faces)

    def set_diameter(self, parent_bundle, value: _decimal):
        self._diameter = value

        vertices, faces = _sphere.create(float(self._diameter) / 2.0)
        self._mesh = [[vertices, faces]]

        self._build()

        for bundle in self.editor3d.mainframe.project.bundles:
            if (
                bundle.obj3d.position.db_id == self.position.db_id and
                parent_bundle != bundle.obj3d
            ):
                bundle.obj3d.set_diameter(self, value)
                break

    @property
    def is_dragging(self) -> bool:
        return self._is_dragging

    @is_dragging.setter
    def is_dragging(self, value: bool):
        self._is_dragging = value

        for bundle in self.editor3d.mainframe.project.bundles:
            if bundle.obj3d.position.db_id == self.position.db_id:
                bundle.obj3d.is_dragging = value


class BundleLayoutMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        item = self.Append(wx.ID_ANY, 'Add Transition')
        canvas.Bind(wx.EVT_MENU, self.on_add_transition, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Delete')
        canvas.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())

    def on_add_transition(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()
