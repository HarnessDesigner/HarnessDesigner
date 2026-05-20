# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QPushButton, QLabel
)
from PySide6.QtGui import QPixmap, QPainter, QFont, QColor

from . import dialog_base as _dialog_base
from ..widgets import float_ctrl as _float_ctrl
from . import error as _error_dialog
from ...gl import vbo as _vbo
from ..widgets import checkbox_ctrl as _checkbox_ctrl
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


class HeaderPanel(QWidget):

    def __init__(self, parent, label):
        QWidget.__init__(self, parent)
        self.setFixedSize(1200, 80)

        # Build pixmap from header image with text drawn on it
        src_pixmap = _image.images.header_1200x80.pixmap
        self._pixmap = QPixmap(src_pixmap)

        painter = QPainter(self._pixmap)

        font = QFont()
        font.setItalic(True)

        # Fit font to ~273x25 target area
        for pt in range(8, 48):
            font.setPointSize(pt)
            painter.setFont(font)
            rect = painter.fontMetrics().boundingRect(label)
            if rect.width() > 273 or rect.height() > 25:
                font.setPointSize(pt - 1)
                break

        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0, 255))
        painter.drawText(12, 6 + painter.fontMetrics().ascent(), label)
        painter.end()

        lbl = QLabel(self)
        lbl.setPixmap(self._pixmap)
        lbl.setGeometry(0, 0, 1200, 80)

    def sizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(1200, 80)


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

        material = _materials.Plastic(
            _color.Color(0.8, 0.3, 0.3, 1.0))
        self.db_obj = db_obj
        data = self.build()

        _base3d.Base3D.__init__(self, parent, db_obj, None,
                                self._angle, self._position, scale,
                                material, data=data)

        self._selected_material = _materials.Plastic(
            _color.Color(0.3, 1.0, 0.3, 1.0))

        self._is_visible = True
        self.autoplace = False
        self.editor3d.update()

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
        self.editor3d.update()

    @property
    def height(self) -> float:
        return self.db_obj.height

    @height.setter
    def height(self, value: float):
        self.db_obj.height = value
        self.build()
        self._compute_obb()
        self._compute_aabb()
        self.editor3d.update()

    @property
    def length(self) -> float:
        return self.db_obj.length

    @length.setter
    def length(self, value: float):
        self.db_obj.length = value
        self.build()
        self._compute_obb()
        self._compute_aabb()
        self.editor3d.update()

    @property
    def is_round(self) -> bool:
        return self.db_obj.round_terminal

    @is_round.setter
    def is_round(self, value: bool):
        self.db_obj.round_terminal = value
        self.build()
        self._compute_obb()
        self._compute_aabb()
        self.editor3d.update()

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

            self._vbo = _cylinder.create_vbo()
            self._scale = _point.Point(radius, radius, self.length)
        else:
            self._vbo = _box.create_vbo()
            self._scale = _point.Point(self.width, self.height, self.length)


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

        angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)
        scale = _point.Point(3.0, 3.0, 3.0)

        self._position = position.copy()
        vbo = _sphere.create_vbo()

        material_color = _color.Color(0.8, 0.2, 0.8, 0.99)
        material = _materials.Plastic(material_color)

        _base3d.Base3D.__init__(self, parent, None, vbo, angle,
                                self._position, scale, material)

        self._selected_material = _materials.Plastic(
            _color.Color(0.8, 0.8, 0.2, 0.99))

        self._is_visible = True
        self.editor3d.update()


class Housing(_objects.ObjectBase):
    obj3d: "Housing3D" = None

    def __init__(self, parent: "HousingEditorDialog",
                 housing: "_housing.Housing"):

        super().__init__(parent, housing)
        self.dialog = parent
        self.obj3d = Housing3D(self, housing)


