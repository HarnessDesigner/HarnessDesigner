import wx
import io
import os
import uuid
import tempfile

from wx.lib.pdfviewer import pdfViewer, pdfButtonPanel

from .. import image as _image


class ImageViewer(wx.Panel):

    def __init__(self, parent, format_type, img):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        if isinstance(img, str):
            self.bmp = wx.Bitmap(img)
            self.filename = None
        elif format_type == 'png':
            self.bmp = wx.Bitmap.FromPNGData(img)
            self.filename = None
        else:
            temp_dir = tempfile.gettempdir()
            file = f'{str(uuid.uuid4())}.{format_type}'
            filename = os.path.join(temp_dir, file)

            with open(filename, 'wb') as f:
                f.write(img)

            self.bmp = wx.Bitmap(filename)
            self.filename = filename

        self.scale = 1.0

        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.hand_cursor = _image.cursors.hand.cursor
        self.grab_cursor = _image.cursors.grab.cursor

        self.SetCursor(self.hand_cursor)

        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.coords = [0, 0]
        self.offset_x = 0
        self.offset_y = 0

        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)

    def on_left_down(self, evt):
        if not self.HasCapture():
            self.CaptureMouse()
            self.SetCursor(self.grab_cursor)
            x, y = evt.GetPosition()
            self.coords = [x, y]

    def on_left_up(self, evt):
        if self.HasCapture():
            self.SetCursor(self.hand_cursor)
            self.ReleaseMouse()
            self.coords = [0, 0]

        evt.Skip()

    def on_motion(self, evt):
        if self.HasCapture():
            x1, y1 = evt.GetPosition()
            x2, y2 = self.coords

            self.coords = [x1, y1]

            diff_x = x2 - x1
            diff_y = y2 - y1
            self.offset_x += diff_x
            self.offset_y += diff_y

            w, h = self.bmp.GetSize()
            cw, ch = self.GetClientSize()

            if self.offset_x > 0:
                self.offset_x = 0
            elif self.offset_x < cw - w:
                self.offset_x = cw - w

            if self.offset_y > 0:
                self.offset_y = 0
            elif self.offset_y < ch - h:
                self.offset_y = ch - h

            def _do():
                self.Update()
                self.Refresh()

            wx.CallAfter(_do)
        evt.Skip()

    def on_mouse_wheel(self, evt: wx.MouseEvent):
        self.scale += evt.GetWheelDelta() / 8000.0

        def _do():
            self.Update()
            self.Refresh()

        wx.CallAfter(_do)

        evt.Skip()

    def on_erase_background(self, _):
        pass

    def on_paint(self, evt):
        dc = wx.BufferedPaintDC(self)
        dc.Clear()

        gcdc = wx.GCDC(dc)

        cw, ch = self.GetClientSize()
        w, h = self.bmp.GetSize()

        if w >= cw:
            x = 0
        else:
            x = int((cw - w) / 2)

        if h >= ch:
            y = 0

        else:
            y = int((ch - h) / 2)

        gcdc.SetUserScale(self.scale, self.scale)

        gcdc.DrawBitmap(self.bmp, x + self.offset_x, y + self.offset_y)
        gcdc.Destroy()
        del gcdc

        evt.Skip()

    def on_close(self, evt):
        self.bmp.Destroy()

        if self.filename is not None:
            os.remove(self.filename)

        evt.Skip()


class PDFViewer(wx.Panel):

    def __init__(self, parent, pdf_file):

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        self.buttonpanel = pdfButtonPanel(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
        vsizer.Add(self.buttonpanel, 0, wx.GROW | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        self.viewer = pdfViewer(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.HSCROLL | wx.VSCROLL | wx.SUNKEN_BORDER)
        vsizer.Add(self.viewer, 1, wx.GROW | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.SetSizer(vsizer)

        self.buttonpanel.viewer = self.viewer
        self.viewer.buttonpanel = self.buttonpanel

        if isinstance(pdf_file, str):
            buf = pdf_file
        else:
            buf = io.BytesIO(pdf_file)
            buf.seek(0)

        wx.BeginBusyCursor()
        self.viewer.LoadFile(buf)
        wx.EndBusyCursor()


class DatasheetViewer(wx.Panel):
    def __init__(self, parent, format_type, datasheet):
        wx.Panel.__init__(self, parent, wx.ID_ANY)

        sizer = wx.BoxSizer(wx.VERTICAL)

        if format_type == 'pdf':
            ctrl = PDFViewer(self, datasheet)
        else:
            ctrl = ImageViewer(self, format_type, datasheet)

        sizer.Add(ctrl, 0, wx.ALL, 10)

        self.SetSizer(sizer)
