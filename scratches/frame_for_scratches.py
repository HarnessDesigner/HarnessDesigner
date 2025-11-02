from typing import Union

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


from matplotlib.backends.backend_wxagg import (  # NOQA
    FigureCanvasWxAgg as FigureCanvas
)
from matplotlib.backends.backend_wxagg import (  # NOQA
    NavigationToolbar2WxAgg as NavigationToolbar
)
from mpl_toolkits.mplot3d import axes3d  # NOQA
from matplotlib.backend_bases import ResizeEvent, MouseEvent, KeyEvent, MouseButton  # NOQA
from mpl_toolkits.mplot3d.axes3d import _Quaternion  # NOQA
from mpl_toolkits.mplot3d import art3d  # NOQA
import matplotlib.pyplot  # NOQA
import matplotlib.artist  # NOQA
import numpy as np  # NOQA
import matplotlib  # NOQA
import itertools  # NOQA
import matplotlib.cbook  # NOQA
from mpl_toolkits.mplot3d import axes3d  # NOQA
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


class wxRealPoint3D(wx.RealPoint):

    def __init__(self, x: Union[int, float, wx.Point, wx.RealPoint, "wxRealPoint3D"],
                 y: int | float | None = None, /, *, z: int | float = None):

        err_msg = f'No matching signature for ({type(x)}, {type(y)}, z={type(z)})'

        if y is None and isinstance(x, (int, float)):
            raise ValueError(err_msg)
        elif not isinstance(x, (int, float)) and y is not None:
            raise ValueError(err_msg)

        if not isinstance(z, (int, float)):
            raise ValueError(err_msg)

        if isinstance(x, (int, float)):
            x = float(x)
            y = float(x)
            wx.RealPoint.__init__(self, float(x), float(y))

        else:
            wx.RealPoint.__init__(self, x)
            x, y = self.Get()

        self._x = x
        self._y = y
        self._z = z

    def GetX(self):
        return self._x

    def GetY(self):
        return self._y

    def GetZ(self):
        return self._z

    def __iter__(self):
        yield self._x
        yield self._y
        yield self._z

    def __str__(self):
        return str(tuple(self))


class PlotMouseEvent(wx.MouseEvent):

    def __init__(self, mouseEventType):
        wx.MouseEvent.__init__(self, mouseEventType)

        self._u_key = None
        self._key_code = None
        self._raw_key_code = None
        self._raw_key_flags = None
        self._pos3d = None
        self._artist = None
        self._m_event = None

    def SetMatplotlibEvent(self, event):
        self._m_event = event

    def GetMatplotlibEvent(self):
        return self._m_event

    def SetUnicodeKey(self, key):
        self._u_key = key

    def GetUnicodeKey(self):
        return self._u_key

    def SetKeyCode(self, key_code):
        self._key_code = key_code

    def GetKeyCode(self):
        return self._key_code

    def SetRawKeyCode(self, key_code):
        self._raw_key_code = key_code

    def GetRawKeyCode(self):
        return self._raw_key_code

    def SetRawKeyFlags(self, flags):
        self._raw_key_flags = flags

    def GetRawKeyFlags(self):
        return self._raw_key_flags

    def GetPosition3D(self) -> "Point":
        return self._pos3d

    def SetPosition3D(self, pt: "Point"):
        self._pos3d = pt

    def SetArtist(self, artist):
        self._artist = artist

    def GetArtist(self):
        return self._artist

    def __str__(self):
        res = [
            f'artist={self.GetArtist()}',
            f'pos3d={str(self.GetPosition3D())}',
            f'pos2d={str(self.GetPosition())}',
            f'keycode={self.GetKeyCode()}',
            f'key={self.GetUnicodeKey()}',
            f'wheel={self.GetWheelDelta()}',
            f'left_down={self.LeftDown()}',
            f'left_dclick={self.LeftDClick()}',
            f'left_is_down={self.LeftIsDown()}',
            f'right_down={self.RightDown()}',
            f'right_dclick={self.RightDClick()}',
            f'right_is_down={self.RightIsDown()}',
            f'alt_down={self.AltDown()}',
            f'control_down={self.ControlDown()}'
        ]
        return ', '.join(res)


class PlotKeyEvent(wx.KeyEvent):

    def __init__(self, keyEventType):
        wx.KeyEvent.__init__(self, keyEventType)
        self._pos3d = None
        self._pos2d = None
        self._artist = None
        self._unicode_key = None
        self._m_event = None

    def SetMatplotlibEvent(self, event):
        self._m_event = event

    def GetMatplotlibEvent(self):
        return self._m_event

    def GetUnicodeKey(self):
        return self._unicode_key

    def SetUnicodeKey(self, char):
        self._unicode_key = char

    def SetPosition(self, pt: tuple[int, int] | wx.Point):
        if isinstance(pt, tuple):
            pt = wx.Point(*[int(item) for item in pt])

        self._pos2d = pt

    def GetPosition(self) -> wx.Point:
        return self._pos2d

    def GetPosition3D(self) -> wxRealPoint3D:
        return self._pos3d

    def SetPosition3D(self, pt: wxRealPoint3D | tuple | list):
        if isinstance(pt, (tuple, list)):
            x, y, z = pt
            pt = wxRealPoint3D(x, y, z=z)

        self._pos3d = pt

    def SetArtist(self, artist):
        self._artist = artist

    def GetArtist(self):
        return self._artist

    def __str__(self):
        res = [
            f'artist={self.GetArtist()}',
            f'pos3d={str(self.GetPosition3D())}',
            f'pos2d={str(self.GetPosition())}',
            f'keycode={self.GetKeyCode()}',
            f'key={self.GetUnicodeKey()}',
            f'alt_down={self.AltDown()}',
            f'control_down={self.ControlDown()}'
        ]
        return ', '.join(res)


def floor_tens(value):
    return _decimal(float(int(value * _decimal(10))) / 10.0)


