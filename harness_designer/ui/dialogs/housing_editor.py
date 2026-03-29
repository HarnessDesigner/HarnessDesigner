from typing import TYPE_CHECKING

import wx
from wx.lib import scrolledpanel

from ..widgets import float_ctrl as _float_ctrl
from ..widgets import checkbox_ctrl as _checkbox_ctrl
from ..widgets import text_ctrl as _text_ctrl
from ...shapes import box as _box
from ...shapes import cylinder as _cylinder
from ...shapes import sphere as _sphere
from ... import objects as _objects
from ...objects.objects3d import base3d as _base3d
from ...geometry import point as _point
from ..widgets import combobox_ctrl as _combobox_ctrl
from ...geometry import angle as _angle
from ...geometry.decimal import Decimal as _d
from ... import utils as _utils
from ... import color as _color
from ... import image as _image

from ...gl import canvas3d as _canvas3d
from ...gl import materials as _materials


from ... import config as _config

if TYPE_CHECKING:
    from ... import ui as _ui
    from ...database.global_db import housing as _housing
    from ...database.global_db import cavity as _cavity
    from ...database.global_db import terminal as _terminal


class Config:

    class editor3d:
        lighting = _config.Config.editor3d.lighting
        virtual_canvas = _config.Config.editor3d.virtual_canvas
        keyboard_settings = _config.Config.editor3d.keyboard_settings
        rotate = _config.Config.editor3d.rotate
        pan_tilt = _config.Config.editor3d.pan_tilt
        truck_pedestal = _config.Config.editor3d.truck_pedestal
        walk = _config.Config.editor3d.walk
        zoom = _config.Config.editor3d.zoom
        reset = _config.Config.editor3d.reset
        floor = _config.Config.editor3d.floor
        headlight = _config.Config.editor3d.headlight
        selected_color = [0.2, 0.6, 0.2, 0.35]
        background_color = [0.70, 0.70, 0.70, 1.0]

        class renderer:
            smooth_covers = False
            smooth_boots = True
            smooth_housings = False
            smooth_wires = True
            smooth_bundles = True
            smooth_seals = True
            smooth_cpa_locks = False
            smooth_tpa_locks = False
            smooth_terminals = False

        class focal_target:
            enable = False
            color = [1.0, 0.4, 0.4, 1.0]
            radius = 0.25

        class axis_overlay:
            is_visible = True
            size = (35, 35)
            position = (0, 0)


class HeaderPanel(wx.Panel):

    def __init__(self, parent, label):
        self.bitmap = wx.Bitmap(_image.images.header_1200x80.bitmap)

        wx.Panel.__init__(self, parent, wx.ID_ANY, size=(1200, 80), style=wx.BORDER_SUNKEN)
        self.SetMinClientSize((1200, 80))
        self.SetMinSize((1200, 80))

        self.SetMaxClientSize((1200, 80))
        self.SetMaxSize((1200, 80))

        font = self.GetFont()
        t_width, t_height = self.GetTextExtent(label)
        while t_width < 273 and t_height < 25:
            psize = font.GetPointSize()
            font.SetPointSize(psize + 1)
            self.SetFont(font)
            t_width, t_height = self.GetTextExtent(label)

        while t_width > 273 or t_height > 25:
            psize = font.GetPointSize()
            font.SetPointSize(psize - 1)
            self.SetFont(font)
            t_width, t_height = self.GetTextExtent(label)

        font.MakeItalic()

        dc = wx.MemoryDC()
        dc.SelectObject(self.bitmap)

        gcdc = wx.GCDC(dc)
        gc = gcdc.GetGraphicsContext()

        gc.SetFont(font, wx.Colour(0, 0, 0, 255))
        gc.DrawText(label, 12.0, 6.0)

        dc.SelectObject(wx.NullBitmap)
        gcdc.Destroy()
        del gcdc

        dc.Destroy()
        del dc

        self.sb = wx.StaticBitmap(self, wx.ID_ANY, bitmap=self.bitmap, pos=(0, 0), size=self.bitmap.GetSize())

    def DoGetBestClientSize(self):
        return wx.Size(600, 80)


class Cavity(_objects.ObjectBase):
    obj3d: "Cavity3D" = None

    def __init__(self, parent: "HousingEditorDialog", cavity: "_cavity.Cavity"):
        super().__init__(parent)
        self.dialog = parent
        self.obj3d = Cavity3D(self, cavity)
        self.obj2d = None

        parent.add_object(self)


