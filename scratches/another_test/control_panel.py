import wx

from wrappers.wrap_decimal import Decimal as _decimal
from geometry import point as _point
from geometry import angle as _angle

from objects import cavity as _cavity
from objects import housing as _housing


class ControlPanel(wx.Panel):

    def __init__(self, parent, size):
        wx.Panel.__init__(self, parent, wx.ID_ANY, size=size)
        self.parent = parent

        sizer = wx.BoxSizer(wx.VERTICAL)

        def _add(label, ctrl):
            h_sizer = wx.BoxSizer(wx.HORIZONTAL)
            st = wx.StaticText(self, wx.ID_ANY, label=label)
            h_sizer.Add(st, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
            h_sizer.Add(ctrl, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
            sizer.Add(h_sizer, 0)

        self.detent_choices = detents = [
            [0, 'OFF'],
            [1, '360.00'],
            [2, '180.00'],
            [3, '120.00'],
            [4, '90.00'],
            [5, '72.00'],
            [6, '60.00'],
            [8, '45.00'],
            [9, '40.00'],
            [10, '36.00'],
            [12, '30.00'],
            [15, '24.00'],
            [16, '22.50'],
            [18, '20.00'],
            [20, '18.00'],
            [24, '15.00'],
            [25, '14.40'],
            [30, '12.00'],
            [32, '11.25'],
            [36, '10.00'],
            [40, '9.00'],
            [45, '8.00'],
            [48, '7.50'],
            [50, '7.20'],
            [60, '6.00'],
            [72, '5.00'],
            [75, '4.80'],
            [80, '4.50'],
            [90, '4.00'],
            [96, '3.75'],
            [100, '3.60']
        ]

        self.detent = 0

        detent_choices = [item[1] for item in self.detent_choices]

        self.angle_detent = wx.Choice(self, wx.ID_ANY, choices=detent_choices)
        self.angle_detent.SetStringSelection('OFF')

        self.angle_x = wx.SpinCtrlDouble(
            self, wx.ID_ANY, size=(100, -1), value="0.0",
            initial=0.0, min=0.0, max=359.9, inc=0.1)

        self.angle_y = wx.SpinCtrlDouble(
            self, wx.ID_ANY, size=(100, -1), value="0.0",
            initial=0.0, min=0.0, max=359.9, inc=0.1)

        self.angle_z = wx.SpinCtrlDouble(
            self, wx.ID_ANY, size=(100, -1), value="0.0",
            initial=0.0, min=0.0, max=359.9, inc=0.1)

        self.rel_angle_x = wx.SpinCtrlDouble(
            self, wx.ID_ANY, size=(100, -1), value="0.0",
            initial=0.0, min=0.0, max=359.9, inc=0.1)

        self.rel_angle_y = wx.SpinCtrlDouble(
            self, wx.ID_ANY, size=(100, -1), value="0.0",
            initial=0.0, min=0.0, max=359.9, inc=0.1)

        self.rel_angle_z = wx.SpinCtrlDouble(
            self, wx.ID_ANY, size=(100, -1), value="0.0",
            initial=0.0, min=0.0, max=359.9, inc=0.1)

        self.pos_x = wx.SpinCtrlDouble(
            self, wx.ID_ANY, size=(100, -1), value="0.0",
            initial=0.0, min=-999.0, max=999.0, inc=0.1)

        self.pos_y = wx.SpinCtrlDouble(
            self, wx.ID_ANY, size=(100, -1), value="0.0",
            initial=0.0, min=-999.0, max=999.0, inc=0.1)

        self.pos_z = wx.SpinCtrlDouble(
            self, wx.ID_ANY, size=(100, -1), value="0.0",
            initial=0.0, min=-999.0, max=999.0, inc=0.1)

        self.rel_pos_x = wx.SpinCtrlDouble(
            self, wx.ID_ANY, size=(100, -1), value="0.0",
            initial=0.0, min=-999.0, max=999.0, inc=0.1)

        self.rel_pos_y = wx.SpinCtrlDouble(
            self, wx.ID_ANY, size=(100, -1), value="0.0",
            initial=0.0, min=-999.0, max=999.0, inc=0.1)

        self.rel_pos_z = wx.SpinCtrlDouble(
            self, wx.ID_ANY, size=(100, -1), value="0.0",
            initial=0.0, min=-999.0, max=999.0, inc=0.1)

        self.length = wx.SpinCtrlDouble(
            self, wx.ID_ANY, size=(100, -1), value="1.0",
            initial=1.0, min=1.0, max=99.0, inc=0.1)

        self.terminal_size = wx.SpinCtrlDouble(
            self, wx.ID_ANY, size=(100, -1), value="1.5",
            initial=1.5, min=0.1, max=99.0, inc=0.1)

        self.use_cylinder = wx.CheckBox(self, wx.ID_ANY, label='')

        _add('Angle Detent:', self.angle_detent)

        _add('X Angle (abs):', self.angle_x)
        _add('Y Angle (abs):', self.angle_y)
        _add('Z Angle (abs):', self.angle_z)
        _add('X Position (abs):', self.pos_x)
        _add('Y Position (abs):', self.pos_y)
        _add('Z Position (abs):', self.pos_z)

        _add('X Angle (rel):', self.rel_angle_x)
        _add('Y Angle (rel):', self.rel_angle_y)
        _add('Z Angle (rel):', self.rel_angle_z)
        _add('X Position (rel):', self.rel_pos_x)
        _add('Y Position (rel):', self.rel_pos_y)
        _add('Z Position (rel):', self.rel_pos_z)

        _add('Cavity Length:', self.length)
        _add('Terminal (blade) Size:', self.terminal_size)
        _add('Cylinder Cavity:', self.use_cylinder)

        self.button = wx.Button(self, wx.ID_ANY,
                                label='Add Cavity', size=(125, -1))

        self.button.Bind(wx.EVT_BUTTON, self.on_button)
        sizer.AddSpacer(1)
        sizer.Add(self.button, 0, wx.ALL, 5)

        self.SetSizer(sizer)

        self.angle_x.Enable(False)
        self.angle_y.Enable(False)
        self.angle_z.Enable(False)

        self.rel_angle_x.Enable(False)
        self.rel_angle_y.Enable(False)
        self.rel_angle_z.Enable(False)

        self.pos_x.Enable(False)
        self.pos_y.Enable(False)
        self.pos_z.Enable(False)

        self.rel_pos_x.Enable(False)
        self.rel_pos_y.Enable(False)
        self.rel_pos_z.Enable(False)

        self.length.Enable(False)
        self.terminal_size.Enable(False)
        self.use_cylinder.Enable(False)

        self.angle_detent.Bind(wx.EVT_CHOICE, self.on_angle_detent)


        self.angle_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_angle_x)
        self.angle_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_angle_y)
        self.angle_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_angle_z)

        self.rel_angle_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rel_angle_x)
        self.rel_angle_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rel_angle_y)
        self.rel_angle_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rel_angle_z)

        self.pos_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_pos_x)
        self.pos_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_pos_y)
        self.pos_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_pos_z)

        self.rel_pos_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rel_pos_x)
        self.rel_pos_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rel_pos_y)
        self.rel_pos_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rel_pos_z)

        self.length.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_length)
        self.terminal_size.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_terminal_size)
        self.use_cylinder.Bind(wx.EVT_CHECKBOX, self.on_use_cylinder)

        self.selected = None

    def on_button(self, evt):
        self.parent.housing.add_cavity()
        evt.Skip()

    def on_angle_detent(self, evt):
        detent = self.angle_detent.GetStringSelection()
        if detent == 'OFF':
            self.detent = 0
        else:
            self.detent = float(detent)
        evt.Skip()

    def on_angle_x(self, evt):
        angle = self.selected.angle
        delta = _decimal(self.angle_x.GetValue()) - angle.x

        angle.unbind(self.on_obj_angle)
        angle.x += delta
        angle.bind(self.on_obj_angle)
        evt.Skip()

        self.GetParent().Refresh(False)

    def on_angle_y(self, evt):
        angle = self.selected.angle
        delta = _decimal(self.angle_y.GetValue()) - angle.y

        angle.unbind(self.on_obj_angle)
        angle.y += delta
        angle.bind(self.on_obj_angle)
        evt.Skip()
        self.GetParent().Refresh(False)

    def on_angle_z(self, evt):
        angle = self.selected.angle
        delta = _decimal(self.angle_z.GetValue()) - angle.z

        angle.unbind(self.on_obj_angle)
        angle.z += delta
        angle.bind(self.on_obj_angle)
        evt.Skip()
        self.GetParent().Refresh(False)

    def on_rel_angle_x(self, evt):
        angle = self.selected.rel_angle
        delta = _decimal(self.rel_angle_x.GetValue()) - angle.x

        angle.unbind(self.on_obj_rel_angle)
        angle.x += delta
        angle.bind(self.on_obj_rel_angle)
        evt.Skip()
        self.GetParent().Refresh(False)

    def on_rel_angle_y(self, evt):
        angle = self.selected.rel_angle
        delta = _decimal(self.rel_angle_y.GetValue()) - angle.y

        angle.unbind(self.on_obj_rel_angle)
        angle.y += delta
        angle.bind(self.on_obj_rel_angle)
        evt.Skip()
        self.GetParent().Refresh(False)

    def on_rel_angle_z(self, evt):
        angle = self.selected.rel_angle
        delta = _decimal(self.rel_angle_z.GetValue()) - angle.z

        angle.unbind(self.on_obj_rel_angle)
        angle.z += delta
        angle.bind(self.on_obj_rel_angle)
        evt.Skip()
        self.GetParent().Refresh(False)

    def on_pos_x(self, evt):
        position = self.selected.position
        delta = _decimal(self.pos_x.GetValue()) - position.x

        position.unbind(self.on_obj_position)
        position.x += delta
        position.bind(self.on_obj_position)

        evt.Skip()
        self.GetParent().Refresh(False)

    def on_pos_y(self, evt):
        position = self.selected.position
        delta = _decimal(self.pos_y.GetValue()) - position.y

        position.unbind(self.on_obj_position)
        position.y += delta
        position.bind(self.on_obj_position)

        evt.Skip()
        self.GetParent().Refresh(False)

    def on_pos_z(self, evt):
        position = self.selected.position
        delta = _decimal(self.pos_z.GetValue()) - position.z

        position.unbind(self.on_obj_position)
        position.z += delta
        position.bind(self.on_obj_position)

        evt.Skip()
        self.GetParent().Refresh(False)

    def on_rel_pos_x(self, evt):
        position = self.selected.rel_position
        delta = _decimal(self.rel_pos_x.GetValue()) - position.x

        position.unbind(self.on_obj_rel_position)
        position.x += delta
        position.bind(self.on_obj_rel_position)

        evt.Skip()
        self.GetParent().Refresh(False)

    def on_rel_pos_y(self, evt):
        position = self.selected.rel_position
        delta = _decimal(self.rel_pos_y.GetValue()) - position.y

        position.unbind(self.on_obj_rel_position)
        position.y += delta
        position.bind(self.on_obj_rel_position)

        evt.Skip()
        self.GetParent().Refresh(False)

    def on_rel_pos_z(self, evt):
        position = self.selected.rel_position
        delta = _decimal(self.rel_pos_z.GetValue()) - position.z

        position.unbind(self.on_obj_rel_position)
        position.z += delta
        position.bind(self.on_obj_rel_position)

        evt.Skip()
        self.GetParent().Refresh(False)

    def on_length(self, evt):
        length = self.length.GetValue()
        self.selected.set_length(length)
        evt.Skip()

    def on_terminal_size(self, evt):
        terminal_size = self.terminal_size.GetValue()
        self.selected.set_terminal_size(terminal_size)
        evt.Skip()
        self.GetParent().Refresh(False)

    def on_use_cylinder(self, evt):
        evt.Skip()
        value = self.use_cylinder.GetValue()
        self.selected.use_cylinder(value)

    def on_obj_angle(self, angle: _angle.Angle):
        x, y, z = angle.as_float
        self.angle_x.SetValue(x)
        self.angle_y.SetValue(y)
        self.angle_z.SetValue(z)

    def on_obj_position(self, point: _point.Point):
        x, y, z = point.as_float
        self.pos_x.SetValue(x)
        self.pos_y.SetValue(y)
        self.pos_z.SetValue(z)

    def on_obj_rel_angle(self, angle: _angle.Angle):
        x, y, z = angle.as_float
        self.rel_angle_x.SetValue(x)
        self.rel_angle_y.SetValue(y)
        self.rel_angle_z.SetValue(z)

    def on_obj_rel_position(self, point: _point.Point):
        x, y, z = point.as_float
        self.rel_pos_x.SetValue(x)
        self.rel_pos_y.SetValue(y)
        self.rel_pos_z.SetValue(z)

    def set_selected(self, obj):
        if obj is None:
            if self.selected is not None:
                self.selected.angle.unbind(self.on_obj_angle)
                self.selected.position.unbind(self.on_obj_position)

                if isinstance(self.selected, _cavity.Cavity):
                    self.selected.rel_angle.unbind(self.on_obj_rel_angle)
                    self.selected.rel_position.unbind(self.on_obj_rel_position)

            self.angle_x.Enable(False)
            self.angle_y.Enable(False)
            self.angle_z.Enable(False)

            self.rel_angle_x.Enable(False)
            self.rel_angle_y.Enable(False)
            self.rel_angle_z.Enable(False)

            self.pos_x.Enable(False)
            self.pos_y.Enable(False)
            self.pos_z.Enable(False)

            self.rel_pos_x.Enable(False)
            self.rel_pos_y.Enable(False)
            self.rel_pos_z.Enable(False)

            self.length.Enable(False)
            self.terminal_size.Enable(False)
            self.use_cylinder.Enable(False)
        else:
            obj.angle.bind(self.on_obj_angle)
            obj.position.bind(self.on_obj_position)

            if isinstance(obj, _cavity.Cavity):
                obj.rel_angle.bind(self.on_obj_rel_angle)
                obj.rel_position.bind(self.on_obj_rel_position)

                self.rel_angle_x.Enable(True)
                self.rel_angle_y.Enable(True)
                self.rel_angle_z.Enable(True)

                self.rel_pos_x.Enable(True)
                self.rel_pos_y.Enable(True)
                self.rel_pos_z.Enable(True)

                x, y, z = obj.rel_angle.as_float

                self.rel_angle_x.SetValue(x)
                self.rel_angle_y.SetValue(y)
                self.rel_angle_z.SetValue(z)

                x, y, z = obj.rel_position.as_float

                self.rel_pos_x.SetValue(x)
                self.rel_pos_y.SetValue(y)
                self.rel_pos_z.SetValue(z)

            self.angle_x.Enable(True)
            self.angle_y.Enable(True)
            self.angle_z.Enable(True)

            self.pos_x.Enable(True)
            self.pos_y.Enable(True)
            self.pos_z.Enable(True)

            x, y, z = obj.angle.as_float

            self.angle_x.SetValue(x)
            self.angle_y.SetValue(y)
            self.angle_z.SetValue(z)

            x, y, z = obj.position.as_float

            self.pos_x.SetValue(x)
            self.pos_y.SetValue(y)
            self.pos_z.SetValue(z)

            if isinstance(obj, _housing.Housing):
                self.length.Enable(False)
                self.terminal_size.Enable(False)
                self.use_cylinder.Enable(False)
            else:
                self.length.Enable(True)
                self.terminal_size.Enable(True)
                self.use_cylinder.Enable(True)
                self.length.SetValue(obj.get_length())
                self.terminal_size.SetValue(obj.get_terminal_size())

        self.selected = obj