class Canvas(FigureCanvas):

    def __init__(self, editor, parent, id_, fig, axes):
        super().__init__(parent, id_, fig)
        self.axes = axes
        self.editor = editor

        self.Bind(wx.EVT_ERASE_BACKGROUND, self._on_erase_background)

        self._key_code = wx.WXK_NONE
        self._raw_key_code = wx.WXK_NONE
        self._raw_key_flags = 0
        self._unicode_key = ''
        self._selected_artist = None
        self._tmp_selected_artist = None
        self._inlay_selected = None
        self._inlay_coords = None
        self._inlay_move = None
        self._inlay_corners = None
        self._inlay_corner_grab = 0
        self._scrap_first_move = True
        self._is_drag_event = False
        self.renderer = None

        self.mpl_connect("pick_event", self._on_pick)

    # bypass erasing the background when the plot is redrawn.
    # This helps to eliminate the flicker that is seen when a redraw occurs.
    # the second piece needed to eliminate the flicker is seen below
    def _on_erase_background(self, _):
        pass
    #
    # def draw(self, drawDC=None):
    #     """
    #     Render the figure using RendererWx instance renderer, or using a
    #     previously defined renderer if none is specified.
    #     """
    #
    #     # no need to recreate the renderer over and over
    #     # again when forcing a redraw
    #
    #     if self.renderer is None:
    #         self.renderer = RendererWx(self.bitmap, self.figure.dpi)
    #
    #     self.figure.draw(self.renderer)
    #     self._isDrawn = True
    #     self.gui_repaint(drawDC=drawDC)

    # override the _on_paint method in the canvas
    # this is done so double buffer is used which eliminates the flicker
    # that is seen when the plot redraws
    def _on_paint(self, event):
        drawDC = wx.BufferedPaintDC(self)
        if not self._isDrawn:
            self.draw(drawDC=drawDC)
        else:
            self.gui_repaint(drawDC=drawDC)

        if self._inlay_corners is not None:
            gcdc = wx.GCDC(drawDC)
            gcdc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 255), 2))
            gcdc.SetBrush(wx.TRANSPARENT_BRUSH)

            x1, y1 = self._inlay_corners[0]
            x2, y2 = self._inlay_corners[-1]
            w = x2 - x1 + 1
            h = y2 - y1 + 1
            gcdc.DrawRectangle(int(x1), int(y1), int(w), int(h))
            gcdc.Destroy()
            del gcdc

        drawDC.Destroy()
    #
    # def gui_repaint(self, drawDC=None):
    #     # The "if self" check avoids a "wrapped C/C++ object has been deleted"
    #     # RuntimeError if doing things after window is closed.
    #     if not (self and self.IsShownOnScreen()):
    #         return
    #
    #     if not drawDC:  # not called from OnPaint use a ClientDC
    #         drawDC = wx.ClientDC(self)
    #     # For 'WX' backend on Windows, the bitmap cannot be in use by another
    #     # DC (see GraphicsContextWx._cache).
    #     bmp = (self.bitmap.ConvertToImage().ConvertToBitmap()
    #            if wx.Platform == '__WXMSW__' and isinstance(self.figure.canvas.get_renderer(), RendererWx)
    #            else self.bitmap)
    #     drawDC.DrawBitmap(bmp, 0, 0)
    #     if self._rubberband_rect is not None:
    #         # Some versions of wx+python don't support numpy.float64 here.
    #         x0, y0, x1, y1 = map(round, self._rubberband_rect)
    #         rect = [(x0, y0, x1, y0), (x1, y0, x1, y1),
    #                 (x0, y0, x0, y1), (x0, y1, x1, y1)]
    #         drawDC.DrawLineList(rect, self._rubberband_pen_white)
    #         drawDC.DrawLineList(rect, self._rubberband_pen_black)
    #
    # def draw_idle(self):
    #     self._isDrawn = False  # Force redraw
    #     self.Refresh(eraseBackground=False)

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

    def _mpl_coords(self, pos=None):
        """
        Convert a wx position, defaulting to the current cursor position, to
        Matplotlib coordinates.
        """
        if pos is None:
            pos = wx.GetMouseState()
            x, y = self.ScreenToClient(pos.X, pos.Y)
        else:
            x, y = pos
        # flip y so y=0 is bottom of canvas
        if not wx.Platform == '__WXMSW__':
            scale = self.GetDPIScaleFactor()
            return x*scale, self.figure.bbox.height - y*scale
        else:
            return x, self.figure.bbox.height - y

    def world_coords(self, point=None) -> "Point":
        x, y = self._mpl_coords(point)

        xv, yv = self._get_inaxes(x, y)

        if None in (xv, yv):
            return None

        if not hasattr(self.axes, '_sx') or not hasattr(self.axes, '_sy'):
            self.axes._sx, self.axes._sy = xv, yv

        p1, pane_idx = self.axes._calc_coord(xv, yv, None)  # NOQA
        xs = self.axes.format_xdata(p1[0])
        ys = self.axes.format_ydata(p1[1])
        zs = self.axes.format_zdata(p1[2])

        def get_decimal(val):
            # this is not a minus sign tho it should be.
            if val.startswith('−'):
                val = val[1:].replace('−', '-')
                return _decimal(-float(val))
            # These are actually different.
            elif '−' in val:
                val = val.replace('−', '-')
                return _decimal(float(val))
            else:
                return _decimal(float(val))

        return Point(get_decimal(xs), get_decimal(ys), z=get_decimal(zs))

    def _get_inaxes(self, x, y):
        inaxes = self.inaxes((x, y))

        if inaxes is not None:
            try:
                return inaxes.transData.inverted().transform((x, y))
            except ValueError:
                pass

        return None, None

    def _on_pick(self, evt):
        artist = evt.artist.get_py_data()

        x, y = self._mpl_coords()
        m_event = MouseEvent("button_press_event", self, x, y, MouseButton.LEFT,
                             modifiers=[], guiEvent=None)

        if self._selected_artist == artist:
            self._tmp_selected_artist = self._selected_artist
            return

        if self._selected_artist is not None:
            e = ArtistEvent(wxEVT_COMMAND_ARTIST_UNSET_SELECTED, self._selected_artist.wxid)
            e.SetEventObject(self)
            e.SetArtist(self._selected_artist)
            e.SetPosition3D(self.world_coords())
            e.SetMatplotlibEvent(m_event)
            self._selected_artist = None
            self.GetParent().ProcessEvent(e)

        self._tmp_selected_artist = artist
        e = ArtistEvent(wxEVT_COMMAND_ARTIST_SET_SELECTED, artist.wxid)
        e.SetEventObject(self)
        e.SetArtist(artist)
        e.SetPosition3D(self.world_coords())
        e.SetMatplotlibEvent(m_event)
        m_state = wx.GetMouseState()
        e.SetPosition(self.ScreenToClient(m_state.GetPosition()))
        self.GetParent().ProcessEvent(e)

    def _on_key_down(self, event: wx.KeyEvent):
        event.StopPropagation()

        self._key_code = event.GetKeyCode()
        self._raw_key_code = event.GetRawKeyCode()
        self._raw_key_flags = event.GetRawKeyFlags()

        e = PlotKeyEvent(wx.wxEVT_KEY_DOWN)
        e.SetShiftDown(event.ShiftDown())
        e.SetAltDown(event.AltDown())
        e.SetControlDown(event.ControlDown())
        e.SetKeyCode(event.GetKeyCode())

        if event.GetUnicodeKey():
            self._unicode_key = chr(event.GetUnicodeKey())

            if not event.ShiftDown():
                self._unicode_key = self._unicode_key.lower()

            e.SetUnicodeKey(self._unicode_key)
        else:
            self._unicode_key = None

        e.SetPosition3D(self.world_coords(event.GetPosition()))
        e.SetPosition(event.GetPosition())
        e.SetEventObject(event.GetEventObject())
        e.SetMetaDown(event.MetaDown())
        e.SetRawControlDown(event.ControlDown())
        e.SetRawKeyCode(event.GetRawKeyCode())
        e.SetRawKeyFlags(event.GetRawKeyFlags())
        e.SetRefData(event.GetRefData())
        e.SetArtist(self._selected_artist)
        e.SetId(event.GetId())
        m_event = KeyEvent("key_press_event", self, self._get_key(event),
                           *self._mpl_coords(event.GetPosition()), guiEvent=event)
        e.SetMatplotlibEvent(m_event)
        self.GetParent().ProcessEvent(e)

        m_event._process()  # NOQA

    def _on_key_up(self, event):
        event.StopPropagation()

        self._key_code = None
        self._raw_key_code = None
        self._raw_key_flags = None
        self._unicode_key = None

        e = PlotKeyEvent(wx.wxEVT_KEY_UP)
        e.SetShiftDown(event.ShiftDown())
        e.SetAltDown(event.AltDown())
        e.SetControlDown(event.ControlDown())
        e.SetKeyCode(event.GetKeyCode())

        if event.GetUnicodeKey():
            unicode_key = chr(event.GetUnicodeKey())

            if not event.ShiftDown():
                unicode_key = unicode_key.lower()

            e.SetUnicodeKey(unicode_key)

        e.SetPosition3D(self.world_coords(event.GetPosition()))
        e.SetPosition(event.GetPosition())
        e.SetEventObject(event.GetEventObject())
        e.SetMetaDown(event.MetaDown())
        e.SetRawControlDown(event.ControlDown())
        e.SetRawKeyCode(event.GetRawKeyCode())
        e.SetRawKeyFlags(event.GetRawKeyFlags())
        e.SetRefData(event.GetRefData())
        e.SetArtist(self._selected_artist)
        e.SetId(event.GetId())

        m_event = KeyEvent("key_release_event", self, self._get_key(event),
                           *self._mpl_coords(event.GetPosition()), guiEvent=event)
        e.SetMatplotlibEvent(m_event)
        self.GetParent().ProcessEvent(e)

        m_event._process()  # NOQA

    def _on_mouse_button(self, event: wx.MouseEvent):
        event.StopPropagation()
        if self.HasCapture():
            self.ReleaseMouse()

        x, y = self._mpl_coords(event.GetPosition())
        button_map = {
            wx.MOUSE_BTN_LEFT: MouseButton.LEFT,
            wx.MOUSE_BTN_MIDDLE: MouseButton.MIDDLE,
            wx.MOUSE_BTN_RIGHT: MouseButton.RIGHT,
            wx.MOUSE_BTN_AUX1: MouseButton.BACK,
            wx.MOUSE_BTN_AUX2: MouseButton.FORWARD,
        }
        button = event.GetButton()
        modifiers = self._mpl_modifiers(event)

        if event.ButtonDClick():
            e_text = 'button_press_event'
        elif event.ButtonDown():
            e_text = 'button_press_event'
        else:
            e_text = 'button_release_event'

        if event.ButtonDClick():
            if button == wx.MOUSE_BTN_LEFT:
                m_event = MouseEvent(e_text, self, x, y,
                                     button_map.get(button, button),
                                     modifiers=modifiers, guiEvent=event)
            else:
                m_event = MouseEvent(e_text, self, x, y,
                                     button_map.get(button, button),
                                     dblclick=True, modifiers=modifiers, guiEvent=event)

        else:
            m_event = MouseEvent(e_text, self, x, y,
                                 button_map.get(button, button),
                                 modifiers=modifiers, guiEvent=event)

        if button == wx.MOUSE_BTN_LEFT:
            if event.ButtonDClick():
                m_event._process()  # NOQA

                if self._tmp_selected_artist:
                    if self._tmp_selected_artist == self._selected_artist:
                        # do double click event for artist
                        pass
                    else:
                        self._selected_artist = self._tmp_selected_artist

                    self._tmp_selected_artist = None
                elif self._selected_artist is not None:
                    e = ArtistEvent(wxEVT_COMMAND_ARTIST_UNSET_SELECTED,
                                    self._selected_artist.wxid)
                    e.SetEventObject(self)
                    e.SetArtist(self._selected_artist)
                    e.SetPosition3D(self.world_coords())
                    self._selected_artist = None
                    self.GetParent().ProcessEvent(e)

                e = PlotMouseEvent(wx.wxEVT_LEFT_DCLICK)
            elif event.ButtonDown():
                mx, my = event.GetPosition()
                if self._inlay_corners is None:
                    bbox = self.editor.inlay.get_position()
                    w, h = self.GetSize()

                    bounds = bbox.bounds
                    x1, y1, inlay_w, inlay_h = [value[0] * value[1]
                                                for value in zip(bounds, [w, h, w, h])]

                    if not wx.Platform == '__WXMSW__':
                        scale = self.GetDPIScaleFactor()
                        y1 *= scale
                        y1 = h - y1 * scale
                        y1 -= inlay_h
                    else:
                        y1 = h - y1 - inlay_h

                    x2 = inlay_w + x1
                    y2 = inlay_h + y1
                else:
                    x1, y1 = self._inlay_corners[0]
                    x2, y2 = self._inlay_corners[-1]

                if self._inlay_selected is None:
                    if x1 <= mx <= x2 and y1 <= my <= y2:
                        self._inlay_move = [mx, my]
                        self._inlay_selected = self.editor.inlay
                        self._inlay_corner_grab = 5
                        self._inlay_corners = [[x1, y1], [x2, y1], [x1, y2], [x2, y2]]
                        self._scrap_first_move = True
                        self.axes.get_figure(root=True).canvas.draw_idle()
                        return
                else:
                    inlay_corners = [[x1, y1], [x2, y1], [x1, y2], [x2, y2]]

                    for i, p in enumerate(inlay_corners):
                        px1 = p[0] - 5
                        py1 = p[1] - 5
                        px2 = p[0] + 5
                        py2 = p[1] + 5

                        if px1 <= mx <= px2 and py1 <= my <= py2:
                            self._inlay_corner_grab = i + 1
                            self._inlay_corners = inlay_corners
                            self._scrap_first_move = True
                            self._inlay_move = [mx, my]
                            self.CaptureMouse()
                            return

                    if x1 <= mx <= x2 and y1 <= my <= y2:
                        self._inlay_corner_grab = 5
                        self._inlay_move = [mx, my]
                        self.CaptureMouse()
                        return
                    elif self._inlay_corners is not None:
                        self._inlay_move = None
                        self._inlay_selected = None
                        self._inlay_corners = None
                        self._inlay_corner_grab = 0
                        self.axes.get_figure(root=True).canvas.draw_idle()

                m_event._process()  # NOQA

                if self._tmp_selected_artist:
                    self._selected_artist = self._tmp_selected_artist
                    self._tmp_selected_artist = None
                    self._is_drag_event = True
                    self.CaptureMouse()

                elif self._selected_artist is not None:
                    e = ArtistEvent(wxEVT_COMMAND_ARTIST_UNSET_SELECTED,
                                    self._selected_artist.wxid)
                    e.SetEventObject(self)
                    e.SetArtist(self._selected_artist)
                    e.SetPosition3D(self.world_coords())
                    self._selected_artist = None
                    self.GetParent().ProcessEvent(e)

                e = PlotMouseEvent(wx.wxEVT_LEFT_DOWN)
            elif event.ButtonUp():
                if self._inlay_move is not None:
                    self._inlay_move = None
                    self._inlay_corner_grab = 0
                    return

                self._is_drag_event = False
                e = PlotMouseEvent(wx.wxEVT_LEFT_UP)
            else:
                return

        elif button == wx.MOUSE_BTN_MIDDLE:
            if event.ButtonDown():
                e = PlotMouseEvent(wx.wxEVT_MIDDLE_DOWN)
            elif event.ButtonDClick():
                e = PlotMouseEvent(wx.wxEVT_MIDDLE_DCLICK)
            elif event.ButtonUp():
                e = PlotMouseEvent(wx.wxEVT_MIDDLE_UP)
            else:
                return
        elif button == wx.MOUSE_BTN_RIGHT:
            if event.ButtonDown():
                e = PlotMouseEvent(wx.wxEVT_RIGHT_DOWN)
            elif event.ButtonDClick():
                e = PlotMouseEvent(wx.wxEVT_RIGHT_DCLICK)
            elif event.ButtonUp():
                e = PlotMouseEvent(wx.wxEVT_RIGHT_UP)
            else:
                return
        elif button == wx.MOUSE_BTN_AUX1:
            if event.ButtonDown():
                e = PlotMouseEvent(wx.wxEVT_AUX1_DOWN)
            elif event.ButtonDClick():
                e = PlotMouseEvent(wx.wxEVT_AUX1_DCLICK)
            elif event.ButtonUp():
                e = PlotMouseEvent(wx.wxEVT_AUX1_UP)
            else:
                return
        elif button == wx.MOUSE_BTN_AUX2:
            if event.ButtonDown():
                e = PlotMouseEvent(wx.wxEVT_AUX2_DOWN)
            elif event.ButtonDClick():
                e = PlotMouseEvent(wx.wxEVT_AUX2_DCLICK)
            elif event.ButtonUp():
                e = PlotMouseEvent(wx.wxEVT_AUX2_UP)
            else:
                return
        else:
            return

        e.SetAltDown(event.AltDown())
        e.SetAux1Down(event.Aux1Down())
        e.SetAux2Down(event.Aux2Down())
        e.SetColumnsPerAction(event.GetColumnsPerAction())
        e.SetControlDown(event.ControlDown())
        e.SetEventObject(event.GetEventObject())
        e.SetEventType(event.GetEventType())
        e.SetLeftDown(event.LeftDown())
        e.SetLinesPerAction(event.GetLinesPerAction())
        e.SetMetaDown(event.MetaDown())
        e.SetMiddleDown(event.MiddleDown())
        e.SetPosition3D(self.world_coords(event.GetPosition()))
        e.SetPosition(event.GetPosition())
        e.SetRawControlDown(event.RawControlDown())
        e.SetRefData(event.GetRefData())
        e.SetRightDown(event.RightDown())
        e.SetShiftDown(event.ShiftDown())
        e.SetTimestamp(event.GetTimestamp())
        e.SetWheelAxis(event.GetWheelAxis())
        e.SetWheelDelta(event.GetWheelDelta())
        e.SetWheelRotation(event.GetWheelRotation())
        e.SetArtist(self._selected_artist)
        e.SetMatplotlibEvent(m_event)

        if self._selected_artist is None:
            e.SetId(event.GetId())
        else:
            e.SetId(self._selected_artist.wxid)

        if self._key_code:
            e.SetKeyCode(self._key_code)

        if self._raw_key_code:
            e.SetRawKeyCode(self._raw_key_code)

        if self._raw_key_flags:
            e.SetRawKeyFlags(self._raw_key_flags)

        if self._unicode_key:
            e.SetUnicodeKey(self._unicode_key)

        self.GetParent().ProcessEvent(e)

        if (
            not (event.ButtonDClick() and button == wx.MOUSE_BTN_LEFT) and
            not (event.ButtonDown() and button == wx.MOUSE_BTN_LEFT)
        ):
            m_event._process()  # NOQA

    def _on_mouse_wheel(self, event):
        event.StopPropagation()

        x, y = self._mpl_coords(event.GetPosition())
        # Convert delta/rotation/rate into a floating point step size
        step = event.LinesPerAction * event.WheelRotation / event.WheelDelta
        # Mac gives two events for every wheel event; skip every second one.
        if wx.Platform == '__WXMAC__':
            if not hasattr(self, '_skipwheelevent'):
                self._skipwheelevent = True
            elif self._skipwheelevent:
                self._skipwheelevent = False
                return  # Return without processing event
            else:
                self._skipwheelevent = True

        e = PlotMouseEvent(wx.wxEVT_MOUSEWHEEL)
        e.SetAltDown(event.AltDown())
        e.SetAux1Down(event.Aux1Down())
        e.SetAux2Down(event.Aux2Down())
        e.SetColumnsPerAction(event.GetColumnsPerAction())
        e.SetControlDown(event.ControlDown())
        e.SetEventObject(event.GetEventObject())
        e.SetEventType(event.GetEventType())
        e.SetLeftDown(event.LeftDown())
        e.SetLinesPerAction(event.GetLinesPerAction())
        e.SetMetaDown(event.MetaDown())
        e.SetMiddleDown(event.MiddleDown())
        e.SetPosition3D(self.world_coords(event.GetPosition()))
        e.SetPosition(event.GetPosition())
        e.SetRawControlDown(event.RawControlDown())
        e.SetRefData(event.GetRefData())
        e.SetRightDown(event.RightDown())
        e.SetShiftDown(event.ShiftDown())
        e.SetTimestamp(event.GetTimestamp())
        e.SetWheelAxis(event.GetWheelAxis())
        e.SetWheelDelta(event.GetWheelDelta())
        e.SetWheelRotation(event.GetWheelRotation())
        e.SetArtist(self._selected_artist)

        if self._selected_artist is None:
            e.SetId(event.GetId())
        else:
            e.SetId(self._selected_artist.wxid)

        if self._key_code:
            e.SetKeyCode(self._key_code)

        if self._raw_key_code:
            e.SetRawKeyCode(self._raw_key_code)

        if self._raw_key_flags:
            e.SetRawKeyFlags(self._raw_key_flags)

        if self._unicode_key:
            e.SetUnicodeKey(self._unicode_key)

        m_event = MouseEvent("scroll_event", self, x, y, step=step,  # NOQA
                             modifiers=self._mpl_modifiers(event),
                             guiEvent=event)

        e.SetMatplotlibEvent(m_event)

        if (
            not event.ControlDown() and not event.RawControlDown() and
            not event.AltDown() and not event.MetaDown()
        ):
            h = min(self.axes._pseudo_h, self.axes._pseudo_w)  # NOQA

            scale = h / (h + (step / 100))
            self.axes._scale_axis_limits(scale, scale, scale)  # NOQA

            self.axes.get_figure(root=True).canvas.draw_idle()

            self.GetParent().ProcessEvent(e)
        else:
            self.GetParent().ProcessEvent(e)

            m_event._process()  # NOQA

    def _wx_coords(self, x, y):
        pw, ph = self.GetParent().GetSize()
        w, h = self.GetSize()

        offset_x = (pw - w) // 2
        offset_y = (ph - h) // 2

        return x + offset_x, y + offset_y

    def _on_motion(self, event):
        event.StopPropagation()

        if self._inlay_selected and event.LeftIsDown():
            self._is_drag_event = False

            if self._inlay_move is not None:
                last_x, last_y = self._inlay_move
                new_x, new_y = event.GetPosition()

                if self._scrap_first_move:
                    self._scrap_first_move = False
                    self._inlay_move = [new_x, new_y]
                    return

                x_diff = new_x - last_x
                y_diff = new_y - last_y
                self._inlay_move = [new_x, new_y]

                inlay_corners = self._inlay_corners[:]

                if self._inlay_corner_grab == 1:
                    inlay_corners[0][0] += int(x_diff)
                    inlay_corners[0][1] += int(y_diff)
                    inlay_corners[1][1] += int(y_diff)
                    inlay_corners[2][0] += int(x_diff)
                elif self._inlay_corner_grab == 2:
                    inlay_corners[1][0] += int(x_diff)
                    inlay_corners[1][1] += int(y_diff)
                    inlay_corners[0][1] += int(y_diff)
                    inlay_corners[3][0] += int(x_diff)
                elif self._inlay_corner_grab == 3:
                    inlay_corners[2][0] += int(x_diff)
                    inlay_corners[2][1] += int(y_diff)
                    inlay_corners[3][1] += int(y_diff)
                    inlay_corners[0][0] += int(x_diff)
                elif self._inlay_corner_grab == 4:
                    inlay_corners[3][0] += int(x_diff)
                    inlay_corners[3][1] += int(y_diff)
                    inlay_corners[2][1] += int(y_diff)
                    inlay_corners[1][0] += int(x_diff)
                elif self._inlay_corner_grab == 5:
                    for i in range(4):
                        inlay_corners[i][0] += int(x_diff)
                        inlay_corners[i][1] += int(y_diff)

                x1, y1 = inlay_corners[0]
                x2, y2 = inlay_corners[-1]
                inlay_w = x2 - x1 + 1
                inlay_h = y2 - y1 + 1

                if inlay_w < 30 or inlay_h < 30:
                    return

                self._inlay_corners = inlay_corners[:]

                w, h = self.GetSize()

                if not wx.Platform == '__WXMSW__':
                    scale = self.GetDPIScaleFactor()
                    inlay_y = (h + x1) / scale
                    inlay_y /= scale
                    inlay_y += inlay_h
                else:
                    inlay_y = h - y1 - inlay_h

                xscalar = x1 / w
                yscalar = inlay_y / h
                wscalar = inlay_w / w
                hscalar = inlay_h / h

                self.editor.inlay.set_position([xscalar, yscalar, wscalar, hscalar])
                self.axes.get_figure(root=True).canvas.draw_idle()
            return

        if (
            event.RightIsDown() and
            not event.ControlDown() and not event.RawControlDown() and
            not event.AltDown() and not event.MetaDown() and
            not event.Aux1IsDown() and not event.Aux2IsDown() and
            not event.LeftIsDown() and not event.MiddleIsDown()
        ):
            self.axes.button_pressed = None
            x, y = self._mpl_coords()

            px, py = self.axes.transData.transform([self.axes._sx, self.axes._sy])  # NOQA
            self.axes.start_pan(px, py, 2)
            # pan view (takes pixel coordinate input)
            self.axes.drag_pan(2, None, x, y)
            self.axes.end_pan()

            self.axes._sx, self.axes._sy = self._get_inaxes(x, y)
            # Always request a draw update at the end of interaction
            self.axes.get_figure(root=True).canvas.draw_idle()
            self._is_drag_event = False

        e = PlotMouseEvent(wx.wxEVT_MOTION)
        e.SetAltDown(event.AltDown())
        e.SetAux1Down(event.Aux1IsDown())
        e.SetAux2Down(event.Aux2IsDown())
        e.SetColumnsPerAction(event.GetColumnsPerAction())
        e.SetControlDown(event.ControlDown())
        e.SetEventObject(event.GetEventObject())
        e.SetLeftDown(event.LeftIsDown())
        e.SetLinesPerAction(event.GetLinesPerAction())
        e.SetMetaDown(event.MetaDown())
        e.SetMiddleDown(event.MiddleIsDown())
        e.SetPosition3D(self.world_coords(event.GetPosition()))
        e.SetPosition(event.GetPosition())
        e.SetRawControlDown(event.RawControlDown())
        e.SetRefData(event.GetRefData())
        e.SetRightDown(event.RightIsDown())
        e.SetShiftDown(event.ShiftDown())
        e.SetTimestamp(event.GetTimestamp())
        e.SetWheelAxis(event.GetWheelAxis())
        e.SetWheelDelta(event.GetWheelDelta())
        e.SetWheelRotation(event.GetWheelRotation())

        if self._selected_artist is not None:
            e.SetArtist(self._selected_artist)

        if self._key_code:
            e.SetKeyCode(self._key_code)

        if self._raw_key_code:
            e.SetRawKeyCode(self._raw_key_code)

        if self._raw_key_flags:
            e.SetRawKeyFlags(self._raw_key_flags)

        if self._unicode_key:
            e.SetUnicodeKey(self._unicode_key)

        e.SetId(self.GetId())

        m_event = MouseEvent("motion_notify_event", self, *self._mpl_coords(event.GetPosition()),
                             buttons=self._mpl_buttons(), modifiers=self._mpl_modifiers(event),
                             guiEvent=event)

        e.SetMatplotlibEvent(m_event)

        if self.HasCapture() and event.LeftIsDown():
            if self._selected_artist is not None:
                self._selected_artist.on_motion(e)
                return
            else:
                self._is_drag_event = True

        else:
            self._is_drag_event = False

        m_event._process()  # NOQA

        self.GetParent().ProcessEvent(e)

    def _on_enter(self, event):
        """Mouse has entered the window."""
        event.Skip()
        # LocationEvent("figure_enter_event", self,
        #               *self._mpl_coords(event.GetPosition()),
        #               modifiers=self._mpl_modifiers(),
        #               guiEvent=event)._process()

    def _on_leave(self, event):
        """Mouse has left the window."""
        event.Skip()
        # LocationEvent("figure_leave_event", self,
        #               *self._mpl_coords(event.GetPosition()),
        #               modifiers=self._mpl_modifiers(),
        #               guiEvent=event)._process()

    def _set_capture(self, capture=True):
        pass

    def _on_capture_lost(self, event):
        if self.HasCapture():
            self.ReleaseMouse()

        event.Skip()