class Cavity3D(_base3d.Base3D):
    db_obj: "_cavity.Cavity" = None

    def __init__(self, parent: Cavity, db_obj: "_cavity.Cavity"):
        self.dialog: "HousingEditorDialog" = parent.dialog

        self._angle = db_obj.angle3d
        self._position = db_obj.position3d.copy()
        self._position.y += abs(self.dialog.housing.obj3d.y_offset)

        self._allow_real_update = True
        self._real_position = db_obj.position3d
        self._o_real_position = self._real_position.copy()

        scale = _point.Point(1.0, 1.0, 1.0)

        material_color = _color.Color(0.8, 0.3, 0.3, 1.0)
        material = _materials.Plastic(material_color)
        self.db_obj = db_obj
        data = self.build()

        _base3d.Base3D.__init__(self, parent, db_obj, None, self._angle, self._position, scale, material, data=data)

        self._selected_material = _materials.Glowing(_color.Color(0.3, 1.0, 0.3, 1.0))

        self._is_visible = True
        self.editor3d.Refresh(False)

    def _update_real_position(self, position: _point.Point):
        delta = position - self._o_real_position

        if self._allow_real_update:
            self._allow_real_update = False
            self._position += delta
            self._allow_real_update = True
            self._o_real_position = position.copy()

    def _update_position(self, position: _point.Point):
        if self._allow_real_update:
            delta = position - self._o_position
            self._allow_real_update = False
            self._real_position += delta
            self._allow_real_update = True
            self._o_real_position = self._real_position.copy()

        _base3d.Base3D._update_position(self, position)

    def set_selected(self, flag: bool):
        if flag:
            self.dialog.cavity_panel.set_cavity(self)
        else:
            self.dialog.cavity_panel.set_cavity(None)

        _base3d.Base3D.set_selected(self, flag)

    @property
    def compat_terminals(self) -> list["_terminal.Terminal"]:
        return self.db_obj.compat_terminals

    @property
    def width(self) -> float:
        return self.db_obj.width

    @width.setter
    def width(self, value: float):
        self.db_obj.width = value
        self._data = self.build()
        self._compute_obb()
        self._compute_aabb()

        self.editor3d.Refresh(False)

    @property
    def height(self) -> float:
        return self.db_obj.height

    @height.setter
    def height(self, value: float):
        self.db_obj.height = value
        old_data = self._data[:]
        self._data = self.build()
        self._compute_obb()
        self._compute_aabb()

        if self._aabb[0][1] < Config.editor3d.floor.ground_height:
            self._data = old_data

        self._compute_obb()
        self._compute_aabb()
        self.editor3d.Refresh(False)

    @property
    def length(self) -> float:
        return self.db_obj.length

    @length.setter
    def length(self, value: float):
        self.db_obj.length = value
        self._data = self.build()
        self._compute_obb()
        self._compute_aabb()

        self.editor3d.Refresh(False)

    @property
    def is_round(self) -> bool:
        return self.db_obj.round_terminal

    @is_round.setter
    def is_round(self, value: bool):
        self.db_obj.round_terminal = value
        self._data = self.build()
        self._compute_obb()
        self._compute_aabb()

        self.editor3d.Refresh(False)

    @property
    def terminal_sizes(self) -> list[float]:
        return self.db_obj.terminal_sizes

    @terminal_sizes.setter
    def terminal_sizes(self, value: list[float]):
        self.db_obj.terminal_sizes = value

    @property
    def name(self) -> str:
        return self.db_obj.name

    @name.setter
    def name(self, value: str):
        self.db_obj.name = value

    def build(self):
        if self.is_round:
            radius = float(_d(self.width) / _d(2.0))
            vertices, faces = _cylinder.create(radius, self.length, resolution=90, split=1)
            vertices @= self._angle
            vertices += self._position

            verts, nrmls, count = _utils.compute_smoothed_vertex_normals(vertices, faces)
        else:
            vertices, faces = _box.create(self.width, self.height, self.length)
            vertices @= self._angle
            vertices += self._position
            verts, nrmls, count = _utils.compute_vertex_normals(vertices, faces)

        return [verts, nrmls, count]


class HousingAccessory(_objects.ObjectBase):
    obj3d: "HousingAccessory3D" = None

    def __init__(self, parent: "HousingEditorDialog", position: _point.Point):
        super().__init__(parent)
        self.dialog = parent
        self.obj3d = HousingAccessory3D(self, position)
        self.obj2d = None

        parent.add_object(self)


class HousingAccessory3D(_base3d.Base3D):
    db_obj: "_housing.Housing" = None

    def __init__(self, parent: HousingAccessory, position: _point.Point):
        self.dialog = parent.dialog

        angle = _angle.Angle()
        scale = _point.Point(3.0, 3.0, 3.0)

        self._allow_real_update = True
        self._real_position = position
        self._o_real_position = self._real_position.copy()
        self._real_position.bind(self._update_real_position)

        self._position = position.copy()
        self._position.y += abs(self.dialog.housing.obj3d.y_offset)

        vertices, faces = _sphere.create(1.0, 20)
        vertices += self._position

        data = _utils.compute_smoothed_vertex_normals(vertices, faces)
        material_color = _color.Color(0.8, 0.2, 0.8, 1.0)
        material = _materials.Plastic(material_color)

        _base3d.Base3D.__init__(self, parent, None, None, angle, self._position, scale, material, data=data)

        self._selected_material = _materials.Plastic(_color.Color(0.8, 0.8, 0.2, 1.0))
        self._is_visible = True
        self.editor3d.Refresh(False)

    def _update_real_position(self, position: _point.Point):
        delta = position - self._o_real_position

        if self._allow_real_update:
            self._allow_real_update = False
            self._position += delta
            self._allow_real_update = True
            self._o_real_position = position.copy()

    def _update_position(self, position: _point.Point):
        delta = position - self._o_position

        if self._allow_real_update:
            self._allow_real_update = False
            self._real_position += delta
            self._allow_real_update = True
            self._o_real_position = self._real_position.copy()

        _base3d.Base3D._update_position(self, position)


class Housing(_objects.ObjectBase):
    obj3d: "Housing3D" = None

    def __init__(self, parent, housing):
        super().__init__(parent)
        self.obj3d = Housing3D(self, housing)
        self.obj2d = None

        parent.add_object(self)


