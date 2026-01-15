
import wx

from . import canvas as _canvas

try:
    from ..geometry import point as _point
    from ..wrappers.wrap_decimal import Decimal as _decimal
    from .. import axis_indicators as _axis_indicators
except ImportError:
    from geometry import point as _point  # NOQA
    from wrappers.wrap_decimal import Decimal as _decimal  # NOQA
    import axis_indicators as _axis_indicators  # NOQA


class CanvasPanel(wx.Panel):

    canvas: _canvas.Canvas = None
    window_screen_position: _point.Point = None

    def __init__(self, parent, size):
        wx.Panel.__init__(self, parent, wx.ID_ANY, size=size, style=wx.BORDER_NONE)
        w_size = size
        view_size = _canvas.Canvas.get_view_size()

        w, h = size
        size = _point.Point(_decimal(w), _decimal(h))
        pos = (size - view_size) / _decimal(2.0)

        self.panel = wx.Panel(self, wx.ID_ANY,
                              size=view_size.as_int[:-1], pos=pos.as_int[:-1])

        self.canvas = _canvas.Canvas(self.panel, parent,
                                     size=view_size.as_int[:-1], pos=(0, 0))

        w, h = w_size
        s = max([w, h])

        x = w
        y = h

        s //= 8

        x -= s
        y -= s + (s / 2)

        self.axis_overlay = _axis_indicators.Overlay(
            self, size=(int(s), int(s)), pos=(int(x), int(y)))

        self.Bind(wx.EVT_SIZE, self.on_size)

    def on_size(self, evt):
        x1, y1 = self.axis_overlay.GetPosition()
        w, h = self.axis_overlay.GetSize()

        x2 = x1 + w
        y2 = y1 + h

        w, h = evt.GetSize()

        if x1 < 0:
            x2 += -x1
            x1 = 0
        if y1 < 0:
            y2 += -y1
            y1 = 0

        if x2 > w:
            x1 += w - x2

        if y2 > h:
            y1 += h - y2

        self.axis_overlay.Move((x1, y1))
        evt.Skip()

    def on_erase_background(self, _):
        pass