class Line3D(art3d.Line3D):
    _py_data = None
    _is_removed = False

    def set_py_data(self, data):
        self._py_data = data
        self.set_picker(True)

    def get_py_data(self):
        return self._py_data

    def remove(self):
        if self._is_removed:
            return
        art3d.Line3D.remove(self)
        self._is_removed = True


setattr(art3d, 'Line3D', Line3D)


class Path3DCollection(art3d.Path3DCollection):
    _py_data = None
    _is_removed = False

    def set_py_data(self, data):
        self._py_data = data
        self.set_picker(True)

    def get_py_data(self):
        return self._py_data

    def remove(self):
        if self._is_removed:
            return
        art3d.Path3DCollection.remove(self)
        self._is_removed = True


setattr(art3d, 'Path3DCollection', Path3DCollection)


class Poly3DCollection(art3d.Poly3DCollection):
    _py_data = None
    _is_removed = False

    def set_py_data(self, data):
        self._py_data = data
        self.set_picker(True)

    def get_py_data(self):
        return self._py_data

    def remove(self):
        if self._is_removed:
            return
        art3d.Poly3DCollection.remove(self)
        self._is_removed = True


setattr(art3d, 'Poly3DCollection', Poly3DCollection)


def remap(value, old_min, old_max, new_min, new_max):
    old_range = old_max - old_min
    new_range = new_max - new_min
    new_value = (((value - old_min) * new_range) / old_range) + new_min
    return new_value


