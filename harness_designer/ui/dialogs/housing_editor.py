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
        keyboard_settings = _config.Config.editor3d.keyboard_settings
        rotate = _config.Config.editor3d.rotate
        pan_tilt = _config.Config.editor3d.pan_tilt
        truck_pedestal = _config.Config.editor3d.truck_pedestal
        walk = _config.Config.editor3d.walk
        zoom = _config.Config.editor3d.zoom
        reset = _config.Config.editor3d.reset
        selected_color = [0.2, 0.6, 0.2, 0.35]
        background_color = [1.0, 0.96, 0.96, 1.0]

        class headlight:
            enable = False
            cutoff = 8.0
            dissipate = 50.0
            color = [0.6, 0.6, 0.4, 0.8]

        class virtual_canvas:
            width = 750
            height = 300

        class floor:
            enable = True
            ground_height = 0.0
            distance = 300
            enable_floor_lock = False

            class grid:
                primary_color = [0.8, 0.1, 0.1, 0.3]
                secondary_color = [0.2925, 0.3430, 0.3430, 0.3]
                size = 50
                enable = False

            class reflections:
                enable = False
                strength = 50.0

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
            is_visible = False
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
        super().__init__(parent, cavity)
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

        scale = _point.Point(1.0, 1.0, 1.0)

        material_color = _color.Color(0.8, 0.3, 0.3, 1.0)
        material = _materials.Plastic(material_color)
        self.db_obj = db_obj
        data = self.build()

        _base3d.Base3D.__init__(self, parent, db_obj, None, self._angle, self._position, scale, material, data=data)

        self._selected_material = _materials.Plastic(_color.Color(0.3, 1.0, 0.3, 1.0))

        self._is_visible = True
        self.autoplace = False
        self.editor3d.Refresh(False)

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
        self._data = self.build()
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
            p1, p2 = _utils.compute_aabb(vertices)

            position = (p2 - p1) / 2.0
            vertices -= position
            vertices @= self._angle
            vertices += self._position

            verts, nrmls, count = _utils.compute_smoothed_vertex_normals(vertices, faces)
        else:
            vertices, faces = _box.create(self.width, self.height, self.length)
            p1, p2 = _utils.compute_aabb(vertices)

            # position = (p2 - p1) / 2.0
            #
            # vertices -= position
            vertices @= self._angle
            vertices += self._position

            verts, nrmls, count = _utils.compute_vertex_normals(vertices, faces)

        return [verts, nrmls, count]


class HousingAccessory(_objects.ObjectBase):
    obj3d: "HousingAccessory3D" = None

    def __init__(self, parent: "HousingEditorDialog", position: _point.Point):
        super().__init__(parent, None)
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

        self._position = position.copy()

        vertices, faces = _sphere.create(1.0, 20)
        vertices += self._position

        data = _utils.compute_smoothed_vertex_normals(vertices, faces)
        material_color = _color.Color(0.8, 0.2, 0.8, 0.99)
        material = _materials.Plastic(material_color)

        _base3d.Base3D.__init__(self, parent, None, None, angle, self._position, scale, material, data=data)

        self._selected_material = _materials.Plastic(_color.Color(0.8, 0.8, 0.2, 0.99))
        self._is_visible = True
        self.editor3d.Refresh(False)


class Housing(_objects.ObjectBase):
    obj3d: "Housing3D" = None

    def __init__(self, parent: "HousingEditorDialog", housing: "_housing.Housing"):
        super().__init__(parent, housing)
        self.dialog = parent
        self.obj3d = Housing3D(self, housing)
        self.obj2d = None

        parent.add_object(self)


