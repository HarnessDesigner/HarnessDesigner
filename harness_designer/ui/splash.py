import wx
import time
import threading

from PIL import Image


class Splash(wx.Frame):

    def __init__(self, parent):

        wx.Frame.__init__(self, parent, wx.ID_ANY, style=wx.FRAME_NO_TASKBAR | wx.FRAME_SHAPED | wx.STAY_ON_TOP)
        import os

        base_path = os.path.dirname(__file__)

        img = Image.open(os.path.join(base_path, '../image/small_splash.png'))

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
        self.init = True

        t = threading.Thread(target=self.run_thread)
        t.daemon = True
        t.start()

        if wx.Platform == "__WXMAC__":
            wx.SafeYield(self, True)

    def run_thread(self):
        while self.init:
            time.sleep(0.1)

        def _do():
            from . import mainframe as _mainframe

            time.sleep(0.5)
            self.SetText('starting mainframe')

            _mainframe._mainframe = _mainframe.MainFrame(self)
            _mainframe._mainframe.Show()  # NOQA

            self.SetText('DONE!')
            time.sleep(0.5)
            self.Show(False)
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
        self.text = text

        self.draw()
        time.sleep(0.2)

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
        self.init = False


if __name__ == '__main__':
    app = wx.App()
    frame = Splash(None)
    app.MainLoop()
