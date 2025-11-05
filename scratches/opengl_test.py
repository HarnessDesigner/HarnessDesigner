
from typing import Union

import wx

import numpy as np  # NOQA
from typing import Iterable as _Iterable  # NOQA
import math  # NOQA
import weakref  # NOQA
from decimal import Decimal as _Decimal  # NOQA
from scipy.spatial.transform import Rotation  # NOQA
import wx.lib.newevent  # NOQA


wxEVT_COMMAND_ARTIST_SET_SELECTED = wx.NewEventType()
wxEVT_COMMAND_ARTIST_UNSET_SELECTED = wx.NewEventType()

EVT_ARTIST_SET_SELECTED = wx.PyEventBinder(wxEVT_COMMAND_ARTIST_SET_SELECTED, 1)
EVT_ARTIST_UNSET_SELECTED = wx.PyEventBinder(wxEVT_COMMAND_ARTIST_UNSET_SELECTED, 1)

# ----------------------------------------------------------------------

cx_factor = 30.0 / 200.0
cy_factor = 62.0 / 200.0
w_factor = 24.0 / 200.0
h_factor = 21.0 / 200.0


class ArtistEvent(wx.PyCommandEvent):

    def __init__(self, command_type, win_id):
        if isinstance(command_type, int):
            wx.PyCommandEvent.__init__(self, command_type, win_id)
        else:
            wx.PyCommandEvent.__init__(self, command_type.GetEventType(), command_type.GetId())

        self.is_dropdown_clicked = False
        self.click_pt = wx.Point(-1, -1)
        self.rect = wx.Rect(-1, -1, 0, 0)
        self.tool_id = -1
        self._artist = None
        self._pos_3d = None
        self._pos = None
        self._m_event = None

    def SetMatplotlibEvent(self, event):
        self._m_event = event

    def GetMatplotlibEvent(self):
        return self._m_event

    def SetPosition(self, pos: wx.Point):
        self._pos = pos

    def GetPosition(self) -> wx.Point:
        return self._pos

    def GetPosition3D(self) -> "Point":
        return self._pos_3d

    def SetPosition3D(self, pos_3d: "Point"):
        self._pos_3d = pos_3d

    def SetArtist(self, artist: Union["Transition"]):
        self._artist = artist

    def GetArtist(self) -> Union["Transition"]:
        return self._artist


# monkey patch the _on_move method for Axes3D
# this is done to change the handling of the right mouse button.
# the right mouse button pans the plot instead of zooming.
# The mouse wheel is used to zoom instead (as it should be)
def _on_move(self, event):
    if not self.button_pressed or event.key:
        return

    if self.get_navigate_mode() is not None:
        return

    if self.M is None:
        return

    x, y = event.xdata, event.ydata

    if x is None or event.inaxes != self:
        return

    dx, dy = x - self._sx, y - self._sy
    w = self._pseudo_w
    h = self._pseudo_h

    if self.button_pressed in self._rotate_btn:
        if dx == 0 and dy == 0:
            return

        style = matplotlib.rcParams['axes3d.mouserotationstyle']
        if style == 'azel':
            roll = np.deg2rad(self.roll)

            delev = (-(dy / h) * 180 * np.cos(roll) +
                     (dx / w) * 180 * np.sin(roll))

            dazim = (-(dy / h) * 180 * np.sin(roll) -
                     (dx / w) * 180 * np.cos(roll))

            elev = self.elev + delev
            azim = self.azim + dazim
            roll = self.roll
        else:
            q = _Quaternion.from_cardan_angles(
                *np.deg2rad((self.elev, self.azim, self.roll)))

            if style == 'trackball':
                k = np.array([0, -dy / h, dx / w])
                nk = np.linalg.norm(k)
                th = nk / matplotlib.rcParams['axes3d.trackballsize']
                dq = _Quaternion(np.cos(th), k * np.sin(th) / nk)
            else:  # 'sphere', 'arcball'
                current_vec = self._arcball(self._sx / w, self._sy / h)
                new_vec = self._arcball(x / w, y / h)
                if style == 'sphere':
                    dq = _Quaternion.rotate_from_to(current_vec, new_vec)
                else:  # 'arcball'
                    dq = (_Quaternion(0, new_vec) *
                          _Quaternion(0, -current_vec))

            q = dq * q
            elev, azim, roll = np.rad2deg(q.as_cardan_angles())

        vertical_axis = self._axis_names[self._vertical_axis]

        self.view_init(elev=elev, azim=azim, roll=roll,
                       vertical_axis=vertical_axis, share=True)

        self.stale = True

    elif self.button_pressed in self._zoom_btn:
        px, py = self.transData.transform([self._sx, self._sy])
        self.start_pan(px, py, 2)
        self.drag_pan(2, None, event.x, event.y)
        self.end_pan()

    self._sx, self._sy = x, y
    self.get_figure(root=True).canvas.draw_idle()


setattr(axes3d.Axes3D, '_on_move', _on_move)


def floor_tens(value):
    return _decimal(float(int(value * _decimal(10))) / 10.0)


def remap(value, old_min, old_max, new_min, new_max):
    old_range = old_max - old_min
    new_range = new_max - new_min
    new_value = (((value - old_min) * new_range) / old_range) + new_min
    return new_value


class Bundle:
    def __init__(self, id, mainframe, editor, axes, diameter, color, branches):
        self.id = id
        self.axes = axes
        self.editor = editor
        self.mainframe = mainframe
        self.wxid = wx.NewIdRef()

        self.diameter = _decimal(diameter)
        self.color = color

        self.transition1, self.branch1 = branches[0]
        self.transition2, self.branch2 = branches[1]

        print('start p1:', self.branch1['cylinder'].p1)
        print('start p2:', self.branch1['cylinder'].p2)
        print('stop p1:', self.branch2['cylinder'].p1)
        print('stop p2:', self.branch2['cylinder'].p2)

        '''
        start p1: X: -56.7, Y: 162.6, Z: -78.1
        start p2: X: -40.7, Y: 169.3, Z: -78.1
        
        stop p1: X: -53.1, Y: 139.5, Z: -149.2
        stop p2: X: -37.1, Y: 146.2, Z: -149.2
        
        
        P1: X: 18.1, Y: 70.6, Z: -25.9
        
        P2: X: 162.5, Y: 70.6, Z: -25.9
        
        '''

        p1 = self.branch1['cylinder'].p2
        p2 = self.branch2['cylinder'].p2

        self.branch1['set_dia'] = _decimal(diameter)
        self.branch2['set_dia'] = _decimal(diameter)

        self.branch1['cylinder'].diameter = _decimal(diameter)
        self.branch2['cylinder'].diameter = _decimal(diameter)

        self.branch1['hemisphere'].hole_diameter = _decimal(diameter)
        self.branch2['hemisphere'].hole_diameter = _decimal(diameter)

        cyl = self.cyl = Cylinder(p1, None, diameter, color, None, p2)

        print('cylp1:', cyl.p1)
        print('cylp2:', cyl.p2)

        cyl.add_to_plot(axes)

        print('cylp1:', cyl.p1)
        print('cylp2:', cyl.p2)

        self._selected = False

    def on_motion(self, evt):
        pass


