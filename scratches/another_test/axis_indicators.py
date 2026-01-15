import wx
from wx import glcanvas
import build123d
import model_to_mesh
import numpy as np

from OpenGL import GL
from OpenGL import GLU

import debug
from wrappers.wrap_decimal import Decimal as _decimal
from geometry import point as _point
from geometry import angle as _angle
from geometry.point import ZERO_POINT
import gl_object


class Overlay(glcanvas.GLCanvas):

    def __init__(self, parent, size=(-1, -1), pos=wx.DefaultPosition):
        glcanvas.GLCanvas.__init__(self, parent, -1, size=size,
                                   pos=pos, style=wx.BORDER_DOUBLE)

        w, h = size

        self.ASPECT = w / h

        self.init = False
        self.context = glcanvas.GLContext(self)
        self.size = None

        self.camera_pos = _point.Point(_decimal(0.0),
                                       _decimal(1.0),
                                       _decimal(0.0))

        self.camera_eye = _point.Point(_decimal(0.0),
                                       _decimal(0.5),
                                       _decimal(10.0))

        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)

        self.Bind(wx.EVT_RIGHT_UP, self.on_right_up)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)

        self.Bind(wx.EVT_MOTION, self.on_mouse_motion)

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)

        self.mouse_pos = None
        self.grab_location = 0
        self.triangles = []
        self._default_cursor = self.GetCursor()

        self.build_model(w)

    def build_model(self, size):
        size /= 44.0
        r = (size / 25) / 2.0

        cylz = build123d.Cylinder(r, size, align=build123d.Align.NONE)
        cylx = build123d.Cylinder(r, size, align=build123d.Align.NONE)
        cyly = build123d.Cylinder(r, size, align=build123d.Align.NONE)
        sphere = build123d.Sphere(r)

        # cylz = cylz.rotate(build123d.Axis((0.0, 0.0, 0.0), (1, 0, 0)), 180.0)
        cylx = cylx.rotate(build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 90.0)
        cyly = cyly.rotate(build123d.Axis((0.0, 0.0, 0.0), (1, 0, 0)), -90.0)

        xnormals, xtriangles, xcount = model_to_mesh.get_smooth_triangles(cylx)
        ynormals, ytriangles, ycount = model_to_mesh.get_smooth_triangles(cyly)
        znormals, ztriangles, zcount = model_to_mesh.get_smooth_triangles(cylz)
        snormals, striangles, scount = model_to_mesh.get_smooth_triangles(sphere)

        self.triangles = [
            [xtriangles, xnormals, [1.0, 0.0, 0.0, 1.0], xcount],
            [ytriangles, ynormals, [0.0, 1.0, 0.0, 1.0], ycount],
            [ztriangles, znormals, [0.2, 0.2, 1.0, 1.0], zcount],
            [striangles, snormals, [0.1, 0.1, 0.1, 1.0], scount]
        ]

    @debug.timeit
    def set_angle(self, point: _point.Point):
        coords = list(point)
        scale = _decimal(1.0)

        for item in coords:
            if item == 0.0:
                continue

            new_scale = _decimal(1.0)

            while abs(item) * new_scale > 20.0:
                new_scale -= _decimal(0.05)

            if new_scale < scale:
                scale = new_scale

        for i, item in enumerate(coords):
            if item == 0.0:
                continue

            coords[i] = -coords[i] * scale

        p = _point.Point(*coords)

        angle = _angle.Angle.from_points(self.camera_pos, p)
        inverse = angle.inverse

        p @= inverse

        p.z = _decimal(10.0)
        p @= angle

        self.camera_eye = p
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
        GLU.gluPerspective(45, 1.77, 0.1, 50.0)

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

        for triangles, normals, color, count in self.triangles:
            GL.glColor4f(*color)

            GL.glVertexPointer(3, GL.GL_DOUBLE, 0, triangles)
            GL.glNormalPointer(GL.GL_DOUBLE, 0, normals)

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
        wx.CallAfter(self.DoSetViewport, event.GetSize())
        event.Skip()

    def DoSetViewport(self, size):
        self.SetCurrent(self.context)

        width, height = self.size = size * self.GetContentScaleFactor()
        #  fix up the viewport to maintain aspect ratio
        GL.glViewport(0, 0, int(width), height)

    def on_erase_background(self, _):
        pass

    def on_left_down(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        w, h = self.GetSize()
        self.mouse_pos = _point.Point(_decimal(x), _decimal(y))

        if 0 <= x <= 5 and 10 <= y <= h - 10:
            # left
            self.grab_location = 1
        elif w - 5 <= x <= w and 10 <= y <= h - 10:
            # right
            self.grab_location = 2
        elif 10 <= x <= w - 10 and 0 <= y <= 5:
            # top
            self.grab_location = 3
        elif 10 <= x <= w - 10 and h - 5 <= y <= h:
            # bottom
            self.grab_location = 4
        elif (
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
        w, h = self.GetSize()

        mouse_pos = _point.Point(_decimal(x), _decimal(y))

        if self.mouse_pos is None:
            self.mouse_pos = mouse_pos

        delta = mouse_pos - self.mouse_pos
        self.mouse_pos = mouse_pos

        if self.grab_location:
            if self.grab_location == 1:
                w -= int(delta.x)
                self.SetSize((w, h))

                x, y = self.GetPosition()
                x += int(delta.x)
                self.Move((x, y))

            elif self.grab_location == 2:
                w += int(delta.x)
                self.SetSize((w, h))

            elif self.grab_location == 3:
                h -= int(delta.y)
                self.SetSize((w, h))

                x, y = self.GetPosition()
                y += int(delta.y)
                self.Move((x, y))

            elif self.grab_location == 4:
                h += int(delta.y)
                self.SetSize((w, h))

            elif self.grab_location == 5:
                w -= int(delta.x)
                h -= int(delta.y)
                self.SetSize((w, h))

                x, y = self.GetPosition()
                x += int(delta.x)
                y += int(delta.y)
                self.Move((x, y))

            elif self.grab_location == 6:
                w += int(delta.x)
                h += int(delta.y)
                self.SetSize((w, h))

            elif self.grab_location == 7:
                w += int(delta.x)
                h -= int(delta.y)
                self.SetSize((w, h))

                x, y = self.GetPosition()
                y += int(delta.y)
                self.Move((x, y))

            elif self.grab_location == 8:
                w -= int(delta.x)
                h += int(delta.y)
                self.SetSize((w, h))

                x, y = self.GetPosition()
                x += int(delta.x)
                self.Move((x, y))

            elif self.grab_location == 9:
                x, y = self.GetPosition()
                x += int(delta.x)
                y += int(delta.y)
                self.Move((x, y))

            if self.grab_location != 9:
                self.build_model(min(w, h))

            self.Refresh(False)

        elif (
            (0 <= x <= 5 and 10 <= y <= h - 10) or
            (w - 5 <= x <= w and 10 <= y <= h - 10)
        ):
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))
        elif (
            (10 <= x <= w - 10 and 0 <= y <= 5) or
            (10 <= x <= w - 10 and h - 5 <= y <= h)
        ):
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZENS))
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


