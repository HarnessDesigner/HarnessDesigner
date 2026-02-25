
from typing import TYPE_CHECKING

import wx

from ...geometry import point as _point
from ...geometry import angle as _angle

from ...gl import materials as _materials
from . import base3d as _base3d
from ...shapes import sphere as _sphere
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_bundle_layout as _pjt_bundle_layout
    from .. import bundle_layout as _bundle_layout


Config = _config.Config.editor3d.renderer


class BundleLayout(_base3d.Base3D):
    _parent: "_bundle_layout.BundleLayout" = None
    db_obj: "_pjt_bundle_layout.PJTBundleLayout"

    def __init__(self, parent: "_bundle_layout.BundleLayout",
                 db_obj: "_pjt_bundle_layout.PJTBundleLayout"):

        bundles = db_obj.attached_bundles

        bundle = bundles[-1]
        layers = bundle.concentric.layers
        self._diameter = layers[-1].diameter

        color = bundle.part.color.ui
        material = _materials.Rubber(color)

        scale = _point.Point(self._diameter, self._diameter, self._diameter)
        vbo = _sphere.create_vbo()
        angle = _angle.Angle()
        position = db_obj.position3d

        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, position, scale, material)

    def set_diameter(self, parent_bundle, value: float):
        self._diameter = value
        scale = _point.Point(value, value, value)
        diff = self._scale - scale
        self._scale += diff

        for bundle in self.editor3d.mainframe.project.bundles:
            if (
                bundle.obj3d.position.db_id == self.position.db_id and
                parent_bundle != bundle.obj3d
            ):
                bundle.obj3d.set_diameter(self, value)
                break


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
