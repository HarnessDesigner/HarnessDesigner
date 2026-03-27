
import wx
from wx import glcanvas
import numpy as np
from OpenGL import GL
from OpenGL import GLU

from ...geometry import angle as _angle
from ...geometry import point as _point
from ... import color as _color

from ... import utils as _utils
from ...shapes import cylinder as _cylinder
from ...shapes import sphere as _sphere

from ...gl import materials as _materials
from ... import config as _config


Config = _config.Config.axis_overlay


class Overlay(wx.Panel):
    def __init__(self, parent):

        wx.Panel.__init__(self, parent, wx.ID_ANY, size=Config.size,
                          pos=Config.position, style=wx.BORDER_DOUBLE)

        self.gl_overlay = GLOverlay(self, size=Config.size)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.gl_overlay, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND)
        self.SetSizer(vsizer)

        # self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        # self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        #
        # self.Bind(wx.EVT_RIGHT_UP, self.on_right_up)
        # self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        #
        # self.Bind(wx.EVT_MOTION, self.on_mouse_motion)

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOVE, self.on_move)

        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)

        self.Show(Config.is_visible)

        def _do():
            self.Move(Config.position)
            self.SendSizeEvent()

        wx.CallAfter(_do)

    def Show(self, flag=True):
        Config.is_visible = flag
        wx.Panel.Show(self, flag)

    @staticmethod
    def on_size(evt):
        w, h = evt.GetSize()
        Config.size = (w, h)
        evt.Skip()

    @staticmethod
    def on_move(evt):
        x, y = evt.GetPosition()
        Config.position = (x, y)
        evt.Skip()

    def set_angle(self, point: _point.Point):
        self.gl_overlay.set_angle(point)

    def on_erase_background(self, _):
        pass

    def SetSize(self, size):
        w, h = size
        w = h = min(w, h)

        wx.Panel.SetSize(self, (w, h))
        self.gl_overlay.SetSize((w, h))