class Transition:
    def __init__(self, id, mainframe, editor, axes, location, data):
        self.id = id
        self.axes = axes
        self.editor = editor
        self.mainframe = mainframe
        self.data = data
        self.wxid = wx.NewIdRef()
        self.objs = []
        self._selected = False
        self._coord_adj = None
        self._last_mouse_pos = None
        self._branch_mode = False

        self.branches = []

        origin = Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
        bulb_offset_apex = None

        for i, (min_dia, max_dia, length, bulb_length, bulb_offset, angle, offset) in enumerate(data):

            if bulb_length:
                if bulb_offset_apex is not None:
                    cyl_1_p1 = Point(bulb_offset_apex - (max_dia * _decimal(0.75)), _decimal(0.0), _decimal(0.0))
                    factor = bulb_length / length
                    b_length = length - bulb_offset_apex + (max_dia / _decimal(2.0)) * factor
                else:
                    cyl_1_p1 = bulb_offset
                    b_length = bulb_length

                cyl1 = Cylinder(cyl_1_p1, b_length - (max_dia / _decimal(2.0)), max_dia, (0.2, 0.2, 0.2, 1.0), None)
                self.objs.append(cyl1)

                if bulb_offset.x or bulb_offset.y:
                    h_sphere1 = Hemisphere(cyl1.p1, max_dia, (0.2, 0.2, 0.2, 1.0), _decimal(0.0))
                    h_sphere1.set_y_angle(_decimal(90.0), h_sphere1.center)
                    self.objs.append(h_sphere1)

                if i == 0:
                    cyl1.set_z_angle(angle, cyl1.p1)
                else:
                    cyl1.set_z_angle(angle, origin)

                h_sphere2 = Hemisphere(cyl1.p2, max_dia, (0.2, 0.2, 0.2, 1.0), min_dia)
                h_sphere2.set_y_angle(_decimal(90.0), h_sphere2.center)
                h_sphere2.set_z_angle(angle, h_sphere2.center)

                self.objs.append(h_sphere2)

                cyl2 = Cylinder(h_sphere2.hole_center, length - bulb_length + (max_dia / _decimal(2.0)), min_dia, (0.2, 0.2, 0.2, 1.0), None)

                cyl2.set_z_angle(angle, cyl2.p1)
                self.objs.append(cyl2)

                if bulb_offset.x or bulb_offset.y:
                    apex = h_sphere1.center.copy() + Point(h_sphere1.diameter / _decimal(2.0), _decimal(0.0), _decimal(0.0))

                    # bulb_offset.x -= max_dia / _decimal(2.0)
                    # bulb_length -= max_dia / _decimal(2.0)
                    bulb_offset_apex = apex.x

                self.branches.append(dict(id=i+1, cylinder=cyl2, min_dia=min_dia,
                                          max_dia=max_dia, set_dia=min_dia,
                                          hemisphere=h_sphere2, is_connected=False))

        points = []
        for obj in self.objs:
            obj.add_to_plot(self.axes)
            obj.set_py_data(self)

        for obj in self.objs:
            if isinstance(obj, Cylinder):
                if obj.p1 not in points:
                    obj.p1 += location
                    points.append(obj.p1)
                if obj.p2 not in points:
                    obj.p2 += location
                    points.append(obj.p2)
            else:
                if obj.center not in points:
                    obj.center += location
                    points.append(obj.center)

        self.origin = location


