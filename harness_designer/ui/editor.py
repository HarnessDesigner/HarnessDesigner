# Press and hold `x`, `y` or `z` and then click on one of the points in the plot
# and drag the point along the axis noted by the key that is being held down.
#
# Left click and drag rotates the plot.
# Right click and drag pans the plot.
# Mouse wheel zooms the plot.
#
# Code was added to remove the flicking that was seen when the plot is redrawn.

import wx
import matplotlib

matplotlib.rcParams[f'axes3d.xaxis.panecolor'] = (0.0, 0.0, 0.0, 0.0)
matplotlib.rcParams[f'axes3d.yaxis.panecolor'] = (0.0, 0.0, 0.0, 0.0)
matplotlib.rcParams[f'axes3d.yaxis.panecolor'] = (0.0, 0.0, 0.0, 0.0)
matplotlib.rcParams['grid.color'] = (0.5, 0.5, 0.5, 0.5)
matplotlib.rcParams['grid.linewidth'] = 0.5
matplotlib.rcParams['grid.linestyle'] = ':'
matplotlib.rcParams['axes.linewidth'] = 0.5
matplotlib.rcParams['axes.edgecolor'] = (0.45, 0.45, 0.45, 0.55)

matplotlib.rcParams['xtick.major.width'] = 0.5
matplotlib.rcParams['ytick.major.width'] = 0.5

matplotlib.rcParams['ytick.minor.width'] = 0.5
matplotlib.rcParams['ytick.minor.width'] = 0.5


matplotlib.use('WXAgg')


from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg  # NOQA
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg  # NOQA
from mpl_toolkits.mplot3d.art3d import Line3D, Path3DCollection  # NOQA
from mpl_toolkits.mplot3d import axes3d  # NOQA
from matplotlib.backend_bases import ResizeEvent  # NOQA
from mpl_toolkits.mplot3d.axes3d import _Quaternion  # NOQA
from decimal import Decimal as decimal  # NOQA
import matplotlib.pyplot  # NOQA
import numpy as np  # NOQA


class Canvas(FigureCanvasWxAgg):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.Bind(wx.EVT_ERASE_BACKGROUND, self._on_erase_background)

    # bypass erasing the background when the plot is redrawn.
    # This helps to eliminate the flicker that is seen when a redraw occurs.
    # the second piece needed to eliminate the flicker is seen below
    def _on_erase_background(self, _):
        pass

    # override the _on_paint method in the canvas
    # this is done so double buffer is used which eliminates the flicker
    # that is seen when the plot redraws
    def _on_paint(self, event):
        drawDC = wx.BufferedPaintDC(self)
        if not self._isDrawn:
            self.draw(drawDC=drawDC)
        else:
            self.gui_repaint(drawDC=drawDC)
        drawDC.Destroy()

    # override the _on_size method in the canvas
    def _on_size(self, event):
        self._update_device_pixel_ratio()
        sz = self.GetParent().GetSizer()
        if sz:
            si = sz.GetItem(self)
        else:
            si = None

        if sz and si and not si.Proportion and not si.Flag & wx.EXPAND:
            size = self.GetMinSize()
        else:
            size = self.GetClientSize()
            size.IncTo(self.GetMinSize())

        if getattr(self, "_width", None):
            if size == (self._width, self._height):
                return

        self._width, self._height = size
        self._isDrawn = False

        if self._width <= 1 or self._height <= 1:
            return

        dpival = self.figure.dpi

        if wx.Platform != '__WXMSW__':
            scale = self.GetDPIScaleFactor()
            dpival /= scale

        winch = self._width / dpival
        hinch = self._height / dpival
        self.figure.set_size_inches(winch, hinch, forward=False)

        self.Refresh(eraseBackground=False)
        ResizeEvent("resize_event", self)._process()  # NOQA
        self.draw_idle()


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


