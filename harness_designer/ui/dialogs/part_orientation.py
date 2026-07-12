# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import numpy as np
import build123d
from typing import TYPE_CHECKING

from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize
from PySide6 import QtWidgets

from . import dialog_base as _dialog_base
from ... import config as _config
from ...gl import canvas3d as _canvas3d
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ...objects import ObjectBase as _ObjectBase
from ...objects.objects3d import base3d as _base3d
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry.angle import quaternion as _quaternion
from ... import color as _color
from ... import utils as _utils
from ... import image as _image

if TYPE_CHECKING:
    from ...database.global_db.model3d import Model3D as _Model3D
    from ... import ui as _ui


def _obb_face_for_direction(
        local_obb: np.ndarray,
        q: "_quaternion.Quaternion",
        target_dir: np.ndarray) -> int:
    """Return the face index (0–5) whose outward normal, after rotating the
    local OBB by *q*, best aligns with *target_dir*.

    Face indices are defined in local-OBB space by sorting the 8 corners
    along each axis: axis 0 → faces 0 (min-X) and 1 (max-X),
    axis 1 → 2/3 (Y), axis 2 → 4/5 (Z).
    """
    rotated = np.array([q @ c for c in local_obb], dtype=np.float32)
    center = rotated.mean(axis=0)
    best_idx, best_dot = 0, -2.0
    for axis in range(3):
        sorted_i = np.argsort(local_obb[:, axis])
        for sign, corner_i in enumerate([sorted_i[:4], sorted_i[4:]]):
            fc = rotated[corner_i].mean(axis=0) - center
            n = float(np.linalg.norm(fc))
            if n > 1e-8:
                dot = float(np.dot(fc / n, target_dir))
                if dot > best_dot:
                    best_dot, best_idx = dot, axis * 2 + sign
    return best_idx


class _Config:
    """Minimal config for the part orientation canvas."""
    lighting = _config.Config.editor3d.lighting
    keyboard_settings = _config.Config.editor3d.keyboard_settings
    rotate = _config.Config.editor3d.rotate
    pan_tilt = _config.Config.editor3d.pan_tilt
    truck_pedestal = _config.Config.editor3d.truck_pedestal
    walk = _config.Config.editor3d.walk
    zoom = _config.Config.editor3d.zoom
    reset = _config.Config.editor3d.reset
    edit2d = _config.Config.editor3d.edit2d
    selected_color = [0.2, 0.6, 0.2, 0.35]
    background_color = [0.13, 0.13, 0.15, 1.0]

    class headlight:
        enable = False
        cutoff = 8.0
        dissipate = 50.0
        color = [0.6, 0.6, 0.4, 0.8]

    class virtual_canvas:
        width = 1920
        height = 1080

    class floor:
        enable = False
        ground_height = 0.0
        size = 2000
        enable_floor_lock = False

        class grid:
            primary_color = [0.3039, 0.3549, 0.3902, 0.7]
            secondary_color = [0.2925, 0.3430, 0.3430, 0.8]
            primary_line_color = [0.87, 0.88, 0.92, 1.0]
            secondary_line_color = [0.57, 0.59, 0.65, 1.0]
            primary_line_width = 0.8
            secondary_line_width = 0.25
            secondary_lines_per_tile = 4
            secondary_line_pattern = 0x0B2664D0
            secondary_line_shift = False
            size = 80
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


class PartModel(_ObjectBase):
    """Non-selectable wrapper for the part model in the orientation dialog."""
    obj3d: "PartModel3D" = None

    def __init__(self, dialog, model_db):
        super().__init__(dialog, model_db)
        self.dialog = dialog
        self.obj3d = PartModel3D(self, model_db)
        dialog.add_object(self)

    def set_selected(self, flag):
        pass

    def delete(self):
        pass

    def close(self):
        pass


