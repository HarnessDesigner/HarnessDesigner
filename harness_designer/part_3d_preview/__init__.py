
import wx
import math
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from wx import glcanvas
import tempfile
import build123d

from ..wrappers.decimal import Decimal as _decimal
from ..geometry import point as _point
from ..geometry import angle as _angle
from .. import gl_materials
from ..database.global_db import model3d as _model3d
from ..wrappers import color as _color
from .. import utils
from ..editor_3d.objects import transition as _t_builder, get_triangles
from ..database.global_db import transition as _transition



def _read_step(data):
    temp_dir = tempfile.gettempdir()
    tmp_file_path = os.path.join(temp_dir, 'harness_designer_tmp.stp')
    with open(tmp_file_path, 'wb') as f:
        f.write(data)

    model = build123d.import_step(tmp_file_path)

    try:
        os.remove(tmp_file_path)
    except OSError:
        pass

    return model


def _read_stl(data: bytes):
    temp_dir = tempfile.gettempdir()
    tmp_file_path = os.path.join(temp_dir, 'harness_designer_tmp.stl')
    with open(tmp_file_path, 'wb') as f:
        f.write(data)

    model = build123d.import_stl(tmp_file_path)

    try:
        os.remove(tmp_file_path)
    except OSError:
        pass

    return model