class Housing3D(_base3d.Base3D):
    db_obj: "_housing.Housing" = None

    def __init__(self, parent: "Housing", db_obj: "_housing.Housing"):
        self.dialog = parent.dialog

        scale = _point.Point(1.0, 1.0, 1.0)
        model = db_obj.model3d

        if model is not None:
            vertices, faces = model.load()
        else:
            vertices, faces = _box.create(db_obj.width, db_obj.height, db_obj.length)

        angle = db_obj.angle3d
        vertices @= angle

        position = _point.Point(0.0, 0.0, 0.0)
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

        self.cavity_autoplace = _checkbox_ctrl.CheckboxCtrl(cavity_sb, 'Use in Autoplace:')
        self.cavity_autoplace.Bind(wx.EVT_CHECKBOX, self.on_cavity_autoplace)
        self.cavity_autoplace.Enable(False)

        left_size_sizer.Add(self.cavity_type, 0, wx.ALL, 5)

        self.cavity_terminal_sizes = _combobox_ctrl.ComboBoxCtrl(cavity_sb, 'Terminal Sizes', [])
        self.cavity_terminal_sizes.Bind(wx.EVT_COMBOBOX, self.on_cavity_terminal_sizes)
        self.cavity_terminal_sizes.Enable(False)

        left_size_sizer.Add(self.cavity_terminal_sizes, 0, wx.EXPAND | wx.ALL, 5)

        self.auto_place = wx.Button(cavity_sb, wx.ID_ANY, label='Auto Place Cavities')
        self.auto_place.Bind(wx.EVT_BUTTON, self.on_auto_place)
        self.auto_place.Enable(False)

        self.remove_cavity = wx.Button(cavity_sb, wx.ID_ANY, label='Remove Cavity')
        self.remove_cavity.Bind(wx.EVT_BUTTON, self.on_remove_cavity)
        self.remove_cavity.Enable(False)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.AddStretchSpacer(3)
        button_sizer.Add(self.auto_place, 1, wx.ALL, 5)
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

        if not self.cavities:
            self.dialog.housing_panel.enable_housing_rotation(True)


    def on_cavity_autoplace(self, _):
        value = self.cavity_autoplace.GetValue()
        self.cavity.autoplace = value

        count = 0
        for cavity in self.cavities:
            if cavity.autoplace:
                count += 1

        if count == 3:
            self.auto_place.Enable(True)
        else:
            self.auto_place.Enable(False)

    def on_auto_place(self, _):
        positions = []

        for cavity in self.cavities:
            if cavity.autoplace:
                positions.append(cavity.position)

        pos1, pos2, pos3 = positions

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


        for cavity in self.cavities:
            cavity.position


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

                    if not self.cavities:
                        self.dialog.housing_panel.enable_housing_rotation(False)

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

        housing_angle_sz = wx.StaticBoxSizer(wx.VERTICAL, self, "Housing Angle")
        housing_angle_sb = housing_angle_sz.GetStaticBox()

        self.housing_x_angle = _float_ctrl.FloatCtrl(
            housing_angle_sb, 'X:', min_val=-180.0, max_val=180.0, inc=0.01, slider=True)
        self.housing_x_angle.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_housing_x_angle)
        self.housing_x_angle.Enable(False)
        self.housing_x_angle.SetToolTip('You need to remove all added cavities in order to rotare the housing')

        self.housing_y_angle = _float_ctrl.FloatCtrl(
            housing_angle_sb, 'Y:', min_val=-180.0, max_val=180.0, inc=0.01, slider=True)
        self.housing_y_angle.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_housing_y_angle)
        self.housing_y_angle.Enable(False)
        self.housing_y_angle.SetToolTip('You need to remove all added cavities in order to rotare the housing')

        self.housing_z_angle = _float_ctrl.FloatCtrl(
            housing_angle_sb, 'Z:', min_val=-180.0, max_val=180.0, inc=0.01, slider=True)
        self.housing_z_angle.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_housing_z_angle)
        self.housing_z_angle.Enable(False)
        self.housing_z_angle.SetToolTip('You need to remove all added cavities in order to rotare the housing')

        self.housing_angle = housing.angle
        self.housing_angle.bind(self.update_housing_angle)
        self.o_housing_angle = self.housing_angle.copy()
        x, y, z = self.housing_angle.as_euler_float

        self.housing_x_angle.SetValue(x)
        self.housing_y_angle.SetValue(y)
        self.housing_z_angle.SetValue(z)

        housing_angle_sz.Add(self.housing_x_angle, 0, wx.EXPAND | wx.ALL, 5)
        housing_angle_sz.Add(self.housing_y_angle, 0, wx.EXPAND | wx.ALL, 5)
        housing_angle_sz.Add(self.housing_z_angle, 0, wx.EXPAND | wx.ALL, 5)

        vsizer.Add(housing_angle_sz, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(vsizer)
        self.SetupScrolling()

    def update_housing_angle(self, angle: _angle.Angle):
        seal_pos = self.seal_pos.copy()
        cover_pos = self.cover_pos.copy()
        cpa_pos = self.cpa_pos.copy()
        tpa1_pos = self.tpa1_pos.copy()
        tpa2_pos = self.tpa2_pos.copy()
        boot_pos = self.boot_pos.copy()

        inverse = self.o_housing_angle.inverse

        seal_pos @= inverse
        cover_pos @= inverse
        cpa_pos @= inverse
        tpa1_pos @= inverse
        tpa2_pos @= inverse
        boot_pos @= inverse

        seal_pos @= angle
        cover_pos @= angle
        cpa_pos @= angle
        tpa1_pos @= angle
        tpa2_pos @= angle
        boot_pos @= angle

        self.o_housing_angle = angle.copy()

        delta = seal_pos - self.seal_pos
        self.seal_pos += delta

        delta = cover_pos - self.cover_pos
        self.cover_pos += delta

        delta = cpa_pos - self.cpa_pos
        self.cpa_pos += delta

        delta = tpa1_pos - self.tpa1_pos
        self.tpa1_pos += delta

        delta = tpa2_pos - self.tpa2_pos
        self.tpa2_pos += delta

        delta = boot_pos - self.boot_pos
        self.boot_pos += delta

    def enable_housing_rotation(self, flag: bool):
        if flag:
            self.housing_x_angle.SetToolTip('')
            self.housing_z_angle.SetToolTip('')
            self.housing_y_angle.SetToolTip('')
        else:
            self.housing_x_angle.SetToolTip('You need to remove all added cavities in order to rotare the housing')
            self.housing_z_angle.SetToolTip('You need to remove all added cavities in order to rotare the housing')
            self.housing_y_angle.SetToolTip('You need to remove all added cavities in order to rotare the housing')

        self.housing_x_angle.Enable(flag)
        self.housing_y_angle.Enable(flag)
        self.housing_z_angle.Enable(flag)

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

    def on_housing_x_angle(self, evt):
        x = self.housing_x_angle.GetValue()
        self.housing_angle.x = x
        evt.Skip()

    def on_housing_y_angle(self, evt):
        y = self.housing_y_angle.GetValue()
        self.housing_angle.y = y
        evt.Skip()

    def on_housing_z_angle(self, evt):
        z = self.housing_z_angle.GetValue()
        self.housing_angle.z = z
        evt.Skip()


from . import dialog_base as _dialog_base

class HousingEditorDialog(_dialog_base.BaseDialog):

    def __init__(self, parent, db_obj):
        self.db_obj = db_obj

        _dialog_base.BaseDialog.__init__(self, parent, 'Edit Housing', size=(1200, 900))

        vsizer = wx.BoxSizer(wx.VERTICAL)

        self.canvas = _canvas3d.Canvas3D(self.panel, Config.editor3d, size=(750, 500))

        self.housing = Housing(self, db_obj)

        self.housing_panel = HousingPanel(self.panel, self.housing.obj3d)
        self.cavity_panel = CavityPanel(self.panel, self.housing.obj3d)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.canvas, 2, wx.ALL | wx.EXPAND, 5)
        hsizer.Add(self.housing_panel, 1, wx.ALL | wx.EXPAND, 5)

        vsizer.Add(hsizer, 1, wx.EXPAND)
        vsizer.Add(self.cavity_panel, 1, wx.ALL | wx.EXPAND, 5)
        self.panel.SetSizer(vsizer)
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

    @property
    def config(self):
        return Config.editor3d