class PartModel3D(_base3d.Base3D):
    """3D representation of the part model being oriented.

    Uses working copies of angle and position — changes are only written
    to the database when the dialog is accepted.
    """

    def __init__(self, parent: PartModel, model_db: "_Model3D"):
        self.db_obj = model_db

        parent.dialog.context.acquire()

        uuid = model_db.uuid
        if uuid in _vbo.PooledVBOHandler:
            vbo = _vbo.PooledVBOHandler(uuid)
        else:
            data_path = model_db.data_path
            if data_path is not None:
                packed = np.load(model_db.data_path).reshape(-1, 3)

                angle = model_db.angle3d
                position = model_db.position3d
                count = model_db.vertex_count

                obb = model_db.obb
                aabb = model_db.aabb

                obb @= angle
                aabb @= angle

                obb += position
                aabb += position

                packed @= angle
                packed[:count] += position

                packed = packed.reshape(-1)

                vbo = _vbo.PooledVBOHandler(uuid, packed, count, aabb=aabb, obb=obb)
            else:
                vbo = None

        # Working copies — not bound to DB until accept()
        angle = model_db.angle3d
        pos = model_db.position3d
        scale = model_db.scale
        material = _materials.Plastic(_color.Color(0.6, 0.6, 0.8, 1.0))

        _base3d.Base3D.__init__(self, parent, model_db, vbo, angle, pos, scale, material)
        self._is_visible = True

        parent.dialog.context.release()

    def set_selected(self, flag):
        pass

    def delete(self):
        pass


class AxisLabel(_ObjectBase):
    """Non-selectable fixed-world axis direction label."""
    obj3d: "AxisLabel3D" = None

    def __init__(self, dialog, text: str,
                 position: "_point.Point", angle: _angle.Angle):
        super().__init__(dialog, None)
        self.dialog = dialog
        self.obj3d = AxisLabel3D(self, text, position, angle)
        dialog.add_object(self)

    def set_selected(self, flag):
        pass

    def delete(self):
        pass

    def close(self):
        pass


class AxisLabel3D(_base3d.Base3D):
    """3D extruded text label indicating a canonical axis direction."""

    def __init__(self, parent: AxisLabel, text: str,
                 position: "_point.Point", angle: _angle.Angle):
        self.db_obj = None

        parent.dialog.context.acquire()

        model = build123d.Text(
            text, font_size=8.0,
            text_align=[build123d.TextAlign.CENTER, build123d.TextAlign.CENTER])

        model = build123d.extrude(model, 0.5)
        vertices, faces = _utils.convert_model_to_mesh(model)
        packed, count = _utils.compute_normals(vertices, faces)
        vbo = _vbo.NonPooledVBOHandler(packed, count)

        scale = _point.Point(1.0, 1.0, 1.0)
        material = _materials.Plastic(_color.Color(1.0, 0.85, 0.0, 1.0))

        _base3d.Base3D.__init__(self, parent, None, vbo, angle, position, scale, material)
        self._is_visible = True

        parent.dialog.context.release()

    def set_selected(self, flag):
        pass

    def delete(self):
        pass