class Housing3D(_base3d.Base3D):
    db_obj: "_housing.Housing" = None

    def __init__(self, parent, db_obj: "_housing.Housing"):
        angle = _angle.Angle()
        scale = _point.Point(1.0, 1.0, 1.0)

        model = db_obj.model3d

        if model is not None:
            vertices, faces = model.load()
        else:
            vertices, faces = _box.create(db_obj.width, db_obj.height, db_obj.length)

        aabb = _utils.compute_aabb(vertices)

        self.y_offset = aabb[0].y

        position = _point.Point(0.0, abs(self.y_offset), 0.0)
        vertices += position

        data = _utils.compute_vertex_normals(vertices, faces)

        material_color = _color.Color(0.4, 0.4, 0.8, 0.35)
        material = _materials.Glowing(material_color)

        _base3d.Base3D.__init__(self, parent, db_obj, None, angle, position, scale, material, data=data)
        self._is_visible = True
        self.editor3d.Refresh(False)

    def set_selected(self, flag: bool):
        pass

    @property
    def is_selected(self):
        return False

    @property
    def tpa1_pos(self):
        return self.db_obj.tpa_lock_1_position3d

    @property
    def tpa2_pos(self):
        return self.db_obj.tpa_lock_2_position3d

    @property
    def seal_pos(self):
        return self.db_obj.seal_position3d

    @property
    def cpa_pos(self):
        return self.db_obj.cpa_lock_position3d

    @property
    def cover_pos(self):
        return self.db_obj.cover_position3d

    @property
    def boot_pos(self):
        return self.db_obj.boot_position3d