import math

from . import dialog_base as _dialog_base


'''
class PinCalculatorDialog():



class Block:

    def __init__(self, x: float, y: float, z: float = 0):
        self.x = x
        self.y = y
        self.z = z

    def distance_to(self, other: 'Block') -> float:
        """Calculate 2D distance to another block (ignoring Z)"""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


def calculate_spacing(blocks: List[Block], direction: str = 'right') -> Dict:
    """
    Calculate X and Y spacing from 3 reference blocks.

    Args:
        blocks: List of exactly 3 Block objects
        direction: 'right', 'left', 'up', or 'down' for population direction

    Returns:
        Dictionary with:
        - x_spacing: Distance between blocks in the same row
        - y_spacing: Distance between row centerlines
        - row1_blocks: List of blocks in first row (2 blocks)
        - row2_blocks: List of blocks in second row (1 block)
        - row1_y: Y coordinate centerline of the row with 2 blocks
        - row2_y: Y coordinate of the row with 1 block
    """
    if len(blocks) != 3:
        raise ValueError("Exactly 3 blocks are required")

    # Sort blocks by Y coordinate
    sorted_by_y = sorted(blocks, key=lambda b: b.y)

    # Calculate Y distances between consecutive blocks
    y_diff_01 = abs(sorted_by_y[1].y - sorted_by_y[0].y)
    y_diff_12 = abs(sorted_by_y[2].y - sorted_by_y[1].y)

    # Determine which blocks are in the same row (smallest Y difference)
    if y_diff_01 < y_diff_12:
        # Blocks 0 and 1 are in the same row
        row1_blocks = [sorted_by_y[0], sorted_by_y[1]]
        row2_blocks = [sorted_by_y[2]]
    else:
        # Blocks 1 and 2 are in the same row
        row1_blocks = [sorted_by_y[1], sorted_by_y[2]]
        row2_blocks = [sorted_by_y[0]]

    # Calculate average Y position for the row with 2 blocks (centerline)
    row1_y_average = (row1_blocks[0].y + row1_blocks[1].y) / 2

    # Now recalculate Y spacing using the centerline of row1 and the single block in row2
    y_spacing = abs(row2_blocks[0].y - row1_y_average)

    # Sort row1_blocks by X to get left-to-right order
    row1_blocks.sort(key=lambda b: b.x)

    # Calculate X spacing from the row with 2 blocks
    x_spacing = abs(row1_blocks[1].x - row1_blocks[0].x)

    return {
        'x_spacing': x_spacing,
        'y_spacing': y_spacing,
        'row1_blocks': row1_blocks,  # Row with 2 blocks
        'row2_blocks': row2_blocks,  # Row with 1 block
        'row1_y': row1_y_average,  # Centerline of row with 2 blocks
        'row2_y': row2_blocks[0].y,  # Y position of single block
        'row1_is_bottom': row1_y_average < row2_blocks[0].y
    }


def populate_blocks(
    reference_blocks: List[Block],
    row1_count: int,
    row2_count: int,
    direction: str = 'right'
) -> List[Block]:
    """
    Generate all blocks based on reference blocks and counts.

    Args:
        reference_blocks: The 3 reference blocks
        row1_count: Number of blocks needed in row with 2 reference blocks
        row2_count: Number of blocks needed in row with 1 reference block
        direction: 'right' or 'left' for X direction

    Returns:
        List of all blocks including reference blocks
    """
    spacing = calculate_spacing(reference_blocks, direction)

    all_blocks = []

    # Determine starting positions and direction multiplier
    x_multiplier = 1 if direction == 'right' else -1

    # Populate row1 (the row with 2 reference blocks)
    # Use the leftmost block's X position as starting point
    start_x_row1 = spacing['row1_blocks'][0].x
    for i in range(row1_count):
        all_blocks.append(
            Block(
                start_x_row1 + (i * spacing['x_spacing'] * x_multiplier),
                spacing['row1_y']  # Use centerline Y
            )
        )

    # Populate row2 (the row with 1 reference block)
    start_x_row2 = spacing['row2_blocks'][0].x
    for i in range(row2_count):
        all_blocks.append(
            Block(
                start_x_row2 + (i * spacing['x_spacing'] * x_multiplier),
                spacing['row2_y']
            )
        )

    return all_blocks


# Example usage
if __name__ == "__main__":
    # Example 1: 2 blocks on bottom, 1 on top (with slight Y variation)
    print("Example 1: 2 on bottom (with slight Y variation), 1 on top")
    blocks1 = [
        Block(0, 0),  # Bottom left
        Block(5, 0.5),  # Bottom right (slightly higher)
        Block(2, 10)  # Top center
    ]

    result1 = calculate_spacing(blocks1)
    print(f"  X Spacing: {result1['x_spacing']}")
    print(f"  Y Spacing: {result1['y_spacing']}")
    print(f"  Row1 centerline Y: {result1['row1_y']}")
    print(f"  Row2 Y: {result1['row2_y']}")
    print(f"  Row with 2 blocks is bottom: {result1['row1_is_bottom']}")
    print()

    # Generate 5 blocks in bottom row, 3 in top row
    all_blocks1 = populate_blocks(blocks1, 5, 3, 'right')
    print("  Generated blocks:")
    for i, block in enumerate(all_blocks1):
        print(f"    Block {i}: ({block.x:.1f}, {block.y:.1f})")
    print()

    # Example 2: 1 block on bottom, 2 on top (with Y variation)
    print("Example 2: 1 on bottom, 2 on top (with Y variation)")
    blocks2 = [
        Block(0, 0),  # Bottom left
        Block(3, 7.8),  # Top left (slightly lower)
        Block(9, 8.2)  # Top right (slightly higher)
    ]

    result2 = calculate_spacing(blocks2)
    print(f"  X Spacing: {result2['x_spacing']}")
    print(f"  Y Spacing: {result2['y_spacing']}")
    print(f"  Row1 centerline Y: {result2['row1_y']}")
    print(f"  Row2 Y: {result2['row2_y']}")
    print(f"  Row with 2 blocks is bottom: {result2['row1_is_bottom']}")
    print()

    # Generate 3 blocks in bottom row, 6 in top row
    all_blocks2 = populate_blocks(blocks2, 3, 6, 'right')
    print("  Generated blocks:")
    for i, block in enumerate(all_blocks2):
        print(f"    Block {i}: ({block.x:.1f}, {block.y:.1f})")


    '''