class AxisIndicator(axes3d.Axes3D):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.grid(False)
        self.patch.set_visible(False)
        self.set_axis_off()

        self.plot_surface(*self.plot_cone((-13, 13, 7), 0.0, 0.0,
                                          0.0, 4.0, 3.0),
                          color=(1.0, 0.0, 0.0, 1.0), alpha=1.0, linewidth=0)

        self.plot_surface(*self.plot_cylinder((-13, 13, -13), 0.0, 0.0,
                                              0.0, 20, 1.0),
                          color=(1.0, 0.0, 0.0, 1.0), alpha=1.0, linewidth=0)

        self.plot_surface(*self.plot_cone((-13, -7, -13), -90.0, 0.0,
                                          0.0, 4.0, 3.0),
                          color=(0.0, 1.0, 0.0, 1.0), alpha=1.0, linewidth=0)

        self.plot_surface(*self.plot_cylinder((-13, 13, -13), -90.0, 0.0,
                                              0.0, 20,  1.0),
                          color=(0.0, 1.0, 0.0, 1.0), alpha=1.0, linewidth=0)

        self.plot_surface(*self.plot_cone((7, 13, -13), 0.0, -90.0,
                                          0.0, 4.0, 3.0),
                          color=(0.0, 0.0, 1.0, 1.0), alpha=1.0, linewidth=0)

        self.plot_surface(*self.plot_cylinder((-13, 13, -13), 0.0, -90.0,
                                              0.0, 20, 1.0),
                          color=(0.0, 0.0, 1.0, 1.0), alpha=1.0, linewidth=0)

        x_label = self.text(-14, 14, 14, "Z", color=(1.0, 0.0, 0.0, 1.0))
        y_label = self.text(-14, -14, -14, "Y", color=(0.0, 1.0, 0.0, 1.0))
        z_label = self.text(14, 14, -14, "X", color=(0.0, 0.0, 1.0, 1.0))

        x_label.set_fontsize(12.0)
        y_label.set_fontsize(12.0)
        z_label.set_fontsize(12.0)

        self.set_xlim3d(-13, 13)
        self.set_ylim3d(-13, 13)
        self.set_zlim3d(-13, 13)

    def plot_cone(self, center, x_angle, y_angle, z_angle,
                  height, diameter, flare=1.0):

        Ra = self._rotation_matrix(x_angle, y_angle, z_angle)

        radius = diameter / 2.0

        cx, cy, cz = center

        theta = np.linspace(0, 2 * np.pi, 25)
        z = np.linspace(0, height, 25)
        Theta, Z = np.meshgrid(theta, z)

        flare = max(0.1, flare)
        R = radius * (1 - (Z / height) ** flare)
        X = R * np.cos(Theta)
        Y = R * np.sin(Theta)

        pts = np.stack((X, Y, Z), axis=-1).reshape(-1, 3)
        pts_rot = pts @ Ra
        Xr = pts_rot[:, 0].reshape(X.shape) + cx
        Yr = pts_rot[:, 1].reshape(Y.shape) + cy
        Zr = pts_rot[:, 2].reshape(Z.shape) + cz

        return Xr, Yr, Zr

    def plot_cylinder(self, p1, x_angle, y_angle, z_angle, length, diameter):
        A2B = np.eye(4)
        x, y, z = p1

        R = self._rotation_matrix(x_angle, y_angle, z_angle)

        t = np.array([0, length])
        angles = np.linspace(0, 2 * np.pi, length)
        t, angles = np.meshgrid(t, angles)

        A2B = np.asarray(A2B)
        axis_start = np.dot(A2B, [0, 0, 0, 1])[:3]
        X, Y, Z = self._elongated_circular_grid(axis_start, A2B, t,
                                                diameter / 2.0, angles)

        pts = np.stack((X, Y, Z), axis=-1).reshape(-1, 3)
        pts_rot = pts @ R
        X = pts_rot[:, 0].reshape(X.shape) + x
        Y = pts_rot[:, 1].reshape(Y.shape) + y
        Z = pts_rot[:, 2].reshape(Z.shape) + z

        return X, Y, Z

    @staticmethod
    def _elongated_circular_grid(bottom_point, A2B, height_fractions, radii, angles):
        return [bottom_point[i] + radii * np.sin(angles) * A2B[i, 0] +
                radii * np.cos(angles) * A2B[i, 1] + A2B[i, 2] * height_fractions
                for i in range(3)]

    @staticmethod
    def _rotation_matrix(angle_x, angle_y, angle_z):
        x_angle = np.radians(float(angle_x))
        y_angle = np.radians(float(angle_y))
        z_angle = np.radians(float(angle_z))

        Rx = np.array([[1, 0, 0],
                       [0, np.cos(x_angle), -np.sin(x_angle)],
                       [0, np.sin(x_angle), np.cos(x_angle)]])

        Ry = np.array([[np.cos(y_angle), 0, np.sin(y_angle)],
                       [0, 1, 0],
                       [-np.sin(y_angle), 0, np.cos(y_angle)]])

        Rz = np.array([[np.cos(z_angle), -np.sin(z_angle), 0],
                       [np.sin(z_angle), np.cos(z_angle), 0],
                       [0, 0, 1]])

        return Rz @ Ry @ Rx


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

        '''
        start p1: X: -272.4, Y: 577.7, Z: -140.8
        
        
        stop p1: X: 4.4, Y: 64.0, Z: -19.4
        
        
        
        start p2: X: -256.4, Y: 571.1, Z: -140.8
        stop p2: X: 20.4, Y: 70.7, Z: -19.4


        cylp1: X: -256.4, Y: 571.1, Z: -140.8
        cylp2: X: 20.4, Y: 70.7, Z: -19.4
        
        cylp1: X: -256.4, Y: 571.1, Z: -140.8
        cylp2: X: 20.4, Y: 70.7, Z: -19.4
        
[[-255.84576821 -255.02810147 -254.35910122 -253.91126402 -253.73311998
  -253.84397377 -254.23181266 -254.8546083  -255.6448711  -256.51696384
  -257.37638173 -258.12999351 -258.69613365 -259.01345208 -259.04756243
  -258.7947683  -258.28246387 -257.56616527 -256.72349457 -255.84576821]
 [-185.10352764 -184.2858609  -183.61686065 -183.16902345 -182.99087941
  -183.1017332  -183.48957209 -184.11236773 -184.90263053 -185.77472327
  -186.63414116 -187.38775294 -187.95389308 -188.27121151 -188.30532186
  -188.05252773 -187.5402233  -186.8239247  -185.981254   -185.10352764]
 [-114.36128707 -113.54362033 -112.87462008 -112.42678288 -112.24863884
  -112.35949263 -112.74733152 -113.37012716 -114.16038996 -115.0324827
  -115.89190059 -116.64551237 -117.21165251 -117.52897094 -117.56308129
  -117.31028716 -116.79798273 -116.08168413 -115.23901343 -114.36128707]
 [ -43.6190465   -42.80137976  -42.13237951  -41.68454231  -41.50639827
   -41.61725206  -42.00509095  -42.62788659  -43.41814939  -44.29024213
   -45.14966002  -45.9032718   -46.46941194  -46.78673037  -46.82084072
   -46.56804659  -46.05574216  -45.33944356  -44.49677286  -43.6190465 ]
 [  27.12319407   27.94086081   28.60986106   29.05769827   29.23584231
    29.12498851   28.73714962   28.11435398   27.32409118   26.45199844
    25.59258055   24.83896877   24.27282863   23.9555102    23.92139985
    24.17419398   24.68649841   25.40279701   26.24546771   27.12319407]]

[[571.40657745 571.85887593 572.22893842 572.47666291 572.57520462
  572.51388501 572.29934903 571.95484497 571.51770519 571.03530058
  570.55990715 570.14304116 569.82987651 569.65434945 569.63548106
  569.77531601 570.05870104 570.45492696 570.92105656 571.40657745]
 [443.5185096  443.97080807 444.34087056 444.58859506 444.68713676
  444.62581716 444.41128118 444.06677712 443.62963734 443.14723272
  442.67183929 442.25497331 441.94180866 441.76628159 441.7474132
  441.88724816 442.17063319 442.56685911 443.03298871 443.5185096 ]
 [315.63044175 316.08274022 316.45280271 316.7005272  316.79906891
  316.73774931 316.52321333 316.17870927 315.74156949 315.25916487
  314.78377144 314.36690545 314.0537408  313.87821374 313.85934535
  313.99918031 314.28256533 314.67879126 315.14492085 315.63044175]
 [187.7423739  188.19467237 188.56473486 188.81245935 188.91100106
  188.84968146 188.63514547 188.29064141 187.85350164 187.37109702
  186.89570359 186.4788376  186.16567295 185.99014589 185.9712775
  186.11111246 186.39449748 186.79072341 187.256853   187.7423739 ]
 [ 59.85430604  60.30660452  60.67666701  60.9243915   61.02293321
   60.9616136   60.74707762  60.40257356  59.96543378  59.48302917
   59.00763574  58.59076975  58.2776051   58.10207804  58.08320965
   58.2230446   58.50642963  58.90265555  59.36878515  59.85430604]]

[[-143.78351092 -143.41619987 -142.76538297 -141.90158633 -140.91841572
  -139.92241293 -139.02151031 -138.31333465 -137.87462776 -137.75293035
  -137.96143022 -138.47753316 -139.24531142 -140.18156432 -141.18483432
  -142.14640154 -142.96206527 -143.54343568 -143.82751226 -143.78351092]
 [-143.78351092 -143.41619987 -142.76538297 -141.90158633 -140.91841572
  -139.92241293 -139.02151031 -138.31333465 -137.87462776 -137.75293035
  -137.96143022 -138.47753316 -139.24531142 -140.18156432 -141.18483432
  -142.14640154 -142.96206527 -143.54343568 -143.82751226 -143.78351092]
 [-143.78351092 -143.41619987 -142.76538297 -141.90158633 -140.91841572
  -139.92241293 -139.02151031 -138.31333465 -137.87462776 -137.75293035
  -137.96143022 -138.47753316 -139.24531142 -140.18156432 -141.18483432
  -142.14640154 -142.96206527 -143.54343568 -143.82751226 -143.78351092]
 [-143.78351092 -143.41619987 -142.76538297 -141.90158633 -140.91841572
  -139.92241293 -139.02151031 -138.31333465 -137.87462776 -137.75293035
  -137.96143022 -138.47753316 -139.24531142 -140.18156432 -141.18483432
  -142.14640154 -142.96206527 -143.54343568 -143.82751226 -143.78351092]
 [-143.78351092 -143.41619987 -142.76538297 -141.90158633 -140.91841572
  -139.92241293 -139.02151031 -138.31333465 -137.87462776 -137.75293035
  -137.96143022 -138.47753316 -139.24531142 -140.18156432 -141.18483432
  -142.14640154 -142.96206527 -143.54343568 -143.82751226 -143.78351092]]
        '''

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
        self.axes.get_figure(root=True).canvas.draw_idle()

        editor.Bind(EVT_ARTIST_SET_SELECTED, self.on_set_selected, id=self.wxid)
        editor.Bind(EVT_ARTIST_UNSET_SELECTED, self.on_unset_selected, id=self.wxid)
        editor.Bind(wx.EVT_MOTION, self.on_motion)

    def IsSelected(self, flag=None):
        if flag is None:
            return self._selected
        else:
            self._selected = flag
            for obj in self.objs:
                obj.set_selected_color(flag)

            if not flag:
                self._coord_adj = None

            self.editor.canvas.draw_idle()

    def on_set_selected(self, evt: ArtistEvent):
        if self._branch_mode:
            m_event = evt.GetMatplotlibEvent()
            for branch in self.branches:
                if branch['is_connected']:
                    continue

                cyl = branch['cylinder']
                if not cyl.artist.contains(m_event)[0]:
                    continue

                self.editor.bundle_dialog.SetTransitionBranch(self, branch)
                return

        if not self._selected:
            self.editor.SetSelected(self, True)

            diff = evt.GetPosition3D() - self.origin
            self._coord_adj = diff
            self._last_mouse_pos = evt.GetPosition3D()

        evt.Skip()

    def on_unset_selected(self, evt: ArtistEvent):
        if self._selected:
            self.editor.SetSelected(self, False)

            self._coord_adj = None
            self._last_mouse_pos = None

        evt.Skip()

    def on_motion(self, evt: PlotMouseEvent):
        if not evt.LeftIsDown() or not self._selected:
            return

        key = evt.GetUnicodeKey()
        if key in (0, None):
            return

        key = key.lower()
        if key not in ('x', 'y', 'z'):
            return

        p = evt.GetPosition3D()
        if p is None:
            return

        p1 = p - self._coord_adj
        p2 = self._last_mouse_pos - self._coord_adj
        p1 -= p2

        if key == 'x':
            p1.y = _decimal(0.0)
            p1.z = _decimal(0.0)
        elif key == 'y':
            p1.x = _decimal(0.0)
            p1.z = _decimal(0.0)
        elif key == 'z':
            p1.x = _decimal(0.0)
            p1.y = _decimal(0.0)

        points = []

        for obj in self.objs:
            if isinstance(obj, Cylinder):
                if obj.p1 not in points:
                    obj.p1 += p1
                    points.append(obj.p1)
                if obj.p2 not in points:
                    obj.p2 += p1
                    points.append(obj.p2)
            else:
                if obj.center not in points:
                    obj.center += p1
                    points.append(obj.center)

        self._last_mouse_pos = p
        self.axes.get_figure(root=True).canvas.draw_idle()

    def highlight_branches(self, flag):

        self._branch_mode = flag

        for branch in self.branches:
            if not branch['is_connected']:
                branch['cylinder'].set_selected_color(flag)

    def get_branch(self, p1):
        x, y, z = p1

        for branch in self.branches:
            cyl = branch['cylinder']
            p2 = cyl.p2
            x3, y3, z3 = p2
            dia = branch['max_dia']
            offset = dia / _decimal(2.0)
            x1 = x3 - offset
            x2 = x3 + offset
            y1 = y3 - offset
            y2 = y3 + offset
            z1 = z3 - offset
            z2 = z3 + offset

            if x1 <= x <= x2 and y1 <= y <= y2 and z1 <= z <= z2:
                return branch

    def hit_test(self, p):
        branch = self.get_branch(p)
        if branch is None:
            return False

        return True


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
        res = [
            [
                _decimal(12.4),
                _decimal(26.9),
                _decimal(38.1),
                _decimal(26.6),
                Point(_decimal(15.2), _decimal(0.0), _decimal(0.0)),
                _decimal(-180.0),
                Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
            ],
            [
                _decimal(6.1),
                _decimal(13.2),
                _decimal(43.2),
                _decimal(32.4),
                Point(_decimal(0.0), _decimal(0.0), _decimal(0.0)),
                _decimal(-22.5),
                Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
            ],
            [
                _decimal(6.1),
                _decimal(13.2),
                _decimal(43.2),
                _decimal(32.4),
                Point(_decimal(0.0), _decimal(0.0), _decimal(0.0)),
                _decimal(22.5),
                Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
            ]
        ]

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
