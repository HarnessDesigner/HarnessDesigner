from typing import TYPE_CHECKING

import os
import wx
import time
import threading
from PIL import Image

from . import critical_error_dialog as _critical_error_dialog

if TYPE_CHECKING:
    from . import logger as _logger


class Splash(wx.Frame):

    def __init__(self, args):
        self.load_database = '--load-database' in args
        self.startup_args = args

        wx.Frame.__init__(self, None, wx.ID_ANY, style=wx.FRAME_NO_TASKBAR | wx.FRAME_SHAPED | wx.STAY_ON_TOP)

        self.logger: "_logger.Log" = None
        self.init_event = threading.Event()

        base_path = os.path.dirname(__file__)

        img = Image.open(os.path.join(base_path, 'image/small_splash.png'))

        rgb_data = img.convert('RGB').tobytes()
        alpha_data = img.convert('RGBA').tobytes()[3::4]
        wx_img = wx.Image(img.size[0], img.size[1], rgb_data, alpha_data)
        self.bmp = wx_img.ConvertToBitmap()
        self._dc = dc = wx.MemoryDC()

        img.close()

        self._draw_lock = threading.Lock()
        self.bmp_lock = threading.Lock()

        self.main_thread = threading.current_thread()
        self.Bind(wx.EVT_WINDOW_CREATE, self.on_window_create)

        if wx.Platform != "__WXGTK__":
            self.SetSplashShape()

        w = self.bmp.GetWidth() + 1
        h = self.bmp.GetHeight() + 1

        self._size = (w - 65, h)

        buf = bytearray([0] * (w * h * 4))
        bmp = wx.Bitmap.FromBufferRGBA(w, h, buf)

        dc.SelectObject(bmp)
        gcdc = wx.GCDC(dc)
        gc = gcdc.GetGraphicsContext()
        gc.DrawBitmap(self.bmp, -30, -20, self.bmp.GetWidth(), self.bmp.GetHeight())
        dc.SelectObject(wx.NullBitmap)

        gcdc.Destroy()
        del gcdc

        self.render_bmp = bmp

        # Set The AdvancedSplash Size To The Bitmap Size
        self.SetClientSize((w - 65, h))
        self.CenterOnScreen()

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)

        self.event = threading.Event()

        self.draw('Loading...')

        self.yield_count = 0

        if wx.Platform == "__WXMAC__":
            wx.SafeYield(self, True)

    def Destroy(self):
        self._dc.Destroy()
        wx.Frame.Destroy(self)

    def set_logger(self, value: "_logger.Log"):
        self.logger = value

        # we start the thread once the logger has been set.
        t = threading.Thread(target=self.run_thread)
        t.daemon = True
        t.start()

    def run_thread(self):
        self.init_event.wait()

        event = threading.Event()

        try:
            from .ui import mainframe as _mainframe
        except Exception as err:  # NOQA
            self.logger.traceback(err)

            dlg = _critical_error_dialog.CriticalErrorDialog(self, err)

            dlg.ShowModal()
            dlg.Destroy()

            self.Show(False)
            self.Destroy()

            app = wx.GetApp()
            app.ExitMainLoop()
            return

        has_error = [False]

        def _do():
            time.sleep(0.25)
            self.SetText('Starting Mainframe')

            try:
                _mainframe._mainframe = _mainframe.MainFrame(self, self.logger)
            except Exception as err:  # NOQA
                self.logger.traceback(err)
                dlg = _critical_error_dialog.CriticalErrorDialog(self, err)

                dlg.ShowModal()
                dlg.Destroy()
                has_error[0] = True

            event.set()

        wx.CallAfter(_do)

        event.wait()

        if has_error[0]:
            self.Show(False)
            self.Destroy()

            app = wx.GetApp()
            app.ExitMainLoop()
        else:
            _mainframe._mainframe.open_database(self)  # NOQA

            self.SetText('DONE!')
            time.sleep(0.50)

            def _do():
                self.Show(False)
                _mainframe._mainframe.Show()  # NOQA
                self.Destroy()

            wx.CallAfter(_do)

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

        if self.main_thread != threading.current_thread():
            wx.CallAfter(self.Refresh, False)
            self.yield_count += 1
            if self.yield_count == 10:
                self.yield_count = 0
                wx.GetApp().Yield(False)
        else:
            self.Refresh(False)

    def draw(self, text):
        with self._draw_lock:
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
            dc = wx.BufferedPaintDC(self)
            gcdc = wx.GCDC(dc)
            #
            # gcdc.SetBackground(wx.Brush(wx.Colour(0, 0, 0, 0)))
            # gcdc.Clear()

            gc = gcdc.GetGraphicsContext()
            gc.DrawBitmap(self.render_bmp, 0, 0, self.render_bmp.GetWidth(), self.render_bmp.GetHeight())

            gcdc.Destroy()
            del gcdc

            self.init_event.set()