class Housing3D(_base3d.Base3D):
    db_obj: "_housing.Housing" = None

    def __init__(self, parent: Housing, db_obj: "_housing.Housing"):
        self.dialog: "HousingEditorDialog" = parent.dialog
        self.db_obj = db_obj

        self._angle = db_obj.angle3d
        self._position = _point.Point(0.0, 0.0, 0.0)
        model = db_obj.model3d

        if model is None:
            length = db_obj.length
            width = db_obj.width
            height = db_obj.height

            parent.dialog.mainframe.status_bar.showMessage()

            if 0.0 in (length, width, height):
                length_ctrl = _float_ctrl.FloatCtrl(None, 'Length',
                                                    0.01, 500.0, 0.01)

                width_ctrl = _float_ctrl.FloatCtrl(None, 'Width',
                                                   0.01, 500.0, 0.01)

                height_ctrl = _float_ctrl.FloatCtrl(None, 'Height',
                                                    0.01, 500.0, 0.01)

                length_ctrl.SetValue(length)
                width_ctrl.SetValue(width)
                height_ctrl.SetValue(height)

                dlg = _error_dialog.ErrorDialog(
                    parent.dialog.mainframe,
                    'Dimensions are not valid.\n\nPlease set correct dimensions.',
                    'Dimension Error', length_ctrl, width_ctrl, height_ctrl)

                while 0.0 in (length, width, height):
                    dlg.exec()
                    length = length_ctrl.GetValue()
                    width = width_ctrl.GetValue()
                    height = height_ctrl.GetValue()

                db_obj.length = length
                db_obj.width = width
                db_obj.height = height

            scale = _point.Point(width, height, length)
            vertices, faces = _box.create_vbo()
            vbo = _utils.compute_vbo_vertex_normals(vertices, faces)
            position3d = _point.Point(0.0, 0.0, 0.0)
            angle3d = _angle.Angle.from_euler(0.0, 0.0, 0.0)
        else:
            uuid = model.uuid
            scale = model.scale
            angle3d = model.angle3d
            position3d = model.position3d

            if uuid in _vbo.VBOHandler:
                vbo = _vbo.VBOHandler(uuid)
            else:
                vertices, faces = model.load()
                verts, nrmls, faces, count = (
                    _utils.compute_vbo_smoothed_vertex_normals(vertices, faces))

                vbo = _vbo.VBOHandler(uuid, verts, nrmls, faces, count)

        material_color = _color.Color(0.6, 0.6, 0.8, 1.0)
        material = _materials.Plastic(material_color)

        _base3d.Base3D.__init__(
            self, parent, db_obj, vbo, angle3d, position3d, scale, material)

        self._selected_material = _materials.Plastic(
            _color.Color(0.3, 0.8, 0.3, 1.0))

        self._is_visible = True


def _make_pos_group(parent_widget, label):
    group = QGroupBox(label, parent_widget)
    layout = QVBoxLayout(group)
    return group, layout


