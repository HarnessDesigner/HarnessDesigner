from typing import TYPE_CHECKING

import io
import wx

from . import dxf as _dxf
from .. import image as _image

from wx.lib.agw import aui

if TYPE_CHECKING:
    from .. import ui as _ui

from .rect import Rect
from .cavity import Cavity
from .pan import Pan
from .brush import Brush
from .line import Line
from .pointer import Pointer
from .circle import Circle
from .eraser import Eraser
from .crop import Crop
from .pencil import Pencil


def _get_tool_bitmaps(image):
    image = image.resize(48, 48)
    bmp = image.bitmap
    dis_bmp = image.bitmap
    dis_bmp.ConvertToDisabled(125)
    return bmp, dis_bmp


class CavityEditor(wx.Panel, Rect, Cavity, Pan, Brush, Line, Pointer, Circle, Eraser, Crop, Pencil):

    def __init__(self, mainframe: "_ui.Frame", parent):

        self.mainframe = mainframe
        wx.Panel.__init__(self, parent, wx.ID_ANY, wx.BORDER_NONE)

        self.cavity_map = None
        self.dirty = False
        self.o_background = wx.NullBitmap
        self.background = wx.NullBitmap
        self.draw_layer = wx.NullBitmap
        self.tool_layer = wx.NullBitmap
        self.overlay = wx.NullBitmap
        self.undo_layers = []
        self.max_x = 0
        self.max_y = 0
        self.render_objs = []
        self.dxf = None

        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.scale = 1.0

        self.coords = [0, 0]

        self.view_coords = None
        self.handles = []
        self.grab_pos = None

        self.dc = wx.MemoryDC()
        self.dc.SelectObject(wx.NullBitmap)

        self.Bind(wx.EVT_MOUSEWHEEL, self.on_wheel)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_MOTION, self.on_move)
        self.Bind(wx.EVT_SIZE, self.on_size)

        toolbar = aui.AuiToolBar(mainframe, wx.ID_ANY, agwStyle=aui.AUI_TB_GRIPPER | aui.AUI_TB_PLAIN_BACKGROUND)
        toolbar.SetAuiManager(mainframe.manager)
        self.toolbar = toolbar

        toolbar.SetToolBitmapSize((48, 48))

        self.mode = self.ID_POINTER_TOOL
        self.tool_size = 1

        bmp, dbmp = _get_tool_bitmaps(_image.icons.pointer)
        toolbar.AddTool(self.ID_POINTER_TOOL, 'Pointer', bmp, dbmp, aui.ITEM_RADIO)
        toolbar.Bind(wx.EVT_MENU, self.on_pointer, id=self.ID_POINTER_TOOL)

        bmp, dbmp = _get_tool_bitmaps(_image.icons.pan)
        toolbar.AddTool(self.ID_PAN_TOOL, 'Pan', bmp, dbmp, aui.ITEM_RADIO, short_help_string='Pan image')
        toolbar.Bind(wx.EVT_MENU, self.on_pan, id=self.ID_PAN_TOOL)

        bmp, dbmp = _get_tool_bitmaps(_image.icons.crop)
        toolbar.AddTool(self.ID_CROP_TOOL, 'Crop', bmp, dbmp, aui.ITEM_RADIO, short_help_string='Crop Image')
        toolbar.Bind(wx.EVT_MENU, self.on_crop_tool, id=self.ID_CROP_TOOL)

        bmp, dbmp = _get_tool_bitmaps(_image.icons.cavity)
        toolbar.AddTool(self.ID_CAVITY_TOOL, 'Add Cavity', bmp, dbmp, aui.ITEM_RADIO, short_help_string='Place a cavity location')
        toolbar.Bind(wx.EVT_MENU, self.on_add_cavity, id=self.ID_CAVITY_TOOL)

        bmp, dbmp = _get_tool_bitmaps(_image.icons.pencil)
        toolbar.AddTool(self.ID_PENCIL_TOOL, 'Pencil', bmp, dbmp, aui.ITEM_RADIO, short_help_string='Pencil Tool')
        toolbar.Bind(wx.EVT_MENU, self.on_pencil, id=self.ID_PENCIL_TOOL)

        bmp, dbmp = _get_tool_bitmaps(_image.icons.brush)
        toolbar.AddTool(self.ID_BRUSH_TOOL, 'Brush', bmp, dbmp, aui.ITEM_RADIO, short_help_string='Brush Tool')
        toolbar.Bind(wx.EVT_MENU, self.on_brush, id=self.ID_BRUSH_TOOL)

        bmp, dbmp = _get_tool_bitmaps(_image.icons.line)
        toolbar.AddTool(self.ID_LINE_TOOL, 'Line', bmp, dbmp, aui.ITEM_RADIO, short_help_string='Line Tool')
        toolbar.Bind(wx.EVT_MENU, self.on_line, id=self.ID_LINE_TOOL)

        bmp, dbmp = _get_tool_bitmaps(_image.icons.eraser)
        toolbar.AddTool(self.ID_ERASER_TOOL, 'Eraser', bmp, dbmp, aui.ITEM_RADIO, short_help_string='Eraser Tool')
        toolbar.Bind(wx.EVT_MENU, self.on_eraser, id=self.ID_ERASER_TOOL)

        bmp, dbmp = _get_tool_bitmaps(_image.icons.square)
        toolbar.AddTool(self.ID_RECT_TOOL, 'Rectangle', bmp, dbmp, aui.ITEM_RADIO, short_help_string='Rectangle Tool')
        toolbar.Bind(wx.EVT_MENU, self.on_rectangle, id=self.ID_RECT_TOOL)

        bmp, dbmp = _get_tool_bitmaps(_image.icons.circle)
        toolbar.AddTool(self.ID_CIRCLE_TOOL, 'Circle', bmp, dbmp, aui.ITEM_RADIO, short_help_string='Circle Tool')
        toolbar.Bind(wx.EVT_MENU, self.on_circle, id=self.ID_CIRCLE_TOOL)

        toolbar.AddSeparator()

        bmp, dbmp = _get_tool_bitmaps(_image.icons.antialias)
        toolbar.AddTool(self.ID_ANTIALIAS, 'Antialias', bmp, dbmp, aui.ITEM_CHECK, short_help_string='Antialias')
        toolbar.Bind(wx.EVT_MENU, self.on_antialias, id=self.ID_ANTIALIAS)

        bmp, dbmp = _get_tool_bitmaps(_image.icons.undo_crop)
        toolbar.AddTool(self.ID_UNDO_CROP, 'Undo Crop', bmp, dbmp, aui.ITEM_NORMAL, short_help_string='Undo cropped image')
        toolbar.Bind(wx.EVT_MENU, self.on_undo_crop, id=self.ID_UNDO_CROP)

        toolbar.AddSeparator()

        self.tool_size_ctrl = wx.SpinCtrl(toolbar, wx.ID_ANY, value='1', min=1, max=50, initial=1)
        toolbar.AddControl(self.tool_size_ctrl, 'Size')
        self.tool_size_ctrl.Bind(wx.EVT_SPINCTRL, self.on_tool_size)

        self.layer_ctrl = wx.Choice(toolbar, wx.ID_ANY, choices=['background', 'overlay'])
        self.layer_ctrl.SetStringSelection('overlay')
        toolbar.AddControl(self.layer_ctrl, 'Layer')
        self.layer_ctrl.Bind(wx.EVT_CHOICE, self.on_layer)

        toolbar.Realize()

        mainframe.manager.AddPane(
            toolbar,
            aui.AuiPaneInfo().ToolbarPane().Show().Name('cavity_map_editor_tools').Floatable().Dockable().DestroyOnClose(False).MinimizeButton(False).MaximizeButton(False).CloseButton(False)
        )

        self.antialias = True
        tool = self.toolbar.FindTool(self.ID_ANTIALIAS)
        tool.SetState(aui.AUI_BUTTON_STATE_CHECKED)

        self.pointer_cursor = self.GetCursor()

    def on_layer(self, evt):
        if self.layer_ctrl.GetStringSelection() == 'overlay':
            self.toolbar.EnableTool(self.ID_CROP_TOOL, False)
            self.toolbar.EnableTool(self.ID_CAVITY_TOOL, True)
            self.toolbar.EnableTool(self.ID_UNDO_CROP, False)
            self.toolbar.EnableTool(self.ID_RECT_TOOL, False)
            self.toolbar.EnableTool(self.ID_CIRCLE_TOOL, False)
            self.toolbar.EnableTool(self.ID_LINE_TOOL, False)
            self.toolbar.EnableTool(self.ID_PENCIL_TOOL, False)
        else:
            self.toolbar.EnableTool(self.ID_CROP_TOOL, True)
            self.toolbar.EnableTool(self.ID_CAVITY_TOOL, False)
            self.toolbar.EnableTool(self.ID_UNDO_CROP, True)
            self.toolbar.EnableTool(self.ID_RECT_TOOL, True)
            self.toolbar.EnableTool(self.ID_CIRCLE_TOOL, True)
            self.toolbar.EnableTool(self.ID_LINE_TOOL, True)
            self.toolbar.EnableTool(self.ID_PENCIL_TOOL, True)

        evt.Skip()

    def on_antialias(self, evt):
        self.antialias = self.toolbar.GetToolToggled(self.ID_ANTIALIAS)
        evt.Skip()

    def on_tool_size(self, evt):
        self.tool_size = self.tool_size_ctrl.GetValue()
        evt.Skip()

    def load(self, cavity_map):

        if self.dirty:
            dlg = wx.MessageDialog(
                self.mainframe,
                message='You have unsaved changes in the cavity editor!\n\nWould you like to save the changes??',
                caption='Cavity Editor Unsaved Changes',
                style=wx.YES_NO | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_QUESTION | wx.STAY_ON_TOP | wx.CENTRE)

            res = dlg.ShowModal()
            dlg.Destroy()
            if res == wx.ID_CANCEL:
                return
            elif res == wx.ID_YES:
                self.Save()

        self.dirty = False
        self.render_objs = []
        self.scale = 1.0
        self.coords = [0, 0]
        self.view_coords = None
        self.handles = []
        self.grab_pos = None

        self.max_x = 0
        self.max_y = 0

        self.cavity_map = cavity_map

        dxf_data = cavity_map.dxf

        if dxf_data is not None:
            background = cavity_map.background

            if background is None:
                self.background = wx.NullBitmap
            else:
                self.background = wx.Bitmap.FromPNGData(background)

            overlay = cavity_map.overlay
            if overlay is None:
                self.overlay = wx.NullBitmap
            else:
                self.overlay = wx.Bitmap.FromPNGData(cavity_map.overlay.data)

            dxf_data = io.BytesIO(dxf_data)
            dxf_data.seek(0)

            self.load_dxf(dxf_data)
        else:
            self.background = wx.NullBitmap
            self.overlay = wx.NullBitmap

        if not self.background.IsOk():
            background = cavity_map.background
            if background is not None:
                self.background = wx.Bitmap.FromPNGData(background)
            elif self.overlay.IsOk():
                w, h = self.overlay.GetSize()
                buf = bytearray([0] * (w * h * 4))
                self.background = wx.Bitmap.FromBufferRGBA(w, h, buf)

        if not self.overlay.IsOk():
            overlay = cavity_map.overlay
            if overlay is not None:
                self.overlay = wx.Bitmap.FromPNGData(overlay)
            elif self.background.IsOk():
                w, h = self.background.GetSize()
                buf = bytearray([0] * (w * h * 4))
                self.overlay = wx.Bitmap.FromBufferRGBA(w, h, buf)

        if not self.background.IsOk():
            buf = bytearray([0] * (600 * 400 * 4))
            self.background = wx.Bitmap.FromBufferRGBA(600, 400, buf)

        if not self.overlay.IsOk():
            buf = bytearray([0] * (600 * 400 * 4))
            self.overlay = wx.Bitmap.FromBufferRGBA(600, 400, buf)

        if self.max_x == 0 and self.max_y == 0:
            self.max_x, self.max_y = self.background.GetSize()

        self.o_background = wx.Bitmap(self.background)

        w, h = self.background.GetSize()
        buf = bytearray([0] * (w * h * 4))
        self.draw_layer = wx.Bitmap.FromBufferRGBA(w, h, buf)
        self.tool_layer = wx.Bitmap(self.draw_layer)

        def _do():
            self.Update()
            self.Refresh()
            self.MakeVisible()

        wx.CallAfter(_do)

    def Save(self):
        self.cavity_map.background = _image.utils.wx_bitmap_2_png_bytes(self.background)
        self.cavity_map.overlay = _image.utils.wx_bitmap_2_png_bytes(self.overlay)

    def load_dxf(self, dxf_file):
        self.dxf = _dxf.DXF(dxf_file)

        w = self.dxf.width
        h = self.dxf.height

        if not self.background.IsOk():
            buf = bytearray([0] * (w * h * 4))
            self.background = wx.Bitmap.FromBufferRGBA(w, h, buf)

        if not self.overlay.IsOk():
            buf = bytearray([0] * (w * h * 4))
            self.overlay = wx.Bitmap.FromBufferRGBA(w, h, buf)

        self.max_x = w
        self.max_y = h

    def on_size(self, evt):
        max_w = self.max_x * self.scale
        max_h = self.max_y * self.scale
        w, h = self.GetSize()
        evt.Skip()

    def on_wheel(self, evt):
        self.scale += evt.GetWheelRotation() / 8000.0

        self._update()

        evt.Skip()

    def on_close(self, evt):
        x1, y1, x2, y2 = self.view_coords

        w = x2 - x1
        h = y2 - y1
        buf = bytearray([0] * (w * h * 4))
        bmp = wx.Bitmap.FromBufferRGBA(w, h, buf)

        dc = wx.MemoryDC()
        dc.SelectObject(bmp)

        gcdc = wx.GCDC(dc)
        gcdc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255), 2))
        gcdc.SetBrush(wx.TRANSPARENT_BRUSH)
        gcdc.SetUserScale(self.scale, self.scale)

        x1 = int(x1 / self.scale)
        y1 = int(y1 / self.scale)
        x2 = int(x2 / self.scale)
        y2 = int(y2 / self.scale)

        for obj in self.render_objs:
            obj.collect(gcdc, x1, y1, x2, y2)

        dc.SelectObject(wx.NullBitmap)

        gcdc.Destroy()
        del gcdc

        dc.Destroy()
        del dc

        bmp.SaveFile(r'test.png', wx.BITMAP_TYPE_PNG)
        evt.Skip()

    def update_undo_layers(self):
        if len(self.undo_layers) > 25:
            dc = self.dc
            dc.SelectObject(self.background)
            gcdc = wx.GCDC(dc)

            layer_len = len(self.undo_layers)

            while layer_len > 25:
                layer = self.undo_layers.pop(0)
                gcdc.DrawBitmap(layer, 0, 0)

                layer.Destroy()
                layer_len = len(self.undo_layers)

            dc.SelectObject(wx.NullBitmap)

            gcdc.Destroy()
            del gcdc

    def on_left_down(self, evt):
        if self.mode == self.ID_CROP_TOOL:
            Crop.on_left_down(self, evt)
        elif self.mode == self.ID_BRUSH_TOOL:
            Brush.on_left_down(self, evt)
        elif self.mode == self.ID_LINE_TOOL:
            Line.on_left_down(self, evt)
        elif self.mode == self.ID_ERASER_TOOL:
            Eraser.on_left_down(self, evt)
        elif self.mode == self.ID_PENCIL_TOOL:
            Pencil.on_left_down(self, evt)
        elif self.mode == self.ID_CIRCLE_TOOL:
            Circle.on_left_down(self, evt)
        elif self.mode == self.ID_RECT_TOOL:
            Rect.on_left_down(self, evt)
        elif self.mode == self.ID_PAN_TOOL:
            Pan.on_left_down(self, evt)
        elif self.mode == self.ID_CAVITY_TOOL:
            Cavity.on_left_down(self, evt)
        elif self.mode == self.ID_POINTER_TOOL:
            Pointer.on_left_down(self, evt)

        evt.Skip()

    def on_left_up(self, evt):
        if self.mode == self.ID_CROP_TOOL:
            Crop.on_left_up(self, evt)
        elif self.mode == self.ID_BRUSH_TOOL:
            Brush.on_left_up(self, evt)
        elif self.mode == self.ID_LINE_TOOL:
            Line.on_left_up(self, evt)
        elif self.mode == self.ID_ERASER_TOOL:
            Eraser.on_left_up(self, evt)
        elif self.mode == self.ID_PENCIL_TOOL:
            Pencil.on_left_up(self, evt)
        elif self.mode == self.ID_CIRCLE_TOOL:
            Circle.on_left_up(self, evt)
        elif self.mode == self.ID_RECT_TOOL:
            Rect.on_left_up(self, evt)
        elif self.mode == self.ID_PAN_TOOL:
            Pan.on_left_up(self, evt)
        elif self.mode == self.ID_CAVITY_TOOL:
            Cavity.on_left_up(self, evt)
        elif self.mode == self.ID_POINTER_TOOL:
            Pointer.on_left_up(self, evt)

        evt.Skip()

    def _update(self):
        def _do():
            self.Update()
            self.Refresh()

        wx.CallAfter(_do)

    def on_move(self, evt):
        if self.mode == self.ID_CROP_TOOL:
            Crop.on_move(self, evt)
        elif self.mode == self.ID_BRUSH_TOOL:
            Brush.on_move(self, evt)
        elif self.mode == self.ID_LINE_TOOL:
            Line.on_move(self, evt)
        elif self.mode == self.ID_ERASER_TOOL:
            Eraser.on_move(self, evt)
        elif self.mode == self.ID_PENCIL_TOOL:
            Pencil.on_move(self, evt)
        elif self.mode == self.ID_CIRCLE_TOOL:
            Circle.on_move(self, evt)
        elif self.mode == self.ID_RECT_TOOL:
            Rect.on_move(self, evt)
        elif self.mode == self.ID_PAN_TOOL:
            Pan.on_move(self, evt)
        elif self.mode == self.ID_CAVITY_TOOL:
            Cavity.on_move(self, evt)
        elif self.mode == self.ID_POINTER_TOOL:
            Pointer.on_move(self, evt)

        evt.Skip()

    def on_erase_background(self, _):
        pass

    def on_paint(self, evt):
        dc = wx.BufferedPaintDC(self)
        dc.Clear()

        dc.SetUserScale(self.scale, self.scale)

        dc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255), 2))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)

        for obj in self.render_objs:
            obj.draw(dc)

        dc.SetUserScale(1.0, 1.0)

        gcdc = wx.GCDC(dc)
        gcdc.SetPen(wx.TRANSPARENT_PEN)
        gcdc.SetBrush(wx.Brush(wx.Colour(0, 0, 0, 125)))

        w, h = self.GetClientSize()

        if self.view_coords is None:
            x1 = int(w * 0.25)
            y1 = int(h * 0.25)
            x2 = w - x1
            y2 = h - y1

            self.view_coords = [x1, y1, x2, y2]

        x1, y1, x2, y2 = self.view_coords

        gcdc.DrawRectangle(0, 0, x1, h)
        gcdc.DrawRectangle(x2, 0, abs(x2 - w), h)
        gcdc.DrawRectangle(x1, 0, x2 - x1, y1)
        gcdc.DrawRectangle(x1, y2, x2 - x1, abs(y2 - h))

        gcdc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 200), 2))
        gcdc.SetBrush(wx.TRANSPARENT_BRUSH)

        gcdc.DrawRectangle(x1, y1, x2 - x1, y2 - y1)

        hbw = int((x2 - x1) / 2)
        hbh = int((y2 - y1) / 2)
        x1m = x1 - 6
        x1p = x1 + 6
        y1m = y1 - 6
        y1p = y1 + 6
        x2m = x2 - 6
        x2p = x2 + 6
        y2m = y2 - 6
        y2p = y2 + 6

        self.handles = [
            ((x1, y1), (x1m, y1m, x1p, y1p)),
            ((x1 + hbw, y1), (x1m + hbw, y1m, x1p + hbw, y1p)),
            ((x2, y1), (x2m, y1m, x2p, y1p)),
            ((x2, y1 + hbh), (x2m, y1m + hbh, x2p, y1p + hbh)),
            ((x2, y2), (x2m, y2m, x2p, y2p)),
            ((x1 + hbw, y2), (x1m + hbw, y2m, x1p + hbw, y2p)),
            ((x1, y2), (x1m, y2m, x1p, y2p)),
            ((x1, y1 + hbh), (x1m, y1m + hbh, x1p, y1p + hbh))
        ]

        for line in self.handles:
            handle = line[0]
            gcdc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255), 1))
            gcdc.SetBrush(wx.TRANSPARENT_BRUSH)
            gcdc.DrawCircle(handle[0], handle[1], 5)

            gcdc.SetPen(wx.TRANSPARENT_PEN)
            gcdc.SetBrush(wx.Brush(wx.Colour(0, 0, 0, 255)))
            gcdc.DrawCircle(handle[0], handle[1], 3)

        evt.Skip()
