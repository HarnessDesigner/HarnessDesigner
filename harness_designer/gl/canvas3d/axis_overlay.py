# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import numpy as np
from OpenGL import GL
from OpenGL import GLU

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QCursor

from ...geometry import angle as _angle
from ...geometry import point as _point
from ... import color as _color
from ... import utils as _utils
from ...shapes import cylinder as _cylinder
from ...shapes import sphere as _sphere
from ...gl import materials as _materials
from ... import config as _config


class Overlay(QWidget):
    def __init__(self, parent, config: _config.Config.editor3d.axis_overlay):

        QWidget.__init__(self, parent)
        self.setFixedSize(*config.size)
        self.move(*config.position)
        self.setStyleSheet("border: 2px solid gray;")

        self.gl_overlay = GLOverlay(self, size=config.size)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.gl_overlay)

        self.config = config

        self.setVisible(config.is_visible)

        QTimer.singleShot(0, lambda: (
            self.move(*self.config.position),
            self.gl_overlay.update()
        ))

    def setVisible(self, flag=True):
        self.config.is_visible = flag
        QWidget.setVisible(self, flag)

    def resizeEvent(self, event):
        def _do():
            w = self.width()
            h = self.height()
            self.config.size = (w, h)
            self.gl_overlay.setFixedSize(w, h)

        QTimer.singleShot(0, _do)
        QWidget.resizeEvent(self, event)

    def moveEvent(self, event):
        def _do():
            pos = self.pos()
            self.config.position = (pos.x(), pos.y())

        QTimer.singleShot(0, _do)
        QWidget.moveEvent(self, event)

    def set_angle(self, point: _point.Point):
        self.gl_overlay.set_angle(point)

    def SetSize(self, size):
        w, h = size
        w = h = min(w, h)
        self.setFixedSize(w, h)
        self.gl_overlay.setFixedSize(w, h)