class CavityPanel(QScrollArea):

    def __init__(self, dialog, panel: "HousingEditorDialog", housing: Housing3D):
        QScrollArea.__init__(self, panel)
        self.setWidgetResizable(True)

        self.__hold_change = False
        self.cavities: list[Cavity3D] = []

        for cavity in housing.db_obj.cavities:
            if cavity is None:
                continue

            cavity = Cavity(dialog, cavity)
            self.cavities.append(cavity.obj3d)

        self.cavity: Cavity3D = None
        self.housing = housing
        self.dialog = dialog

        inner = QWidget()
        self.setWidget(inner)

        # Cavity group
        cavity_group = QGroupBox('Cavity', inner)
        cavity_layout = QHBoxLayout(cavity_group)

        left_layout = QVBoxLayout()

        self.cavity_names = sorted([c.name for c in self.cavities])

        self.cavity_name = _combobox_ctrl.ComboBoxCtrl(
            cavity_group, 'Name:', self.cavity_names)

        self.cavity_name.setToolTip(
            'Select OR enter a new name and then press enter to add.')

        self.cavity_name.currentTextChanged.connect(self._on_cavity_name_changed)
        left_layout.addWidget(self.cavity_name)

        self.change_name = _checkbox_ctrl.CheckboxCtrl(
            cavity_group, 'Change Name:')

        self.change_name.setToolTip(
            'Changes the selected cavities name to the name entered above.')

        self.change_name.Enable(False)
        left_layout.addWidget(self.change_name)

        self.cavity_type = _checkbox_ctrl.CheckboxCtrl(
            cavity_group, 'Is Round:')

        self.cavity_type.Enable(False)
        self.cavity_type.checkStateChanged.connect(lambda _: self.on_cavity_type())
        left_layout.addWidget(self.cavity_type)

        self.cavity_autoplace = _checkbox_ctrl.CheckboxCtrl(
            cavity_group, 'Use in Autoplace:')

        self.cavity_autoplace.Enable(False)
        self.cavity_autoplace.checkStateChanged.connect(
            lambda _: self.on_cavity_autoplace())

        left_layout.addWidget(self.cavity_autoplace)

        self.cavity_terminal_sizes = _combobox_ctrl.ComboBoxCtrl(
            cavity_group, 'Terminal Sizes', [])

        self.cavity_terminal_sizes.Enable(False)

        self.cavity_terminal_sizes.currentTextChanged.connect(
            self.on_cavity_terminal_sizes)

        left_layout.addWidget(self.cavity_terminal_sizes)

        btn_row = QHBoxLayout()
        self.auto_place = QPushButton('Auto Place Cavities', cavity_group)
        self.auto_place.setEnabled(False)
        self.auto_place.clicked.connect(self.on_auto_place)

        self.remove_cavity = QPushButton('Remove Cavity', cavity_group)
        self.remove_cavity.setEnabled(False)
        self.remove_cavity.clicked.connect(self.on_remove_cavity)

        btn_row.addStretch(3)
        btn_row.addWidget(self.auto_place)
        btn_row.addWidget(self.remove_cavity)
        left_layout.addLayout(btn_row)

        cavity_layout.addLayout(left_layout)

        # Position sub-group
        pos_group = QGroupBox('Position', cavity_group)
        pos_layout = QVBoxLayout(pos_group)

        self.cavity_x_pos = _float_ctrl.FloatCtrl(
            pos_group, 'X:', min_val=-999.0,
            max_val=999.0, inc=0.01, slider=True)

        self.cavity_x_pos.Enable(False)
        self.cavity_x_pos.value_changed.connect(self.on_cavity_x_pos)
        pos_layout.addWidget(self.cavity_x_pos)

        self.cavity_y_pos = _float_ctrl.FloatCtrl(
            pos_group, 'Y:', min_val=0.0,
            max_val=999.0, inc=0.01, slider=True)

        self.cavity_y_pos.Enable(False)
        self.cavity_y_pos.value_changed.connect(self.on_cavity_y_pos)
        pos_layout.addWidget(self.cavity_y_pos)

        self.cavity_z_pos = _float_ctrl.FloatCtrl(
            pos_group, 'Z:', min_val=-999.0,
            max_val=999.0, inc=0.01, slider=True)

        self.cavity_z_pos.Enable(False)
        self.cavity_z_pos.value_changed.connect(self.on_cavity_z_pos)
        pos_layout.addWidget(self.cavity_z_pos)
        cavity_layout.addWidget(pos_group)

        # Size sub-group
        size_group = QGroupBox('Size', cavity_group)
        size_layout = QVBoxLayout(size_group)

        self.cavity_x_size = _float_ctrl.FloatCtrl(
            size_group, 'X:', min_val=0.0,
            max_val=999.0, inc=0.01, slider=True)

        self.cavity_x_size.Enable(False)
        self.cavity_x_size.value_changed.connect(self.on_cavity_x_size)
        size_layout.addWidget(self.cavity_x_size)

        self.cavity_y_size = _float_ctrl.FloatCtrl(
            size_group, 'Y:', min_val=0.1,
            max_val=999.0, inc=0.01, slider=True)

        self.cavity_y_size.Enable(False)
        self.cavity_y_size.value_changed.connect(self.on_cavity_y_size)
        size_layout.addWidget(self.cavity_y_size)

        self.cavity_z_size = _float_ctrl.FloatCtrl(
            size_group, 'Z:', min_val=0.1,
            max_val=999.0, inc=0.01, slider=True)

        self.cavity_z_size.Enable(False)
        self.cavity_z_size.value_changed.connect(self.on_cavity_z_size)
        size_layout.addWidget(self.cavity_z_size)
        cavity_layout.addWidget(size_group)

        # Angle sub-group
        angle_group = QGroupBox('Angle', cavity_group)
        angle_layout = QVBoxLayout(angle_group)

        self.cavity_x_angle = _float_ctrl.FloatCtrl(
            angle_group, 'X:', min_val=-180.0,
            max_val=180.0, inc=0.01, slider=True)

        self.cavity_x_angle.Enable(False)
        self.cavity_x_angle.value_changed.connect(self.on_cavity_x_angle)
        angle_layout.addWidget(self.cavity_x_angle)

        self.cavity_y_angle = _float_ctrl.FloatCtrl(
            angle_group, 'Y:', min_val=-180.0,
            max_val=180.0, inc=0.01, slider=True)

        self.cavity_y_angle.Enable(False)
        self.cavity_y_angle.value_changed.connect(self.on_cavity_y_angle)
        angle_layout.addWidget(self.cavity_y_angle)

        self.cavity_z_angle = _float_ctrl.FloatCtrl(
            angle_group, 'Z:', min_val=-180.0,
            max_val=180.0, inc=0.01, slider=True)

        self.cavity_z_angle.Enable(False)
        self.cavity_z_angle.value_changed.connect(self.on_cavity_z_angle)
        angle_layout.addWidget(self.cavity_z_angle)
        cavity_layout.addWidget(angle_group)

        outer_layout = QVBoxLayout(inner)
        outer_layout.addWidget(cavity_group)
        outer_layout.addStretch()

        self.cavity_pos: _point.Point = None
        self.cavity_angle_ref: _angle.Angle = None

        if not self.cavities:
            self.dialog.housing_panel.enable_housing_rotation(True)

    def _on_cavity_name_changed(self, name):
        self.on_cavity_name(name)

    def on_cavity_autoplace(self):
        value = self.cavity_autoplace.GetValue()
        self.cavity.autoplace = value

        count = sum(1 for c in self.cavities if c.autoplace)
        self.auto_place.setEnabled(count == 3)

    def on_auto_place(self):
        positions = [c.position for c in self.cavities if c.autoplace]
        pos1, pos2, pos3 = positions

    def on_cavity_terminal_sizes(self, value):
        values = self.cavity_terminal_sizes.GetItems()

        if not value:
            return

        if '.' not in value:
            value += '.0'

        if value in values:
            return

        values.append(value)
        values.pop(0)

        for i, item in enumerate(values):
            if '.' not in item:
                item += '.0'
            values[i] = float(item)

        self.cavity.terminal_sizes = values

        values = [str(item) for item in values]
        values.insert(0, '')

        self.cavity_terminal_sizes.SetItems(values)
        self.cavity_terminal_sizes.SetValue('')

    def on_remove_cavity(self):
        self.cavities.remove(self.cavity)
        self.cavity_names.remove(self.cavity.name)
        self.cavity_names = sorted(self.cavity_names)
        self.cavity_name.SetItems(self.cavity_names)

        self.cavity.delete()

        for i, cavity in enumerate(self.cavities):
            cavity.db_obj.idx = i + 1

        self.set_cavity(None)

    def on_cavity_name(self, name):
        name = name.strip()
        if not name:
            for cavity in self.cavities:
                if cavity.is_selected:
                    cavity.set_selected(False)
                    break
            return

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
            cavities_table = self.housing.db_obj.table.db.cavities_table

            if (num_pins > 0 and idx <= num_pins) or num_pins == 0:
                cavity = cavities_table.insert(housing_id, idx)

                if not self.cavities:
                    self.dialog.housing_panel.enable_housing_rotation(False)

                cavity = Cavity(self.dialog, cavity).obj3d
                cavity.name = name
                self.cavity_names.append(name)
                self.cavity_names = sorted(self.cavity_names)
                self.cavity_name.SetItems(self.cavity_names)
                self.cavities.append(cavity)

                for c in self.cavities:
                    if c.is_selected:
                        c.set_selected(False)
                        break

                housing_length = self.housing.db_obj.length
                housing_width = self.housing.db_obj.width
                y_offset = -(housing_length / 2.0)
                c_x_offset = 0

                for n in self.cavity_names:
                    for c in self.cavities:
                        if c.name != n:
                            continue
                        c_x = (c.width / 2.0) + c_x_offset
                        c_y = (c.length / 2.0) + y_offset
                        c_x_offset += c.width
                        p2d = c.db_obj.position2d
                        p2d.x = c_x
                        p2d.y = c_y

                cavity.set_selected(True)

    def on_cavity_type(self):
        self.cavity.is_round = self.cavity_type.GetValue()

    def on_cavity_x_pos(self, x):
        self.cavity_pos.unbind(self.on_cavity_pos)
        self.cavity.position.x = x
        self.cavity_pos.bind(self.on_cavity_pos)

    def on_cavity_y_pos(self, y):
        self.cavity_pos.unbind(self.on_cavity_pos)
        self.cavity.position.y = y
        self.cavity_pos.bind(self.on_cavity_pos)

    def on_cavity_z_pos(self, z):
        self.cavity_pos.unbind(self.on_cavity_pos)
        self.cavity.position.z = z
        self.cavity_pos.bind(self.on_cavity_pos)

    def on_cavity_x_size(self, width):
        self.cavity.width = width

    def on_cavity_y_size(self, height):
        self.cavity.height = height

    def on_cavity_z_size(self, length):
        self.cavity.length = length

    def on_cavity_x_angle(self, x):
        self.cavity_angle_ref.unbind(self.on_cavity_angle)
        self.cavity.angle.x = x
        self.cavity_angle_ref.bind(self.on_cavity_angle)

    def on_cavity_y_angle(self, y):
        self.cavity_angle_ref.unbind(self.on_cavity_angle)
        self.cavity.angle.y = y
        self.cavity_angle_ref.bind(self.on_cavity_angle)

    def on_cavity_z_angle(self, z):
        self.cavity_angle_ref.unbind(self.on_cavity_angle)
        self.cavity.angle.z = z
        self.cavity_angle_ref.bind(self.on_cavity_angle)

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

        enabled = cavity is not None
        for ctrl in (self.change_name, self.cavity_type, self.cavity_terminal_sizes,
                     self.cavity_x_pos, self.cavity_y_pos, self.cavity_z_pos,
                     self.cavity_x_size, self.cavity_y_size, self.cavity_z_size,
                     self.cavity_x_angle, self.cavity_y_angle, self.cavity_z_angle,
                     self.remove_cavity):
            ctrl.setEnabled(enabled)

        self.change_name.SetValue(False)

        if self.cavity is not None:
            self.cavity_pos.unbind(self.on_cavity_pos)
            self.cavity_angle_ref.unbind(self.on_cavity_angle)

        self.cavity = cavity

        if cavity is None:
            self.cavity_name.SetValue('')
        else:
            self.cavity_pos = cavity.position
            self.cavity_angle_ref = cavity.angle

            self.cavity_pos.bind(self.on_cavity_pos)
            self.cavity_angle_ref.bind(self.on_cavity_angle)

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


