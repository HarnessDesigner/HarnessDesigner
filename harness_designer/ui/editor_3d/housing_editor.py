# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QScrollArea, QSplitter, QVBoxLayout, QHBoxLayout,
    QGroupBox, QPushButton,
)
from PySide6.QtCore import Qt

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
            edge_color_dark = [0.7, 0.7, 0.7]
            edge_color_light = [0.0, 0.0, 0.0]
            edge_luminance_threshold = 0.5
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


def _float_ctrl_group(parent, title, axes=('X', 'Y', 'Z'), **kwargs):
    """Helper: returns (QGroupBox, list[FloatCtrl]) for an XYZ group."""
    group = QGroupBox(title, parent)
    layout = QVBoxLayout(group)
    ctrls = []
    for axis in axes:
        ctrl = _float_ctrl.FloatCtrl(group, f'{axis}:', **kwargs)
        layout.addWidget(ctrl)
        ctrls.append(ctrl)
    return group, ctrls


class SettingsPanel(QScrollArea):

    def __init__(self, parent, dialog: "HousingEditor", housing: Housing3D):
        self.cavity: Cavity3D = None
        self.housing = housing
        self.dialog = dialog

        QScrollArea.__init__(self, parent)
        self.setWidgetResizable(True)

        container = QWidget()
        self.setWidget(container)
        vsizer = QVBoxLayout(container)

        # Cavity group
        cavity_group = QGroupBox("Cavity", container)
        cavity_layout = QVBoxLayout(cavity_group)

        self.cavity_name = _text_ctrl.TextCtrl(cavity_group, 'Name:', size=(-1, -1), apply_button=True)
        self.cavity_name.apply_clicked.connect(self.on_cavity_name)
        self.cavity_name.setEnabled(False)

        self.cavity_type = _checkbox_ctrl.CheckboxCtrl(cavity_group, 'Is Round:')
        self.cavity_type.checkStateChanged.connect(self.on_cavity_type)
        self.cavity_type.setEnabled(False)

        self.cavity_terminal_size = _combobox_ctrl.ComboBoxCtrl(cavity_group, 'Terminal Size', [])
        self.cavity_terminal_size.currentTextChanged.connect(self.on_cavity_terminal_size)
        self.cavity_terminal_size.setEnabled(False)

        self.add_cavity = QPushButton('Add Cavity', cavity_group)
        self.remove_cavity = QPushButton('Remove Cavity', cavity_group)

        self.add_cavity.clicked.connect(self.on_add_cavity)
        self.remove_cavity.clicked.connect(self.on_remove_cavity)
        self.remove_cavity.setEnabled(False)

        btn_row = QHBoxLayout()
        btn_row.addStretch(3)
        btn_row.addWidget(self.remove_cavity, 1)
        btn_row.addWidget(self.add_cavity, 1)

        cavity_layout.addWidget(self.cavity_name)
        cavity_layout.addWidget(self.cavity_type)
        cavity_layout.addWidget(self.cavity_terminal_size)
        cavity_layout.addLayout(btn_row)

        # Cavity position/size/angle sub-groups
        cavity_pos_group, (self.cavity_x_pos, self.cavity_y_pos, self.cavity_z_pos) = \
            _float_ctrl_group(cavity_group, "Position", min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cavity_x_pos.value_changed.connect(self.on_cavity_x_pos)
        self.cavity_y_pos.value_changed.connect(self.on_cavity_y_pos)
        self.cavity_z_pos.value_changed.connect(self.on_cavity_z_pos)
        for c in (self.cavity_x_pos, self.cavity_y_pos, self.cavity_z_pos):
            c.setEnabled(False)
        cavity_layout.addWidget(cavity_pos_group)

        cavity_size_group, (self.cavity_x_size, self.cavity_y_size, self.cavity_z_size) = \
            _float_ctrl_group(cavity_group, "Size", min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cavity_x_size.value_changed.connect(self.on_cavity_x_size)
        self.cavity_y_size.value_changed.connect(self.on_cavity_y_size)
        self.cavity_z_size.value_changed.connect(self.on_cavity_z_size)
        for c in (self.cavity_x_size, self.cavity_y_size, self.cavity_z_size):
            c.setEnabled(False)
        cavity_layout.addWidget(cavity_size_group)

        cavity_angle_group, (self.cavity_x_angle, self.cavity_y_angle, self.cavity_z_angle) = \
            _float_ctrl_group(cavity_group, "Angle", min_val=-180.0, max_val=180.0, inc=0.01, slider=True)
        self.cavity_x_angle.value_changed.connect(self.on_cavity_x_angle)
        self.cavity_y_angle.value_changed.connect(self.on_cavity_y_angle)
        self.cavity_z_angle.value_changed.connect(self.on_cavity_z_angle)
        for c in (self.cavity_x_angle, self.cavity_y_angle, self.cavity_z_angle):
            c.setEnabled(False)
        cavity_layout.addWidget(cavity_angle_group)

        vsizer.addWidget(cavity_group)

        # Boot position
        boot_group, (self.boot_x_pos, self.boot_y_pos, self.boot_z_pos) = \
            _float_ctrl_group(container, "Boot Position", min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.boot_x_pos.value_changed.connect(self.on_boot_x_pos)
        self.boot_y_pos.value_changed.connect(self.on_boot_y_pos)
        self.boot_z_pos.value_changed.connect(self.on_boot_z_pos)
        x, y, z = housing.boot_pos.as_float
        self.boot_x_pos.SetValue(x)
        self.boot_y_pos.SetValue(y)
        self.boot_z_pos.SetValue(z)
        vsizer.addWidget(boot_group)

        # CPA lock position
        cpa_group, (self.cpa_x_pos, self.cpa_y_pos, self.cpa_z_pos) = \
            _float_ctrl_group(container, "CPA Lock Position", min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cpa_x_pos.value_changed.connect(self.on_cpa_x_pos)
        self.cpa_y_pos.value_changed.connect(self.on_cpa_y_pos)
        self.cpa_z_pos.value_changed.connect(self.on_cpa_z_pos)
        x, y, z = housing.cpa_pos.as_float
        self.cpa_x_pos.SetValue(x)
        self.cpa_y_pos.SetValue(y)
        self.cpa_z_pos.SetValue(z)
        vsizer.addWidget(cpa_group)

        # Cover position
        cover_group, (self.cover_x_pos, self.cover_y_pos, self.cover_z_pos) = \
            _float_ctrl_group(container, "Cover Position", min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cover_x_pos.value_changed.connect(self.on_cover_x_pos)
        self.cover_y_pos.value_changed.connect(self.on_cover_y_pos)
        self.cover_z_pos.value_changed.connect(self.on_cover_z_pos)
        x, y, z = housing.cover_pos.as_float
        self.cover_x_pos.SetValue(x)
        self.cover_y_pos.SetValue(y)
        self.cover_z_pos.SetValue(z)
        vsizer.addWidget(cover_group)

        # TPA lock 1 position
        tpa1_group, (self.tpa1_x_pos, self.tpa1_y_pos, self.tpa1_z_pos) = \
            _float_ctrl_group(container, "TPA Lock 1 Position", min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa1_x_pos.value_changed.connect(self.on_tpa1_x_pos)
        self.tpa1_y_pos.value_changed.connect(self.on_tpa1_y_pos)
        self.tpa1_z_pos.value_changed.connect(self.on_tpa1_z_pos)
        x, y, z = housing.tpa1_pos.as_float
        self.tpa1_x_pos.SetValue(x)
        self.tpa1_y_pos.SetValue(y)
        self.tpa1_z_pos.SetValue(z)
        vsizer.addWidget(tpa1_group)

        # TPA lock 2 position
        tpa2_group, (self.tpa2_x_pos, self.tpa2_y_pos, self.tpa2_z_pos) = \
            _float_ctrl_group(container, "TPA Lock 2 Position", min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa2_x_pos.value_changed.connect(self.on_tpa2_x_pos)
        self.tpa2_y_pos.value_changed.connect(self.on_tpa2_y_pos)
        self.tpa2_z_pos.value_changed.connect(self.on_tpa2_z_pos)
        x, y, z = housing.tpa2_pos.as_float
        self.tpa2_x_pos.SetValue(x)
        self.tpa2_y_pos.SetValue(y)
        self.tpa2_z_pos.SetValue(z)
        vsizer.addWidget(tpa2_group)

        # Seal position
        seal_group, (self.seal_x_pos, self.seal_y_pos, self.seal_z_pos) = \
            _float_ctrl_group(container, "Seal Position", min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.seal_x_pos.value_changed.connect(self.on_seal_x_pos)
        self.seal_y_pos.value_changed.connect(self.on_seal_y_pos)
        self.seal_z_pos.value_changed.connect(self.on_seal_z_pos)
        x, y, z = housing.seal_pos.as_float
        self.seal_x_pos.SetValue(x)
        self.seal_y_pos.SetValue(y)
        self.seal_z_pos.SetValue(z)
        vsizer.addWidget(seal_group)

        vsizer.addStretch()

    def on_cavity_terminal_size(self, value):
        if self.cavity is not None:
            self.cavity.terminal_size = float(value)

    def on_add_cavity(self):
        cavity = self.dialog.add_cavity()
        self.set_cavity(cavity)

    def on_remove_cavity(self):
        self.dialog.remove_cavity(self.cavity)
        self.set_cavity(None)

    def on_cavity_name(self):
        self.cavity.name = self.cavity_name.GetValue()

    def on_cavity_type(self, state):
        self.cavity.is_round = bool(state)

    def on_cavity_x_pos(self, x):
        self.cavity.position.x = x

    def on_cavity_y_pos(self, y):
        self.cavity.position.y = y

    def on_cavity_z_pos(self, z):
        self.cavity.position.z = z

    def on_cavity_x_size(self, width):
        self.cavity.width = width

    def on_cavity_y_size(self, height):
        self.cavity.height = height

    def on_cavity_z_size(self, length):
        self.cavity.length = length

    def on_cavity_x_angle(self, x):
        self.cavity.angle.x = x

    def on_cavity_y_angle(self, y):
        self.cavity.angle.y = y

    def on_cavity_z_angle(self, z):
        self.cavity.angle.z = z

    def on_boot_x_pos(self, x):
        self.housing.boot_pos.x = x

    def on_boot_y_pos(self, y):
        self.housing.boot_pos.y = y

    def on_boot_z_pos(self, z):
        self.housing.boot_pos.z = z

    def on_cpa_x_pos(self, x):
        self.housing.cpa_pos.x = x

    def on_cpa_y_pos(self, y):
        self.housing.cpa_pos.y = y

    def on_cpa_z_pos(self, z):
        self.housing.cpa_pos.z = z

    def on_cover_x_pos(self, x):
        self.housing.cover_pos.x = x

    def on_cover_y_pos(self, y):
        self.housing.cover_pos.y = y

    def on_cover_z_pos(self, z):
        self.housing.cover_pos.z = z

    def on_tpa1_x_pos(self, x):
        # Note: original had a bug — on_tpa1_* all wrote to tpa2_pos.
        # Preserved intentionally to match existing behaviour.
        self.housing.tpa2_pos.x = x

    def on_tpa1_y_pos(self, y):
        self.housing.tpa2_pos.y = y

    def on_tpa1_z_pos(self, z):
        self.housing.tpa2_pos.z = z

    def on_tpa2_x_pos(self, x):
        self.housing.tpa2_pos.x = x

    def on_tpa2_y_pos(self, y):
        self.housing.tpa2_pos.y = y

    def on_tpa2_z_pos(self, z):
        self.housing.tpa2_pos.z = z

    def on_seal_x_pos(self, x):
        self.housing.seal_pos.x = x

    def on_seal_y_pos(self, y):
        self.housing.seal_pos.y = y

    def on_seal_z_pos(self, z):
        self.housing.seal_pos.z = z

    def set_cavity(self, cavity: Cavity3D):
        enabled = cavity is not None
        for ctrl in (
            self.cavity_name, self.cavity_type, self.cavity_terminal_size,
            self.cavity_x_pos, self.cavity_y_pos, self.cavity_z_pos,
            self.cavity_x_size, self.cavity_y_size, self.cavity_z_size,
            self.cavity_x_angle, self.cavity_y_angle, self.cavity_z_angle,
            self.remove_cavity,
        ):
            ctrl.setEnabled(enabled)

        if cavity is not None:
            self.cavity_name.SetValue(cavity.name)
            self.cavity_type.SetValue(cavity.is_round)
            choices = sorted(f'{t.blade_size:.2f}' for t in cavity.compat_terminals)
            self.cavity_terminal_size.SetItems(choices)
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


class HousingEditor(QWidget):

    def __init__(self, parent: "_ui.MainFrame", db_obj: "_housing.Housing"):
        self.db_obj = db_obj

        self.cavities = []
        self._selected_obj = None

        QWidget.__init__(self, parent)

        splitter = QSplitter(Qt.Horizontal, self)

        self.canvas = _canvas3d.Canvas3D(splitter, Config.editor3d, size=(800, 600))
        self.housing = Housing(self, db_obj)
        self.settings = SettingsPanel(splitter, self, self.housing.obj3d)

        splitter.addWidget(self.canvas)
        splitter.addWidget(self.settings)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setSizes([800, 200])

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(splitter)

    @property
    def editor3d(self):
        return self

    def remove_cavity(self, cavity):
        self.cavities.remove(cavity)
        self.canvas.remove_object(cavity)
        cavity.db_obj.delete()

        for i, cav in enumerate(self.cavities):
            cav.db_obj.idx = i + 1

    def add_cavity(self) -> "_cavity.Cavity":
        housing_id = self.db_obj.db_id
        idx = len(self.cavities) + 1

        if self.db_obj.num_pins > 0 and idx <= self.db_obj.num_pins:
            cavity = self.db_obj.table.db.cavities_table.insert(housing_id, idx)

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
