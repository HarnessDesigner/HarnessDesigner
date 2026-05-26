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
    """Represent a config in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    class editor3d:
        """Represent an editor 3D in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

        UNKNOWN details are inferred from the class name and surrounding code.
        """
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
            """Represent a renderer in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

            UNKNOWN details are inferred from the class name and surrounding code.
            """
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
            """Represent a focal target in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

            UNKNOWN details are inferred from the class name and surrounding code.
            """
            enable = False
            color = [1.0, 0.4, 0.4, 1.0]
            radius = 0.25

        class floor:
            """Represent a floor in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

            UNKNOWN details are inferred from the class name and surrounding code.
            """
            enable = False
            ground_height = 0.0
            distance = 1000

            class grid:
                """Represent a grid in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

                UNKNOWN details are inferred from the class name and surrounding code.
                """
                primary_color = [0.2039, 0.2549, 0.2902, 0.8]
                secondary_color = [0.2925, 0.3430, 0.3430, 0.8]
                size = 50
                enable = False

            class reflections:
                """Represent a reflections in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

                UNKNOWN details are inferred from the class name and surrounding code.
                """
                enable = False
                strength = 50.0

    class debug:
        """Represent a debug in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

        UNKNOWN details are inferred from the class name and surrounding code.
        """

        class rendering3d:
            """Represent a rendering 3D in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

            UNKNOWN details are inferred from the class name and surrounding code.
            """
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
        """Represent an axis overlay in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

        UNKNOWN details are inferred from the class name and surrounding code.
        """
        is_visible = False
        size = (75, 75)
        position = (830, 245)


class Cavity(_objects.ObjectBase):
    """Represent a cavity in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, cavity):
        """Initialise the :class:`Cavity` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param cavity: Value for ``cavity``.
        :type cavity: UNKNOWN
        """
        super().__init__(parent)
        self.obj3d = Cavity3D(self, cavity)
        self.obj2d = None

        parent.add_object(self)