class HousingPanel(QScrollArea):

    def __init__(self, dialog, panel: "HousingEditorDialog", housing: Housing3D):
        QScrollArea.__init__(self, panel)
        self.setWidgetResizable(True)

        self.housing = housing
        self.dialog = dialog

        inner = QWidget()
        self.setWidget(inner)
        v_layout = QVBoxLayout(inner)

        group = QGroupBox('Boot Position', inner)
        gl = QVBoxLayout(group)

        self.setMaximumWidth(400)

        self.boot_x_pos = _float_ctrl.FloatCtrl(group, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.boot_y_pos = _float_ctrl.FloatCtrl(group, 'Y:', min_val=0.0, max_val=999.0, inc=0.01, slider=True)
        self.boot_z_pos = _float_ctrl.FloatCtrl(group, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)

        gl.addWidget(self.boot_x_pos)
        gl.addWidget(self.boot_y_pos)
        gl.addWidget(self.boot_z_pos)

        pos = housing.db_obj.boot_position3d
        
        self.boot_pos = pos
        pos.bind(self.on_boot_pos)

        px, py, pz = pos.as_float
        self.boot_x_pos.SetValue(px)
        self.boot_y_pos.SetValue(py)
        self.boot_z_pos.SetValue(pz)
        
        self.boot = HousingAccessory(dialog, pos)

        self.boot_x_pos.value_changed.connect(self.on_boot_x_pos)
        self.boot_y_pos.value_changed.connect(self.on_boot_y_pos)
        self.boot_z_pos.value_changed.connect(self.on_boot_z_pos)

        v_layout.addWidget(group)

        group = QGroupBox('CPA Lock Position', inner)
        gl = QVBoxLayout(group)

        self.cpa_x_pos = _float_ctrl.FloatCtrl(group, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cpa_y_pos = _float_ctrl.FloatCtrl(group, 'Y:', min_val=0.0, max_val=999.0, inc=0.01, slider=True)
        self.cpa_z_pos = _float_ctrl.FloatCtrl(group, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)

        gl.addWidget(self.cpa_x_pos)
        gl.addWidget(self.cpa_y_pos)
        gl.addWidget(self.cpa_z_pos)

        pos = housing.db_obj.cpa_lock_position3d
        
        self.cpa_pos = pos
        pos.bind(self.on_cpa_pos)

        px, py, pz = pos.as_float
        self.cpa_x_pos.SetValue(px)
        self.cpa_y_pos.SetValue(py)
        self.cpa_z_pos.SetValue(pz)
        
        self.cpa_lock = HousingAccessory(dialog, pos)
        
        self.cpa_x_pos.value_changed.connect(self.on_cpa_x_pos)
        self.cpa_y_pos.value_changed.connect(self.on_cpa_y_pos)
        self.cpa_z_pos.value_changed.connect(self.on_cpa_z_pos)

        v_layout.addWidget(group)

        group = QGroupBox('Cover Position', inner)
        gl = QVBoxLayout(group)

        self.cover_x_pos = _float_ctrl.FloatCtrl(group, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.cover_y_pos = _float_ctrl.FloatCtrl(group, 'Y:', min_val=0.0, max_val=999.0, inc=0.01, slider=True)
        self.cover_z_pos = _float_ctrl.FloatCtrl(group, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)

        gl.addWidget(self.cover_x_pos)
        gl.addWidget(self.cover_y_pos)
        gl.addWidget(self.cover_z_pos)

        pos = housing.db_obj.cover_position3d
        
        self.cover_pos = pos
        pos.bind(self.on_cover_pos)

        px, py, pz = pos.as_float
        self.cover_x_pos.SetValue(px)
        self.cover_y_pos.SetValue(py)
        self.cover_z_pos.SetValue(pz)
        
        self.cover = HousingAccessory(dialog, pos)
        
        self.cover_x_pos.value_changed.connect(self.on_cover_x_pos)
        self.cover_y_pos.value_changed.connect(self.on_cover_y_pos)
        self.cover_z_pos.value_changed.connect(self.on_cover_z_pos)

        v_layout.addWidget(group)

        group = QGroupBox('TPA Lock 1 Position', inner)
        gl = QVBoxLayout(group)

        self.tpa1_x_pos = _float_ctrl.FloatCtrl(group, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa1_y_pos = _float_ctrl.FloatCtrl(group, 'Y:', min_val=0.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa1_z_pos = _float_ctrl.FloatCtrl(group, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)

        gl.addWidget(self.tpa1_x_pos)
        gl.addWidget(self.tpa1_y_pos)
        gl.addWidget(self.tpa1_z_pos)

        pos = housing.db_obj.tpa_lock_1_position3d
        
        self.tpa1_pos = pos
        pos.bind(self.on_tpa1_pos)

        px, py, pz = pos.as_float
        self.tpa1_x_pos.SetValue(px)
        self.tpa1_y_pos.SetValue(py)
        self.tpa1_z_pos.SetValue(pz)
        
        self.tpa_lock1 = HousingAccessory(dialog, pos)

        self.tpa1_x_pos.value_changed.connect(self.on_tpa1_x_pos)
        self.tpa1_y_pos.value_changed.connect(self.on_tpa1_y_pos)
        self.tpa1_z_pos.value_changed.connect(self.on_tpa1_z_pos)

        v_layout.addWidget(group)

        group = QGroupBox('TPA Lock 2 Position', inner)
        gl = QVBoxLayout(group)

        self.tpa2_x_pos = _float_ctrl.FloatCtrl(group, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa2_y_pos = _float_ctrl.FloatCtrl(group, 'Y:', min_val=0.0, max_val=999.0, inc=0.01, slider=True)
        self.tpa2_z_pos = _float_ctrl.FloatCtrl(group, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)

        gl.addWidget(self.tpa2_x_pos)
        gl.addWidget(self.tpa2_y_pos)
        gl.addWidget(self.tpa2_z_pos)

        pos = housing.db_obj.tpa_lock_2_position3d
        
        self.tpa2_pos = pos
        pos.bind(self.on_tpa2_pos)

        px, py, pz = pos.as_float
        self.tpa2_x_pos.SetValue(px)
        self.tpa2_y_pos.SetValue(py)
        self.tpa2_z_pos.SetValue(pz)
        
        self.tpa_lock2 = HousingAccessory(dialog, pos)

        self.tpa2_x_pos.value_changed.connect(self.on_tpa2_x_pos)
        self.tpa2_y_pos.value_changed.connect(self.on_tpa2_y_pos)
        self.tpa2_z_pos.value_changed.connect(self.on_tpa2_z_pos)

        v_layout.addWidget(group)

        group = QGroupBox('Seal Position', inner)
        gl = QVBoxLayout(group)

        self.seal_x_pos = _float_ctrl.FloatCtrl(group, 'X:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)
        self.seal_y_pos = _float_ctrl.FloatCtrl(group, 'Y:', min_val=0.0, max_val=999.0, inc=0.01, slider=True)
        self.seal_z_pos = _float_ctrl.FloatCtrl(group, 'Z:', min_val=-999.0, max_val=999.0, inc=0.01, slider=True)

        gl.addWidget(self.seal_x_pos)
        gl.addWidget(self.seal_y_pos)
        gl.addWidget(self.seal_z_pos)

        pos = housing.db_obj.seal_position3d
        
        self.seal_pos = pos
        pos.bind(self.on_seal_pos)

        px, py, pz = pos.as_float
        self.seal_x_pos.SetValue(px)
        self.seal_y_pos.SetValue(py)
        self.seal_z_pos.SetValue(pz)
        
        self.seal = HousingAccessory(dialog, pos)

        self.seal_x_pos.value_changed.connect(self.on_seal_x_pos)
        self.seal_y_pos.value_changed.connect(self.on_seal_y_pos)
        self.seal_z_pos.value_changed.connect(self.on_seal_z_pos)

        v_layout.addWidget(group)

        # Housing Angle group
        angle_group = QGroupBox('Housing Angle', inner)
        agl = QVBoxLayout(angle_group)
        tip = 'You need to remove all added cavities in order to rotate the housing'

        self.housing_x_angle = _float_ctrl.FloatCtrl(
            angle_group, 'X:', min_val=-180.0, max_val=180.0, inc=0.01, slider=True)
        self.housing_x_angle.setEnabled(False)
        self.housing_x_angle.setToolTip(tip)
        self.housing_x_angle.value_changed.connect(lambda v: setattr(self.housing_angle, 'x', v))
        agl.addWidget(self.housing_x_angle)

        self.housing_y_angle = _float_ctrl.FloatCtrl(
            angle_group, 'Y:', min_val=-180.0, max_val=180.0, inc=0.01, slider=True)
        self.housing_y_angle.setEnabled(False)
        self.housing_y_angle.setToolTip(tip)
        self.housing_y_angle.value_changed.connect(lambda v: setattr(self.housing_angle, 'y', v))
        agl.addWidget(self.housing_y_angle)

        self.housing_z_angle = _float_ctrl.FloatCtrl(
            angle_group, 'Z:', min_val=-180.0, max_val=180.0, inc=0.01, slider=True)
        self.housing_z_angle.setEnabled(False)
        self.housing_z_angle.setToolTip(tip)
        self.housing_z_angle.value_changed.connect(lambda v: setattr(self.housing_angle, 'z', v))
        agl.addWidget(self.housing_z_angle)

        self.housing_angle = housing.angle
        self.housing_angle.bind(self.update_housing_angle)
        self.o_housing_angle = self.housing_angle.copy()

        x, y, z = self.housing_angle.as_euler_float
        self.housing_x_angle.SetValue(x)
        self.housing_y_angle.SetValue(y)
        self.housing_z_angle.SetValue(z)

        v_layout.addWidget(angle_group)
        v_layout.addStretch()

    def update_housing_angle(self, angle: _angle.Angle):
        inverse = self.o_housing_angle.inverse

        for attr in ('seal_pos', 'cover_pos', 'cpa_pos', 'tpa1_pos', 'tpa2_pos', 'boot_pos'):
            pos = getattr(self, attr)
            p = pos.copy()
            p @= inverse
            p @= angle
            delta = p - pos
            pos += delta

        self.o_housing_angle = angle.copy()

    def enable_housing_rotation(self, flag: bool):
        tip = '' if flag else 'You need to remove all added cavities in order to rotate the housing'
        for ctrl in (self.housing_x_angle, self.housing_y_angle, self.housing_z_angle):
            ctrl.setEnabled(flag)
            ctrl.setToolTip(tip)

    def _sync_pos(self, x_ctrl, y_ctrl, z_ctrl, position: _point.Point):
        x, y, z = position.as_float
        x_ctrl.SetValue(x)
        y_ctrl.SetValue(y)
        z_ctrl.SetValue(z)

    def on_boot_x_pos(self, value):
        self.boot_pos.unbind(self.on_boot_pos)
        self.boot_pos.x = value                
        self.boot_pos.bind(self.on_boot_pos)

    def on_boot_y_pos(self, value):
        self.boot_pos.unbind(self.on_boot_pos)
        self.boot_pos.y = value
        self.boot_pos.bind(self.on_boot_pos)

    def on_boot_z_pos(self, value):
        self.boot_pos.unbind(self.on_boot_pos)
        self.boot_pos.z = value
        self.boot_pos.bind(self.on_boot_pos)
    
    def on_cpa_x_pos(self, value):
        self.cpa_pos.unbind(self.on_cpa_pos)
        self.cpa_pos.x = value                
        self.cpa_pos.bind(self.on_cpa_pos)

    def on_cpa_y_pos(self, value):
        self.cpa_pos.unbind(self.on_cpa_pos)
        self.cpa_pos.y = value
        self.cpa_pos.bind(self.on_cpa_pos)

    def on_cpa_z_pos(self, value):
        self.cpa_pos.unbind(self.on_cpa_pos)
        self.cpa_pos.z = value
        self.cpa_pos.bind(self.on_cpa_pos)

    def on_cover_x_pos(self, value):
        self.cover_pos.unbind(self.on_cover_pos)
        self.cover_pos.x = value                
        self.cover_pos.bind(self.on_cover_pos)

    def on_cover_y_pos(self, value):
        self.cover_pos.unbind(self.on_cover_pos)
        self.cover_pos.y = value
        self.cover_pos.bind(self.on_cover_pos)

    def on_cover_z_pos(self, value):
        self.cover_pos.unbind(self.on_cover_pos)
        self.cover_pos.z = value
        self.cover_pos.bind(self.on_cover_pos)

    def on_tpa1_x_pos(self, value):
        self.tpa1_pos.unbind(self.on_tpa1_pos)
        self.tpa1_pos.x = value                
        self.tpa1_pos.bind(self.on_tpa1_pos)

    def on_tpa1_y_pos(self, value):
        self.tpa1_pos.unbind(self.on_tpa1_pos)
        self.tpa1_pos.y = value
        self.tpa1_pos.bind(self.on_tpa1_pos)

    def on_tpa1_z_pos(self, value):
        self.tpa1_pos.unbind(self.on_tpa1_pos)
        self.tpa1_pos.z = value
        self.tpa1_pos.bind(self.on_tpa1_pos)
        
    def on_tpa2_x_pos(self, value):
        self.tpa2_pos.unbind(self.on_tpa2_pos)
        self.tpa2_pos.x = value                
        self.tpa2_pos.bind(self.on_tpa2_pos)

    def on_tpa2_y_pos(self, value):
        self.tpa2_pos.unbind(self.on_tpa2_pos)
        self.tpa2_pos.y = value
        self.tpa2_pos.bind(self.on_tpa2_pos)

    def on_tpa2_z_pos(self, value):
        self.tpa2_pos.unbind(self.on_tpa2_pos)
        self.tpa2_pos.z = value
        self.tpa2_pos.bind(self.on_tpa2_pos)
        
    def on_seal_x_pos(self, value):
        self.seal_pos.unbind(self.on_seal_pos)
        self.seal_pos.x = value                
        self.seal_pos.bind(self.on_seal_pos)

    def on_seal_y_pos(self, value):
        self.seal_pos.unbind(self.on_seal_pos)
        self.seal_pos.y = value
        self.seal_pos.bind(self.on_seal_pos)

    def on_seal_z_pos(self, value):
        self.seal_pos.unbind(self.on_seal_pos)
        self.seal_pos.z = value
        self.seal_pos.bind(self.on_seal_pos)

    def on_boot_pos(self, p):
        self._sync_pos(self.boot_x_pos, self.boot_y_pos, self.boot_z_pos, p)

    def on_cpa_pos(self, p):
        self._sync_pos(self.cpa_x_pos, self.cpa_y_pos, self.cpa_z_pos, p)

    def on_cover_pos(self, p):
        self._sync_pos(self.cover_x_pos, self.cover_y_pos, self.cover_z_pos, p)

    def on_tpa1_pos(self, p):
        self._sync_pos(self.tpa1_x_pos, self.tpa1_y_pos, self.tpa1_z_pos, p)

    def on_tpa2_pos(self, p):
        self._sync_pos(self.tpa2_x_pos, self.tpa2_y_pos, self.tpa2_z_pos, p)

    def on_seal_pos(self, p):
        self._sync_pos(self.seal_x_pos, self.seal_y_pos, self.seal_z_pos, p)


class HousingEditorDialog(_dialog_base.BaseDialog):

    def __init__(self, parent: "_ui.mainframe", db_obj):
        self.db_obj = db_obj

        _dialog_base.BaseDialog.__init__(self, parent, 'Edit Housing', size=(1200, 900))

        w = _config.Config.editor3d.virtual_canvas.width
        h = _config.Config.editor3d.virtual_canvas.height

        self.canvas = _canvas3d.Canvas3D(
            self.panel, Config.editor3d, size=(w, h))

        self.housing = Housing(self, db_obj)

        self.housing_panel = HousingPanel(self, self.panel, self.housing.obj3d)
        self.cavity_panel = CavityPanel(self, self.panel, self.housing.obj3d)

        h_layout = QHBoxLayout()
        h_layout.addWidget(self.canvas)
        h_layout.addSpacing(5)
        h_layout.addWidget(self.housing_panel)
        h_layout.addSpacing(5)

        v_layout = QVBoxLayout(self.panel)
        v_layout.addLayout(h_layout, 1)
        v_layout.addWidget(self.cavity_panel)

    def closeEvent(self, event):  # noqa: N802
        """Clean up the dialog's GL canvas before the window is destroyed."""
        self.canvas.cleanup()
        super().closeEvent(event)

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
