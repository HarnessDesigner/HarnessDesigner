from typing import TYPE_CHECKING

import wx
from wx.lib import scrolledpanel

import numpy as np
from ....geometry import point as _point
from ....geometry import angle as _angle
from .... import utils as _utils
from . import preview
from . import loader as _loader

if TYPE_CHECKING:
    from . import Model3D as _Model3D


class PositioningDialog(wx.Dialog):

    def __init__(self, parent, vertices: np.ndarray,
                 faces: np.ndarray, db_obj: "_Model3D"):

        wx.Dialog.__init__(self, parent, wx.ID_ANY, title='Model Orientation',
                           style=wx.CAPTION | wx.RESIZE_BORDER | wx.CLOSE_BOX | wx.STAY_ON_TOP)

        position = self._position = db_obj.point3d.copy()
        angle = self._angle = db_obj.angle3d.copy()
        scale = self._scale = db_obj.scale.copy()

        self.vertices = vertices
        self.faces = faces

        self.o_vertices = vertices.copy()
        self.o_faces = faces.copy()

        self.triangles: np.ndarray = None
        self.normals: np.ndarray = None
        self.count: int = 0
        self.plane_size = 0

        self.preview = preview.Preview(self)

        sp = scrolledpanel.ScrolledPanel(self, wx.ID_ANY)

        self.smooth = wx.CheckBox(sp, wx.ID_ANY, label='')
        self.smooth.Bind(wx.EVT_CHECKBOX, self.on_smooth)
        smooth_sizer = _utils.HSizer(sp, 'Smoothing:', self.smooth)

        simplify_model = wx.StaticBox(sp, wx.ID_ANY, 'Simplify Model')
        enabled = db_obj.simplify

        self.simplify = wx.CheckBox(simplify_model, wx.ID_ANY, label='')
        self.simplify.SetValue(enabled)

        self.simplify.Bind(wx.EVT_CHECKBOX, self.on_simplify)

        simplify_sizer = _utils.HSizer(
            simplify_model, 'Enable:', self.simplify
        )

        self.vertex_count = wx.StaticText(
            simplify_model, wx.ID_ANY, label='0000000000')

        vertex_count_sizer = _utils.HSizer(
            simplify_model, 'Vertex Count:', self.vertex_count)

        self.faces_count = wx.StaticText(
            simplify_model, wx.ID_ANY, label='0000000000')

        faces_count_sizer = _utils.HSizer(
            simplify_model, 'Faces Count:', self.faces_count)

        self.target_vertices = wx.TextCtrl(
            simplify_model, wx.ID_ANY, value='0000000000')

        self.target_vertices.Enable(enabled)

        target_vertices_sizer = _utils.HSizer(
            simplify_model, 'Target Vertex Count:', self.target_vertices)

        self.aggressiveness = wx.SpinCtrlDouble(
            simplify_model, wx.ID_ANY, value="7.0", min=0.1, max=10.0, inc=0.1, initial=7.0)

        self.aggressiveness.Enable(enabled)

        aggressiveness_sizer = _utils.HSizer(
            simplify_model, 'Aggressiveness:', self.aggressiveness)

        self.update_rate = wx.SpinCtrl(
            simplify_model, wx.ID_ANY, value="1", min=1, max=300, initial=1)

        self.update_rate.Enable(enabled)

        update_rate_sizer = _utils.HSizer(
            simplify_model, 'Update Rate:', self.update_rate)

        self.iterations = wx.SpinCtrl(
            simplify_model, wx.ID_ANY, value="150", min=1, max=150, initial=150)

        self.iterations.Enable(enabled)

        iterations_sizer = _utils.HSizer(
            simplify_model, 'Iterations:', self.iterations)

        self.simplify_model_button = wx.Button(
            simplify_model, wx.ID_ANY, label='Simplify')

        self.simplify_model_button.Enable(enabled)

        self.reset_model_button = wx.Button(
            simplify_model, wx.ID_ANY, label='Reset')

        self.reset_model_button.Enable(enabled)

        self.simplify_model_button.Bind(wx.EVT_BUTTON, self.on_simplify_model)
        self.reset_model_button.Bind(wx.EVT_BUTTON, self.on_reset_model)

        counts_sizer = wx.BoxSizer(wx.VERTICAL)
        counts_sizer.Add(vertex_count_sizer, 0, wx.BOTTOM, 3)
        counts_sizer.Add(faces_count_sizer, 0, wx.TOP, 3)

        simplify_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        simplify_button_sizer.AddStretchSpacer(2)

        simplify_button_sizer.Add(
            self.reset_model_button, 1, wx.RIGHT | wx.EXPAND, 10)

        simplify_button_sizer.Add(
            self.simplify_model_button, 1, wx.LEFT | wx.EXPAND, 10)

        simplify_model_sizer = wx.BoxSizer(wx.VERTICAL)

        simplify_model_sizer.Add(counts_sizer, 0, wx.BOTTOM | wx.EXPAND, 15)

        simplify_model_sizer.Add(
            simplify_sizer, 0, wx.BOTTOM | wx.EXPAND, 7)

        simplify_model_sizer.Add(
            target_vertices_sizer, 0, wx.BOTTOM | wx.TOP | wx.EXPAND, 3)

        simplify_model_sizer.Add(
            aggressiveness_sizer, 0, wx.BOTTOM | wx.TOP | wx.EXPAND, 3)

        simplify_model_sizer.Add(
            update_rate_sizer, 0, wx.BOTTOM | wx.TOP | wx.EXPAND, 3)

        simplify_model_sizer.Add(
            iterations_sizer, 0, wx.TOP | wx.EXPAND, 3)

        simplify_model_sizer.Add(
            simplify_model_sizer, 0, wx.TOP | wx.EXPAND, 15)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(simplify_model_sizer, 0, wx.EXPAND | wx.ALL, 5)

        simplify_model.SetSizer(hsizer)

        ang_box = wx.StaticBox(sp, wx.ID_ANY, 'Angle')
        x, y, z = [round(item, 6) for item in [angle.x, angle.y, angle.z]]

        self.x_angle = wx.SpinCtrlDouble(
            ang_box, wx.ID_ANY, value=str(x), min=-180.0, max=180.0, inc=0.000001, initial=x)
        self.x_angle.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_x_angle)
        x_sizer = _utils.HSizer(ang_box, 'X:', self.x_angle)

        self.y_angle = wx.SpinCtrlDouble(
            ang_box, wx.ID_ANY, value=str(y), min=-180.0, max=180.0, inc=0.000001, initial=y)
        self.y_angle.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_y_angle)
        y_sizer = _utils.HSizer(ang_box, 'Y:', self.y_angle)

        self.z_angle = wx.SpinCtrlDouble(
            ang_box, wx.ID_ANY, value=str(z), min=-180.0, max=180.0, inc=0.000001, initial=z)
        self.z_angle.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_z_angle)
        z_sizer = _utils.HSizer(ang_box, 'Z:', self.z_angle)

        self.angle_reset = wx.Button(ang_box, wx.ID_ANY, 'Reset Angle')
        self.angle_reset.Bind(wx.EVT_BUTTON, self.on_angle_reset)

        angle_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        angle_button_sizer.AddStretchSpacer(1)
        angle_button_sizer.Add(self.angle_reset, 3)

        angle_sizer = wx.BoxSizer(wx.VERTICAL)
        angle_sizer.Add(x_sizer, 0, wx.BOTTOM, 5)
        angle_sizer.Add(y_sizer, 0, wx.TOP | wx.BOTTOM, 5)
        angle_sizer.Add(z_sizer, 0, wx.TOP, 5)
        angle_sizer.Add(angle_button_sizer, 0, wx.TOP, 15)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(angle_sizer, 0, wx.EXPAND | wx.ALL, 10)
        ang_box.SetSizer(hsizer)

        pos_box = wx.StaticBox(sp, wx.ID_ANY, 'Position')
        x, y, z = [round(item, 6) for item in position.as_float]

        self.x_pos = wx.SpinCtrlDouble(
            pos_box, wx.ID_ANY, value=str(x), min=-500.0, max=500.0, inc=0.01, initial=x)
        self.x_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_x_pos)
        x_sizer = _utils.HSizer(pos_box, 'X:', self.x_pos)

        self.y_pos = wx.SpinCtrlDouble(
            pos_box, wx.ID_ANY, value=str(y), min=-500.0, max=500.0, inc=0.01, initial=y)
        self.y_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_y_pos)
        y_sizer = _utils.HSizer(pos_box, 'Y:', self.y_pos)

        self.z_pos = wx.SpinCtrlDouble(
            pos_box, wx.ID_ANY, value=str(z), min=-500.0, max=500.0, inc=0.01, initial=z)
        self.z_pos.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_z_pos)
        z_sizer = _utils.HSizer(pos_box, 'Z:', self.z_pos)

        self.position_center = wx.Button(pos_box, wx.ID_ANY, 'Center Position')
        self.position_center.Bind(wx.EVT_BUTTON, self.on_position_center)

        self.position_reset = wx.Button(pos_box, wx.ID_ANY, 'Reset Position')
        self.position_reset.Bind(wx.EVT_BUTTON, self.on_position_reset)

        position_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        position_button_sizer.AddStretchSpacer(1)
        position_button_sizer.Add(self.position_reset, 3)
        position_button_sizer.Add(self.position_center, 3)

        position_sizer = wx.BoxSizer(wx.VERTICAL)
        position_sizer.Add(x_sizer, 0, wx.BOTTOM, 5)
        position_sizer.Add(y_sizer, 0, wx.TOP | wx.BOTTOM, 5)
        position_sizer.Add(z_sizer, 0, wx.TOP, 5)
        position_sizer.Add(position_button_sizer, 0, wx.TOP, 15)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(position_sizer, 0, wx.EXPAND | wx.ALL, 10)
        pos_box.SetSizer(hsizer)

        scale_box = wx.StaticBox(sp, wx.ID_ANY, 'Scale')
        x, y, z = [round(item, 2) for item in scale.as_float]

        self.x_scale = wx.SpinCtrlDouble(
            scale_box, wx.ID_ANY, value=str(x), min=0.05, max=500.0, inc=0.05, initial=x)
        self.x_scale.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_x_scale)
        x_sizer = _utils.HSizer(scale_box, 'X:', self.x_scale)

        self.y_scale = wx.SpinCtrlDouble(
            scale_box, wx.ID_ANY, value=str(y), min=0.05, max=500.0, inc=0.05, initial=y)
        self.y_scale.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_y_scale)
        y_sizer = _utils.HSizer(scale_box, 'Y:', self.y_scale)

        self.z_scale = wx.SpinCtrlDouble(
            scale_box, wx.ID_ANY, value=str(z), min=0.05, max=500.0, inc=0.05, initial=z)
        self.z_scale.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_z_scale)
        z_sizer = _utils.HSizer(scale_box, 'Z:', self.z_scale)

        self.scale_reset = wx.Button(scale_box, wx.ID_ANY, 'Reset Scale')
        self.scale_reset.Bind(wx.EVT_BUTTON, self.on_scale_reset)

        scale_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        scale_button_sizer.AddStretchSpacer(4)
        scale_button_sizer.Add(self.scale_reset, 1)

        scale_sizer = wx.BoxSizer(wx.VERTICAL)
        scale_sizer.Add(x_sizer, 0, wx.BOTTOM, 5)
        scale_sizer.Add(y_sizer, 0, wx.TOP | wx.BOTTOM, 5)
        scale_sizer.Add(z_sizer, 0, wx.TOP, 5)
        scale_sizer.Add(scale_button_sizer, 0, wx.TOP, 15)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(scale_sizer, 0, wx.EXPAND | wx.ALL, 10)
        scale_box.SetSizer(hsizer)

        column1_sizer = wx.BoxSizer(wx.VERTICAL)
        column1_sizer.Add(self.preview, 0, wx.EXPAND)

        column2_sizer = wx.BoxSizer(wx.VERTICAL)
        column2_sizer.Add(smooth_sizer, 0, wx.EXPAND | wx.BOTTOM, 15)

        column2_sizer.Add(pos_box, 0, wx.EXPAND | wx.BOTTOM | wx.TOP, 5)
        column2_sizer.Add(ang_box, 0, wx.EXPAND | wx.BOTTOM | wx.TOP, 5)
        column2_sizer.Add(scale_box, 0, wx.EXPAND | wx.BOTTOM | wx.TOP, 5)
        column2_sizer.Add(simplify_model, 0, wx.EXPAND | wx.TOP, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(column2_sizer, 0, wx.ALL | wx.EXPAND, 5)

        sp.SetSizer(hsizer)

        column2_sizer = wx.BoxSizer(wx.VERTICAL)
        column2_sizer.Add(sp, 0, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(column1_sizer, 0, wx.ALL | wx.EXPAND, 10)
        hsizer.Add(column2_sizer, 0, wx.ALL | wx.EXPAND, 10)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(hsizer, 0, wx.EXPAND)

        button_sizer = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        vsizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(vsizer)

        wx.CallAfter(self.set_counts)

    def set_counts(self):
        self.faces_count.SetLabel(str(len(self.faces)))
        self.vertex_count.SetLabel(str(len(self.vertices)))

    def on_simplify(self, evt):
        enabled = self.simplify.GetValue()

        self.target_vertices.Enable(enabled)
        self.aggressiveness.Enable(enabled)
        self.update_rate.Enable(enabled)
        self.iterations.Enable(enabled)
        self.simplify_model_button.Enable(enabled)
        self.reset_model_button.Enable(enabled)

        evt.Skip()

    def _set_angle(self, x=None, y=None, z=None):
        if x is not None:
            self._angle.x = x
        if y is None:
            self._angle.y = y
        if z is None:
            self._angle.z = z

        self.update_model(self.vertices, self.faces)

    def on_x_angle(self, evt):
        self._set_angle(x=self.x_angle.GetValue())
        evt.Skip()

    def on_y_angle(self, evt):
        self._set_angle(y=self.y_angle.GetValue())
        evt.Skip()

    def on_z_angle(self, evt):
        self._set_angle(z=self.z_angle.GetValue())
        evt.Skip()

    def on_angle_reset(self, evt):
        self._angle.x = 0.0
        self._angle.y = 0.0
        self._angle.z = 0.0

        self.update_model(self.vertices, self.faces)
        evt.Skip()

    def on_position_reset(self, evt):
        self._set_position(0.0, 0.0, 0.0)
        evt.skip()

    def _set_position(self, x=None, y=None, z=None):
        if x is None:
            x = 0.0
        else:
            x -= self._position.x
        if y is None:
            y = 0.0
        else:
            y -= self._position.y

        if z is None:
            z = 0.0
        else:
            z -= self._position.z

        diff = _point.Point(x, y, z)

        self._position += diff
        self.x_pos.SetValue(self._position.x)
        self.y_pos.SetValue(self._position.y)
        self.z_pos.SetValue(self._position.z)

        for i, (tris, nrmls, count) in enumerate(self.triangles):
            tris += diff
            self.triangles[i] = [tris, nrmls, count]

        self.preview.set_model(self.triangles,  self.plane_size)

    def GetValues(self) -> tuple[bool, float, float, int, int, _point.Point, _angle.Angle, _point.Point]:
        return (
            self.simplify.GetValue(),
            self.target_vertices.GetValue(),
            self.aggressiveness.GetValue(),
            self.update_rate.GetValue(),
            self.iterations.GetValue(),
            self._position,
            self._angle,
            self._scale
        )

    def on_x_pos(self, evt):
        value = self.x_pos.GetValue()
        self._set_position(x=value)
        evt.Skip()

    def on_y_pos(self, evt):
        value = self.y_pos.GetValue()
        self._set_position(y=value)
        evt.Skip()

    def on_z_pos(self, evt):
        value = self.z_pos.GetValue()
        self._set_position(z=value)
        evt.Skip()

    def on_position_center(self, evt):
        p1, p2 = _utils.compute_aabb(*self.triangles)

        center = ((p2 - p1) / 2.0)

        x, y, z = [round(item, 6) for item in center.as_float]

        self._set_position(x, y, z)
        evt.Skip()

    def _set_scale(self, x=None, y=None, z=None):
        if x is not None:
            self._scale.x = x
        if y is not None:
            self._scale.y = y
        if z is not None:
            self._scale.z = z

        self.update_model(self.vertices, self.faces)

    def on_scale_reset(self, evt):
        self._set_scale(x=1.0, y=1.0, z=1.0)
        evt.skip()

    def on_x_scale(self, evt):
        value = self.x_scale.GetValue()
        self._set_scale(x=value)
        evt.Skip()

    def on_y_scale(self, evt):
        value = self.y_scale.GetValue()
        self._set_scale(y=value)
        evt.Skip()

    def on_z_scale(self, evt):
        value = self.z_scale.GetValue()
        self._set_scale(z=value)
        evt.Skip()

    def on_simplify_model(self, evt):
        target_vertices = self.target_vertices.GetValue()
        aggressiveness = self.aggressiveness.GetValue()
        update_rate = self.update_rate.GetValue()
        iterations = self.iterations.GetValue()

        wx.BeginBusyCursor()

        vertices, faces = _loader.reduce_triangles(
            self.o_vertices, self.o_faces, target_vertices,
            aggressiveness, update_rate, iterations)

        wx.EndBusyCursor()

        self.update_model(vertices, faces)
        evt.Skip()

    def on_smooth(self, evt):
        self.update_model(self.vertices, self.faces)
        evt.Skip()

    def update_model(self, vertices, faces):
        self.vertices = vertices
        self.faces = faces

        self.set_counts()

        if self.smooth.GetValue():
            tris, nrmls, count = (
                _utils.compute_smoothed_vertex_normals(vertices, faces))

        else:
            tris, nrmls, count = (
                _utils.compute_vertex_normals(vertices, faces))

        tris *= self._scale
        tris @= self._angle
        nrmls @= self._angle
        tris += self._position

        triangles = [tris, nrmls, count]

        self.plane_size = self._compute_plane_size(triangles)
        self.triangles = triangles
        self.preview.set_model(triangles,  self.plane_size)

    def on_reset_model(self, evt):
        self.update_model(self.o_vertices.copy(), self.o_faces.copy())
        evt.Skip()

    @staticmethod
    def _compute_plane_size(triangles: list[np.ndarray, np.ndarray, int]) -> float:
        p1, p2 = _utils.compute_aabb(triangles[0])
        diff = p2 - p1

        size = max([abs(item) for item in diff.as_float])
        return size * 1.5


# ShowWindowModal
