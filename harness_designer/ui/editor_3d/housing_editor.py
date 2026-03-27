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

        class floor:
            enable = False
            ground_height = 0.0
            distance = 1000

            class grid:
                primary_color = [0.2039, 0.2549, 0.2902, 0.8]
                secondary_color = [0.2925, 0.3430, 0.3430, 0.8]
                size = 50
                enable = False

            class reflections:
                enable = False
                strength = 50.0

    class debug:

        class rendering3d:
            draw_obb = False
            draw_aabb = False
            draw_normals = False
            draw_edges = False
            draw_vertices = False
            draw_faces = True
            edge_color_dark = [0.7, 0.7, 0.7]  # For dark materials
            edge_color_light = [0.0, 0.0, 0.0]  # For light materials
            edge_luminance_threshold = 0.5  # Brightness cutoff
            vertices_color = [1.0, 0.0, 0.0]
            normals_color = [1.0, 1.0, 1.0]

    class axis_overlay:
        is_visible = False
        size = (75, 75)
        position = (830, 245)


class Cavity(_objects.ObjectBase):

    def __init__(self, parent, cavity):
        super().__init__(parent)
        self.obj3d = Cavity3D(self, cavity)
        self.obj2d = None

        parent.add_object(self)


class Cavity3D(_base3d.Base3D):
    db_obj: "_cavity.Cavity" = None

    def __init__(self, parent, db_obj: "_cavity.Cavity"):
        angle = db_obj.angle3d
        position = db_obj.position3d
        scale = _point.Point(1.0, 1.0, 1.0)

        data = self.build()

        material_color = _color.Color(0.6, 0.2, 0.2, 0.35)
        material = _materials.Plastic(material_color)

        _base3d.Base3D.__init__(self, parent, db_obj, None, angle, position, scale, material, data=data)

    @property
    def compat_terminals(self) -> list["_terminal.Terminal"]:
        return self.db_obj.compat_terminals

    @property
    def width(self) -> float:
        return self.db_obj.width

    @width.setter
    def width(self, value: float):
        self.db_obj.width = value
        self.build()

    @property
    def height(self) -> float:
        return self.db_obj.height

    @height.setter
    def height(self, value: float):
        self.db_obj.height = value
        self.build()

    @property
    def length(self) -> float:
        return self.db_obj.length

    @length.setter
    def length(self, value: float):
        self.db_obj.length = value
        self.build()

    @property
    def is_round(self) -> bool:
        return self.db_obj.round_terminal

    @is_round.setter
    def is_round(self, value: bool):
        self.db_obj.round_terminal = value
        self.build()

    @property
    def terminal_size(self) -> bool:
        return self.db_obj.terminal_size

    @terminal_size.setter
    def terminal_size(self, value: bool):
        self.db_obj.terminal_size = value

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
        else:
            vertices, faces = _box.create(self.width, self.height, self.length)

        verts, nrmls, count = _utils.compute_smoothed_vertex_normals(vertices, faces)
        return verts, nrmls, count


class HousingAccessory(_objects.ObjectBase):

    def __init__(self, parent, position: _point.Point):
        super().__init__(parent)
        self.obj3d = HousingAccessory3D(self, position)
        self.obj2d = None

        parent.add_object(self)


class HousingAccessory3D(_base3d.Base3D):
    db_obj: "_housing.Housing" = None

    def __init__(self, parent, position: _point.Point):
        angle = _angle.Angle()
        scale = _point.Point(1.0, 1.0, 1.0)

        vertices, faces = _sphere.create(1.0, 20)

        data = _utils.compute_smoothed_vertex_normals(vertices, faces)
        material_color = _color.Color(1.0, 0.2, 1.0, 1.0)
        material = _materials.Metallic(material_color)

        _base3d.Base3D.__init__(self, parent, None, None, angle, position, scale, material, data=data)


class Housing(_objects.ObjectBase):

    def __init__(self, parent, housing):
        super().__init__(parent)
        self.obj3d = Housing3D(self, housing)
        self.obj2d = None

        parent.add_object(self)


class Housing3D(_base3d.Base3D):
    db_obj: "_housing.Housing" = None

    def __init__(self, parent, db_obj: "_housing.Housing"):
        angle = _angle.Angle()
        position = _point.Point(0.0, 0.0, 0.0)
        scale = _point.Point(1.0, 1.0, 1.0)

        model = db_obj.model3d

        if model is not None:
            scale = _point.Point(1.0, 1.0, 1.0)
            vertices, faces = model.load()
        else:
            vertices, faces = _box.create(db_obj.width, db_obj.height, db_obj.length)

        data = _utils.compute_vertex_normals(vertices, faces)

        material_color = _color.Color(0.4, 0.4, 0.4, 0.35)
        material = _materials.Plastic(material_color)

        _base3d.Base3D.__init__(self, parent, db_obj, None, angle, position, scale, material, data=data)

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