class CavityPanel(scrolledpanel.ScrolledPanel):

    def __init__(self, parent: "HousingEditorDialog", housing: Housing3D):
        self.__hold_change = False
        self.cavities: list[Cavity3D] = []

        for cavity in housing.db_obj.cavities:
            if cavity is None:
                continue

            cavity = Cavity(parent, cavity)
            self.cavities.append(cavity.obj3d)

        self.cavity: Cavity3D = None
        self.housing = housing
        self.dialog = parent

        scrolledpanel.ScrolledPanel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        cavity_sz = wx.StaticBoxSizer(wx.HORIZONTAL, self, "Cavity")
        cavity_sb = cavity_sz.GetStaticBox()

        left_size_sizer = wx.BoxSizer(wx.VERTICAL)

        self.cavity_names = sorted([cavity.name for cavity in self.cavities])

        self.cavity_name = _combobox_ctrl.ComboBoxCtrl(cavity_sb, 'Name:', self.cavity_names)
        self.cavity_name.Bind(wx.EVT_COMBOBOX, self.on_cavity_name)
        self.cavity_name.SetToolTipString('Select OR enter a new name and then press enter to add.')

        left_size_sizer.Add(self.cavity_name, 0, wx.EXPAND | wx.ALL, 5)

        self.change_name = _checkbox_ctrl.CheckboxCtrl(cavity_sb, 'Change Name:')
        self.change_name.SetToolTipString('Changes the selected cavities name to the name entered above.')
        self.change_name.Enable(False)

        left_size_sizer.Add(self.change_name, 0, wx.ALL, 5)

        self.cavity_type = _checkbox_ctrl.CheckboxCtrl(cavity_sb, 'Is Round:')
        self.cavity_type.Bind(wx.EVT_CHECKBOX, self.on_cavity_type)
        self.cavity_type.Enable(False)

        left_size_sizer.Add(self.cavity_type, 0, wx.ALL, 5)

        self.cavity_terminal_sizes = _combobox_ctrl.ComboBoxCtrl(cavity_sb, 'Terminal Sizes', [])
        self.cavity_terminal_sizes.Bind(wx.EVT_COMBOBOX, self.on_cavity_terminal_sizes)
        self.cavity_terminal_sizes.Enable(False)

        left_size_sizer.Add(self.cavity_terminal_sizes, 0, wx.EXPAND | wx.ALL, 5)

        self.remove_cavity = wx.Button(cavity_sb, wx.ID_ANY, label='Remove Cavity')

        self.remove_cavity.Bind(wx.EVT_BUTTON, self.on_remove_cavity)
        self.remove_cavity.Enable(False)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.AddStretchSpacer(3)
        button_sizer.Add(self.remove_cavity, 1, wx.ALL, 5)

        left_size_sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 10)

        cavity_sz.Add(left_size_sizer, 0)

        cavity_position_sz = wx.StaticBoxSizer(wx.VERTICAL, cavity_sb, "Position")
        cavity_position_sb = cavity_position_sz.GetStaticBox()

        self.cavity_x_pos = _float_ctrl.FloatCtrl(
            cavity_position_sb, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cavity_x_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cavity_x_pos)
        self.cavity_x_pos.Enable(False)

        self.cavity_y_pos = _float_ctrl.FloatCtrl(
            cavity_position_sb, 'Y:', min_val=0.0, max_val=999.0, inc=0.01, slider=True)
        self.cavity_y_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cavity_y_pos)
        self.cavity_y_pos.Enable(False)

        self.cavity_z_pos = _float_ctrl.FloatCtrl(
            cavity_position_sb, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cavity_z_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cavity_z_pos)
        self.cavity_z_pos.Enable(False)

        cavity_position_sz.Add(self.cavity_x_pos, 0, wx.ALL, 5)
        cavity_position_sz.Add(self.cavity_y_pos, 0, wx.ALL, 5)
        cavity_position_sz.Add(self.cavity_z_pos, 0, wx.ALL, 5)

        cavity_sz.Add(cavity_position_sz, 0, wx.ALL, 5)

        cavity_size_sz = wx.StaticBoxSizer(wx.VERTICAL, cavity_sb, "Size")
        cavity_size_sb = cavity_size_sz.GetStaticBox()
        self.cavity_x_size = _float_ctrl.FloatCtrl(
            cavity_size_sb, 'X:', min_val=0.0, max_val=999.0, inc=0.01, slider=True)
        self.cavity_x_size.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cavity_x_size)
        self.cavity_x_size.Enable(False)

        self.cavity_y_size = _float_ctrl.FloatCtrl(
            cavity_size_sb, 'Y:', min_val=0.1, max_val=999.0, inc=0.01, slider=True)
        self.cavity_y_size.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cavity_y_size)
        self.cavity_y_size.Enable(False)

        self.cavity_z_size = _float_ctrl.FloatCtrl(
            cavity_size_sb, 'Z:', min_val=0.1, max_val=999.0, inc=0.01, slider=True)
        self.cavity_z_size.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cavity_z_size)
        self.cavity_z_size.Enable(False)

        cavity_size_sz.Add(self.cavity_x_size, 0, wx.ALL, 5)
        cavity_size_sz.Add(self.cavity_y_size, 0, wx.ALL, 5)
        cavity_size_sz.Add(self.cavity_z_size, 0, wx.ALL, 5)

        cavity_sz.Add(cavity_size_sz, 0, wx.ALL, 5)

        cavity_angle_sz = wx.StaticBoxSizer(wx.VERTICAL, cavity_sb, "Angle")
        cavity_angle_sb = cavity_angle_sz.GetStaticBox()

        self.cavity_x_angle = _float_ctrl.FloatCtrl(
            cavity_angle_sb, 'X:', min_val=-180.0, max_val=180.0, inc=0.01, slider=True)
        self.cavity_x_angle.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cavity_x_angle)
        self.cavity_x_angle.Enable(False)

        self.cavity_y_angle = _float_ctrl.FloatCtrl(
            cavity_angle_sb, 'Y:', min_val=-180.0, max_val=180.0, inc=0.01, slider=True)
        self.cavity_y_angle.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cavity_y_angle)
        self.cavity_y_angle.Enable(False)

        self.cavity_z_angle = _float_ctrl.FloatCtrl(
            cavity_angle_sb, 'Z:', min_val=-180.0, max_val=180.0, inc=0.01, slider=True)
        self.cavity_z_angle.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cavity_z_angle)
        self.cavity_z_angle.Enable(False)

        cavity_angle_sz.Add(self.cavity_x_angle, 0, wx.ALL, 5)
        cavity_angle_sz.Add(self.cavity_y_angle, 0, wx.ALL, 5)
        cavity_angle_sz.Add(self.cavity_z_angle, 0, wx.ALL, 5)

        cavity_sz.Add(cavity_angle_sz, 0, wx.ALL, 5)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(cavity_sz, 0, wx.EXPAND | wx.ALL, 5)

        self.cavity_pos: _point.Point = None
        self.cavity_angle: _angle.Angle = None

        self.SetSizer(vsizer)
        self.SetupScrolling()

    def on_cavity_terminal_sizes(self, evt):
        evt.Skip()

        value = self.cavity_terminal_sizes.GetValue()
        values = self.cavity_terminal_sizes.GetItems()

        if value == '':
            return

        if '.' not in value:
            value += '.0'

        if value in values:
            return

        values.append(value)
        values.pop(0)

        for i, item in values:
            if '.' not in item:
                item += '.0'

            values[i] = float(item)

        self.cavity.terminal_sizes = values

        for i, item in enumerate(values):
            values[i] = str(item)

        values.insert(0, '')

        self.cavity_terminal_sizes.SetItems(values)
        self.cavity_terminal_sizes.SetValue('')

    def on_remove_cavity(self, evt):
        self.cavities.remove(self.cavity)
        self.cavity_names.remove(self.cavity.name)
        self.cavity_names = sorted(self.cavity_names)
        self.cavity_name.SetItems(self.cavity_names)

        self.cavity.delete()

        for i, cavity in enumerate(self.cavities):
            cavity.db_obj.idx = i + 1

        self.set_cavity(None)
        evt.Skip()

    def on_cavity_name(self, evt):
        evt.Skip()
        name = self.cavity_name.GetValue().strip()
        if name:
            if self.change_name.GetValue():
                if name in self.cavity_names:
                    raise RuntimeError
                else:
                    self.cavity_names.remove(self.cavity.name)
                    self.cavity.name = name
                    self.cavity_names.append(name)
                    self.cavity_names = sorted(self.cavity_names)
                    self.cavity_name.SetItems(self.cavity_names)
                    self.cavity_name.SetValue(name)
                    self.change_name.SetValue(False)
            elif name in self.cavity_names:
                for cavity in self.cavities:
                    if cavity.name == name:
                        self.set_cavity(cavity)
                        break
                else:
                    raise RuntimeError('sanity check')
            else:
                housing_id = self.housing.db_obj.db_id
                idx = len(self.cavities) + 1

                num_pins = self.housing.db_obj.num_pins

                if (num_pins > 0 and idx <= num_pins) or num_pins == 0:
                    cavity = self.housing.db_obj.table.db.cavities_table.insert(housing_id, idx)

                    cavity = Cavity(self.dialog, cavity).obj3d
                    cavity.name = name
                    self.cavity_names.append(name)
                    self.cavity_names = sorted(self.cavity_names)
                    self.cavity_name.SetItems(self.cavity_names)
                    self.cavities.append(cavity)

                    for cavity in self.cavities:
                        if cavity.is_selected:
                            cavity.set_selected(False)
                            break

                    housing_length = self.housing.db_obj.length
                    housing_width = self.housing.db_obj.width

                    housing_x = housing_width / 2.0
                    housing_y = housing_length / 2.0

                    y_offset = -housing_y

                    c_x_offset = 0

                    for name in self.cavity_names:
                        for cavity in self.cavities:
                            if cavity.name != name:
                                continue

                            c_x = (cavity.width / 2.0) + c_x_offset
                            c_y = (cavity.length / 2.0) + y_offset

                            c_x_offset += cavity.width

                            p2d = cavity.db_obj.position2d
                            p2d.x = c_x
                            p2d.y = c_y

                    cavity.set_selected(True)
        else:
            for cavity in self.cavities:
                if cavity.is_selected:
                    cavity.set_selected(False)
                    break

            return

    def on_cavity_type(self, evt):
        is_round = self.cavity_type.GetValue()
        self.cavity.is_round = is_round
        evt.Skip()

    def on_cavity_x_pos(self, evt):
        x = self.cavity_x_pos.GetValue()
        self.cavity_pos.unbind(self.on_cavity_pos)
        self.cavity.position.x = x
        self.cavity_pos.bind(self.on_cavity_pos)
        evt.Skip()

    def on_cavity_y_pos(self, evt):
        y = self.cavity_y_pos.GetValue()
        self.cavity_pos.unbind(self.on_cavity_pos)
        self.cavity.position.y = y
        self.cavity_pos.bind(self.on_cavity_pos)
        evt.Skip()

    def on_cavity_z_pos(self, evt):
        z = self.cavity_z_pos.GetValue()
        self.cavity_pos.unbind(self.on_cavity_pos)
        self.cavity.position.z = z
        self.cavity_pos.bind(self.on_cavity_pos)
        evt.Skip()

    def on_cavity_x_size(self, evt):
        width = self.cavity_x_size.GetValue()
        self.cavity.width = width
        evt.Skip()

    def on_cavity_y_size(self, evt):
        height = self.cavity_y_size.GetValue()
        self.cavity.height = height
        evt.Skip()

    def on_cavity_z_size(self, evt):
        length = self.cavity_z_size.GetValue()
        self.cavity.length = length
        evt.Skip()

    def on_cavity_x_angle(self, evt):
        x = self.cavity_x_angle.GetValue()
        self.cavity_angle.unbind(self.on_cavity_angle)
        self.cavity.angle.x = x
        self.cavity_angle.bind(self.on_cavity_angle)
        evt.Skip()

    def on_cavity_y_angle(self, evt):
        y = self.cavity_y_angle.GetValue()
        self.cavity_angle.unbind(self.on_cavity_angle)
        self.cavity.angle.y = y
        self.cavity_angle.bind(self.on_cavity_angle)
        evt.Skip()

    def on_cavity_z_angle(self, evt):
        z = self.cavity_z_angle.GetValue()
        self.cavity_angle.unbind(self.on_cavity_angle)
        self.cavity.angle.z = z
        self.cavity_angle.bind(self.on_cavity_angle)
        evt.Skip()

    def on_cavity_pos(self, position: _point.Point):
        x, y, z = position.as_float

        self.cavity_x_pos.SetValue(x)
        self.cavity_y_pos.SetValue(y)
        self.cavity_z_pos.SetValue(z)

    def on_cavity_angle(self, angle: _angle.Angle):
        x, y, z = angle.as_euler_float

        self.cavity_x_angle.SetValue(x)
        self.cavity_y_angle.SetValue(y)
        self.cavity_z_angle.SetValue(z)

    def set_cavity(self, cavity: Cavity3D):
        if self.__hold_change:
            self.__hold_change = False
            return

        self.change_name.Enable(cavity is not None)
        self.cavity_type.Enable(cavity is not None)
        self.cavity_terminal_sizes.Enable(cavity is not None)
        self.cavity_x_pos.Enable(cavity is not None)
        self.cavity_y_pos.Enable(cavity is not None)
        self.cavity_z_pos.Enable(cavity is not None)
        self.cavity_x_size.Enable(cavity is not None)
        self.cavity_y_size.Enable(cavity is not None)
        self.cavity_z_size.Enable(cavity is not None)
        self.cavity_x_angle.Enable(cavity is not None)
        self.cavity_y_angle.Enable(cavity is not None)
        self.cavity_z_angle.Enable(cavity is not None)
        self.remove_cavity.Enable(cavity is not None)

        self.change_name.SetValue(False)

        if self.cavity is not None:
            self.cavity_pos.unbind(self.on_cavity_pos)
            self.cavity_angle.unbind(self.on_cavity_angle)

        self.cavity = cavity

        if cavity is None:
            self.cavity_name.SetValue('')
        else:
            self.cavity_pos = cavity.position
            self.cavity_angle = cavity.angle

            self.cavity_pos.bind(self.on_cavity_pos)
            self.cavity_angle.bind(self.on_cavity_angle)

            self.cavity_name.SetValue(cavity.name)
            self.cavity_type.SetValue(cavity.is_round)
            choices = [str(item) for item in cavity.terminal_sizes]
            choices.insert(0, '')

            self.cavity_terminal_sizes.SetItems(choices)
            self.cavity_terminal_sizes.SetValue('')

            x, y, z = cavity.position.as_float
            self.cavity_x_pos.SetValue(x)
            self.cavity_y_pos.SetValue(y)
            self.cavity_z_pos.SetValue(z)

            self.cavity_x_size.SetValue(cavity.width)
            self.cavity_y_size.SetValue(cavity.height)
            self.cavity_z_size.SetValue(cavity.length)

            x, y, z = cavity.angle.as_euler_float
            self.cavity_x_angle.SetValue(x)
            self.cavity_y_angle.SetValue(y)
            self.cavity_z_angle.SetValue(z)

        self.cavity = cavity


