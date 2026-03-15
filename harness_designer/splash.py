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

    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, style=wx.FRAME_NO_TASKBAR | wx.FRAME_SHAPED | wx.STAY_ON_TOP)

        self.logger: "_logger.Log" = None
        self.init_event = threading.Event()

        base_path = os.path.dirname(__file__)

        img = Image.open(os.path.join(base_path, 'image/small_splash.png'))

        rgb_data = img.convert('RGB').tobytes()
        alpha_data = img.convert('RGBA').tobytes()[3::4]
        wx_img = wx.Image(img.size[0], img.size[1], rgb_data, alpha_data)
        self.bmp = wx_img.ConvertToBitmap()

        img.close()

        self.Bind(wx.EVT_WINDOW_CREATE, self.on_window_create)

        if wx.Platform != "__WXGTK__":
            self.SetSplashShape()

        w = self.bmp.GetWidth() + 1
        h = self.bmp.GetHeight() + 1

        # Set The AdvancedSplash Size To The Bitmap Size
        self.SetClientSize((w - 65, h))

        self.CenterOnScreen()

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)
        self.text = 'Loading....'

        self.main_thread = threading.current_thread()
        self.text_lock = threading.Lock()

        self.event = threading.Event()

        if wx.Platform == "__WXMAC__":
            wx.SafeYield(self, True)

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
            self.logger.print_traceback(err)

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
            self.SetText('starting mainframe')
            try:
                _mainframe._mainframe = _mainframe.MainFrame(self, self.logger)
            except Exception as err:  # NOQA
                self.logger.print_traceback(err)
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
        if self.main_thread != threading.current_thread():

            def _do(t):
                self.logger.print_info(t)
                self.text = t
                self.draw()
                self.event.set()

            wx.CallAfter(_do, text)
            self.event.wait(0.2)
            self.event.clear()
        else:
            self.logger.print_info(text)
            self.text = text
            self.draw()
            time.sleep(0.05)

    def draw(self, dc=None):
        if dc is None:
            dc = wx.ClientDC(self)

        gcdc = wx.GCDC(dc)
        gc = gcdc.GetGraphicsContext()

        w, h = self.GetClientSize()

        bmp_height = self.bmp.GetHeight() - 30

        gcdc.SetTextForeground(wx.Colour(190, 190, 190, 255))
        tw = dc.GetTextExtent(self.text)[0]

        tx = (w // 2) - (tw // 2)

        ty = bmp_height

        gcdc.SetBrush(wx.Brush(wx.Colour(0, 0, 0, 255)))
        gcdc.DrawRectangle(0, bmp_height, w, h - bmp_height)

        gc.DrawText(self.text, tx, ty)

        gcdc.Destroy()
        del gcdc

    def OnPaint(self, _):
        dc = wx.BufferedPaintDC(self)
        gcdc = wx.GCDC(dc)

        gcdc.SetBackground(wx.Brush(wx.Colour(0, 0, 0, 0)))
        gcdc.Clear()

        gc = gcdc.GetGraphicsContext()

        gc.DrawBitmap(self.bmp, -30, -20, self.bmp.GetWidth(), self.bmp.GetHeight())

        gcdc.Destroy()
        del gcdc

        self.draw(dc)
        self.init_event.set()
