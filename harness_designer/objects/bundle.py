from typing import TYPE_CHECKING

import wx
import math

from ..shapes import cylinder as _cylinder
from ..geometry import line as _line
from ..wrappers import wxartist_event as _wxartist_event
from . import wire as _wire
from . import base as _base
from ..wrappers.decimal import Decimal as _decimal


if TYPE_CHECKING:
    from ..database.project_db import pjt_bundle as _pjt_bundle
    from .. import editor_3d as _editor_3d
    from ..wrappers import wxkey_event as _wxkey_event
    from ..wrappers import wxmouse_event as _wxmouse_event


class Bundle(_base.ObjectBase):

    def delete(self):
        pass

    def __init__(self, db_obj: "_pjt_bundle.PJTBundle", editor3d: "_editor_3d.Editor3D", _):
        _base.ObjectBase.__init__(self, db_obj, editor3d, None)
        _wire_sizes = []

        p1 = db_obj.start_point.point
        p2 = db_obj.stop_point.point

        pi = _decimal(math.pi)
        two = _decimal(2.0)
        for obj in p1.objects:
            if isinstance(object, _wire.Wire):
                obj.hide()
                r = obj.part.od_mm / two
                area = pi * r * r
                _wire_sizes.append(area)

        total_area = sum(_wire_sizes)
        # add 10% for space between the wires
        total_area *= _decimal(1.10)
        # TODO: need to do a proper calculation to figure out the concentric twisting
        #       of the budle and also calculate any additional fill wires
        total_area /= pi
        diameter = math.sqrt(total_area)

        if diameter < self._part.min_size:
            diameter = self._part.min_size

        cyl = _cylinder.Cylinder(p1, None, diameter, self._part.color, p2)
        cyl.add_to_plot(editor3d.axes)
        self._objs.append(cyl)
        cyl.p1.add_object(self)
        cyl.p2.add_object(self)

    def _on_properties(self, evt):
        evt.Skip()

    def _on_add_layout(self, evt):
        evt.Skip()

    def _on_delete(self, evt):
        evt.Skip()

    def menu3d(self, x, y):
        menu = wx.Menu()

        menu_item = menu.Append(wx.ID_ANY, 'Add Layout')
        self._editor3d.Bind(wx.EVT_MENU, self._on_add_layout, id=menu_item.GetId())
        menu.AppendSeparator()
        menu_item = menu.Append(wx.ID_ANY, 'Delete')
        self._editor3d.Bind(wx.EVT_MENU, self._on_delete, id=menu_item.GetId())
        menu.AppendSeparator()
        menu_item = menu.Append(wx.ID_ANY, 'Properties')
        self._editor3d.Bind(wx.EVT_MENU, self._on_properties, id=menu_item.GetId())

        self._editor3d.PopupMenu(menu, (x, y))
