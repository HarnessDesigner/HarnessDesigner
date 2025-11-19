
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
from .. import gl_materials
from ..database.global_db import model3d as _model3d
from ..wrappers import color as _color
from .. import utils


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
    def __init__(self, parent):
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
        
        self.normals = None
        self.triangles = None
        self.triangle_count = None
        self.material = None
        self.color = None

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

    def _on_erase_background(self, _):
        pass
    
    def set_model(self, normals, triangles, triangle_count, material, color):
        self.normals = normals
        self.triangles = triangles
        self.triangle_count = triangle_count
        self.material = material
        self.color = color 

    def _on_paint(self, _):
        _ = wx.PaintDC(self)
        self.SetCurrent(self.context)

        if not self.init:
            self.renderer.init()
            self.init = True

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

                self.renderer.add_to_view_angle(new_x, new_y)
                self.last_left_x, self.last_left_y = x, y
                self.update_objects = False
                self.Refresh(False)

            elif event.RightIsDown():
                new_x = self.last_right_x - x
                new_y = self.last_right_y - y

                self.renderer.set_pan(new_x, new_y)
                self.last_right_x, self.last_right_y = x, y
                self.update_objects = False
                self.Refresh(False)

    def _on_mouse_wheel(self, event: wx.MouseEvent):
        scale = event.GetWheelRotation() / 20000
        scale = self.renderer.add_to_scale(scale, scale, scale)

        if scale < 0.001:
            scale = 0.001 - scale
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
    
    
    def set_db_object(self, db_obj: _model3d.Model3D, color: _color.Color, material: gl_materials.GLMaterial):
        self._angle = db_obj.angle
        self._offset = db_obj.offset
        self._index = db_obj.index
        self._models = db_obj.all_model_data
        self._color = color
        self._material = material
        
        self.x_angle_ctrl.Enable(True)
        self.y_angle_ctrl.Enable(True)
        self.z_angle_ctrl.Enable(True)

        self.x_offset_ctrl.Enable(True)
        self.y_offset_ctrl.Enable(True)
        self.z_offset_ctrl.Enable(True)

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sl = wx.StaticLine(self, wx.ID_ANY, size=(5, 5))
        sizer.Add(sl, 1, wx.EXPAND | wx.ALL, 10)
        
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

        sizer.Add(utils.HSizer(self, 'X Angle:', self.x_angle_ctrl), 0, wx.LEFT, 10) 
        sizer.Add(utils.HSizer(self, 'Y Angle:', self.y_angle_ctrl), 0, wx.LEFT, 10)
        sizer.Add(utils.HSizer(self, 'Z Angle:', self.z_angle_ctrl), 0, wx.LEFT, 10) 
        
        sizer.Add(utils.HSizer(self, 'X Offset:', self.x_offset_ctrl), 0, wx.LEFT, 10) 
        sizer.Add(utils.HSizer(self, 'Y Offset:', self.y_offset_ctrl), 0, wx.LEFT, 10) 
        sizer.Add(utils.HSizer(self, 'Z Offset:', self.z_offset_ctrl), 0, wx.LEFT, 10)

        if db_obj is None:
            
        else:
            

            if self._models:
                
            