class GLPreview(glcanvas.GLCanvas):
    def __init__(self, parent: "Preview3D"):
        self.parent = parent

        glcanvas.GLCanvas.__init__(self, parent, wx.ID_ANY)
        self.update_objects = True
        self.init = False
        self.context = glcanvas.GLContext(self)

        self.last_left_x = 0
        self.last_left_y = 0
        self.last_right_x = 0
        self.last_right_y = 0

        self.size = None
        self.Bind(wx.EVT_ERASE_BACKGROUND, self._on_erase_background)
        self.Bind(wx.EVT_SIZE, self._on_size)
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_mouse_down)
        self.Bind(wx.EVT_RIGHT_DOWN, self._on_mouse_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_mouse_up)
        self.Bind(wx.EVT_RIGHT_UP, self._on_mouse_up)
        self.Bind(wx.EVT_MOTION, self._on_mouse_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self._on_mouse_wheel)

        self._is_drag_event = False
        self._grid = None
        self.viewMatrix = None
        self._up_down_angle = 0.0
        self._left_right_angle = 0.0
        self._near_far_angle = 0.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._pan_z = 0.0
        self._scale_x = 1.0
        self._scale_y = 1.0
        self._scale_z = 1.0

    def look_at(self, *, camera_point: _point.Point | None = None,
                focus_point: _point.Point | None = None,
                direction_vector: _point.Point | None = None):
        pass

    def add_to_view_angle(self, x: float | None = None, y: float | None = None,
                          z: float | None = None) -> tuple[float, float, float]:
        if x is not None:
            self._left_right_angle += x
        if y is not None:
            self._up_down_angle += y
        if z is not None:
            self._near_far_angle += z

        return self._up_down_angle, self._left_right_angle, self._near_far_angle

    def set_view_angle(self, x: float | None = None, y: float | None = None,
                       z: float | None = None) -> None:
        if x is not None:
            self._left_right_angle = x
        if y is not None:
            self._up_down_angle = y
        if z is not None:
            self._near_far_angle = z

    def get_view_angle(self) -> tuple[float, float, float]:
        return self._up_down_angle, self._left_right_angle, self._near_far_angle

    def add_to_pan(self, x: float | None = None, y: float | None = None,
                   z: float | None = None) -> tuple[float, float, float]:
        if x is not None:
            self._pan_x += x
        if y is not None:
            self._pan_y += y
        if z is not None:
            self._pan_z += z

        return self._pan_x, self._pan_y, self._pan_z

    def set_pan(self, x: float | None = None, y: float | None = None,
                z: float | None = None) -> None:
        if x is not None:
            self._pan_x = x
        if y is not None:
            self._pan_y = y
        if z is not None:
            self._pan_z = z

    def get_pan(self) -> tuple[float, float, float]:
        return self._pan_x, self._pan_y, self._pan_z

    def add_to_scale(self, x: float | None = None, y: float | None = None,
                     z: float | None = None) -> tuple[float, float, float]:
        if x is not None:
            self._scale_x += x
        if y is not None:
            self._scale_y += y
        if z is not None:
            self._scale_z += z

        return self._scale_x, self._scale_y, self._scale_z

    def set_scale(self, x: float | None = None, y: float | None = None,
                  z: float | None = None) -> None:
        if x is not None:
            self._scale_x = x
        if y is not None:
            self._scale_y = y
        if z is not None:
            self._scale_z = z

    def get_scale(self) -> tuple[float, float, float]:
        return self._scale_x, self._scale_y, self._scale_z

    def draw(self):
        normals, triangles, triangle_count = self.parent.get_triangles()

        glLoadIdentity()
        glRotatef(self._up_down_angle * 0.1, 1.0, 0.0, 0.0)
        glRotatef(self._left_right_angle * 0.1, 0.0, 1.0, 0.0)

        glPushMatrix()
        glLoadIdentity()

        if self._pan_x:
            glTranslatef(-self._pan_x * 0.1, 0, 0)
            self._pan_x = 0.0

        if self._pan_y:
            glTranslatef(0, self._pan_y * 0.1, 0)
            self._pan_y = 0.0

        glMultMatrixf(self.viewMatrix)
        self.viewMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)

        glPopMatrix()
        glMultMatrixf(self.viewMatrix)

        glScalef(self._scale_x, self._scale_y, self._scale_z)

        # Clear color and depth buffers.
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if triangle_count > 0:
            glPushMatrix()

            glEnableClientState(GL_VERTEX_ARRAY)
            glEnableClientState(GL_NORMAL_ARRAY)

            glColor4f(*self.parent.color)

            if self.parent.material is not None:
                self.parent.material.set()

            glVertexPointer(3, GL_DOUBLE, 0, triangles)
            glNormalPointer(GL_DOUBLE, 0, normals)
            glDrawArrays(GL_TRIANGLES, 0, triangle_count)

            glDisableClientState(GL_VERTEX_ARRAY)
            glDisableClientState(GL_NORMAL_ARRAY)
            glPopMatrix()

        self.draw_grid(25.0, 25.0, 100.0)

    def draw_grid(self, size=25.0, step=1.0, fade_dist=100.0):
        if self._grid is None:
            self._grid = []

            y = getattr(self, 'min_y', 0.0) - 1e-3
            half = size / 2.0
            lines = int(math.ceil(size / step))

            for i in range(-lines, lines+1):
                coord = i * step
                d = min(1.0, abs(coord) / fade_dist)
                c = 0.6 * (1.0 - d) + 0.15 * d
                self._grid.append(
                    ((c, c, c),
                     np.array([[self.center[0] - half, y, self.center[2] + coord],
                               [self.center[0] + half, y, self.center[2] + coord],
                               [self.center[0] + coord, y, self.center[2] - half],
                               [self.center[0] + coord, y, self.center[2] + half]], dtype=float)))

        glDisable(GL_LIGHTING)
        glLineWidth(1.0)
        glEnableClientState(GL_VERTEX_ARRAY)

        for color, arr in self._grid:
            glColor3f(*color)
            glVertexPointer(3, GL_DOUBLE, 0, arr)
            glDrawArrays(GL_LINES, 0, 4)

        glDisableClientState(GL_VERTEX_ARRAY)

        glEnable(GL_LIGHTING)

    def init_gl(self):
        w, h = self.GetSize()

        glClearColor(0.95, 0.95, 0.95, 0.0)
        glViewport(0, 0, w, h)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glShadeModel(GL_SMOOTH)
        glEnable(GL_COLOR_MATERIAL)
        # glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.1, 0.1, 0.1, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.1, 0.1, 0.1, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0])

        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, w / float(h), 0.1, 1000.0)

        glMatrixMode(GL_MODELVIEW)
        gluLookAt(0.0, 2.0, -100.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)
        self.viewMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)

    def _on_erase_background(self, _):
        pass

    def set_ortho(self, size):
        self.SetCurrent(self.context)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(-size, size, -size, size, -size, size)
        glMatrixMode(GL_MODELVIEW)

    def _on_paint(self, _):
        _ = wx.PaintDC(self)
        self.SetCurrent(self.context)

        if self.viewMatrix is None:
            self.init_gl()

        self.draw()
        self.SwapBuffers()

    # override the _on_size method in the canvas
    def _on_size(self, event):
        wx.CallAfter(self._set_viewport)
        event.Skip()

    def _on_mouse_down(self, event: wx.MouseEvent):
        if self.HasCapture():
            self.ReleaseMouse()
        self.CaptureMouse()

        if event.LeftIsDown():
            self.last_left_x, self.last_left_y = event.GetPosition()
        elif event.RightIsDown():
            self.last_right_x, self.last_right_y = event.GetPosition()

    def _on_mouse_up(self, _):
        if self.HasCapture():
            self.ReleaseMouse()

    def _on_mouse_motion(self, event: wx.MouseEvent):
        if event.Dragging():
            x, y = event.GetPosition()

            if event.LeftIsDown():
                new_x = self.last_left_x - x
                new_y = self.last_left_y - y

                self.add_to_view_angle(new_x, new_y)
                self.last_left_x, self.last_left_y = x, y
                self.Refresh(False)

            elif event.RightIsDown():
                new_x = self.last_right_x - x
                new_y = self.last_right_y - y

                self.set_pan(new_x, new_y)
                self.last_right_x, self.last_right_y = x, y
                self.Refresh(False)

    def _on_mouse_wheel(self, event: wx.MouseEvent):
        scale = event.GetWheelRotation() / 20000
        scale = self.renderer.add_to_scale(scale, scale, scale)

        if scale < 0.001:
            scale = 0.001
            self.renderer.add_to_scale(scale, scale, scale)

        self.update_objects = False
        self.Refresh(False)
        event.Skip()

    def _set_viewport(self):
        self.SetCurrent(self.context)
        size = self.GetClientSize() * self.GetContentScaleFactor()
        glViewport(0, 0, size.width, size.height)

    def _on_enter(self, event):
        event.Skip()

    def _on_leave(self, event):
        event.Skip()

    def _on_capture_lost(self, event):
        if self.HasCapture():
            self.ReleaseMouse()

        event.Skip()


