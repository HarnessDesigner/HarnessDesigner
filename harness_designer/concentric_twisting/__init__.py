from typing import TYPE_CHECKING

import wx

from . import layer as _layer
from ..wrappers.decimal import Decimal as _decimal
from ..geometry import point as _point

if TYPE_CHECKING:
    from ..ui import MainFrame as _Mainframe
    from ..database.project_db import pjt_bundle as _pjt_bundle
    from ..database.project_db import pjt_wire as _pjt_wire


class ConcentricViewPanel(wx.Panel):

    def __init__(self, parent: "_Mainframe"):
        self.mainframe = parent
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_SUNKEN)
        self._bundle = None
        self._layers = None
        self._selected: "_pjt_wire.PJTWire" = None

        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)
        self.Bind(wx.EVT_PAINT, self.on_paint)

        self.hover_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_hover_timer, id=self.hover_timer.GetId())
        self.last_mouse_coords = _point.Point(_decimal(0), _decimal(0))

    def on_erase_background(self, _):
        pass

    def on_paint(self, _):
        pdc = wx.BufferedPaintDC(self)
        gcdc = wx.GCDC(pdc)
        gc = gcdc.GetGraphicsContext()

        gcdc.Clear()

        for layer in self:
            layer.draw(gcdc, gc)

        gcdc.Destroy()
        del gcdc

    def set_bundle(self, bundle: "_pjt_bundle.PJTBundle"):
        self._bundle = bundle
        del self._layers[:]
        self._layers = [_layer.Layer(layer) for layer in bundle.layers]
        self.Refresh(False)

    def on_hover_timer(self, evt: wx.TimerEvent):
        p = self.last_mouse_coords

        for layer in self._layers:
            wire = layer.hit_test(p)

            if wire is None:
                continue

            # TODO: Add properties quick view
        evt.Skip()

    def on_motion(self, evt: wx.MouseEvent):
        self.hover_timer.Stop()
        x, y = evt.GetPosition()
        p = _point.Point(_decimal(x), _decimal(y))

        if not evt.Dragging():
            self.last_mouse_coords = p
            self.hover_timer.Start(500)
        elif evt.LeftIsDown():
            diff = p - self.last_mouse_coords
            self.last_mouse_coords = p

            view_point = self._selected.layer_view_point
            view_point += diff

            self.Refresh(False)

        evt.Skip()

    def on_left_down(self, evt: wx.MouseEvent):
        self.hover_timer.Stop()
        x, y = evt.GetPosition()
        p = _point.Point(_decimal(x), _decimal(y))

        for layer in self._layers:
            self._selected = layer.hit_test(p)
            if self._selected is not None:
                if not self.HasCapture():
                    self.CaptureMouse()

                break

        self.last_mouse_coords = p

        evt.Skip()

    def on_left_up(self, evt: wx.MouseEvent):
        self._selected = None
        if self.HasCapture():
            self.ReleaseMouse()
        evt.Skip()

    def on_right_down(self, evt: wx.MouseEvent):
        self.hover_timer.Stop()
        x, y = evt.GetPosition()

        menu = wx.Menu()
        menu_item = menu.Append(wx.ID_ANY, 'Properties')

        def on_properties(event):
            # TODO: Add properties dialog/window
            event.Skip()

        self.Bind(wx.wxEVT_MENU, on_properties, id=menu_item.GetId())
        self.PopupMenu(menu, x, y)
        evt.Skip()

    @property
    def bundle(self) -> "_pjt_bundle.PJTBundle":
        return self._bundle

    @bundle.setter
    def bundle(self, value: "_pjt_bundle.PJTBundle"):
        self._bundle = value