class SettingsPanel(scrolledpanel.ScrolledPanel):

    def __init__(self, parent, dialog: "HousingEditor", housing: Housing3D):
        self.cavity: Cavity3D = None
        self.housing = housing
        self.dialog = dialog

        scrolledpanel.ScrolledPanel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        cavity_sz = wx.StaticBoxSizer(wx.VERTICAL, self, "Cavity")
        cavity_sb = cavity_sz.GetStaticBox()

        self.cavity_name = _text_ctrl.TextCtrl(cavity_sb, 'Name:', size=(-1, -1), apply_button=True)
        self.cavity_name.Bind(wx.EVT_BUTTON, self.on_cavity_name)
        self.cavity_name.Enable(False)

        self.cavity_type = _checkbox_ctrl.CheckboxCtrl(cavity_sb, 'Is Round:')
        self.cavity_type.Bind(wx.EVT_CHECKBOX, self.on_cavity_type)
        self.cavity_type.Enable(False)

        self.cavity_terminal_size = _combobox_ctrl.ComboBoxCtrl(cavity_sb, 'Terminal Size', [])
        self.cavity_terminal_size.Bind(wx.EVT_COMBOBOX, self.on_cavity_terminal_size)
        self.cavity_terminal_size.Enable(False)

        self.add_cavity = wx.Button(cavity_sb, wx.ID_ANY, label='Add Cavity')
        self.remove_cavity = wx.Button(cavity_sb, wx.ID_ANY, label='Remove Cavity')

        self.add_cavity.Bind(wx.EVT_BUTTON, self.on_add_cavity)
        self.remove_cavity.Bind(wx.EVT_BUTTON, self.on_remove_cavity)
        self.remove_cavity.Enable(False)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.AddStretchSpacer(3)
        button_sizer.Add(self.remove_cavity, 1, wx.ALL, 5)
        button_sizer.Add(self.add_cavity, 1, wx.ALL, 5)

        cavity_sz.Add(self.cavity_name, 0, wx.ALL, 5)
        cavity_sz.Add(self.cavity_type, 0, wx.ALL, 5)
        cavity_sz.Add(self.cavity_terminal_size, 0, wx.ALL, 5)
        cavity_sz.Add(button_sizer, 0)

        cavity_position_sz = wx.StaticBoxSizer(wx.VERTICAL, cavity_sb, "Position")
        cavity_position_sb = cavity_position_sz.GetStaticBox()

        self.cavity_x_pos = _float_ctrl.FloatCtrl(
            cavity_position_sb, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cavity_x_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cavity_x_pos)
        self.cavity_x_pos.Enable(False)

        self.cavity_y_pos = _float_ctrl.FloatCtrl(
            cavity_position_sb, 'Y:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
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
            cavity_size_sb, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cavity_x_size.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cavity_x_size)
        self.cavity_x_size.Enable(False)

        self.cavity_y_size = _float_ctrl.FloatCtrl(
            cavity_size_sb, 'Y:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cavity_y_size.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cavity_y_size)
        self.cavity_y_size.Enable(False)

        self.cavity_z_size = _float_ctrl.FloatCtrl(
            cavity_size_sb, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
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

        vsizer.Add(cavity_sz, 0)

        boot_position_sz = wx.StaticBoxSizer(wx.VERTICAL, self, "Boot Position")
        boot_position_sb = boot_position_sz.GetStaticBox()

        self.boot_x_pos = _float_ctrl.FloatCtrl(
            boot_position_sb, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.boot_x_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_boot_x_pos)

        self.boot_y_pos = _float_ctrl.FloatCtrl(
            boot_position_sb, 'Y:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.boot_y_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_boot_y_pos)

        self.boot_z_pos = _float_ctrl.FloatCtrl(
            boot_position_sb, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.boot_z_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_boot_z_pos)

        x, y, z = housing.boot_pos.as_float

        self.boot_x_pos.SetValue(x)
        self.boot_y_pos.SetValue(y)
        self.boot_z_pos.SetValue(z)

        boot_position_sz.Add(self.boot_x_pos, 0, wx.ALL, 5)
        boot_position_sz.Add(self.boot_y_pos, 0, wx.ALL, 5)
        boot_position_sz.Add(self.boot_z_pos, 0, wx.ALL, 5)

        vsizer.Add(boot_position_sz, 0)

        cpa_lock_position_sz = wx.StaticBoxSizer(wx.VERTICAL, self, "CPA Lock Position")
        cpa_lock_position_sb = cpa_lock_position_sz.GetStaticBox()

        self.cpa_x_pos = _float_ctrl.FloatCtrl(
            cpa_lock_position_sb, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cpa_x_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cpa_x_pos)

        self.cpa_y_pos = _float_ctrl.FloatCtrl(
            cpa_lock_position_sb, 'Y:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cpa_y_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cpa_y_pos)

        self.cpa_z_pos = _float_ctrl.FloatCtrl(
            cpa_lock_position_sb, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cpa_z_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cpa_z_pos)

        x, y, z = housing.cpa_pos.as_float

        self.cpa_x_pos.SetValue(x)
        self.cpa_y_pos.SetValue(y)
        self.cpa_z_pos.SetValue(z)

        cpa_lock_position_sz.Add(self.cpa_x_pos, 0, wx.ALL, 5)
        cpa_lock_position_sz.Add(self.cpa_y_pos, 0, wx.ALL, 5)
        cpa_lock_position_sz.Add(self.cpa_z_pos, 0, wx.ALL, 5)

        vsizer.Add(cpa_lock_position_sz, 0)

        cover_position_sz = wx.StaticBoxSizer(wx.VERTICAL, self, "Cover Position")
        cover_position_sb = cover_position_sz.GetStaticBox()

        self.cover_x_pos = _float_ctrl.FloatCtrl(
            cover_position_sb, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cover_x_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cover_x_pos)

        self.cover_y_pos = _float_ctrl.FloatCtrl(
            cover_position_sb, 'Y:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cover_y_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cover_y_pos)

        self.cover_z_pos = _float_ctrl.FloatCtrl(
            cover_position_sb, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cover_z_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_cover_z_pos)

        x, y, z = housing.cover_pos.as_float

        self.cover_x_pos.SetValue(x)
        self.cover_y_pos.SetValue(y)
        self.cover_z_pos.SetValue(z)

        cover_position_sz.Add(self.cover_x_pos, 0, wx.ALL, 5)
        cover_position_sz.Add(self.cover_y_pos, 0, wx.ALL, 5)
        cover_position_sz.Add(self.cover_z_pos, 0, wx.ALL, 5)

        vsizer.Add(cover_position_sz, 0)

        tpa_lock1_position_sz = wx.StaticBoxSizer(wx.VERTICAL, self, "TPA Lock 1 Position")
        tpa_lock1_position_sb = tpa_lock1_position_sz.GetStaticBox()

        self.tpa1_x_pos = _float_ctrl.FloatCtrl(
            tpa_lock1_position_sb, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa1_x_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_tpa1_x_pos)

        self.tpa1_y_pos = _float_ctrl.FloatCtrl(
            tpa_lock1_position_sb, 'Y:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa1_y_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_tpa1_y_pos)

        self.tpa1_z_pos = _float_ctrl.FloatCtrl(
            tpa_lock1_position_sb, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa1_z_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_tpa1_z_pos)

        x, y, z = housing.tpa1_pos.as_float

        self.tpa1_x_pos.SetValue(x)
        self.tpa1_y_pos.SetValue(y)
        self.tpa1_z_pos.SetValue(z)

        tpa_lock1_position_sz.Add(self.tpa1_x_pos, 0, wx.ALL, 5)
        tpa_lock1_position_sz.Add(self.tpa1_y_pos, 0, wx.ALL, 5)
        tpa_lock1_position_sz.Add(self.tpa1_z_pos, 0, wx.ALL, 5)

        vsizer.Add(tpa_lock1_position_sz, 0)

        tpa_lock2_position_sz = wx.StaticBoxSizer(wx.VERTICAL, self, "TPA Lock 2 Position")
        tpa_lock2_position_sb = tpa_lock2_position_sz.GetStaticBox()

        self.tpa2_x_pos = _float_ctrl.FloatCtrl(
            tpa_lock2_position_sb, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa2_x_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_tpa2_x_pos)

        self.tpa2_y_pos = _float_ctrl.FloatCtrl(
            tpa_lock2_position_sb, 'Y:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa2_y_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_tpa2_y_pos)

        self.tpa2_z_pos = _float_ctrl.FloatCtrl(
            tpa_lock2_position_sb, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa2_z_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_tpa2_z_pos)

        x, y, z = housing.tpa2_pos.as_float

        self.tpa2_x_pos.SetValue(x)
        self.tpa2_y_pos.SetValue(y)
        self.tpa2_z_pos.SetValue(z)

        tpa_lock2_position_sz.Add(self.tpa2_x_pos, 0, wx.ALL, 5)
        tpa_lock2_position_sz.Add(self.tpa2_y_pos, 0, wx.ALL, 5)
        tpa_lock2_position_sz.Add(self.tpa2_z_pos, 0, wx.ALL, 5)

        vsizer.Add(tpa_lock2_position_sz, 0)

        seal_position_sz = wx.StaticBoxSizer(wx.VERTICAL, self, "Seal Position")
        seal_position_sb = seal_position_sz.GetStaticBox()

        self.seal_x_pos = _float_ctrl.FloatCtrl(
            seal_position_sb, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.seal_x_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_seal_x_pos)

        self.seal_y_pos = _float_ctrl.FloatCtrl(
            seal_position_sb, 'Y:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.seal_y_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_seal_y_pos)

        self.seal_z_pos = _float_ctrl.FloatCtrl(
            seal_position_sb, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.seal_z_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_seal_z_pos)

        x, y, z = housing.seal_pos.as_float

        self.seal_x_pos.SetValue(x)
        self.seal_y_pos.SetValue(y)
        self.seal_z_pos.SetValue(z)

        seal_position_sz.Add(self.seal_x_pos, 0, wx.ALL, 5)
        seal_position_sz.Add(self.seal_y_pos, 0, wx.ALL, 5)
        seal_position_sz.Add(self.seal_z_pos, 0, wx.ALL, 5)

        vsizer.Add(seal_position_sz, 0)

        self.SetSizer(vsizer)
        self.SetupScrolling()

    def on_cavity_terminal_size(self, evt):
        self.cavity.terminal_size = float(self.cavity_terminal_size.GetValue())
        evt.Skip()

    def on_add_cavity(self, evt):
        cavity = self.dialog.add_cavity()
        self.set_cavity(cavity)
        evt.Skip()

    def on_remove_cavity(self, evt):
        self.dialog.remove_cavity(self.cavity)
        self.set_cavity(None)
        evt.Skip()

    def on_cavity_name(self, evt):
        name = self.cavity_name.GetValue()
        self.cavity.name = name
        evt.Skip()

    def on_cavity_type(self, evt):
        is_round = self.cavity_type.GetValue()
        self.cavity.is_round = is_round
        evt.Skip()

    def on_cavity_x_pos(self, evt):
        x = self.cavity_x_pos.GetValue()
        self.cavity.position.x = x
        evt.Skip()

    def on_cavity_y_pos(self, evt):
        y = self.cavity_y_pos.GetValue()
        self.cavity.position.y = y
        evt.Skip()

    def on_cavity_z_pos(self, evt):
        z = self.cavity_z_pos.GetValue()
        self.cavity.position.z = z
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
        self.cavity.angle.x = x
        evt.Skip()

    def on_cavity_y_angle(self, evt):
        y = self.cavity_y_angle.GetValue()
        self.cavity.angle.y = y
        evt.Skip()

    def on_cavity_z_angle(self, evt):
        z = self.cavity_z_angle.GetValue()
        self.cavity.angle.z = z
        evt.Skip()

    def on_boot_x_pos(self, evt):
        x = self.boot_x_pos.GetValue()
        self.housing.boot_pos.x = x
        evt.Skip()

    def on_boot_y_pos(self, evt):
        y = self.boot_y_pos.GetValue()
        self.housing.boot_pos.y = y
        evt.Skip()

    def on_boot_z_pos(self, evt):
        z = self.boot_z_pos.GetValue()
        self.housing.boot_pos.z = z
        evt.Skip()

    def on_cpa_x_pos(self, evt):
        x = self.cpa_x_pos.GetValue()
        self.housing.cpa_pos.x = x
        evt.Skip()

    def on_cpa_y_pos(self, evt):
        y = self.cpa_y_pos.GetValue()
        self.housing.cpa_pos.y = y
        evt.Skip()

    def on_cpa_z_pos(self, evt):
        z = self.cpa_z_pos.GetValue()
        self.housing.cpa_pos.z = z
        evt.Skip()

    def on_cover_x_pos(self, evt):
        x = self.cover_x_pos.GetValue()
        self.housing.cover_pos.x = x
        evt.Skip()

    def on_cover_y_pos(self, evt):
        y = self.cover_y_pos.GetValue()
        self.housing.cover_pos.y = y
        evt.Skip()

    def on_cover_z_pos(self, evt):
        z = self.cover_z_pos.GetValue()
        self.housing.cover_pos.z = z
        evt.Skip()

    def on_tpa1_x_pos(self, evt):
        x = self.tpa1_x_pos.GetValue()
        self.housing.tpa2_pos.x = x
        evt.Skip()

    def on_tpa1_y_pos(self, evt):
        y = self.tpa1_y_pos.GetValue()
        self.housing.tpa2_pos.y = y
        evt.Skip()

    def on_tpa1_z_pos(self, evt):
        z = self.tpa1_z_pos.GetValue()
        self.housing.tpa2_pos.z = z
        evt.Skip()

    def on_tpa2_x_pos(self, evt):
        x = self.tpa2_x_pos.GetValue()
        self.housing.tpa2_pos.x = x
        evt.Skip()

    def on_tpa2_y_pos(self, evt):
        y = self.tpa2_y_pos.GetValue()
        self.housing.tpa2_pos.y = y
        evt.Skip()

    def on_tpa2_z_pos(self, evt):
        z = self.tpa2_z_pos.GetValue()
        self.housing.tpa2_pos.z = z
        evt.Skip()

    def on_seal_x_pos(self, evt):
        x = self.seal_x_pos.GetValue()
        self.housing.seal_pos.x = x
        evt.Skip()

    def on_seal_y_pos(self, evt):
        y = self.seal_y_pos.GetValue()
        self.housing.seal_pos.y = y
        evt.Skip()

    def on_seal_z_pos(self, evt):
        z = self.seal_z_pos.GetValue()
        self.housing.seal_pos.z = z
        evt.Skip()

    def set_cavity(self, cavity: Cavity3D):
        self.cavity_name.Enable(cavity is not None)
        self.cavity_type.Enable(cavity is not None)
        self.cavity_terminal_size.Enable(cavity is not None)
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

        if cavity is not None:
            self.cavity_name.SetValue(cavity.name)
            self.cavity_type.SetValue(cavity.is_round)
            choices = []
            for terminal in cavity.compat_terminals:
                choices.append(f'{terminal.blade_size:.2f}')

            self.cavity_terminal_size.SetItems(sorted(choices))
            self.cavity_terminal_size.SetValue(cavity.terminal_size)
            self.cavity_x_pos.SetValue(float(cavity.position.x))
            self.cavity_y_pos.SetValue(float(cavity.position.y))
            self.cavity_z_pos.SetValue(float(cavity.position.z))
            self.cavity_x_size.SetValue(cavity.width)
            self.cavity_y_size.SetValue(cavity.height)
            self.cavity_z_size.SetValue(cavity.length)
            self.cavity_x_angle.SetValue(float(cavity.angle.x))
            self.cavity_y_angle.SetValue(float(cavity.angle.y))
            self.cavity_z_angle.SetValue(float(cavity.angle.z))

        self.cavity = cavity


class HousingEditor(wx.Panel):

    def __init__(self, parent: "_ui.MainFrame", db_obj: "_housing.Housing"):
        self.db_obj = db_obj

        self.cavities = []
        self._selected_obj = None

        wx.Panel.__init__(self, parent, wx.ID_ANY)

        splitter = wx.SplitterWindow(self, wx.ID_ANY, style=wx.BORDER_NONE | wx.SP_LIVE_UPDATE)

        self.canvas = _canvas3d.Canvas3D(splitter, Config.editor3d, size=(800, 600))
        self.housing = Housing(self, db_obj)
        self.settings = SettingsPanel(splitter, self, self.housing.obj3d)

        splitter.SetMinimumPaneSize(20)
        splitter.SplitVertically(self.canvas, self.settings, -200)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer.Add(splitter, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND)
        self.SetSizer(vsizer)

    @property
    def editor3d(self):
        return self

    def remove_cavity(self, cavity):
        self.cavities.remove(cavity)
        self.canvas.remove_object(cavity)
        cavity.db_obj.delete()

        for i, cavity in enumerate(self.cavities):
            cavity.db_obj.idx = i + 1

    def add_cavity(self) -> "_cavity.Cavity":
        housing_id = self.db_obj.db_id
        idx = len(self.cavities) + 1

        if self.db_obj.num_pins > 0 and idx <= self.db_obj.num_pins:

            print(housing_id, idx)

            cavity = self.db_obj.table.db.cavities_table.insert(housing_id, idx)
            print(cavity)

            cavity = Cavity(self, cavity)
            self.cavities.append(cavity)

            return cavity

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