class GLOverlay(glcanvas.GLCanvas):

    def __init__(self, parent: Overlay, size=(-1, -1)):
        glcanvas.GLCanvas.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        self.parent = parent
        self.init = False
        self.context = glcanvas.GLContext(self)
        self.size = None

        self.mouse_pos = None
        self.grab_location = 0
        self._default_cursor = self.GetCursor()

        self.camera_pos = _point.Point(0.0,
                                       1.0,
                                       0.0)

        self.camera_eye = _point.Point(0.0,
                                       0.5,
                                       10.0)

        self.distance = 10.0

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_PAINT, self.on_paint)

        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)

        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_RIGHT_UP, self.on_right_up)

        self.Bind(wx.EVT_MOTION, self.on_mouse_motion)

        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)

        self._triangles = []

        w, h = size
        self.build_model(min(w, h))

    def on_left_down(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        w, h = self.GetSize()

        sx, sy = self.ClientToScreen((x, y))
        self.mouse_pos = _point.Point(sx, sy)

        # if 0 <= x <= 5 and 10 <= y <= h - 10:
        #     # left
        #     self.grab_location = 1
        # elif w - 5 <= x <= w and 10 <= y <= h - 10:
        #     # right
        #     self.grab_location = 2
        # elif 10 <= x <= w - 10 and 0 <= y <= 5:
        #     # top
        #     self.grab_location = 3
        # elif 10 <= x <= w - 10 and h - 5 <= y <= h:
        #     # bottom
        #     self.grab_location = 4
        if (
            (0 <= x <= 5 and 0 <= y <= 10) or
            (0 <= x <= 10 and 0 <= y <= 5)
        ):
            # top left
            self.grab_location = 5
        elif (
            (w - 10 <= x <= w and h - 5 <= y <= h) or
            (w - 5 <= x <= w and h - 10 <= y <= h)
        ):
            # bottom right
            self.grab_location = 6
        elif (
            (w - 10 <= x <= w and 0 <= y <= 5) or
            (w <= x <= w - 5 and 0 <= y <= 10)
        ):
            # top right
            self.grab_location = 7
        elif (
            (0 <= x <= 5 and h - 10 <= y <= h) or
            (0 <= x <= 10 and h - 5 <= y <= h)
        ):
            # bottom left
            self.grab_location = 8
        else:
            self.grab_location = 9

        if not self.HasCapture():
            self.CaptureMouse()

        evt.Skip()

    def on_left_up(self, evt: wx.MouseEvent):
        if self.HasCapture():
            self.ReleaseMouse()

        self.grab_location = 0

        evt.Skip()

    def on_right_up(self, evt: wx.MouseEvent):  # NOQA
        evt.Skip()

    def on_right_down(self, evt: wx.MouseEvent):  # NOQA
        evt.Skip()

    def on_mouse_motion(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        w, h = self.parent.GetSize()

        sx, sy = self.ClientToScreen((x, y))

        mouse_pos = _point.Point(sx, sy)

        if self.mouse_pos is None:
            self.mouse_pos = mouse_pos

        delta = mouse_pos - self.mouse_pos
        self.mouse_pos = mouse_pos

        if self.grab_location:
            if self.grab_location == 1:
                w -= int(delta.x)
                self.parent.SetSize((w, h))

                x, y = self.parent.GetPosition()
                x += int(delta.x)
                self.parent.Move((x, y))

            elif self.grab_location == 2:
                w += int(delta.x)
                self.parent.SetSize((w, h))

            elif self.grab_location == 3:
                h -= int(delta.y)
                self.parent.SetSize((w, h))

                x, y = self.parent.GetPosition()
                y += int(delta.y)
                self.parent.Move((x, y))

            elif self.grab_location == 4:
                h += int(delta.y)
                self.parent.SetSize((w, h))

            elif self.grab_location == 5:
                w -= int(delta.x)
                h -= int(delta.y)

                x, y = self.parent.GetPosition()
                x += int(delta.x)
                y += int(delta.y)

                self.parent.Move((x, y))
                self.parent.SetSize((w, h))

            elif self.grab_location == 6:
                w += int(delta.x)
                h += int(delta.y)
                self.parent.SetSize((w, h))

            elif self.grab_location == 7:
                w += int(delta.x)
                h -= int(delta.y)
                self.parent.SetSize((w, h))

                x, y = self.parent.GetPosition()
                y += int(delta.y)
                self.parent.Move((x, y))

            elif self.grab_location == 8:
                w -= int(delta.x)
                h += int(delta.y)
                self.parent.SetSize((w, h))

                x, y = self.parent.GetPosition()
                x += int(delta.x)
                self.parent.Move((x, y))

            elif self.grab_location == 9:
                x, y = self.parent.GetPosition()
                x += int(delta.x)
                y += int(delta.y)
                self.parent.Move((x, y))

            if self.grab_location != 9:
                self.build_model(min(w, h))

            self.parent.Refresh(False)

        # elif (
        #     (0 <= x <= 5 and 10 <= y <= h - 10) or
        #     (w - 5 <= x <= w and 10 <= y <= h - 10)
        # ):
        #     self.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))
        # elif (
        #     (10 <= x <= w - 10 and 0 <= y <= 5) or
        #     (10 <= x <= w - 10 and h - 5 <= y <= h)
        # ):
        #     self.SetCursor(wx.Cursor(wx.CURSOR_SIZENS))
        elif (
            (0 <= x <= 5 and 0 <= y <= 10) or
            (0 <= x <= 10 and 0 <= y <= 5) or
            (w - 10 <= x <= w and h - 5 <= y <= h) or
            (w - 5 <= x <= w and h - 10 <= y <= h)
        ):
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZENWSE))
        elif (
            (w - 10 <= x <= w and 0 <= y <= 5) or
            (w <= x <= w - 5 and 0 <= y <= 10) or
            (0 <= x <= 5 and h - 10 <= y <= h) or
            (0 <= x <= 10 and h - 5 <= y <= h)
        ):
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZENESW))
        else:
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZING))

        evt.Skip()

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

        self.Refresh(False)

    def InitGL(self):
        w, h = self.GetSize()
        GL.glClearColor(0.1, 0.1, 0.1, 1.0)
        GL.glViewport(0, 0, w, h)

        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_LIGHTING)
        # glEnable(GL_ALPHA_TEST)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_BLEND)

        GL.glEnable(GL.GL_DITHER)
        GL.glEnable(GL.GL_MULTISAMPLE)
        # glEnable(GL_FOG)
        GL.glDepthMask(GL.GL_TRUE)
        # glShadeModel(GL_FLAT)

        GL.glShadeModel(GL.GL_SMOOTH)
        GL.glColorMaterial(GL.GL_FRONT, GL.GL_AMBIENT_AND_DIFFUSE)
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        # glEnable(GL_NORMALIZE)
        GL.glEnable(GL.GL_RESCALE_NORMAL)
        # glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)

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

    def OnDraw(self):
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

        self.SwapBuffers()

    def on_paint(self, _):
        _ = wx.PaintDC(self)
        self.SetCurrent(self.context)

        if not self.init:
            self.InitGL()
            self.init = True

        self.OnDraw()

    def on_size(self, event):
        size = event.GetSize()

        self.SetCurrent(self.context)

        width, height = self.size = size
        #  fix up the viewport to maintain aspect ratio
        GL.glViewport(0, 0, width, height)

        # wx.CallAfter(self.DoSetViewport, event.GetSize())
        event.Skip()

    def DoSetViewport(self, size):
        self.SetCurrent(self.context)

        width, height = self.size = size
        #  fix up the viewport to maintain aspect ratio
        GL.glViewport(0, 0, width, height)

    def on_erase_background(self, _):
        pass