class Editor(wx.Frame):

    def __init__(self, size):
        super().__init__(None, wx.ID_ANY, size=size)

        v_sizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.fig = matplotlib.pyplot.figure(figsize=(3.5, 3.5))
        ax = self.axes = axes3d.Axes3D(self.fig, [-0.80, -0.95, 2.8, 2.8], box_aspect=(1, 1, 1))

        self.fig.add_axes(ax)
        # ax.autoscale(True)

        ax.set_xlim(-50, 50)
        ax.set_ylim(-50, 50)
        ax.set_zlim(-50, 50)

        # get_tightbbox
        ax.set_adjustable('datalim')
        ax.set_aspect('equal', 'box')

        panel = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_NONE)

        self.canvas = Canvas(self, panel, wx.ID_ANY, self.fig, self.axes)

        self.canvas.SetPosition((0, 0))
        self.canvas.SetSize((500, 500))

        inlay = self.inlay = AxisIndicator(self.fig, [0.88, 0.02, 0.10, 0.10])
        ax.shareview(inlay)
        self.fig.add_axes(inlay)

        x_label = wx.StaticText(self, wx.ID_ANY, label='X Axis:')
        self.x_slider = wx.Slider(self, wx.ID_ANY, maxValue=359)
        y_label = wx.StaticText(self, wx.ID_ANY, label='Y Axis:')
        self.y_slider = wx.Slider(self, wx.ID_ANY, maxValue=359)
        z_label = wx.StaticText(self, wx.ID_ANY, label='Z Axis:')
        self.z_slider = wx.Slider(self, wx.ID_ANY, maxValue=359)

        hsizer.Add(panel, 1, wx.EXPAND | wx.ALL, 5)
        v_sizer.Add(hsizer, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(x_label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)
        hsizer.Add(self.x_slider, 0, wx.RIGHT | wx.EXPAND, 10)
        v_sizer.Add(hsizer, 0, wx.TOP, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(y_label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)
        hsizer.Add(self.y_slider, 0, wx.RIGHT | wx.EXPAND, 10)
        v_sizer.Add(hsizer, 0, wx.TOP, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(z_label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)
        hsizer.Add(self.z_slider, 0, wx.RIGHT | wx.EXPAND, 10)
        v_sizer.Add(hsizer, 0, wx.BOTTOM | wx.TOP, 10)

        self.SetSizer(v_sizer)

        def panel_on_size(evt):
            w, h = evt.GetSize()
            self.canvas.SetSize((w, h))
            size_ = max(w, h)
            axes_off_x = remap(size_, 474, 2333, -1.1, -1.60)
            axes_off_y = remap(size_, 474, 2333, -1.1, -1.4)
            axes_size = remap(size_, 474, 2333, 3.2, 4.20)
            self.axes.set_position([axes_off_x, axes_off_y, axes_size, axes_size])

            # xmin, xmax = self.axes.get_xlim3d()
            # ymin, ymax = self.axes.get_ylim3d()
            # zmin, zmax = self.axes.get_zlim3d()
            #
            # maxlim = max(xmax, ymax, zmax)
            # minlim = min(xmin, ymin, xmin)
            #
            # ax.set_xlim3d(minlim, maxlim)
            # ax.set_ylim3d(minlim, maxlim)
            # ax.set_zlim3d(minlim, maxlim)

            self.fig.canvas.draw_idle()

            evt.Skip()

        panel.Bind(wx.EVT_SIZE, panel_on_size)
        panel.Bind(wx.EVT_MOTION, self._on_motion)
        panel.Bind(wx.EVT_LEFT_DOWN, self._on_left_down)
        panel.Bind(wx.EVT_LEFT_UP, self._on_left_up)
        # panel.Bind(wx.EVT_LEFT_DCLICK, self._on_left_dclick)
        panel.Bind(wx.EVT_RIGHT_DOWN, self._on_right_down)
        panel.Bind(wx.EVT_RIGHT_UP, self._on_right_up)
        # panel.Bind(wx.EVT_RIGHT_DCLICK, self._on_right_dclick)
        # panel.Bind(wx.EVT_MOUSEWHEEL, self._on_mouse_wheel)
        panel.Bind(wx.EVT_KEY_UP, self._on_key_up)
        panel.Bind(wx.EVT_KEY_DOWN, self._on_key_down)

        self.Bind(wx.EVT_MENU, self.on_add_bundle, id=self.ID_ADD_BUNDLE)
        self.Bind(wx.EVT_MENU, self.on_add_transition, id=self.ID_ADD_TRANSITION)

        self.transitions = []
        self.bundles = []
        self._selected = None
        self._mouse_click_location = None
        self.bundle_dialog = None
        self._right_motion = None
        self.canvas.draw()

    def on_add_bundle(self, evt):
        evt.Skip()

        if self.bundle_dialog is not None:
            self.bundle_dialog.Show()
            self.bundle_dialog.Iconize()
            self.bundle_dialog.Restore()
            self.bundle_dialog.SetFocusFromKbd()
            self.bundle_dialog.CenterOnParent()

        self.bundle_dialog = AddBundleDialog(self, self)
        self.bundle_dialog.CenterOnParent()
        self.bundle_dialog.Show()

    def on_add_transition(self, evt):
        evt.Skip()
        dlg = AddTransitionDialog(self)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return

        branches = dlg.GetValues()
        dlg.Destroy()

        transition = Transition(len(self.transitions) + 1, self, self, self.axes, self._mouse_click_location, branches)
        self.transitions.append(transition)

    def SetSelected(self, obj, flag):
        if not flag and self._selected == obj:
            self._selected.IsSelected(False)
            self._selected = None
        elif flag and self._selected is not None and self._selected != obj:
            self._selected.IsSelected(False)
            self._selected = obj
            self._selected.IsSelected(True)
        elif flag and self._selected is None:
            self._selected = obj
            self._selected.IsSelected(True)
        else:
            raise RuntimeError('sanity check')

    def _on_motion(self, evt: PlotMouseEvent):
        if evt.RightIsDown():
            self._right_motion = True

        evt.Skip()

    def _on_left_down(self, evt: PlotMouseEvent):
        evt.Skip()

    def _on_left_up(self, evt: PlotMouseEvent):
        evt.Skip()

    ID_ADD_TRANSITION = wx.NewIdRef()
    ID_ADD_BUNDLE = wx.NewIdRef()

    def _on_right_down(self, evt: PlotMouseEvent):
        self._right_motion = False
        evt.Skip()

    def _on_right_up(self, evt: PlotMouseEvent):
        evt.Skip()

        if self._right_motion:
            self._right_motion = False
            return

        artist = evt.GetArtist()
        x, y = evt.GetPosition()

        if artist is None:
            menu = wx.Menu()
            menu.Append(self.ID_ADD_TRANSITION, "Add Transition")
            menu.Append(self.ID_ADD_BUNDLE, "Add Bundle")

            self._mouse_click_location = evt.GetPosition3D()

            self.PopupMenu(menu, x, y)
        else:
            pass
            # obj.menu(self, x, y)

    def _on_key_up(self, evt: PlotKeyEvent):
        evt.Skip()

    def _on_key_down(self, evt: PlotKeyEvent):
        evt.Skip()


def h_sizer(parent, text, ctrl):
    hsizer = wx.BoxSizer(wx.HORIZONTAL)
    label = wx.StaticText(parent, wx.ID_ANY, label=text)
    hsizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
    hsizer.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
    return hsizer


import wx.lib.colourselect


class AddBundleDialog(wx.Dialog):

    def __init__(self, parent, editor):
        self.editor = editor

        self.selected_branches = []

        wx.Dialog.__init__(self, parent, wx.ID_ANY, title='Add Bundle', style=wx.CAPTION | wx.RESIZE_BORDER | wx.SYSTEM_MENU)

        sizer = wx.BoxSizer(wx.VERTICAL)

        count_ctrl = self.count = wx.StaticText(self, wx.ID_ANY, label='0')
        sizer.Add(h_sizer(self, 'Branch Count:', count_ctrl), 0, wx.ALL, 5)

        dia_ctrl = self.dia = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', initial=0.0, inc=0.1)
        sizer.Add(h_sizer(self, 'Diameter:', dia_ctrl), 0, wx.ALL, 5)
        dia_ctrl.Enable(False)

        color_btn = self.color_btn = wx.lib.colourselect.ColourSelect(self, -1, '', wx.Colour(51, 51, 51, 255), size=(75, -1))
        sizer.Add(h_sizer(self, 'Color:', color_btn), 0, wx.ALL, 5)

        self.remove_btn = wx.Button(self, wx.ID_ANY, label='Remove Branch', size=(100, -1))
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.AddSpacer(1)
        hsizer.Add(self.remove_btn, 0, wx.ALL, 5)

        self.remove_btn.Enable(False)

        self.select_btn = wx.Button(self, wx.ID_ANY, label='Select Branch', size=(100, -1))
        hsizer.Add(self.select_btn, 0, wx.ALL, 5)

        sizer.Add(hsizer, 0, wx.ALL, 5)

        self.select_btn.Bind(wx.EVT_BUTTON, self.on_select)
        self.remove_btn.Bind(wx.EVT_BUTTON, self.on_remove)

        line = wx.StaticLine(self, -1, size=(20, -1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, wx.EXPAND | wx.RIGHT | wx.TOP, 5)

        btnsizer = wx.StdDialogButtonSizer()

        btn = self.ok_btn = wx.Button(self, wx.ID_OK)
        btnsizer.AddButton(btn)
        btn.Enable(False)
        btn.Bind(wx.EVT_BUTTON, self.on_ok)

        btn = self.cancel_btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()
        btn.Bind(wx.EVT_BUTTON, self.on_cancel)

        sizer.Add(btnsizer, 0, wx.ALL, 5)

        self._selection_mode = False

        self.SetSizer(sizer)
        sizer.Fit(self)

    def SetTransitionBranch(self, transition, branch):
        self.selected_branches.append((transition, branch))
        self.count.SetLabel(str(len(self.selected_branches)))

        branch['is_connected'] = True
        branch['cylinder'].set_connected_color(True)

        print('branch', len(self.selected_branches), ':', branch['cylinder'].p1)
        print('branch', len(self.selected_branches), ':', branch['cylinder'].p2)

        if len(self.selected_branches) == 2:
            min_val = _decimal(0.0)
            max_val = _decimal(999999.0)

            for _, branch in self.selected_branches:
                min_val = max(min_val, branch['min_dia'])
                max_val = min(max_val, branch['max_dia'])

            for _, branch in self.selected_branches:
                if branch['max_dia'] < min_val:
                    raise RuntimeError

            self.ok_btn.Enable(True)
            self.select_btn.Enable(False)
            self.dia.SetMin(min_val)
            self.dia.SetMax(max_val)
            self.dia.SetValue(min_val)

            self.dia.Enable(True)
            self.ok_btn.Enable(True)

            self._selection_mode = False
            for transition in self.editor.transitions:
                transition.highlight_branches(False)

        self.remove_btn.Enable(True)

    def on_select(self, evt):
        for transition in self.editor.transitions:
            transition.highlight_branches(True)

        self.select_btn.Enable(False)
        self.remove_btn.Enable(False)
        self._selection_mode = True

        evt.Skip()

    def on_remove(self, evt):
        _, branch = self.selected_branches.pop(-1)
        branch['is_connected'] = False
        branch['cylinder'].set_connected_color(False)

        self.select_btn.Enable(True)
        self.ok_btn.Enable(False)
        self.remove_btn.Enable(len(self.selected_branches) > 0)
        self.dia.Enable(False)
        self.count.SetLabel(str(len(self.selected_branches)))

        evt.Skip()

    def on_ok(self, evt):
        color = self.color_btn.GetColour()
        color = tuple(item / 255.0 for item in (color.GetRed(), color.GetGreen(), color.GetBlue(), 255))
        diameter = _decimal(self.dia.GetValue())

        self.editor.bundles.append(Bundle(len(self.editor.bundles) + 1, self.GetParent(),
                                          self.editor, self.editor.axes, diameter, color,
                                          self.selected_branches))

        self.editor.bundle_dialog = None
        wx.CallAfter(self.Destroy)

    def on_cancel(self, evt):
        if self._selection_mode:
            for transition in self.editor.transitions:
                transition.highlight_branches(False)

            return

        for branch in self.selected_branches:
            branch['is_connected'] = False

        for transition in self.editor.transitions:
            transition.highlight_branches(False)

        self.editor.bundle_dialog = None

        wx.CallAfter(self.Destroy)


class AddTransitionDialog(wx.Dialog):

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title='Add Transition', style=wx.CAPTION | wx.RESIZE_BORDER | wx.SYSTEM_MENU | wx.STAY_ON_TOP)

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.res = []

        count_ctrl = self.count = wx.StaticText(self, wx.ID_ANY, label='0')
        sizer.Add(h_sizer(self, 'Branch Count:', count_ctrl), 0, wx.ALL, 5)

        min_dia_ctrl = self.min_dia = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', initial=0.0, inc=0.1)
        sizer.Add(h_sizer(self, 'Min Diameter:', min_dia_ctrl), 0, wx.ALL, 5)

        max_dia_ctrl = self.max_dia = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', initial=0.0, inc=0.1)
        sizer.Add(h_sizer(self, 'Max Diameter:', max_dia_ctrl), 0, wx.ALL, 5)

        len_ctrl = self.len = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', max=300.0, initial=0.0, inc=0.1)
        sizer.Add(h_sizer(self, 'Length:', len_ctrl), 0, wx.ALL, 5)

        b_len_ctrl = self.b_len = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', max=300.0, initial=0.0, inc=0.1)
        sizer.Add(h_sizer(self, 'Bulb length:', b_len_ctrl), 0, wx.ALL, 5)

        b_off_x_ctrl = self.b_off_x = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', initial=0.0, inc=0.1)
        sizer.Add(h_sizer(self, 'Bulb offset x:', b_off_x_ctrl), 0, wx.ALL, 5)

        b_off_y_ctrl = self.b_off_y = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', initial=0.0, inc=0.1)
        sizer.Add(h_sizer(self, 'Bulb offset y:', b_off_y_ctrl), 0, wx.ALL, 5)

        angle_ctrl = self.angle = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', min=-500.0, max=500.0, initial=0.0, inc=0.1)
        sizer.Add(h_sizer(self, 'Angle:', angle_ctrl), 0, wx.ALL, 5)

        off_x_ctrl = self.off_x = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', initial=0.0, inc=0.1)
        sizer.Add(h_sizer(self, 'Offset x:', off_x_ctrl), 0, wx.ALL, 5)

        off_y_ctrl = self.off_y = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', initial=0.0, inc=0.1)
        sizer.Add(h_sizer(self, 'Offset y:', off_y_ctrl), 0, wx.ALL, 5)

        self.add_button = wx.Button(self, wx.ID_ANY, label='Add Branch', size=(75, -1))
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.AddSpacer(1)
        hsizer.Add(self.add_button, 0, wx.ALL, 5)
        sizer.Add(hsizer, 0, wx.ALL, 5)

        self.add_button.Bind(wx.EVT_BUTTON, self.on_add)

        line = wx.StaticLine(self, -1, size=(20, -1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, wx.EXPAND | wx.RIGHT | wx.TOP, 5)

        btnsizer = wx.StdDialogButtonSizer()

        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALL, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

    def on_add(self, evt):
        evt.Skip()
        self.res.append([
            _decimal(self.min_dia.GetValue()),
            _decimal(self.max_dia.GetValue()),
            _decimal(self.len.GetValue()),
            _decimal(self.b_len.GetValue()),
            Point(_decimal(self.b_off_x.GetValue()), _decimal(self.b_off_y.GetValue()), _decimal(0.0)),
            _decimal(self.angle.GetValue()),
            Point(_decimal(self.off_x.GetValue()), _decimal(self.off_y.GetValue()), _decimal(0.0))
        ])

        self.count.SetLabel(str(len(self.res)))

    def GetValues(self):

        return res


class Decimal(_Decimal):

    def __new__(cls, value, *args, **kwargs):
        if not isinstance(value, (str, Decimal)):
            value = str(float(value))

        return super().__new__(cls, value, *args, **kwargs)


_decimal = Decimal


class Point:
    _instances = {}

    @property
    def project_id(self):
        return self._project_id

    @property
    def point_id(self):
        return self._point_id

    def add_to_db(self, project_id, point_id):
        assert (project_id, point_id) not in self._instances, 'Sanity Check'

        self._instances[(project_id, point_id)] = weakref.ref(self, self._remove_instance)

    @classmethod
    def _remove_instance(cls, ref):
        for key, value in cls._instances.items():
            if ref == value:
                break
        else:
            return

        del cls._instances[key]

    def __init__(self, x: _decimal, y: _decimal, z: _decimal | None = None,
                 project_id: int | None = None, point_id: int | None = None):

        self._project_id = project_id
        self._point_id = point_id

        if z is None:
            z = _decimal(0.0)

        self._x = floor_tens(x)
        self._y = floor_tens(y)
        self._z = floor_tens(z)

        self._callbacks = []
        self._cb_disabled = False

    def __enter__(self):
        self._cb_disabled = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cb_disabled = False
        self.__do_callbacks()

    def Bind(self, cb):
        for ref in self._callbacks[:]:
            if ref() is None:
                self._callbacks.remove(ref)
            elif ref() == cb:
                return False
        else:
            self._callbacks.append(weakref.WeakMethod(cb, self.__remove_ref))

        return True

    def Unbind(self, cb):
        for ref in self._callbacks[:]:
            if ref() is None:
                self._callbacks.remove(ref)
            elif ref() == cb:
                self._callbacks.remove(ref)
                break

    def __remove_ref(self, ref):
        if ref in self._callbacks:
            self._callbacks.remove(ref)

    @property
    def x(self) -> _decimal:
        return self._x

    @x.setter
    def x(self, value: _decimal):
        self._x = floor_tens(value)
        self.__do_callbacks()

    @property
    def y(self) -> _decimal:
        return self._y

    @y.setter
    def y(self, value: _decimal):
        self._y = floor_tens(value)
        self.__do_callbacks()

    @property
    def z(self) -> _decimal:
        return self._z

    @z.setter
    def z(self, value: _decimal):
        self._z = floor_tens(value)
        self.__do_callbacks()

    def copy(self) -> "Point":
        return Point(_decimal(self._x), _decimal(self._y), _decimal(self._z))

    def __do_callbacks(self):
        if self._cb_disabled:
            return

        for ref in self._callbacks[:]:
            func = ref()
            if func is None:
                self._callbacks.remove(ref)
            else:
                func(self)

    def __iadd__(self, other: "Point"):
        x, y, z = other
        self.x += x
        self.y += y
        self.z += z

        self.__do_callbacks()

        return self

    def __add__(self, other: "Point") -> "Point":
        x1, y1, z1 = self
        x2, y2, z2 = other

        x = x1 + x2
        y = y1 + y2
        z = z1 + z2

        return Point(x, y, z)

    def __isub__(self, other: "Point"):
        x, y, z = other
        self.x -= x
        self.y -= y
        self.z -= z
        self.__do_callbacks()

        return self

    def __sub__(self, other: "Point") -> "Point":
        x1, y1, z1 = self
        x2, y2, z2 = other

        x = x1 - x2
        y = y1 - y2
        z = z1 - z2

        return Point(x, y, z)

    def __itruediv__(self, other: _decimal):
        self.x /= other
        self.y /= other
        self.z /= other

        self.__do_callbacks()

        return self

    def __truediv__(self, other: _decimal) -> "Point":
        x, y, z = self
        return Point(x / other, y / other, z / other)

    def set_x_angle(self, angle: _decimal, origin: "Point") -> None:
        self.set_angles(angle, _decimal(0.0), _decimal(0.0), origin)

    def set_y_angle(self, angle: _decimal, origin: "Point") -> None:
        self.set_angles(_decimal(0.0), angle, _decimal(0.0), origin)

    def set_z_angle(self, angle: _decimal, origin: "Point") -> None:
        self.set_angles(_decimal(0.0), _decimal(0.0), angle, origin)

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, origin: "Point") -> None:

        R = Rotation.from_euler('xyz',
                                [x_angle, y_angle, z_angle], degrees=True)

        p1 = self.as_numpy
        p2 = origin.as_numpy

        p1 -= p2
        p1 = R.apply(p1.T).T
        p1 += p2
        self._x, self._y, self._z = [_decimal(float(item)) for item in p1]
        self.__do_callbacks()

    def __eq__(self, other: "Point") -> bool:
        x1, y1, z1 = self
        x2, y2, z2 = other

        return x1 == x2 and y1 == y2 and z1 == z2

    def __ne__(self, other: "Point") -> bool:
        return not self.__eq__(other)

    @property
    def as_float(self):
        return float(self._x), float(self._y), float(self._z)

    @property
    def as_int(self):
        return int(self._x), int(self._y), int(self._z)

    @property
    def as_numpy(self):
        return np.array(self.as_float, dtype=float)

    def __iter__(self):
        yield self._x
        yield self._y
        yield self._z

    def __str__(self):
        return f'X: {self.x}, Y: {self.y}, Z: {self.z}'


class Line:

    def __init__(self, p1: Point,
                 p2: Point | None = None,
                 length: _decimal | None = None,
                 x_angle: _decimal | None = None,
                 y_angle: _decimal | None = None,
                 z_angle: _decimal | None = None):

        self._p1 = p1

        if p2 is None:
            if None in (length, x_angle, y_angle, z_angle):
                raise ValueError('If an end point is not supplied then the "length", '
                                 '"x_angle", "y_angle" and "z_angle" parameters need to be supplied')

            p2 = Point(length, _decimal(0.0), _decimal(0.0))
            p2 += p1

            p2.set_angles(x_angle, y_angle, z_angle, p1)

        self._p2 = p2

    def copy(self) -> "Line":
        p1 = self._p1.copy()
        p2 = self._p2.copy()
        return Line(p1, p2)

    @property
    def p1(self) -> Point:
        return self._p1

    @property
    def p2(self) -> Point:
        return self._p2

    def __len__(self) -> int:
        res = math.sqrt((self._p2.x - self._p1.x) ** _decimal('2') +
                        (self._p2.y - self._p1.y) ** _decimal('2') +
                        (self._p2.z - self._p1.z) ** _decimal('2'))

        return int(round(res))

    def length(self) -> _decimal:
        return _decimal(math.sqrt((self._p2.x - self._p1.x) ** _decimal(2) +
                        (self._p2.y - self._p1.y) ** _decimal(2) +
                        (self._p2.z - self._p1.z) ** _decimal(2)))

    def get_x_angle(self) -> _decimal:
        return angles_from_3_points(self._p1, self._p2)[0]

    def get_y_angle(self) -> _decimal:
        return angles_from_3_points(self._p1, self._p2)[1]

    def get_z_angle(self) -> _decimal:
        return angles_from_3_points(self._p1, self._p2)[2]

    def get_angles(self):
        return angles_from_3_points(self._p1, self._p2)

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal,
                   origin: Point | None = None) -> None:

        if origin is None:
            origin = self.center

        if origin != self.p1 and origin != self.p2:
            self.p1.set_angles(x_angle, y_angle, z_angle, origin)
            self.p2.set_angles(x_angle, y_angle, z_angle, origin)
        elif origin != self.p1:
            self.p1.set_angles(x_angle, y_angle, z_angle, origin)
        else:
            self.p2.set_angles(x_angle, y_angle, z_angle, origin)

    def set_x_angle(self, angle: _decimal, origin: Point | None = None) -> None:
        self.set_angles(angle, _decimal(0.0), _decimal(0.0), origin)

    def set_y_angle(self, angle: _decimal, origin: Point | None = None) -> None:
        self.set_angles(_decimal(0.0), angle, _decimal(0.0), origin)

    def set_z_angle(self, angle: _decimal, origin: Point | None = None) -> None:
        self.set_angles(_decimal(0.0), _decimal(0.0), angle, origin)

    @property
    def center(self) -> Point:
        return Point(
            self._p1.x + (self._p1.x - self._p2.x),
            self._p1.y + (self._p1.y - self._p2.y),
            self._p1.z + (self._p1.z - self._p2.z)
        )

    def __iter__(self) -> _Iterable[Point]:
        yield self._p1
        yield self._p2


class Sphere:

    def __init__(self, center: Point, diameter: _decimal, color):
        center.Bind(self._update_artist)
        self._center = center
        self._diameter = diameter
        self._color = color
        self.artist = None
        self._verts = None

        self._sections = int((_decimal(1.65) /
                             (_decimal(9.0) /
                             (diameter ** (_decimal(1.0) / _decimal(6.0))))) *
                             _decimal(100.0))

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self._color = value
        self._update_artist()

    @property
    def center(self) -> Point:
        return self._center

    @center.setter
    def center(self, value: Point):
        if not value.Bind(self._update_artist):
            if value != self._center:
                raise RuntimeError('sanity check')

            return

        self._center.Unbind(self._update_artist)
        self._center = value
        self._update_artist()

    @property
    def diameter(self) -> _decimal:
        return self._diameter

    @diameter.setter
    def diameter(self, value: _decimal):
        self._diameter = value
        self._sections = int((_decimal(1.65) /
                             (_decimal(9.0) /
                             (value ** (_decimal(1.0) / _decimal(6.0))))) *
                             _decimal(100.0))

        self._verts = None
        self._update_artist()

    @property
    def is_added(self) -> bool:
        return self.artist is not None

    def move(self, point: Point) -> None:
        self._center += point

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, origin: Point):
        if origin == self._center:
            return

        self._center.set_angles(x_angle, y_angle, z_angle, origin)

    def set_x_angle(self, angle: _decimal, origin: Point) -> None:
        self.set_angles(angle, _decimal(0.0), _decimal(0.0), origin)

    def set_y_angle(self, angle: _decimal, origin: Point) -> None:
        self.set_angles(_decimal(0.0), angle, _decimal(0.0), origin)

    def set_z_angle(self, angle: _decimal, origin: Point) -> None:
        self.set_angles(_decimal(0.0), _decimal(0.0), angle, origin)

    def _get_verts(self) -> tuple[np.array, np.array, np.array]:
        if self._verts is None:
            radius = float(self._diameter / _decimal(2.0))

            u = np.linspace(0, 2 * np.pi, int(self._sections / 1.5))
            v = np.linspace(0, np.pi, self._sections // 3)
            X = radius * np.outer(np.cos(u), np.sin(v))
            Y = radius * np.outer(np.sin(u), np.sin(v))
            Z = radius * np.outer(np.ones(np.size(u)), np.cos(v))

            self._verts = [X, Y, Z]

        X, Y, Z = self._verts

        X += float(self._center.x)
        Y += float(self._center.y)
        Z += float(self._center.z)

        return X, Y, Z

    def _update_artist(self, *_) -> None:
        if not self.is_added:
            return

        x, y, z = self._get_verts()

        z = matplotlib.cbook._to_unmasked_float_array(z)  # NOQA
        z, y, z = np.broadcast_arrays(x, y, z)
        rows, cols = z.shape

        has_stride = False
        has_count = False

        rstride = 10
        cstride = 10
        rcount = 50
        ccount = 50

        if matplotlib.rcParams['_internal.classic_mode']:
            compute_strides = has_count
        else:
            compute_strides = not has_stride

        if compute_strides:
            rstride = int(max(np.ceil(rows / rcount), 1))
            cstride = int(max(np.ceil(cols / ccount), 1))

        if (rows - 1) % rstride == 0 and (cols - 1) % cstride == 0:
            polys = np.stack([matplotlib.cbook._array_patch_perimeters(a, rstride, cstride)  # NOQA
                              for a in (x, y, z)], axis=-1)
        else:
            row_inds = list(range(0, rows - 1, rstride)) + [rows - 1]
            col_inds = list(range(0, cols - 1, cstride)) + [cols - 1]

            polys = []
            for rs, rs_next in itertools.pairwise(row_inds):
                for cs, cs_next in itertools.pairwise(col_inds):
                    ps = [matplotlib.cbook._array_perimeter(a[rs:rs_next + 1, cs:cs_next + 1])  # NOQA
                          for a in (x, y, z)]
                    ps = np.array(ps).T
                    polys.append(ps)

        if not isinstance(polys, np.ndarray) or not np.isfinite(polys).all():
            new_polys = []

            for p in polys:
                new_poly = np.array(p)[np.isfinite(p).all(axis=1)]

                if len(new_poly):
                    new_polys.append(new_poly)

            polys = new_polys

        self.artist.set_verts(polys)

        normals = art3d._generate_normals(polys)
        facecolors = art3d._shade_colors(self._color, normals, None)
        self.artist.set_facecolor(facecolors)

    def add_to_plot(self, axes: axes3d.Axes3D) -> None:
        if self.is_added:
            return

        # we create an empty artist and then update the artist due to a bug in
        # matplotlib that causes the shading to not get rendered when updating
        # the color. We want the shading light source to be the same all the time.
        # To save some processor time we do the work of calculating the verts
        # only a single time.
        self.artist = axes.plot_surface(np.array([[np.NAN]], dtype=float),
                                        np.array([[np.NAN]], dtype=float),
                                        np.array([[np.NAN]], dtype=float),
                                        color=self._color, antialiaseds=False)
        self._update_artist()

    def set_py_data(self, py_data):
        if not self.is_added:
            raise ValueError('sanity check')

        self.artist.set_py_data(py_data)


class Hemisphere:

    def __init__(self, center: Point, diameter: _decimal, color, hole_diameter: _decimal | None):
        center.Bind(self._update_artist)
        self._center = center
        self._diameter = diameter
        self._color = color
        self._saved_color = self._color
        self.artist = None
        self._verts = None

        self._x_angle = _decimal(0.0)
        self._y_angle = _decimal(0.0)
        self._z_angle = _decimal(0.0)

        self._sections = int((_decimal(1.65) /
                             (_decimal(9.0) /
                             (diameter ** (_decimal(1.0) / _decimal(6.0))))) *
                             _decimal(100.0))

        self._hole_diameter = hole_diameter
        self._hole_center = None
        self._hc = None

    @property
    def hole_diameter(self) -> _decimal | None:
        return self._hole_diameter

    @hole_diameter.setter
    def hole_diameter(self, value: _decimal | None):
        self._hole_diameter = value
        self._verts = None

        self._update_artist()

    def set_selected_color(self, flag):
        if flag:
            self.color = (0.6, 0.2, 0.2, 1.0)
        else:
            self.color = self._saved_color

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value: tuple[float, float, float, float]):
        self._color = value
        self._update_artist()

    @property
    def center(self) -> Point:
        return self._center

    @center.setter
    def center(self, value: Point):
        if not value.Bind(self._update_artist):
            if value != self._center:
                raise RuntimeError('sanity check')

            return

        self._center.Unbind(self._update_artist)
        self._center = value
        self._update_artist()

    @property
    def diameter(self) -> _decimal:
        return self._diameter

    @diameter.setter
    def diameter(self, value: _decimal):
        self._diameter = value
        self._sections = int((_decimal(1.65) /
                             (_decimal(9.0) /
                             (value ** (_decimal(1.0) / _decimal(6.0))))) *
                             _decimal(100.0))

        self._verts = None
        self._update_artist()

    @property
    def is_added(self) -> bool:
        return self.artist is not None

    def move(self, point: Point) -> None:
        self._center += point

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, origin: Point):
        if origin != self.center:
            self._center.set_angles(x_angle, y_angle, z_angle, origin)
            return

        self._x_angle = x_angle
        self._y_angle = y_angle
        self._z_angle = z_angle
        self._update_artist()

    def set_x_angle(self, angle: _decimal, origin: Point) -> None:
        if origin != self._center:
            self.set_angles(angle, _decimal(0.0), _decimal(0.0), origin)
        else:
            self.set_angles(angle, self._y_angle, self._z_angle, origin)

    def set_y_angle(self, angle: _decimal, origin: Point) -> None:
        if origin != self._center:
            self.set_angles(_decimal(0.0), angle, _decimal(0.0), origin)
        else:
            self.set_angles(self._x_angle, angle, self._z_angle, self._center)

    def set_z_angle(self, angle: _decimal, origin: Point) -> None:
        if origin != self._center:
            self.set_angles(_decimal(0.0), _decimal(0.0), angle, origin)
        else:
            self.set_angles(self._x_angle, self._y_angle, angle, origin)

    def get_angles(self) -> tuple[_decimal, _decimal, _decimal]:
        return self._x_angle, self._y_angle, self._z_angle

    def _get_verts(self) -> tuple[np.array, np.array, np.array]:
        if self._verts is None:
            radius = float(self._diameter / _decimal(2.0))

            u = np.linspace(0, 2 * np.pi, int(self._sections / 1.5))
            v = np.linspace(0, np.pi / 2, self._sections // 3)
            X = radius * np.outer(np.cos(u), np.sin(v))
            Y = radius * np.outer(np.sin(u), np.sin(v))
            Z = radius * np.outer(np.ones(np.size(u)), np.cos(v))

            if self._hole_diameter:
                hole_dia = float(self._hole_diameter / _decimal(2.0) / _decimal(1.15))

                mask = np.sqrt(X ** 2 + Y ** 2) >= hole_dia
                X = np.where(mask, X, np.nan)
                Y = np.where(mask, Y, np.nan)
                Z = np.where(mask, Z, np.nan)

                z_max = np.nanmax(Z.flatten())
                self._hc = Point(_decimal(0.0), _decimal(0.0), _decimal(z_max))

            self._verts = [X, Y, Z]

        x, y, z = self._verts

        x_angle, y_angle, z_angle = self.get_angles()
        R = Rotation.from_euler('xyz',
                                [x_angle, y_angle, z_angle], degrees=True)
        local_points = np.vstack((x.flatten(), y.flatten(), z.flatten()))
        rp = R.apply(local_points.T).T

        origin = self._center.as_float

        # Translate to start point
        X = rp[0].reshape(x.shape) + origin[0]
        Y = rp[1].reshape(y.shape) + origin[1]
        Z = rp[2].reshape(z.shape) + origin[2]

        if self._hc is None:
            hole_center = self._center
        else:
            local_points = self._hc.as_numpy
            rp = R.apply(local_points.T).T

            origin = np.array(origin, dtype=float)

            new_point = rp + origin
            hole_center = Point(*[_decimal(float(item)) for item in new_point])

        if self._hole_center is None:
            self._hole_center = hole_center
        elif self._hole_center != hole_center:
            hc = self._hole_center
            diff = hole_center - hc
            hc += diff

        return X, Y, Z

    @property
    def hole_center(self):
        if self._hole_center is None:
            _ = self._get_verts()

        return self._hole_center

    def _update_artist(self, *_) -> None:
        if not self.is_added:
            return

        x, y, z = self._get_verts()

        z = matplotlib.cbook._to_unmasked_float_array(z)  # NOQA
        z, y, z = np.broadcast_arrays(x, y, z)
        rows, cols = z.shape

        has_stride = False
        has_count = False

        rstride = 10
        cstride = 10
        rcount = 50
        ccount = 50

        if matplotlib.rcParams['_internal.classic_mode']:
            compute_strides = has_count
        else:
            compute_strides = not has_stride

        if compute_strides:
            rstride = int(max(np.ceil(rows / rcount), 1))
            cstride = int(max(np.ceil(cols / ccount), 1))

        if (rows - 1) % rstride == 0 and (cols - 1) % cstride == 0:
            polys = np.stack([matplotlib.cbook._array_patch_perimeters(a, rstride, cstride)  # NOQA
                              for a in (x, y, z)], axis=-1)
        else:
            row_inds = list(range(0, rows - 1, rstride)) + [rows - 1]
            col_inds = list(range(0, cols - 1, cstride)) + [cols - 1]

            polys = []
            for rs, rs_next in itertools.pairwise(row_inds):
                for cs, cs_next in itertools.pairwise(col_inds):
                    ps = [matplotlib.cbook._array_perimeter(a[rs:rs_next + 1, cs:cs_next + 1])  # NOQA
                          for a in (x, y, z)]
                    ps = np.array(ps).T
                    polys.append(ps)

        if not isinstance(polys, np.ndarray) or not np.isfinite(polys).all():
            new_polys = []

            for p in polys:
                new_poly = np.array(p)[np.isfinite(p).all(axis=1)]

                if len(new_poly):
                    new_polys.append(new_poly)

            polys = new_polys

        self.artist.set_verts(polys)

        normals = art3d._generate_normals(polys)
        facecolors = art3d._shade_colors(self._color, normals, None)
        self.artist.set_facecolor(facecolors)

    def add_to_plot(self, axes: axes3d.Axes3D) -> None:
        if self.is_added:
            return

        # we create an empty artist and then update the artist due to a bug in
        # matplotlib that causes the shading to not get rendered when updating
        # the color. We want the shading light source to be the same all the time.
        # To save some processor time we do the work of calculating the verts
        # only a single time.
        self.artist = axes.plot_surface(np.array([[np.NAN]], dtype=float),
                                        np.array([[np.NAN]], dtype=float),
                                        np.array([[np.NAN]], dtype=float),
                                        color=self._color, antialiaseds=False)
        self._update_artist()

    def set_py_data(self, py_data):
        if not self.is_added:
            raise ValueError('sanity check')

        self.artist.set_py_data(py_data)


class Cylinder:

    def __init__(self, start: Point, length, diameter: _decimal, primary_color, edge_color, p2=None):
        start.Bind(self._update_artist)
        self._primary_color = primary_color
        self._saved_color = self._primary_color
        self._edge_color = edge_color
        self._p1 = start
        self._p2 = p2
        self._length = length
        self._diameter = diameter

        self._update_disabled = False
        self.artist = None
        self._show = True
        self._verts = None

        if p2 is not None:
            p2.Bind(self._update_artist)

    @property
    def p1(self) -> Point:
        return self._p1

    @p1.setter
    def p1(self, value: Point):
        if not value.Bind(self._update_artist):
            if value != self._p1:
                raise RuntimeError('sanity check')

            return

        self._p1.Unbind(self._update_artist)
        self._p1 = value
        self._verts = None
        self._update_artist()

    @property
    def p2(self) -> Point:
        if self._p2 is None:
            # R = Rotation.from_euler('xyz', [0.0, 90.0, 0.0], degrees=True)
            # p = self._p1.as_numpy + R.apply([0, 0, float(self._length)])
            self._p2 = Point(_decimal(self._length), _decimal(0.0), _decimal(0.0))
            self._p2 += self._p1
            self._p2.Bind(self._update_artist)

            # self._p2 = Point(_decimal(float(p[0])), _decimal(float(p[1])), _decimal(float(p[2])))

        return self._p2

    @p2.setter
    def p2(self, value: Point):
        if not value.Bind(self._update_artist):
            if value != self._p2:
                raise RuntimeError('sanity check')

            return

        if self._p2 is not None:
            self._p2.Unbind(self._update_artist)

        print('P1:', self.p1)
        print('P2:', self.p2)

        self._p2 = value
        self._verts = None
        self._update_artist()

    @property
    def color(self):
        return self._primary_color

    @color.setter
    def color(self, value):
        self._primary_color = value
        self._update_artist()

    def set_selected_color(self, flag):
        if flag:
            self.color = (0.6, 0.2, 0.2, 1.0)
        else:
            self.color = self._saved_color

    def set_connected_color(self, flag):
        if flag:
            self.color = (0.2, 0.6, 0.2, 1.0)
        else:
            self.color = self._saved_color

    @property
    def is_added(self) -> bool:
        return self.artist is not None

    def show(self) -> None:
        self.artist.set_visible(True)

    def hide(self) -> None:
        self.artist.set_visible(False)

    def _update_artist(self, p=None) -> None:
        if not self.is_added:
            return

        if p is not None:
            self._verts = None

        x, y, z = self._build_verts()

        print(x)
        print()
        print(y)
        print()
        print(z)
        print()

        z = matplotlib.cbook._to_unmasked_float_array(z)  # NOQA
        z, y, z = np.broadcast_arrays(x, y, z)
        rows, cols = z.shape

        has_stride = False
        has_count = False

        rstride = 10
        cstride = 10
        rcount = 50
        ccount = 50

        if matplotlib.rcParams['_internal.classic_mode']:
            compute_strides = has_count
        else:
            compute_strides = not has_stride

        if compute_strides:
            rstride = int(max(np.ceil(rows / rcount), 1))
            cstride = int(max(np.ceil(cols / ccount), 1))

        if (rows - 1) % rstride == 0 and (cols - 1) % cstride == 0:
            polys = np.stack([matplotlib.cbook._array_patch_perimeters(a, rstride, cstride)  # NOQA
                              for a in (x, y, z)], axis=-1)
        else:
            row_inds = list(range(0, rows - 1, rstride)) + [rows - 1]
            col_inds = list(range(0, cols - 1, cstride)) + [cols - 1]

            polys = []
            for rs, rs_next in itertools.pairwise(row_inds):
                for cs, cs_next in itertools.pairwise(col_inds):
                    ps = [matplotlib.cbook._array_perimeter(a[rs:rs_next + 1, cs:cs_next + 1])  # NOQA
                          for a in (x, y, z)]
                    ps = np.array(ps).T
                    polys.append(ps)

        if not isinstance(polys, np.ndarray) or not np.isfinite(polys).all():
            new_polys = []

            for p in polys:
                new_poly = np.array(p)[np.isfinite(p).all(axis=1)]

                if len(new_poly):
                    new_polys.append(new_poly)

            polys = new_polys

        self.artist.set_verts(polys)

        normals = art3d._generate_normals(polys)
        facecolors = art3d._shade_colors(self._primary_color, normals, None)
        self.artist.set_facecolor(facecolors)

    @property
    def diameter(self) -> _decimal:
        return self._diameter

    @diameter.setter
    def diameter(self, value: _decimal):
        self._diameter = value
        self._verts = None
        self._update_artist()

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, origin: Point) -> None:
        line = Line(self._p1, self.p2)
        line.set_angles(x_angle, y_angle, z_angle, origin)

    def get_angles(self):
        x, y, z = angles_from_3_points(self._p1, self.p2)
        return x, y, z

    def get_x_angle(self) -> _decimal:
        return angles_from_3_points(self._p1, self.p2)[0]

    def get_y_angle(self) -> _decimal:
        return angles_from_3_points(self.p1, self.p2)[1]

    def get_z_angle(self) -> _decimal:
        return angles_from_3_points(self._p1, self.p2)[2]

    def set_x_angle(self, angle: _decimal, origin: Point) -> None:
        line = Line(self._p1, self.p2)
        line.set_x_angle(angle, origin)

    def set_y_angle(self, angle: _decimal, origin: Point) -> None:
        line = Line(self._p1, self.p2)
        line.set_y_angle(angle, origin)

    def set_z_angle(self, angle: _decimal, origin: Point) -> None:
        line = Line(self._p1, self.p2)
        line.set_z_angle(angle, origin)

    @property
    def length(self):
        line = Line(self._p1, self.p2)
        length = line.length()
        return round(length, 1)

    def move(self, point: Point) -> None:
        self._p1 += point
        self.p2 += point

    def _build_verts(self):
        if self._verts is None:
            length = float(self.length)
            radius = float(self._diameter / _decimal(2.0))

            theta = np.linspace(0, 2 * np.pi, 20)
            z = np.linspace(0, length, 5)
            theta_grid, z_grid = np.meshgrid(theta, z)

            x = radius * np.cos(theta_grid)
            y = radius * np.sin(theta_grid)
            z = z_grid

            # Stack local coordinates
            local_points = np.vstack((x.flatten(), y.flatten(), z.flatten()))

            # Rotation from Euler angles
            R = Rotation.from_euler('xyz',
                                    [0.0, 90.0, 0.0], degrees=True)
            rp = R.apply(local_points.T).T

            # Translate to start point
            X = rp[0].reshape(x.shape)
            Y = rp[1].reshape(y.shape)
            Z = rp[2].reshape(z.shape)

            self._verts = [X, Y, Z]

        x, y, z = self._verts

        x_angle, y_angle, z_angle = self.get_angles()
        R = Rotation.from_euler('xyz',
                                [x_angle, y_angle, z_angle], degrees=True)
        local_points = np.vstack((x.flatten(), y.flatten(), z.flatten()))
        rp = R.apply(local_points.T).T

        origin = self._p1.as_float

        # Translate to start point
        X = rp[0].reshape(x.shape) + origin[0]
        Y = rp[1].reshape(y.shape) + origin[1]
        Z = rp[2].reshape(z.shape) + origin[2]

        return X, Y, Z

    def add_to_plot(self, axes: axes3d.Axes3D) -> None:
        if self.is_added:
            return

        # we create an empty artist and then update the artist due to a bug in
        # matplotlib that causes the shading to not get rendered when updating
        # the color. We want the shading light source to be the same all the time.
        # To save some processor time we do the work of calculating the verts
        # only a single time.
        self.artist = axes.plot_surface(np.array([[np.NAN]], dtype=float),
                                        np.array([[np.NAN]], dtype=float),
                                        np.array([[np.NAN]], dtype=float),
                                        color=self._primary_color, antialiaseds=False)
        self._update_artist()

    def set_py_data(self, py_data):
        if not self.is_added:
            raise ValueError('sanity check')

        self.artist.set_py_data(py_data)


