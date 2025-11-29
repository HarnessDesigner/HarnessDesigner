from typing import TYPE_CHECKING

import wx
import math

from ..editor_3d.shapes import cylinder as _cylinder
from ..geometry import line as _line
from ..wrappers import wxartist_event as _wxartist_event
from . import wire as _wire
from . import base as _base
from ..wrappers.decimal import Decimal as _decimal
from . import bundle_layout as _bundle_layout

if TYPE_CHECKING:
    from ..database.global_db import bundle_cover as _bundle_cover
    from ..database.project_db import pjt_bundle as _pjt_bundle
    from .. import editor_3d as _editor_3d
    from ..wrappers import wxkey_event as _wxkey_event
    from ..wrappers import wxmouse_event as _wxmouse_event


class Bundle(_base.ObjectBase):
    _part: "_bundle_cover.BundleCover" = None
    _db_obj: "_pjt_bundle.PJTBundle" = None
    _editor3d: "_editor_3d.Editor3D" = None

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
        cyl.set_py_data(self)

    def _on_properties(self, evt):
        evt.Skip()

    def _on_add_layout(self, evt: wx.MenuEvent):
        cyl1 = self._objs[0]
        dia = cyl1.diameter

        p1 = cyl1.p1
        p2 = self._menu_coords[1]
        p3 = cyl1.p2

        p3.remove_object(self)

        line = _line.Line(p1, p2)
        line_len = line.length()

        line = _line.Line(p1, p3)
        p2 = line.point_from_start(line_len)

        p2_db_id = p2.add_to_db(self._editor3d.mainframe.project.ptables.pjt_points_3d_table)
        cyl1.p2 = p2

        p2.add_object(self)

        self._db_obj.stop_coord_id = p2_db_id

        p3_db_id = p2.point_id

        new_bundle_db = self._editor3d.mainframe.project.ptables.pjt_bundles_table.insert(self.part.part_id, p2_db_id, p3_db_id)
        new_layout_db = self._editor3d.mainframe.project.ptables.pjt_bundle_layouts_table.insert(p2_db_id, dia)

        new_bundle = Bundle(new_bundle_db, self._editor3d, None)
        new_layout = _bundle_layout.BundleLayout(new_layout_db, self._editor3d, None)

        self._editor3d.mainframe.project.add_bundle(new_bundle)
        self._editor3d.mainframe.project.add_bundle_layout(new_layout)

        evt.Skip()

    def _on_delete(self, evt):
        evt.Skip()

    def menu3d(self, p2d, p3d):
        menu = wx.Menu()

        menu_item = menu.Append(wx.ID_ANY, 'Add Layout')
        self._editor3d.Bind(wx.EVT_MENU, self._on_add_layout, id=menu_item.GetId())
        menu.AppendSeparator()
        menu_item = menu.Append(wx.ID_ANY, 'Delete')
        self._editor3d.Bind(wx.EVT_MENU, self._on_delete, id=menu_item.GetId())
        menu.AppendSeparator()
        menu_item = menu.Append(wx.ID_ANY, 'Properties')
        self._editor3d.Bind(wx.EVT_MENU, self._on_properties, id=menu_item.GetId())
        self._menu_coords = [p2d, p3d]
        self._editor3d.PopupMenu(menu, p2d)