class HousingPanel(scrolledpanel.ScrolledPanel):

    def __init__(self, parent: "HousingEditorDialog", housing: Housing3D):
        self.housing = housing
        self.dialog = parent

        scrolledpanel.ScrolledPanel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        boot_position_sz = wx.StaticBoxSizer(wx.VERTICAL, self, "Boot Position")
        boot_position_sb = boot_position_sz.GetStaticBox()

        self.boot_x_pos = _float_ctrl.FloatCtrl(
            boot_position_sb, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.boot_x_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_boot_x_pos)

        self.boot_y_pos = _float_ctrl.FloatCtrl(
            boot_position_sb, 'Y:', min_val=0.0, max_val=999.0, inc=0.01, slider=True)
        self.boot_y_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_boot_y_pos)

        self.boot_z_pos = _float_ctrl.FloatCtrl(
            boot_position_sb, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.boot_z_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_boot_z_pos)

        self.boot_pos = housing.boot_pos
        self.boot_pos_obj = HousingAccessory(self.dialog, self.boot_pos).obj3d

        self.boot_pos.bind(self.on_boot_pos)

        x, y, z = self.boot_pos.as_float

        self.boot_x_pos.SetValue(x)
        self.boot_y_pos.SetValue(y)
        self.boot_z_pos.SetValue(z)

        boot_position_sz.Add(self.boot_x_pos, 0, wx.EXPAND | wx.ALL, 5)
        boot_position_sz.Add(self.boot_y_pos, 0, wx.EXPAND | wx.ALL, 5)
        boot_position_sz.Add(self.boot_z_pos, 0, wx.EXPAND | wx.ALL, 5)

        vsizer.Add(boot_position_sz, 0, wx.EXPAND | wx.ALL, 5)

        cpa_lock_position_sz = wx.StaticBoxSizer(wx.VERTICAL, self, "CPA Lock Position")
        cpa_lock_position_sb = cpa_lock_position_sz.GetStaticBox()

        self.cpa_x_pos = _float_ctrl.FloatCtrl(
            cpa_lock_position_sb, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cpa_x_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cpa_x_pos)

        self.cpa_y_pos = _float_ctrl.FloatCtrl(
            cpa_lock_position_sb, 'Y:', min_val=0.0, max_val=999.0, inc=0.01, slider=True)
        self.cpa_y_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cpa_y_pos)

        self.cpa_z_pos = _float_ctrl.FloatCtrl(
            cpa_lock_position_sb, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cpa_z_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cpa_z_pos)

        self.cpa_pos = housing.cpa_pos
        self.cpa_pos_obj = HousingAccessory(self.dialog, self.cpa_pos).obj3d

        self.cpa_pos.bind(self.on_cpa_pos)

        x, y, z = self.cpa_pos.as_float

        self.cpa_x_pos.SetValue(x)
        self.cpa_y_pos.SetValue(y)
        self.cpa_z_pos.SetValue(z)

        cpa_lock_position_sz.Add(self.cpa_x_pos, 0, wx.EXPAND | wx.ALL, 5)
        cpa_lock_position_sz.Add(self.cpa_y_pos, 0, wx.EXPAND | wx.ALL, 5)
        cpa_lock_position_sz.Add(self.cpa_z_pos, 0, wx.EXPAND | wx.ALL, 5)

        vsizer.Add(cpa_lock_position_sz, 0, wx.EXPAND | wx.ALL, 5)

        cover_position_sz = wx.StaticBoxSizer(wx.VERTICAL, self, "Cover Position")
        cover_position_sb = cover_position_sz.GetStaticBox()

        self.cover_x_pos = _float_ctrl.FloatCtrl(
            cover_position_sb, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cover_x_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cover_x_pos)

        self.cover_y_pos = _float_ctrl.FloatCtrl(
            cover_position_sb, 'Y:', min_val=0.0, max_val=999.0, inc=0.01, slider=True)
        self.cover_y_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cover_y_pos)

        self.cover_z_pos = _float_ctrl.FloatCtrl(
            cover_position_sb, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cover_z_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cover_z_pos)

        self.cover_pos = housing.cover_pos
        self.cover_pos_obj = HousingAccessory(self.dialog, self.cover_pos).obj3d
        self.cover_pos.bind(self.on_cover_pos)

        x, y, z = self.cover_pos.as_float

        self.cover_x_pos.SetValue(x)
        self.cover_y_pos.SetValue(y)
        self.cover_z_pos.SetValue(z)

        cover_position_sz.Add(self.cover_x_pos, 0, wx.EXPAND | wx.ALL, 5)
        cover_position_sz.Add(self.cover_y_pos, 0, wx.EXPAND | wx.ALL, 5)
        cover_position_sz.Add(self.cover_z_pos, 0, wx.EXPAND | wx.ALL, 5)

        vsizer.Add(cover_position_sz, 0, wx.EXPAND | wx.ALL, 5)

        tpa_lock1_position_sz = wx.StaticBoxSizer(wx.VERTICAL, self, "TPA Lock 1 Position")
        tpa_lock1_position_sb = tpa_lock1_position_sz.GetStaticBox()

        self.tpa1_x_pos = _float_ctrl.FloatCtrl(
            tpa_lock1_position_sb, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa1_x_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_tpa1_x_pos)

        self.tpa1_y_pos = _float_ctrl.FloatCtrl(
            tpa_lock1_position_sb, 'Y:', min_val=0.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa1_y_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_tpa1_y_pos)

        self.tpa1_z_pos = _float_ctrl.FloatCtrl(
            tpa_lock1_position_sb, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa1_z_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_tpa1_z_pos)

        self.tpa1_pos = housing.tpa1_pos
        self.tpa1_pos_obj = HousingAccessory(self.dialog, self.tpa1_pos).obj3d
        self.tpa1_pos.bind(self.on_tpa1_pos)

        x, y, z = self.tpa1_pos.as_float

        self.tpa1_x_pos.SetValue(x)
        self.tpa1_y_pos.SetValue(y)
        self.tpa1_z_pos.SetValue(z)

        tpa_lock1_position_sz.Add(self.tpa1_x_pos, 0, wx.EXPAND | wx.ALL, 5)
        tpa_lock1_position_sz.Add(self.tpa1_y_pos, 0, wx.EXPAND | wx.ALL, 5)
        tpa_lock1_position_sz.Add(self.tpa1_z_pos, 0, wx.EXPAND | wx.ALL, 5)

        vsizer.Add(tpa_lock1_position_sz, 0, wx.EXPAND | wx.ALL, 5)

        tpa_lock2_position_sz = wx.StaticBoxSizer(wx.VERTICAL, self, "TPA Lock 2 Position")
        tpa_lock2_position_sb = tpa_lock2_position_sz.GetStaticBox()

        self.tpa2_x_pos = _float_ctrl.FloatCtrl(
            tpa_lock2_position_sb, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa2_x_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_tpa2_x_pos)

        self.tpa2_y_pos = _float_ctrl.FloatCtrl(
            tpa_lock2_position_sb, 'Y:', min_val=0.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa2_y_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_tpa2_y_pos)

        self.tpa2_z_pos = _float_ctrl.FloatCtrl(
            tpa_lock2_position_sb, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa2_z_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_tpa2_z_pos)

        self.tpa2_pos = housing.tpa2_pos
        self.tpa2_pos_obj = HousingAccessory(self.dialog, self.tpa2_pos).obj3d
        self.tpa2_pos.bind(self.on_tpa2_pos)

        x, y, z = self.tpa2_pos.as_float

        self.tpa2_x_pos.SetValue(x)
        self.tpa2_y_pos.SetValue(y)
        self.tpa2_z_pos.SetValue(z)

        tpa_lock2_position_sz.Add(self.tpa2_x_pos, 0, wx.EXPAND | wx.ALL, 5)
        tpa_lock2_position_sz.Add(self.tpa2_y_pos, 0, wx.EXPAND | wx.ALL, 5)
        tpa_lock2_position_sz.Add(self.tpa2_z_pos, 0, wx.EXPAND | wx.ALL, 5)

        vsizer.Add(tpa_lock2_position_sz, 0, wx.EXPAND | wx.ALL, 5)

        seal_position_sz = wx.StaticBoxSizer(wx.VERTICAL, self, "Seal Position")
        seal_position_sb = seal_position_sz.GetStaticBox()

        self.seal_x_pos = _float_ctrl.FloatCtrl(
            seal_position_sb, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.seal_x_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_seal_x_pos)

        self.seal_y_pos = _float_ctrl.FloatCtrl(
            seal_position_sb, 'Y:', min_val=0.0, max_val=999.0, inc=0.01, slider=True)
        self.seal_y_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_seal_y_pos)

        self.seal_z_pos = _float_ctrl.FloatCtrl(
            seal_position_sb, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.seal_z_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_seal_z_pos)

        self.seal_pos = housing.seal_pos
        self.seal_pos_obj = HousingAccessory(self.dialog, self.seal_pos).obj3d
        self.seal_pos.bind(self.on_seal_pos)

        x, y, z = self.seal_pos.as_float

        self.seal_x_pos.SetValue(x)
        self.seal_y_pos.SetValue(y)
        self.seal_z_pos.SetValue(z)

        seal_position_sz.Add(self.seal_x_pos, 0, wx.EXPAND | wx.ALL, 5)
        seal_position_sz.Add(self.seal_y_pos, 0, wx.EXPAND | wx.ALL, 5)
        seal_position_sz.Add(self.seal_z_pos, 0, wx.EXPAND | wx.ALL, 5)

        vsizer.Add(seal_position_sz, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(vsizer)
        self.SetupScrolling()

    def on_boot_pos(self, position: _point.Point):
        x, y, z = position.as_float

        self.boot_x_pos.SetValue(x)
        self.boot_y_pos.SetValue(y)
        self.boot_z_pos.SetValue(z)

    def on_cpa_pos(self, position: _point.Point):
        x, y, z = position.as_float

        self.cpa_x_pos.SetValue(x)
        self.cpa_y_pos.SetValue(y)
        self.cpa_z_pos.SetValue(z)

    def on_cover_pos(self, position: _point.Point):
        x, y, z = position.as_float

        self.cover_x_pos.SetValue(x)
        self.cover_y_pos.SetValue(y)
        self.cover_z_pos.SetValue(z)

    def on_tpa1_pos(self, position: _point.Point):
        x, y, z = position.as_float

        self.tpa1_x_pos.SetValue(x)
        self.tpa1_y_pos.SetValue(y)
        self.tpa1_z_pos.SetValue(z)

    def on_tpa2_pos(self, position: _point.Point):
        x, y, z = position.as_float

        self.tpa2_x_pos.SetValue(x)
        self.tpa2_y_pos.SetValue(y)
        self.tpa2_z_pos.SetValue(z)

    def on_seal_pos(self, position: _point.Point):
        x, y, z = position.as_float

        self.seal_x_pos.SetValue(x)
        self.seal_y_pos.SetValue(y)
        self.seal_z_pos.SetValue(z)

    def on_boot_x_pos(self, evt):
        x = self.boot_x_pos.GetValue()
        self.boot_pos.unbind(self.on_boot_pos)
        self.boot_pos.x = x
        self.boot_pos.bind(self.on_boot_pos)
        evt.Skip()

    def on_boot_y_pos(self, evt):
        y = self.boot_y_pos.GetValue()
        self.boot_pos.unbind(self.on_boot_pos)
        self.boot_pos.y = y
        self.boot_pos.bind(self.on_boot_pos)
        evt.Skip()

    def on_boot_z_pos(self, evt):
        z = self.boot_z_pos.GetValue()
        self.boot_pos.unbind(self.on_boot_pos)
        self.boot_pos.z = z
        self.boot_pos.bind(self.on_boot_pos)
        evt.Skip()

    def on_cpa_x_pos(self, evt):
        x = self.cpa_x_pos.GetValue()
        self.cpa_pos.unbind(self.on_cpa_pos)
        self.cpa_pos.x = x
        self.cpa_pos.bind(self.on_cpa_pos)
        evt.Skip()

    def on_cpa_y_pos(self, evt):
        y = self.cpa_y_pos.GetValue()
        self.cpa_pos.unbind(self.on_cpa_pos)
        self.cpa_pos.y = y
        self.cpa_pos.bind(self.on_cpa_pos)
        evt.Skip()

    def on_cpa_z_pos(self, evt):
        z = self.cpa_z_pos.GetValue()
        self.cpa_pos.unbind(self.on_cpa_pos)
        self.cpa_pos.z = z
        self.cpa_pos.bind(self.on_cpa_pos)
        evt.Skip()

    def on_cover_x_pos(self, evt):
        x = self.cover_x_pos.GetValue()
        self.cover_pos.unbind(self.on_cover_pos)
        self.cover_pos.x = x
        self.cover_pos.bind(self.on_cover_pos)
        evt.Skip()

    def on_cover_y_pos(self, evt):
        y = self.cover_y_pos.GetValue()
        self.cover_pos.unbind(self.on_cover_pos)
        self.cover_pos.y = y
        self.cover_pos.bind(self.on_cover_pos)
        evt.Skip()

    def on_cover_z_pos(self, evt):
        z = self.cover_z_pos.GetValue()
        self.cover_pos.unbind(self.on_cover_pos)
        self.cover_pos.z = z
        self.cover_pos.bind(self.on_cover_pos)
        evt.Skip()

    def on_tpa1_x_pos(self, evt):
        x = self.tpa1_x_pos.GetValue()
        self.tpa1_pos.unbind(self.on_tpa1_pos)
        self.tpa1_pos.x = x
        self.tpa1_pos.bind(self.on_tpa1_pos)
        evt.Skip()

    def on_tpa1_y_pos(self, evt):
        y = self.tpa1_y_pos.GetValue()
        self.tpa1_pos.unbind(self.on_tpa1_pos)
        self.tpa1_pos.y = y
        self.tpa1_pos.bind(self.on_tpa1_pos)
        evt.Skip()

    def on_tpa1_z_pos(self, evt):
        z = self.tpa1_z_pos.GetValue()
        self.tpa1_pos.unbind(self.on_tpa1_pos)
        self.tpa1_pos.z = z
        self.tpa1_pos.bind(self.on_tpa1_pos)
        evt.Skip()

    def on_tpa2_x_pos(self, evt):
        x = self.tpa2_x_pos.GetValue()
        self.tpa2_pos.unbind(self.on_tpa2_pos)
        self.tpa2_pos.x = x
        self.tpa2_pos.bind(self.on_tpa2_pos)
        evt.Skip()

    def on_tpa2_y_pos(self, evt):
        y = self.tpa2_y_pos.GetValue()
        self.tpa2_pos.unbind(self.on_tpa2_pos)
        self.tpa2_pos.y = y
        self.tpa2_pos.bind(self.on_tpa2_pos)
        evt.Skip()

    def on_tpa2_z_pos(self, evt):
        z = self.tpa2_z_pos.GetValue()
        self.tpa2_pos.unbind(self.on_tpa2_pos)
        self.tpa2_pos.z = z
        self.tpa2_pos.bind(self.on_tpa2_pos)
        evt.Skip()

    def on_seal_x_pos(self, evt):
        x = self.seal_x_pos.GetValue()
        self.seal_pos.unbind(self.on_seal_pos)
        self.seal_pos.x = x
        self.seal_pos.bind(self.on_seal_pos)
        evt.Skip()

    def on_seal_y_pos(self, evt):
        y = self.seal_y_pos.GetValue()
        self.seal_pos.unbind(self.on_seal_pos)
        self.seal_pos.y = y
        self.seal_pos.bind(self.on_seal_pos)
        evt.Skip()

    def on_seal_z_pos(self, evt):
        z = self.seal_z_pos.GetValue()
        self.seal_pos.unbind(self.on_seal_pos)
        self.seal_pos.z = z
        self.seal_pos.bind(self.on_seal_pos)
        evt.Skip()


class HousingEditorDialog(wx.Dialog):

    def __init__(self, parent, db_obj):
        self.db_obj = db_obj

        style = wx.CAPTION | wx.CLOSE_BOX | wx.STAY_ON_TOP

        wx.Dialog.__init__(self, parent, wx.ID_ANY, title='', size=(1200, 700),
                           style=style)

        self.header = HeaderPanel(self, 'Edit Housing')

        button_sizer = self.CreateStdDialogButtonSizer(wx.OK)
        self.button_sizer = self.CreateSeparatedSizer(button_sizer)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self.header, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        self.canvas = _canvas3d.Canvas3D(self, Config.editor3d, size=(750, 300))

        self.housing = Housing(self, db_obj)

        self.housing_panel = HousingPanel(self, self.housing.obj3d)
        self.cavity_panel = CavityPanel(self, self.housing.obj3d)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.canvas, 2, wx.ALL | wx.EXPAND, 5)
        hsizer.Add(self.housing_panel, 1, wx.ALL | wx.EXPAND, 5)

        vsizer.Add(hsizer, 1, wx.EXPAND)
        vsizer.Add(self.cavity_panel, 1, wx.ALL | wx.EXPAND, 5)

        vsizer.Add(self.button_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(vsizer)
        self.CenterOnParent()

    @property
    def editor2d(self):
        return None

    @property
    def editor3d(self):
        return self

    def add_object(self, obj):
        self.canvas.add_object(obj)

    def remove_object(self, obj):
        self.canvas.remove_object(obj)

    def _set_selected(self, obj):
        self._selected_obj = obj
        self.canvas.set_selected(obj)

    def set_selected(self, obj):
        if obj is not None:
            obj.set_selected(True)

    def get_selected(self):
        return self._selected_obj