class GLOverlay(QOpenGLWidget):

    def __init__(self, parent: Overlay, size=(-1, -1)):
        QOpenGLWidget.__init__(self, parent)
        self.parent_overlay = parent
        self._init = False
        self.size = None

        self.mouse_pos = None
        self.grab_location = 0

        self.camera_pos = _point.Point(0.0, 1.0, 0.0)
        self.camera_eye = _point.Point(0.0, 0.5, 10.0)

        self.distance = 10.0

        self._triangles = []

        w, h = size
        if w > 0 and h > 0:
            self.build_model(min(w, h))

        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_left_down(event)
        elif event.button() == Qt.RightButton:
            self._on_right_down(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_left_up(event)
        elif event.button() == Qt.RightButton:
            self._on_right_up(event)

    def mouseMoveEvent(self, event):
        self._on_mouse_motion(event)

    def _on_left_down(self, event):
        x = event.position().x()
        y = event.position().y()
        w = self.width()
        h = self.height()

        sx = event.globalPosition().x()
        sy = event.globalPosition().y()
        self.mouse_pos = _point.Point(sx, sy)

        if (
            (0 <= x <= 10 and 0 <= y <= 10) or
            (0 <= x <= 10 and 0 <= y <= 10)
        ):
            self.grab_location = 5
        elif (
            (w - 10 <= x <= w and h - 10 <= y <= h) or
            (w - 10 <= x <= w and h - 10 <= y <= h)
        ):
            self.grab_location = 6
        elif (
            (w - 10 <= x <= w and 0 <= y <= 10) or
            (w <= x <= w - 10 and 0 <= y <= 10)
        ):
            self.grab_location = 7
        elif (
            (0 <= x <= 10 and h - 10 <= y <= h) or
            (0 <= x <= 10 and h - 10 <= y <= h)
        ):
            self.grab_location = 8
        else:
            self.grab_location = 9

        self.grabMouse()

    def _on_left_up(self, event):
        self.releaseMouse()
        self.grab_location = 0

    def _on_right_up(self, event):
        pass

    def _on_right_down(self, event):
        pass

    def _on_mouse_motion(self, event):
        x = event.position().x()
        y = event.position().y()
        w = self.parent_overlay.width()
        h = self.parent_overlay.height()

        sx = event.globalPosition().x()
        sy = event.globalPosition().y()

        mouse_pos = _point.Point(sx, sy)

        if self.mouse_pos is None:
            self.mouse_pos = mouse_pos

        mouse_delta = mouse_pos - self.mouse_pos
        self.mouse_pos = mouse_pos

        delta_x = int(mouse_delta.x)
        delta_y = int(mouse_delta.y)

        if self.grab_location:
            if self.grab_location == 1:
                w -= delta_x
                self.parent_overlay.setFixedSize(w, h)
                pos = self.parent_overlay.pos()
                self.parent_overlay.move(pos.x() + delta_x, pos.y())

            elif self.grab_location == 2:
                w += delta_x
                self.parent_overlay.setFixedSize(w, h)

            elif self.grab_location == 3:
                h -= delta_y
                self.parent_overlay.setFixedSize(w, h)
                pos = self.parent_overlay.pos()
                self.parent_overlay.move(pos.x(), pos.y() + delta_y)

            elif self.grab_location == 4:
                h += delta_y
                self.parent_overlay.setFixedSize(w, h)

            elif self.grab_location == 5:
                delta = max(delta_x, delta_y)
                w -= delta
                h -= delta
                pos = self.parent_overlay.pos()
                self.parent_overlay.setFixedSize(w, h)
                self.parent_overlay.move(pos.x() + delta, pos.y() + delta)

            elif self.grab_location == 6:
                delta = min(delta_x, delta_y)
                w += delta
                h += delta
                self.parent_overlay.setFixedSize(w, h)

            elif self.grab_location == 7:
                delta = max(abs(delta_x), abs(delta_y))
                pos = self.parent_overlay.pos()
                if delta_x < 0:
                    w += delta
                    h -= delta
                    self.parent_overlay.setFixedSize(w, h)
                    self.parent_overlay.move(pos.x(), pos.y() + delta)
                else:
                    w += delta
                    h += delta
                    self.parent_overlay.setFixedSize(w, h)
                    self.parent_overlay.move(pos.x(), pos.y() - delta)

            elif self.grab_location == 8:
                pos = self.parent_overlay.pos()
                delta = max(abs(delta_x), abs(delta_y))
                if delta_x < 0:
                    w += delta
                    h += delta
                    self.parent_overlay.setFixedSize(w, h)
                    self.parent_overlay.move(pos.x() - delta, pos.y())
                else:
                    w -= delta_x
                    h -= delta_y
                    self.parent_overlay.setFixedSize(w, h)
                    self.parent_overlay.move(pos.x() + delta, pos.y())

            elif self.grab_location == 9:
                pos = self.parent_overlay.pos()
                self.parent_overlay.move(pos.x() + delta_x, pos.y() + delta_y)

            if self.grab_location != 9:
                self.build_model(min(w, h))

            parent = self.parent_overlay.parent()
            if parent is not None:
                parent.update()
            self.parent_overlay.update()

        elif (
            (0 <= x <= 5 and 0 <= y <= 10) or
            (0 <= x <= 10 and 0 <= y <= 5) or
            (w - 10 <= x <= w and h - 5 <= y <= h) or
            (w - 5 <= x <= w and h - 10 <= y <= h)
        ):
            self.setCursor(QCursor(Qt.SizeFDiagCursor))
        elif (
            (w - 10 <= x <= w and 0 <= y <= 5) or
            (w <= x <= w - 5 and 0 <= y <= 10) or
            (0 <= x <= 5 and h - 10 <= y <= h) or
            (0 <= x <= 10 and h - 5 <= y <= h)
        ):
            self.setCursor(QCursor(Qt.SizeBDiagCursor))
        else:
            self.setCursor(QCursor(Qt.SizeAllCursor))

    def build_model(self, size):
        self.distance = size / 14.0
        size /= 40.0
        r = (size / 22)

        x_vertices, x_faces = _cylinder.create(r, size, resolution=10, split=1)
        y_vertices, y_faces = _cylinder.create(r, size, resolution=10, split=1)
        z_vertices, z_faces = _cylinder.create(r, size, resolution=10, split=1)
        s_vertices, s_faces = _sphere.create(r, resolution=10)

        x_material = _materials.Plastic(_color.Color(1.0, 0.2, 0.2, 1.0))
        y_material = _materials.Plastic(_color.Color(0.2, 1.0, 0.2, 1.0))
        z_material = _materials.Plastic(_color.Color(0.2, 0.2, 1.0, 1.0))
        s_material = _materials.Plastic(_color.Color(0.1, 0.1, 0.1, 1.0))

        x_tris, x_nrmls, x_count = (
            _utils.compute_smoothed_vertex_normals(x_vertices, x_faces))
        y_tris, y_nrmls, y_count = (
            _utils.compute_smoothed_vertex_normals(y_vertices, y_faces))
        z_tris, z_nrmls, z_count = (
            _utils.compute_smoothed_vertex_normals(z_vertices, z_faces))
        s_tris, s_nrmls, s_count = (
            _utils.compute_smoothed_vertex_normals(s_vertices, s_faces))

        x_angle = _angle.Angle.from_euler(0.0, 90.0, 0.0)
        y_angle = _angle.Angle.from_euler(270.0, 0.0, 0.0)

        x_tris @= x_angle
        x_nrmls @= x_angle

        y_tris @= y_angle
        y_nrmls @= y_angle

        self._triangles = [
            [s_tris, s_nrmls, s_count, s_material],
            [x_tris, x_nrmls, x_count, x_material],
            [y_tris, y_nrmls, y_count, y_material],
            [z_tris, z_nrmls, z_count, z_material]
        ]

    def set_angle(self, point: _point.Point):
        coords = list(point)

        scale = 1.0

        for item in coords:
            if item == 0.0:
                continue

            new_scale = 1.0

            while abs(item) * new_scale > 20.0:
                new_scale -= 0.05

            if new_scale < scale:
                scale = new_scale

        for i, item in enumerate(coords):
            if item == 0.0:
                continue

            coords[i] = -coords[i] * scale

        new_camera_eye = _point.Point(*coords).as_numpy

        camera_pos = self.camera_pos.as_numpy

        delta = new_camera_eye - camera_pos
        distance = np.linalg.norm(delta)

        nce = camera_pos + delta * (self.distance / distance)
        nce = _point.Point(*[float(item) for item in nce])

        self.camera_eye = nce

        self.update()

    def initializeGL(self):
        w = self.width()
        h = self.height()
        GL.glClearColor(0.1, 0.1, 0.1, 1.0)
        GL.glViewport(0, 0, w, h)

        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_LIGHTING)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_BLEND)

        GL.glEnable(GL.GL_DITHER)
        GL.glEnable(GL.GL_MULTISAMPLE)
        GL.glDepthMask(GL.GL_TRUE)

        GL.glShadeModel(GL.GL_SMOOTH)
        GL.glColorMaterial(GL.GL_FRONT, GL.GL_AMBIENT_AND_DIFFUSE)
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        GL.glEnable(GL.GL_RESCALE_NORMAL)

        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, [0.5, 0.5, 0.5, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.3, 0.3, 0.3, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])

        GL.glMaterialfv(GL.GL_FRONT, GL.GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        GL.glMaterialfv(GL.GL_FRONT, GL.GL_DIFFUSE, [0.5, 0.5, 0.5, 1.0])
        GL.glMaterialfv(GL.GL_FRONT, GL.GL_SPECULAR, [0.8, 0.8, 0.8, 1.0])
        GL.glMaterialf(GL.GL_FRONT, GL.GL_SHININESS, 80.0)

        GL.glEnable(GL.GL_LIGHT0)

        GL.glMatrixMode(GL.GL_PROJECTION)
        GLU.gluPerspective(45, 1.0, 0.1, 50.0)

        GL.glMatrixMode(GL.GL_MODELVIEW)

        camera = self.camera_eye.as_float + self.camera_pos.as_float + (0.0, 1.0, 0.0)
        GLU.gluLookAt(*camera)

    def resizeGL(self, width, height):
        self.size = (width, height)
        GL.glViewport(0, 0, width, height)

    def paintGL(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

        forward = (self.camera_pos - self.camera_eye).as_numpy

        fn = np.linalg.norm(forward)
        if fn < 1e-6:
            forward = np.array(
                [0.0, 0.0, -1.0],
                dtype=np.dtypes.Float64DType
                )
        else:
            forward = forward / fn

        temp_up = np.array(
            [0.0, 1.0, 0.0],
            dtype=np.dtypes.Float64DType
        )

        right = np.cross(temp_up, forward)  # NOQA

        rn = np.linalg.norm(right)
        if rn < 1e-6:
            right = np.array(
                [1.0, 0.0, 0.0],
                dtype=np.dtypes.Float64DType
                )
        else:
            right = right / rn

        up = np.cross(forward, right)  # NOQA

        un = np.linalg.norm(up)
        if un < 1e-6:
            up = np.array(
                [0.0, 1.0, 0.0],
                dtype=np.dtypes.Float64DType
                )
        else:
            up = up / un

        camera = self.camera_eye.as_float + self.camera_pos.as_float + tuple(up.tolist())
        GLU.gluLookAt(*camera)

        GL.glPushMatrix()

        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glEnableClientState(GL.GL_NORMAL_ARRAY)

        for tris, nrmls, count, material in self._triangles:
            GL.glColor4f(*material.color_scalar)
            GL.glMaterialfv(GL.GL_FRONT, GL.GL_AMBIENT, material.ambient)
            GL.glMaterialfv(GL.GL_FRONT, GL.GL_DIFFUSE, material.diffuse)
            GL.glMaterialfv(GL.GL_FRONT, GL.GL_SPECULAR, material.specular)
            GL.glMaterialf(GL.GL_FRONT, GL.GL_SHININESS, material.shininess)

            GL.glVertexPointer(3, GL.GL_DOUBLE, 0, tris)
            GL.glNormalPointer(GL.GL_DOUBLE, 0, nrmls)
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, count)

        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        GL.glDisableClientState(GL.GL_NORMAL_ARRAY)

        GL.glPopMatrix()
        # Qt handles SwapBuffers automatically.