class Preview3D(wx.Panel):

    @property
    def model_count(self):
        return len(self._models)

    def set_transition(self, t_db: _transition.Transition):
        center = _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
        branch_points = [None] * t_db.branch_count
        sizes = [branch.min_dia for branch in t_db.branches]

        model = _t_builder.build_model(center, t_db, branch_points, sizes)[0]

        bb = model.bounding_box()
        x1, y1, z1 = bb.min
        x2, y2, z2 = bb.max
        x_size = x2 - x1
        y_size = y2 - y1
        z_size = z2 - z1
        size = max(x_size, y_size, z_size)

        h_size = size / 2

        self.normals = [None]
        self.triangles = [None]
        self.triangle_count = [0]
        self._angle = _angle.Angle(_decimal(0.0), _decimal(0.0), _decimal(0.0))
        self._offset = _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
        self._index = 0
        self._models = [model]
        self.color = t_db.color.ui.rgb_scalar
        self.material = gl_materials.Rubber(self.color)

        self.x_angle_ctrl.Enable(False)
        self.y_angle_ctrl.Enable(False)
        self.z_angle_ctrl.Enable(False)

        self.x_offset_ctrl.Enable(False)
        self.y_offset_ctrl.Enable(False)
        self.z_offset_ctrl.Enable(False)

        self.canvas.set_ortho(h_size)
        self.canvas.Refresh(False)

    def get_triangles(self):
        index = self._index

        if self.triangles[index] is None:
            model = self._models[index]
            normals, triangles, triangle_count = get_triangles(model)
            self.normals[index] = normals
            self.triangles[index] = triangles
            self.triangle_count[index] = triangle_count

        normals = self.normals[index]
        triangles = self.triangles[index]
        triangle_count = self.triangle_count[index]

        if self._angle:
            triangles @= self._angle

        if self._offset:
            triangles @= self._offset

        return normals, triangles, triangle_count

    def set_model_db(self, db_obj: _model3d.Model3D, color: _color.Color, material: gl_materials.GLMaterial):
        models = db_obj.all_model_data
        new_models = []

        for model, type_ in models:
            if type_ in ('stp', 'step'):
                model = _read_step(model)
            elif type_ == 'stl':
                model = _read_stl(model)
            else:
                continue

            new_models.append(model)

        self._angle = db_obj.angle
        self._offset = db_obj.offset
        self._index = db_obj.index
        self._db_obj = db_obj

        self.color = color.rgb_scalar
        self.material = material

        self.x_angle_ctrl.Enable(True)
        self.y_angle_ctrl.Enable(True)
        self.z_angle_ctrl.Enable(True)

        self.x_offset_ctrl.Enable(True)
        self.y_offset_ctrl.Enable(True)
        self.z_offset_ctrl.Enable(True)

        self.x_angle_ctrl.SetValue(float(self._angle.x))
        self.y_angle_ctrl.SetValue(float(self._angle.y))
        self.z_angle_ctrl.SetValue(float(self._angle.z))

        self.x_offset_ctrl.SetValue(float(self._offset.x))
        self.y_offset_ctrl.SetValue(float(self._offset.y))
        self.z_offset_ctrl.SetValue(float(self._offset.z))

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sl = wx.StaticLine(self, wx.ID_ANY, size=(5, 5))
        sizer.Add(sl, 1, wx.EXPAND | wx.ALL, 10)

        self.normals = []
        self.triangles = []
        self.triangle_count = []
        self._angle = _angle.Angle(_decimal(0.0), _decimal(0.0), _decimal(0.0))
        self._offset = _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
        self._index = -1
        self._models = []
        self.color = None
        self.material = None
        self._pending_index = None
        self._db_obj = None

        self.canvas = GLPreview(self)

        self.x_angle_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', min=0.0, max=359.9, initial=0.0, inc=0.1)
        self.y_angle_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', min=0.0, max=359.9, initial=0.0, inc=0.1)
        self.z_angle_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', min=0.0, max=359.9, initial=0.0, inc=0.1)

        self.x_angle_ctrl.Enable(False)
        self.y_angle_ctrl.Enable(False)
        self.z_angle_ctrl.Enable(False)

        self.x_offset_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', min=0.0, max=999999.9, initial=0.0, inc=0.1)
        self.y_offset_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', min=0.0, max=999999.9, initial=0.0, inc=0.1)
        self.z_offset_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', min=0.0, max=999999.9, initial=0.0, inc=0.1)

        self.x_offset_ctrl.Enable(False)
        self.y_offset_ctrl.Enable(False)
        self.z_offset_ctrl.Enable(False)

        sizer.Add(self.canvas, 2, wx.ALL, 5)

        sizer.Add(utils.HSizer(self, 'X Angle:', self.x_angle_ctrl), 0, wx.LEFT, 10) 
        sizer.Add(utils.HSizer(self, 'Y Angle:', self.y_angle_ctrl), 0, wx.LEFT, 10)
        sizer.Add(utils.HSizer(self, 'Z Angle:', self.z_angle_ctrl), 0, wx.LEFT, 10) 
        
        sizer.Add(utils.HSizer(self, 'X Offset:', self.x_offset_ctrl), 0, wx.LEFT, 10) 
        sizer.Add(utils.HSizer(self, 'Y Offset:', self.y_offset_ctrl), 0, wx.LEFT, 10) 
        sizer.Add(utils.HSizer(self, 'Z Offset:', self.z_offset_ctrl), 0, wx.LEFT, 10)

        self.SetSizer(sizer)

        self.x_angle_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_x_angle)
        self.y_angle_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_y_angle)
        self.z_angle_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_z_angle)

        self.x_offset_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_x_offset)
        self.y_offset_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_y_offset)
        self.z_offset_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_z_offset)

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)

    def on_x_angle(self, evt):
        self._angle.x = _decimal(self.x_angle_ctrl.GetValue())
        self._db_obj.angle = self._angle
        self.canvas.Refresh(False)
        evt.Skip()

    def on_y_angle(self, evt):
        self._angle.y = _decimal(self.y_angle_ctrl.GetValue())
        self._db_obj.angle = self._angle
        self.canvas.Refresh(False)
        evt.Skip()

    def on_z_angle(self, evt):
        self._angle.z = _decimal(self.z_angle_ctrl.GetValue())
        self._db_obj.angle = self._angle
        self.canvas.Refresh(False)
        evt.Skip()

    def on_x_offset(self, evt):
        self._offset.x = _decimal(self.x_offset_ctrl.GetValue())
        self._db_obj.angle = self._angle
        self.canvas.Refresh(False)
        evt.Skip()

    def on_y_offset(self, evt):
        self._offset.y = _decimal(self.y_offset_ctrl.GetValue())
        self._db_obj.offset = self._offset
        self.canvas.Refresh(False)
        evt.Skip()

    def on_z_offset(self, evt):
        self._offset.z = _decimal(self.z_offset_ctrl.GetValue())
        self._db_obj.offset = self._offset
        self.canvas.Refresh(False)
        evt.Skip()

    def on_left_down(self, evt):
        num_models = len(self._models)
        if num_models > 1:
            x, y = evt.GetPosition()
            point = wx.Point(_decimal(x), _decimal(y))

            cw, ch = self.canvas.GetClientSize()
            sel_width = 30 * num_models

            x = (cw - sel_width) / 2
            y = ch - 30

            offset = _point.Point(_decimal(10.0), _decimal(10.0))

            for i in range(num_models):
                x += 15
                p = _point.Point(_decimal(x), _decimal(y))
                x += 15

                if i == self._index:
                    continue

                p1 = p - offset
                p2 = p + offset

                if p1 <= point <= p2:
                    self._pending_index = i
                    break
            else:
                self._pending_index = None

        evt.Skip()

    def on_left_up(self, evt):
        if self._pending_index is not None:
            self._index = self._pending_index
            self._pending_index = None
            self.canvas.Refresh(False)

        evt.Skip()

    def on_paint(self, evt):
        num_models = len(self._models)

        if num_models > 1:
            dc = wx.BufferedPaintDC(self)
            gcdc = wx.GCDC(dc)
            cw, ch = self.canvas.GetClientSize()
            sel_width = 30 * num_models

            x = (cw - sel_width) / 2
            y = ch - 30

            gcdc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255), 2))
            for i in range(num_models):
                x += 15
                if self._index == i:
                    gcdc.SetBrush(wx.Brush(wx.Colour(0, 0, 0, 255)))
                else:
                    gcdc.SetBrush(wx.TRANSPARENT_BRUSH)

                gcdc.DrawCircle(x, y, 10)

                x += 15
        evt.Skip()

    def on_erase_background(self, _):
        pass
