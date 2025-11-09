from typing import TYPE_CHECKING
import wx

from . import base as _base

if TYPE_CHECKING:
    from ..database.global_db import housing as _housing
    from ..database.project_db import pjt_housing as _pjt_housing
    from .. import editor_3d as _editor_3d
    from .. import editor_2d as _editor_2d


ADD_TERMINAL_2D_ID = wx.NewIdRef()
DELETE_TERMINAL_2D_ID = wx.NewIdRef()

ADD_TERMINAL_3D_ID = wx.NewIdRef()
DELETE_TERMINAL_3D_ID = wx.NewIdRef()

HOUSING_DELETE_ID = wx.NewIdRef()
HOUSING_PROPERTIES_ID = wx.NewIdRef()

HOUSING_ROTATE_2D_ID = wx.NewIdRef()
HOUSING_ROTATE_3D_ID = wx.NewIdRef()


class HSizer(wx.BoxSizer):

    def __init__(self, parent, text, ctrl):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)

        if text is not None:
            st = wx.StaticText(parent, wx.ID_ANY, label=text)
            self.Add(st, 0, wx.ALL, 5)

        self.Add(ctrl, 0, wx.ALL, 5)


class Rotate3DCtrl(wx.PopupTransientWindow):

    def __init__(self, parent, obj):
        wx.PopupTransientWindow.__init__(self, parent)

        x_angle, y_angle, z_angle = obj.get_angles()

        self.x_ctrl = wx.Slider(self, wx.ID_ANY, value=x_angle, minValue=0, maxValue=359)
        self.y_ctrl = wx.Slider(self, wx.ID_ANY, value=y_angle, minValue=0, maxValue=359)
        self.z_ctrl = wx.Slider(self, wx.ID_ANY, value=z_angle, minValue=0, maxValue=359)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(HSizer(self, 'X:', self.x_ctrl), 0)
        sizer.Add(HSizer(self, 'Y:', self.y_ctrl), 0)
        sizer.Add(HSizer(self, 'Z:', self.z_ctrl), 0)

        self.SetSizer(sizer)

    def on_x(self, evt):
        evt.Skip()

    def on_y(self, evt):
        evt.Skip()

    def on_z(self, evt):
        evt.Skip()


class Housing(_base.ObjectBase):
    _part: "_housing.Housing" = None
    _db_obj: "_pjt_housing.PJTHousing" = None

    def __init__(self, db_obj: "_pjt_housing.PJTHousing", editor3d: "_editor_3d.Editor3D", editor2d: "_editor_2d.Editor2D"):
        _base.ObjectBase.__init__(self, db_obj, editor3d, editor2d)

        part = db_obj.part

        center = db_obj.point3d.point

        model3d = part.model3d
        if model3d is None:
            from ..editor_3d.shapes import box as _box
            model3d = _box.Box(center, part.length, part.width, part.height, part.color, part.color)
        else:
            from ..editor_3d.shapes import model3d as _model3d

            model3d = _model3d.Model3D(center, model3d, part.model3d_type, part.color)

        model3d.set_angles(db_obj.x_angle_3d, db_obj.y_angle_3d, db_obj.z_angle_3d, center)
        model3d.add_to_plot(editor3d.axes)
        self._objs.append(model3d)
        model3d.center.add_object(self)
        model3d.set_py_data(self)

        editor2d.add_connector(db_obj)

    def menu2d(self, p2d):
        menu = wx.Menu()

        menu_item = menu.Append(wx.ID_ANY, 'Add Terminal')
        self._editor2d.Bind(wx.EVT_MENU, self._on_add_terminal_2d, id=menu_item.GetId())
        menu.AppendSeparator()
        menu_item = menu.Append(wx.ID_ANY, 'Delete')
        self._editor2d.Bind(wx.EVT_MENU, self._on_delete, id=menu_item.GetId())
        menu.AppendSeparator()
        menu_item = menu.Append(wx.ID_ANY, 'Properties')
        self._editor2d.Bind(wx.EVT_MENU, self._on_properties, id=menu_item.GetId())
        self._menu_coords = [p2d]
        self._editor2d.PopupMenu(menu, p2d)

    def menu3d(self, p2d, p3d):
        menu = wx.Menu()

        menu_item = menu.Append(wx.ID_ANY, 'Add Layout')
        self._editor3d.Bind(wx.EVT_MENU, self._on_add_terminal_3d, id=menu_item.GetId())
        menu.AppendSeparator()
        menu_item = menu.Append(wx.ID_ANY, 'Delete')
        self._editor3d.Bind(wx.EVT_MENU, self._on_delete, id=menu_item.GetId())
        menu.AppendSeparator()
        menu_item = menu.Append(wx.ID_ANY, 'Properties')
        self._editor3d.Bind(wx.EVT_MENU, self._on_properties, id=menu_item.GetId())
        self._menu_coords = [p2d, p3d]
        self._editor3d.PopupMenu(menu, p2d)