class Cavity3D(_base3d.Base3D):
    """Represent a cavity 3D in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    db_obj: "_cavity.Cavity" = None

    def __init__(self, parent, db_obj: "_cavity.Cavity"):
        """Initialise the :class:`Cavity3D` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_cavity.Cavity`
        """
        angle = db_obj.angle3d
        position = db_obj.position3d
        scale = _point.Point(1.0, 1.0, 1.0)

        data = self.build()

        material_color = _color.Color(0.6, 0.2, 0.2, 0.35)
        material = _materials.Plastic(material_color)

        _base3d.Base3D.__init__(self, parent, db_obj, None, angle, position, scale, material, data=data)

    @property
    def compat_terminals(self) -> list["_terminal.Terminal"]:
        """Return the compat terminals.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_terminal.Terminal']
        """
        return self.db_obj.compat_terminals

    @property
    def width(self) -> float:
        """Return the width.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.db_obj.width

    @width.setter
    def width(self, value: float):
        """Set the width.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self.db_obj.width = value
        self.build()

    @property
    def height(self) -> float:
        """Return the height.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.db_obj.height

    @height.setter
    def height(self, value: float):
        """Set the height.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self.db_obj.height = value
        self.build()

    @property
    def length(self) -> float:
        """Return the length.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.db_obj.length

    @length.setter
    def length(self, value: float):
        """Set the length.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self.db_obj.length = value
        self.build()

    @property
    def is_round(self) -> bool:
        """Return the is round.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self.db_obj.round_terminal

    @is_round.setter
    def is_round(self, value: bool):
        """Set the is round.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self.db_obj.round_terminal = value
        self.build()

    @property
    def terminal_size(self) -> bool:
        """Return the terminal size.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self.db_obj.terminal_size

    @terminal_size.setter
    def terminal_size(self, value: bool):
        """Set the terminal size.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self.db_obj.terminal_size = value

    @property
    def name(self) -> str:
        """Return the name.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self.db_obj.name

    @name.setter
    def name(self, value: str):
        """Set the name.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self.db_obj.name = value

    def build(self):
        """Execute the build operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if self.is_round:
            radius = float(_d(self.width) / _d(2.0))
            vertices, faces = _cylinder.create(radius, self.length, resolution=90, split=1)
        else:
            vertices, faces = _box.create(self.width, self.height, self.length)

        verts, nrmls, count = _utils.compute_smoothed_vertex_normals(vertices, faces)
        return verts, nrmls, count


class HousingAccessory(_objects.ObjectBase):
    """Represent a housing accessory in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, position: _point.Point):
        """Initialise the :class:`HousingAccessory` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param position: Position value.
        :type position: :class:`_point.Point`
        """
        super().__init__(parent)
        self.obj3d = HousingAccessory3D(self, position)
        self.obj2d = None

        parent.add_object(self)


class HousingAccessory3D(_base3d.Base3D):
    """Represent a housing accessory 3D in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    db_obj: "_housing.Housing" = None

    def __init__(self, parent, position: _point.Point):
        """Initialise the :class:`HousingAccessory3D` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param position: Position value.
        :type position: :class:`_point.Point`
        """
        angle = _angle.Angle()
        scale = _point.Point(1.0, 1.0, 1.0)

        vertices, faces = _sphere.create(1.0, 20)

        data = _utils.compute_smoothed_vertex_normals(vertices, faces)
        material_color = _color.Color(1.0, 0.2, 1.0, 1.0)
        material = _materials.Metallic(material_color)

        _base3d.Base3D.__init__(self, parent, None, None, angle, position, scale, material, data=data)


class Housing(_objects.ObjectBase):
    """Represent a housing in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, housing):
        """Initialise the :class:`Housing` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param housing: Value for ``housing``.
        :type housing: UNKNOWN
        """
        super().__init__(parent)
        self.obj3d = Housing3D(self, housing)
        self.obj2d = None

        parent.add_object(self)


class Housing3D(_base3d.Base3D):
    """Represent a housing 3D in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    db_obj: "_housing.Housing" = None

    def __init__(self, parent, db_obj: "_housing.Housing"):
        """Initialise the :class:`Housing3D` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_housing.Housing`
        """
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
        """Return the TPA 1 pos.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.db_obj.tpa_lock_1_position3d

    @property
    def tpa2_pos(self):
        """Return the TPA 2 pos.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.db_obj.tpa_lock_2_position3d

    @property
    def seal_pos(self):
        """Return the seal pos.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.db_obj.seal_position3d

    @property
    def cpa_pos(self):
        """Return the CPA pos.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.db_obj.cpa_lock_position3d

    @property
    def cover_pos(self):
        """Return the cover pos.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.db_obj.cover_position3d

    @property
    def boot_pos(self):
        """Return the boot pos.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
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
    """Represent a settings panel in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, dialog: "HousingEditor", housing: Housing3D):
        """Initialise the :class:`SettingsPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param dialog: Value for ``dialog``.
        :type dialog: :class:`HousingEditor`
        :param housing: Value for ``housing``.
        :type housing: :class:`Housing3D`
        """
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
        """Handle the cavity terminal size event.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        if self.cavity is not None:
            self.cavity.terminal_size = float(value)

    def on_add_cavity(self):
        """Handle the add cavity event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        cavity = self.dialog.add_cavity()
        self.set_cavity(cavity)

    def on_remove_cavity(self):
        """Handle the remove cavity event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.dialog.remove_cavity(self.cavity)
        self.set_cavity(None)

    def on_cavity_name(self):
        """Handle the cavity name event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.cavity.name = self.cavity_name.GetValue()

    def on_cavity_type(self, state):
        """Handle the cavity type event.

        UNKNOWN details are inferred from the callable name and signature.

        :param state: Value for ``state``.
        :type state: UNKNOWN
        """
        self.cavity.is_round = bool(state)

    def on_cavity_x_pos(self, x):
        """Handle the cavity x pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param x: X-coordinate value.
        :type x: UNKNOWN
        """
        self.cavity.position.x = x

    def on_cavity_y_pos(self, y):
        """Handle the cavity y pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param y: Y-coordinate value.
        :type y: UNKNOWN
        """
        self.cavity.position.y = y

    def on_cavity_z_pos(self, z):
        """Handle the cavity z pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param z: Z-coordinate value.
        :type z: UNKNOWN
        """
        self.cavity.position.z = z

    def on_cavity_x_size(self, width):
        """Handle the cavity x size event.

        UNKNOWN details are inferred from the callable name and signature.

        :param width: Value for ``width``.
        :type width: UNKNOWN
        """
        self.cavity.width = width

    def on_cavity_y_size(self, height):
        """Handle the cavity y size event.

        UNKNOWN details are inferred from the callable name and signature.

        :param height: Value for ``height``.
        :type height: UNKNOWN
        """
        self.cavity.height = height

    def on_cavity_z_size(self, length):
        """Handle the cavity z size event.

        UNKNOWN details are inferred from the callable name and signature.

        :param length: Value for ``length``.
        :type length: UNKNOWN
        """
        self.cavity.length = length

    def on_cavity_x_angle(self, x):
        """Handle the cavity x angle event.

        UNKNOWN details are inferred from the callable name and signature.

        :param x: X-coordinate value.
        :type x: UNKNOWN
        """
        self.cavity.angle.x = x

    def on_cavity_y_angle(self, y):
        """Handle the cavity y angle event.

        UNKNOWN details are inferred from the callable name and signature.

        :param y: Y-coordinate value.
        :type y: UNKNOWN
        """
        self.cavity.angle.y = y

    def on_cavity_z_angle(self, z):
        """Handle the cavity z angle event.

        UNKNOWN details are inferred from the callable name and signature.

        :param z: Z-coordinate value.
        :type z: UNKNOWN
        """
        self.cavity.angle.z = z

    def on_boot_x_pos(self, x):
        """Handle the boot x pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param x: X-coordinate value.
        :type x: UNKNOWN
        """
        self.housing.boot_pos.x = x

    def on_boot_y_pos(self, y):
        """Handle the boot y pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param y: Y-coordinate value.
        :type y: UNKNOWN
        """
        self.housing.boot_pos.y = y

    def on_boot_z_pos(self, z):
        """Handle the boot z pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param z: Z-coordinate value.
        :type z: UNKNOWN
        """
        self.housing.boot_pos.z = z

    def on_cpa_x_pos(self, x):
        """Handle the CPA x pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param x: X-coordinate value.
        :type x: UNKNOWN
        """
        self.housing.cpa_pos.x = x

    def on_cpa_y_pos(self, y):
        """Handle the CPA y pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param y: Y-coordinate value.
        :type y: UNKNOWN
        """
        self.housing.cpa_pos.y = y

    def on_cpa_z_pos(self, z):
        """Handle the CPA z pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param z: Z-coordinate value.
        :type z: UNKNOWN
        """
        self.housing.cpa_pos.z = z

    def on_cover_x_pos(self, x):
        """Handle the cover x pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param x: X-coordinate value.
        :type x: UNKNOWN
        """
        self.housing.cover_pos.x = x

    def on_cover_y_pos(self, y):
        """Handle the cover y pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param y: Y-coordinate value.
        :type y: UNKNOWN
        """
        self.housing.cover_pos.y = y

    def on_cover_z_pos(self, z):
        """Handle the cover z pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param z: Z-coordinate value.
        :type z: UNKNOWN
        """
        self.housing.cover_pos.z = z

    def on_tpa1_x_pos(self, x):
        """Handle the TPA 1 x pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param x: X-coordinate value.
        :type x: UNKNOWN
        """
        # Note: original had a bug — on_tpa1_* all wrote to tpa2_pos.
        # Preserved intentionally to match existing behaviour.
        self.housing.tpa2_pos.x = x

    def on_tpa1_y_pos(self, y):
        """Handle the TPA 1 y pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param y: Y-coordinate value.
        :type y: UNKNOWN
        """
        self.housing.tpa2_pos.y = y

    def on_tpa1_z_pos(self, z):
        """Handle the TPA 1 z pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param z: Z-coordinate value.
        :type z: UNKNOWN
        """
        self.housing.tpa2_pos.z = z

    def on_tpa2_x_pos(self, x):
        """Handle the TPA 2 x pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param x: X-coordinate value.
        :type x: UNKNOWN
        """
        self.housing.tpa2_pos.x = x

    def on_tpa2_y_pos(self, y):
        """Handle the TPA 2 y pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param y: Y-coordinate value.
        :type y: UNKNOWN
        """
        self.housing.tpa2_pos.y = y

    def on_tpa2_z_pos(self, z):
        """Handle the TPA 2 z pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param z: Z-coordinate value.
        :type z: UNKNOWN
        """
        self.housing.tpa2_pos.z = z

    def on_seal_x_pos(self, x):
        """Handle the seal x pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param x: X-coordinate value.
        :type x: UNKNOWN
        """
        self.housing.seal_pos.x = x

    def on_seal_y_pos(self, y):
        """Handle the seal y pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param y: Y-coordinate value.
        :type y: UNKNOWN
        """
        self.housing.seal_pos.y = y

    def on_seal_z_pos(self, z):
        """Handle the seal z pos event.

        UNKNOWN details are inferred from the callable name and signature.

        :param z: Z-coordinate value.
        :type z: UNKNOWN
        """
        self.housing.seal_pos.z = z

    def set_cavity(self, cavity: Cavity3D):
        """Set the cavity.

        UNKNOWN details are inferred from the callable name and signature.

        :param cavity: Value for ``cavity``.
        :type cavity: :class:`Cavity3D`
        """
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
    """Represent a housing editor in :mod:`harness_designer.ui.editor_3d.housing_editor.backup`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent: "_ui.MainFrame", db_obj: "_housing.Housing"):
        """Initialise the :class:`HousingEditor` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_housing.Housing`
        """
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
        """Return the editor 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self

    def remove_cavity(self, cavity):
        """Remove the cavity.

        UNKNOWN details are inferred from the callable name and signature.

        :param cavity: Value for ``cavity``.
        :type cavity: UNKNOWN
        """
        self.cavities.remove(cavity)
        self.canvas.remove_object(cavity)
        cavity.db_obj.delete()

        for i, cav in enumerate(self.cavities):
            cav.db_obj.idx = i + 1

    def add_cavity(self) -> "_cavity.Cavity":
        """Add a cavity.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_cavity.Cavity`
        """
        housing_id = self.db_obj.db_id
        idx = len(self.cavities) + 1

        if self.db_obj.num_pins > 0 and idx <= self.db_obj.num_pins:
            cavity = self.db_obj.table.db.cavities_table.insert(housing_id, idx)

            cavity = Cavity(self, cavity)
            self.cavities.append(cavity)

            return cavity

    def add_object(self, obj):
        """Add an object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self.canvas.add_object(obj)

    def remove_object(self, obj):
        """Remove the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self.canvas.remove_object(obj)

    def _set_selected(self, obj):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self._selected_obj = obj
        self.canvas.set_selected(obj)

    def set_selected(self, obj):  # NOQA
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        if obj is not None:
            obj.set_selected(True)

    def get_selected(self):
        """Return the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._selected_obj