class Indicators(gl_object.GLObject):

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        cylz = build123d.Cylinder(0.1, 50.0, align=build123d.Align.NONE)
        cylx = build123d.Cylinder(0.1, 50.0, align=build123d.Align.NONE)
        cyly = build123d.Cylinder(0.1, 50.0, align=build123d.Align.NONE)

        # cylz = cylz.rotate(build123d.Axis((0.0, 0.0, 0.0), (1, 0, 0)), 180.0)
        cylx = cylx.rotate(build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 90.0)
        cyly = cyly.rotate(build123d.Axis((0.0, 0.0, 0.0), (1, 0, 0)), -90.0)

        xnormals, xtriangles, xcount = self.get_bundle_triangles(cylx)
        ynormals, ytriangles, ycount = self.get_bundle_triangles(cyly)
        znormals, ztriangles, zcount = self.get_bundle_triangles(cylz)

        xcolors = np.full((xcount, 4),
                          [1.0, 0.0, 0.0, 1.0], dtype=np.float32)

        ycolors = np.full((ycount, 4),
                          [0.0, 1.0, 0.0, 1.0], dtype=np.float32)

        zcolors = np.full((zcount, 4),
                          [0.0, 0.0, 1.0, 1.0], dtype=np.float32)

        self._triangles = [
            [xtriangles, xnormals, xcolors, xcount, True],
            [ytriangles, ynormals, ycolors, ycount, True],
            [ztriangles, znormals, zcolors, zcount, True]
        ]

        self._position = ZERO_POINT.copy()

        obj = cylx + cyly + cylz
        bb = obj.bounding_box()

        self.hit_test_rect = [[_point.Point(_decimal(bb.min.X), _decimal(bb.min.Y), _decimal(bb.min.Z)),
                               _point.Point(_decimal(bb.max.X), _decimal(bb.max.Y), _decimal(bb.max.Z))]]

        self.adjust_hit_points()

        self.parent.canvas.add_object(self)

    def get_first_points(self):
        points = []
        for i in range(3):
            tris = self._triangles[i][0]
            p = _point.Point(_decimal(tris[0][0]),
                             _decimal(tris[0][1]),
                             _decimal(tris[0][2]))

            points.append(p)

        return points

    @property
    def position(self):
        return self._position