def angles_from_3_points(p1: Point, p2: Point) -> tuple[_decimal, _decimal, _decimal]:

    # to get the "roll" we need to have a directional vew we are looking from.
    # We always want that to be from a point looking down on the model. So we create
    # a 3rd point looking down with a z axis of 20 and then add the input
    # point that has the highest Z axis to it.
    p3 = Point(_decimal(0.0), _decimal(0.0), _decimal(20.0))

    if float(p1.z) > float(p2.z):
        p3 += p1
    else:
        p3 += p2

    # Convert to numpy arrays
    p1, p2, p3 = np.array(p1.as_float), np.array(p2.as_float), np.array(p3.as_float)

    # Direction vector (main axis)
    forward = p2 - p1
    forward /= np.linalg.norm(forward)

    # Temporary "up" vector
    up_temp = p3 - p1
    up_temp /= np.linalg.norm(up_temp)

    # Right vector (perpendicular to forward and up_temp)
    right = np.cross(up_temp, forward)
    right /= np.linalg.norm(right)

    # True up vector (recomputed to ensure orthogonality)
    up = np.cross(forward, right)

    # Build rotation matrix
    matrix = np.array([right, up, forward]).T  # 3x3 rotation matrix

    # Extract Euler angles (XYZ order)
    pitch = np.arctan2(-matrix[2, 1], matrix[2, 2])
    yaw = np.arctan2(matrix[1, 0], matrix[0, 0])
    roll = np.arctan2(matrix[2, 0],
                      np.sqrt(matrix[2, 1] ** 2 + matrix[2, 2] ** 2))

    pitch, yaw, roll = np.degrees([pitch, yaw, roll])
    return _decimal(pitch) + _decimal(90.0), _decimal(roll), _decimal(yaw) - _decimal(90.0)


if __name__ == '__main__':
    app = wx.App()

    frame = Editor((1000, 1000))
    frame.Show()

    app.MainLoop()