class PartOrientationDialog(_dialog_base.BaseDialog):
    """Dialog for setting the canonical orientation and position offset of a 3D part model.

    Displays the part model in a GL canvas with fixed FORWARD (-Z) and TOP (+Y)
    direction labels.  Spin and flip buttons apply quaternion-path rotations so
    accumulated spins never cause gimbal lock.  Changes are written to the
    database only when the user clicks OK.
    """
    config = _Config

    def __init__(self, parent: "_ui.MainFrame"):
        _dialog_base.BaseDialog.__init__(
            self, parent, 'Part Orientation', size=(1100, 650),
            button_ids=QtWidgets.QDialogButtonBox.StandardButton.Ok)

        self._model_db: "_Model3D | None" = None
        self._part_model: "PartModel | None" = None
        self._mainframe = parent
        self._selected_obj = None
        self.o_angle: _angle.Angle = None
        self.o_position: _point.Point = None

        self.canvas = _canvas3d.Canvas3D(
            self.panel, _Config, size=(1600, 900))

        # Orientation controls — one button per icon, all ±90° steps
        orient_group = QtWidgets.QGroupBox('Orientation', self.panel)
        orient_layout = QtWidgets.QVBoxLayout(orient_group)

        _icon_size = QSize(64, 64)

        def _make_btn(icon_img, tooltip, slot):
            btn = QtWidgets.QPushButton()
            btn.setIcon(QIcon(icon_img.resize(64, 64).pixmap))
            btn.setIconSize(_icon_size)
            btn.setFixedSize(64, 64)
            btn.setToolTip(tooltip)
            btn.clicked.connect(slot)
            return btn

        self._btn_rotate_left = _make_btn(
            _image.icons.rotate_left, 'Rotate left (Y +90°)', self._on_rotate_left)
        self._btn_rotate_right = _make_btn(
            _image.icons.rotate_right, 'Rotate right (Y -90°)', self._on_rotate_right)
        self._btn_flip_forward = _make_btn(
            _image.icons.flip_forward, 'Flip forward (X +90°)', self._on_flip_forward)
        self._btn_flip_backward = _make_btn(
            _image.icons.flip_backward, 'Flip backward (X −90°)', self._on_flip_backward)
        self._btn_roll_right = _make_btn(
            _image.icons.roll_right, 'Roll right (Z +90°)', self._on_roll_right)
        self._btn_roll_left = _make_btn(
            _image.icons.roll_left, 'Roll left (Z -90°)', self._on_roll_left
        )

        line_layout = QtWidgets.QHBoxLayout()
        line_layout.addStretch(1)
        line_layout.addWidget(self._btn_rotate_left)
        line_layout.addWidget(self._btn_rotate_right)
        line_layout.addStretch(1)

        orient_layout.addLayout(line_layout)
        orient_layout.addSpacing(8)

        line_layout = QtWidgets.QHBoxLayout()
        line_layout.addStretch(1)
        line_layout.addWidget(self._btn_flip_forward)
        line_layout.addWidget(self._btn_flip_backward)
        line_layout.addStretch(1)

        orient_layout.addLayout(line_layout)
        orient_layout.addSpacing(8)

        line_layout = QtWidgets.QHBoxLayout()
        line_layout.addStretch(1)
        line_layout.addWidget(self._btn_roll_right)
        line_layout.addWidget(self._btn_roll_left)
        line_layout.addStretch(1)

        orient_layout.addLayout(line_layout)

        from ..widgets import triple_float_ctrl as _triple_float_ctrl

        self.position_ctrl = _triple_float_ctrl.TripleFloatCtrl(
            self.panel, None, None, True, label='Position Offset'
        )

        h_layout = QtWidgets.QHBoxLayout(self.panel)
        h_layout.addWidget(self.canvas, 4)

        h_layout.addSpacing(5)

        v_layout = QtWidgets.QVBoxLayout()
        v_layout.addWidget(orient_group)
        v_layout.addSpacing(5)
        v_layout.addWidget(self.position_ctrl)
        v_layout.addStretch(1)

        h_layout.addLayout(v_layout, 1)
        self.setLayout(h_layout)

    def SetValue(self, model_db: "_Model3D"):
        self.canvas.show()
        self.canvas.repaint()
        self.canvas.update()

        self._model_db = model_db
        self._mainframe.editor3d.context.acquire()
        self._part_model = PartModel(self, model_db)

        self.o_angle = self._model_db.angle3d.copy()
        self.o_position = self._model_db.position3d.copy()

        # Point the ctrl at the working position so slider changes go to the
        # 3D model directly; the DB write happens only on accept().
        working_pos = self._part_model.obj3d._position
        self.position_ctrl.set_obj(working_pos)

        # Compute label placement from model AABB
        aabb = self._part_model.obj3d.aabb
        if aabb is not None:
            cx = float((aabb[0][0] + aabb[1][0]) / 2)
            cy = float((aabb[0][1] + aabb[1][1]) / 2)
            cz = float((aabb[0][2] + aabb[1][2]) / 2)
            ext = max(
                abs(float(aabb[1][0]) - float(aabb[0][0])),
                abs(float(aabb[1][1]) - float(aabb[0][1])),
                abs(float(aabb[1][2]) - float(aabb[0][2])),
            )
            dist = ext * 0.7 + 5.0
        else:
            cx = cy = cz = 0.0
            dist = 15.0

        fwd_pos = _point.Point(cx, cy, cz + dist)
        fwd_angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)
        AxisLabel(self, 'FORWARD', fwd_pos, fwd_angle)

        # TOP label at +Y: text in XY plane, rotate -90° around X to face +Y
        top_pos = _point.Point(cx, cy + dist, cz)
        top_angle = _angle.Angle.from_euler(-90.0, 0.0, 0.0)
        AxisLabel(self, 'TOP', top_pos, top_angle)

        self._mainframe.editor3d.context.release()
        self._update_forward_up()

    def _on_rotate_left(self):
        angle = self._part_model.obj3d.angle.y + 90.0

        if angle > 180.0:
            angle -= 360.0

        self._part_model.obj3d.angle.y = angle
        self._model_db.angle3d.y = angle

        self._update_forward_up()

    def _on_rotate_right(self):
        angle = self._part_model.obj3d.angle.y - 90.0

        if angle < -180.0:
            angle += 360.0

        self._part_model.obj3d.angle.y = angle
        self._model_db.angle3d.y = angle
        self._update_forward_up()

    def _on_flip_forward(self):
        angle = self._part_model.obj3d.angle.x + 90.0

        if angle > 180.0:
            angle -= 360.0

        self._part_model.obj3d.angle.x = angle
        self._model_db.angle3d.x = angle

        self._update_forward_up()

    def _on_flip_backward(self):
        angle = self._part_model.obj3d.angle.x - 90.0

        if angle < -180.0:
            angle += 360.0

        self._part_model.obj3d.angle.x = angle
        self._model_db.angle3d.x = angle
        self._update_forward_up()

    def _on_roll_left(self):
        angle = self._part_model.obj3d.angle.z - 90.0

        if angle < -180.0:
            angle += 360.0

        self._part_model.obj3d.angle.z = angle
        self._model_db.angle3d.z = angle
        self._update_forward_up()

    def _on_roll_right(self):
        angle = self._part_model.obj3d.angle.z + 90.0

        if angle > 180.0:
            angle -= 360.0

        self._part_model.obj3d.angle.z = angle
        self._model_db.angle3d.z = angle

        self._update_forward_up()

    def _update_forward_up(self):
        if self._model_db is None or self._part_model is None:
            return

        local_obb = self._model_db.obb
        if local_obb is None:
            return

        q = self._part_model.obj3d.angle._q
        fwd = _obb_face_for_direction(
            local_obb, q, np.array([0.0, 0.0, 1.0], dtype=np.float32))
        up = _obb_face_for_direction(
            local_obb, q, np.array([0.0, 1.0, 0.0], dtype=np.float32))
        self._model_db.forward_up = [fwd, up]

    def _flush_and_invalidate_vbo(self):
        """Sync working state to DB and evict the stale VBO from the singleton.

        Must be called before exec() returns so the next user of this model's
        VBO recreates it from the final DB angle/position rather than reusing
        the orientation-dialog's initial (pre-rotation) baked data.
        """
        if self._part_model is None:
            return

        with self.context:
            position = self._part_model.obj3d.position
            model_position = self._model_db.position3d

            delta = position - model_position
            model_position += delta

            angle = self._part_model.obj3d.angle
            model_angle = self._model_db.angle3d

            with model_angle:
                model_angle.x = angle.x
                model_angle.y = angle.y

            model_angle.z = angle.z

            vbo = self._part_model.obj3d._vbo

            if vbo is not None and hasattr(vbo, 'id'):
                uuid = vbo.id
                if uuid in _vbo.VBOSingleton._instances:  # NOQA
                    vbo.release()
                    _vbo.PooledVBOHandler.release_model_allocation(uuid)
                    del _vbo.VBOSingleton._instances[uuid]  # NOQA

        self._part_model = None

    def accept(self):
        self._flush_and_invalidate_vbo()
        self.canvas.cleanup()
        super().accept()

    def reject(self):
        self._flush_and_invalidate_vbo()
        self.canvas.cleanup()
        super().reject()

    def closeEvent(self, event):
        self._flush_and_invalidate_vbo()
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
        pass

    def set_selected(self, obj):
        pass

    def get_selected(self):
        return None

    def Refresh(self, *_, **__):
        self.canvas.update()

    @property
    def context(self):
        return self.canvas.context