class Editor(wx.Panel):
    def __init__(self, parent):
        self.key = None
        self.selected_object = None
        self.button_held = False
        self.had_motion = False
        self.object_tooltip = None

        self.wires = []
        self.artists_mapping = {}
        self._offset = None

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        v_sizer = wx.BoxSizer(wx.VERTICAL)
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.fig = matplotlib.pyplot.figure()

        ax = self.axes = self.fig.add_subplot(projection='3d')
        ax.autoscale(True)

        for line in self.data:
            obj = ax.scatter(*line[:-1], marker=line[-1], picker=True)
            self.artists_mapping[obj] = line

        for line in self.lines:
            wire = Line3D(*line[:-1], linewidth=line[-1], picker=True)
            ax.add_line(wire)
            self.wires.append(wire)

        # Set the axis labels
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_zlabel('z')

        self.canvas = Canvas(self, wx.ID_ANY, self.fig)

        # MouseEvent
        self.canvas.mpl_connect("button_press_event", self.on_press)
        self.canvas.mpl_connect("motion_notify_event", self.on_motion)
        self.canvas.mpl_connect("button_release_event", self.on_release)
        self.canvas.mpl_connect("scroll_event", self.on_mouse_scroll)

        # LocationEvent
        self.canvas.mpl_connect("figure_enter_event", self.on_figure_enter)
        self.canvas.mpl_connect("figure_leave_event", self.on_figure_leave)
        self.canvas.mpl_connect("axes_enter_event", self.on_axes_enter)
        self.canvas.mpl_connect("axes_leave_event", self.on_axes_leave)

        # KeyEvent
        self.canvas.mpl_connect("key_press_event", self.on_key_press)
        self.canvas.mpl_connect("key_release_event", self.on_key_release)

        # CloseEvent
        self.canvas.mpl_connect("close_event", self.on_close)

        # DrawEvent
        self.canvas.mpl_connect("draw_event", self.on_draw)

        # PickEvent
        self.canvas.mpl_connect("pick_event", self.on_pick)

        # ResizeEvent
        self.canvas.mpl_connect("resize_event", self.on_resize)

        toolbar = NavigationToolbar2WxAgg(self.canvas)
        toolbar.Realize()

        h_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)
        v_sizer.Add(h_sizer, 1, wx.EXPAND)
        v_sizer.Add(toolbar, 0, wx.LEFT | wx.EXPAND)

        self.SetSizer(v_sizer)
        toolbar.update()

        def _do():
            for value in self.axes._axis_map.values():  # NOQA
                value.set_ticks_position('both')
                value.set_label_position('both')
            self.canvas.draw()

        wx.CallAfter(_do)

    def on_close(self, evt):
        pass

    def on_draw(self, evt):
        pass

    def on_key_press(self, evt):
        key = evt.key
        if isinstance(key, str):
            self.key = key.lower()

    def on_key_release(self, evt):
        key = evt.key
        if isinstance(key, str) and key.lower() == self.key:
            self.key = None

    def on_pick(self, evt):
        if isinstance(evt.artist, Path3DCollection):
            self.selected_object = evt.artist
            self.axes.button_pressed = None

    def on_resize(self, evt):
        pass

    def on_mouse_scroll(self, evt):
        x, y = evt.xdata, evt.ydata

        if x is None or evt.inaxes != self.axes:
            return

        if not hasattr(self.axes, '_sx') or not hasattr(self.axes, '_sy'):
            self.axes._sx, self.axes._sy = x, y

        h = self.axes._pseudo_h  # NOQA

        scale = h / (h + (evt.step / 100))
        self.axes._scale_axis_limits(scale, scale, scale)  # NOQA

        self.axes.get_figure(root=True).canvas.draw_idle()

    def on_figure_enter(self, evt):
        pass

    def on_figure_leave(self, evt):
        pass

    def on_axes_enter(self, evt):
        pass

    def on_axes_leave(self, evt):
        pass

    def on_press(self, event):
        if event.button == 1:
            # left button
            if event.dblclick:
                pass
            elif self.selected_object is not None:
                self.button_held = True
                self.axes.button_pressed = None

        elif event.button == 2:
            # middle button
            pass
        elif event.button == 3:
            # right button
            # open context menu
            self.had_motion = False

        elif event.button == 8:
            # forward
            pass
        elif event.button == 9:
            # back
            pass

    def location_coords(self, xv, yv):
        p1, pane_idx = self.axes._calc_coord(xv, yv, None)  # NOQA
        xs = self.axes.format_xdata(p1[0])
        ys = self.axes.format_ydata(p1[1])
        zs = self.axes.format_zdata(p1[2])

        def get_float(val):
            if val.startswith('−'):
                return decimal(str(-float(val[1:])))
            else:
                return decimal(str(float(val)))

        return get_float(xs), get_float(ys), get_float(zs)

    def on_motion(self, event):
        if event.button == 3:
            self.had_motion = True
            # Start the pan event with pixel coordinates

            x, y = event.xdata, event.ydata
            # In case the mouse is out of bounds.
            if x is None or event.inaxes != self:
                return

            self.axes.button_pressed = None

            if not hasattr(self.axes, '_sx') or not hasattr(self.axes, '_sy'):
                self.axes._sx, self.axes._sy = event.xdata, event.ydata

            px, py = self.axes.transData.transform([self.axes._sx, self.axes._sy])  # NOQA
            self.axes.start_pan(px, py, 2)
            # pan view (takes pixel coordinate input)
            self.axes.drag_pan(2, None, event.x, event.y)
            self.axes.end_pan()

            self.axes._sx, self.axes._sy = event.xdata, event.ydata
            # Always request a draw update at the end of interaction
            self.axes.get_figure(root=True).canvas.draw_idle()

        elif self.button_held and self.selected_object is not None:
            if self.key not in ('x', 'y', 'z'):
                return

            try:
                x, y, z = self.location_coords(event.xdata, event.ydata)
            except TypeError:
                return

            old_pos = self.artists_mapping[self.selected_object]

            old_x, old_y, old_z = old_pos[:-1]

            if self._offset is None:
                if self.key == 'x':
                    self._offset = decimal(str(old_x)) - x
                elif self.key == 'y':
                    self._offset = decimal(str(old_y)) - y
                else:  # 'z'
                    self._offset = decimal(str(old_z)) - z

                return

            # self.axes.autoscale(False)

            if self.key == 'x':
                x += self._offset
            elif self.key == 'y':
                y += self._offset
            elif self.key == 'z':
                z += self._offset

            for wire in self.wires:
                xs, ys, zs = wire.get_data_3d()

                if xs[0] == old_x and ys[0] == old_y and zs[0] == old_z:
                    if self.key == 'x':
                        xs[0] = float(x)
                    elif self.key == 'y':
                        ys[0] = float(y)
                    elif self.key == 'z':
                        zs[0] = float(z)

                    wire.set_data_3d(xs, ys, zs)

                elif xs[1] == old_x and ys[1] == old_y and zs[1] == old_z:
                    if self.key == 'x':
                        xs[1] = float(x)
                    elif self.key == 'y':
                        ys[1] = float(y)
                    elif self.key == 'z':
                        zs[1] = float(z)

                    wire.set_data_3d(xs, ys, zs)

            if self.key == 'x':
                old_pos[0] = float(x)
                self.selected_object._offsets3d[0][0] = float(x)  # NOQA
            elif self.key == 'y':
                old_pos[1] = float(y)
                self.selected_object._offsets3d[1][0] = float(y)  # NOQA
            elif self.key == 'z':
                old_pos[2] = float(z)
                self.selected_object._offsets3d[2][0] = float(z)  # NOQA

            self.axes.get_figure(root=True).canvas.draw_idle()

            height = self.canvas.GetSize()[1]
            x = round(x, 2)
            y = round(y, 2)
            z = round(z, 2)
            label = f'x: {x} y: {y} z: {z}'

            size = self.canvas.GetTextExtent(label)
            if self.object_tooltip is None:
                self.object_tooltip = wx.StaticText(self.canvas, wx.ID_ANY,
                                                    label=label, size=size,
                                                    pos=(0, height - size[1]))
            else:
                self.object_tooltip.SetLabel(label)
                self.object_tooltip.SetPosition((0, height - size[1]))
                self.object_tooltip.SetSize(size)

    def on_release(self, event):
        if self.object_tooltip is not None:
            self.object_tooltip.Destroy()
            self.object_tooltip = None
            self._offset = None

        if event.button == 3 and not self.had_motion:
            menu = wx.Menu()

            wx.MenuItem()

            menu.Append(wx.ID_ANY, 'menu item 1')
            menu.Append(wx.ID_ANY, 'menu item 2')
            menu.Append(wx.ID_ANY, 'menu item 3')
            menu.AppendSeparator()
            menu.Append(wx.ID_ANY, 'menu item 4')
            menu.Append(wx.ID_ANY, 'menu item 5')
            menu.AppendSeparator()

            sub_menu = wx.Menu()
            sub_menu.Append(wx.ID_ANY, 'sub menu item 1')
            sub_menu.Append(wx.ID_ANY, 'sub menu item 2')
            sub_menu.Append(wx.ID_ANY, 'sub menu item 3')
            sub_menu.AppendSeparator()
            sub_menu.Append(wx.ID_ANY, 'sub menu item 4')
            sub_menu.Append(wx.ID_ANY, 'sub menu item 5')

            menu.AppendSubMenu(sub_menu, 'menu item 6')

            x = event.x
            y = event.y

            height = self.canvas.GetSize()[1]

            y = abs(y - height)

            self.canvas.PopupMenu(menu, x, y)
        else:
            self.selected_object = None
            self.button_held = False

        self.had_motion = False
