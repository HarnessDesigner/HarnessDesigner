from typing import TYPE_CHECKING

import os
import wx
import threading
from PIL import Image

if TYPE_CHECKING:
    from . import logger as _logger

import time


class Splash(wx.Frame):

    def __init__(self, args, logger: "_logger.Log"):
        self.logger = logger
        self.load_database = '--load-database' in args
        self.startup_args = args
        wx.Frame.__init__(self, None, wx.ID_ANY, style=wx.FRAME_NO_TASKBAR | wx.FRAME_SHAPED | wx.STAY_ON_TOP)

        base_path = os.path.dirname(__file__)
        img = Image.open(os.path.join(base_path, 'image/small_splash.png'))

        rgb_data = img.convert('RGB').tobytes()
        alpha_data = img.convert('RGBA').tobytes()[3::4]
        wx_img = wx.Image(img.size[0], img.size[1], rgb_data, alpha_data)
        img.close()

        self.bmp = wx_img.ConvertToBitmap()
        self._dc = dc = wx.MemoryDC()

        self._draw_lock = threading.Lock()
        self._init_event = threading.Event()

        self.Bind(wx.EVT_WINDOW_CREATE, self.on_window_create)

        if wx.Platform != "__WXGTK__":
            self.SetSplashShape()

        w = self.bmp.GetWidth() + 1
        h = self.bmp.GetHeight() + 1

        self._size = (w - 65, h)

        buf = bytearray([0] * (w * h * 4))
        bmp = wx.Bitmap.FromBufferRGBA(w, h, buf)  # NOQA

        dc.SelectObject(bmp)
        gcdc = wx.GCDC(dc)
        gc = gcdc.GetGraphicsContext()
        gc.DrawBitmap(self.bmp, -30, -20, self.bmp.GetWidth(), self.bmp.GetHeight())
        dc.SelectObject(wx.NullBitmap)

        gcdc.Destroy()
        del gcdc

        self.render_bmp = bmp
        self.draw('Loading...')

        # Set The AdvancedSplash Size To The Bitmap Size
        self.SetClientSize((w - 65, h))
        self.CenterOnScreen()

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)

        if wx.Platform == "__WXMAC__":
            wx.SafeYield(self, True)

    def wait(self):
        self._init_event.wait()

    def Destroy(self):
        with self._draw_lock:
            self._dc.Destroy()
            self._dc = None

        wx.Frame.Destroy(self)

    def on_window_create(self, evt):
        if wx.Platform == "__WXGTK__":
            self.SetSplashShape()

        evt.Skip()

    def on_erase_background(self, _):
        pass

    def SetSplashShape(self):
        reg = wx.Region(self.bmp)

        self.SetShape(reg)

    def SetText(self, text: str) -> None:
        self.logger.info(text)
        self.draw(text)

        if threading.main_thread() != threading.current_thread():
            event = threading.Event()

            def _do():
                if self._dc is None:
                    return

                self.Refresh(False)
                event.set()

            wx.CallAfter(_do)
            event.wait()
        elif self._dc is not None:
            self.Refresh(False)

    def flush(self):
        wx.Yield()

    def draw(self, text):
        with self._draw_lock:
            if self._dc is None:
                return

            w, h = self._size
            dc = self._dc

            dc.SelectObject(self.render_bmp)
            gcdc = wx.GCDC(dc)
            gc = gcdc.GetGraphicsContext()

            bmp_height = self.bmp.GetHeight() - 35

            height = h - bmp_height

            gcdc.SetBrush(wx.BLACK_BRUSH)
            gcdc.SetPen(wx.BLACK_PEN)
            gcdc.DrawRectangle(0, bmp_height, w, height)

            gcdc.SetTextForeground(wx.Colour(190, 190, 190, 255))

            tw, th = dc.GetTextExtent(text)
            tx = (w - tw) // 2
            ty = bmp_height + ((height - th) // 2) - 5

            gc.DrawText(text, tx, ty)
            dc.SelectObject(wx.NullBitmap)

            gcdc.Destroy()
            del gcdc

    def OnPaint(self, _):
        with self._draw_lock:
            if self._dc is None:
                return

            dc = wx.BufferedPaintDC(self)
            gcdc = wx.GCDC(dc)
            #
            # gcdc.SetBackground(wx.Brush(wx.Colour(0, 0, 0, 0)))
            # gcdc.Clear()

            gc = gcdc.GetGraphicsContext()
            gc.DrawBitmap(self.render_bmp, 0, 0, self.render_bmp.GetWidth(), self.render_bmp.GetHeight())

            gcdc.Destroy()
            del gcdc

            self._init_event.set()
