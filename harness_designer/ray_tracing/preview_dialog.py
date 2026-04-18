import wx
from PIL import Image

from ..ui import headers as _headers


class RayTracingPreviewDialog(wx.Dialog):
    """Dialog showing live ray tracing progress"""

    def __init__(self, parent, title="Ray Tracing Progress"):
        super().__init__(parent, title=title, size=(1200, 650))

        self.header = _headers.Header1200x80(self, 'Render')

        self.cancelled = False
        self.current_image = None

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.status_text = wx.StaticText(panel, label="Initializing ray tracer...")
        self.status_text.SetFont(self.status_text.GetFont().Bold())
        sizer.Add(self.status_text, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        self.image_panel = wx.Panel(panel, size=(1180, 480))
        self.image_panel.SetBackgroundColour(wx.Colour(45, 49, 53))
        self.image_panel.Bind(wx.EVT_PAINT, self.on_paint)
        self.image_panel.Bind(wx.EVT_ERASE_BACKGROUND, lambda x: None)

        sizer.Add(self.image_panel, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        self.progress = wx.Gauge(panel, range=100)
        sizer.Add(self.progress, 0, wx.EXPAND | wx.ALL, 10)

        self.progress_text = wx.StaticText(panel, label="0%")
        sizer.Add(self.progress_text, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Cancel")
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        button_sizer.Add(self.cancel_btn, 0, wx.ALL, 5)

        self.save_btn = wx.Button(panel, wx.ID_OK, "Save Image")
        self.save_btn.Enable(False)
        button_sizer.Add(self.save_btn, 0, wx.ALL, 5)

        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)

        panel.SetSizer(sizer)
        self.Center()

    def on_paint(self, _):
        dc = wx.BufferedPaintDC(self.image_panel)

        if self.current_image:
            panel_size = self.image_panel.GetSize()
            img_width = self.current_image.GetWidth()
            img_height = self.current_image.GetHeight()

            scale_x = panel_size.width / img_width
            scale_y = panel_size.height / img_height
            scale = min(scale_x, scale_y)

            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            scaled_img = self.current_image.Scale(new_width, new_height, wx.IMAGE_QUALITY_HIGH)
            bitmap = wx.Bitmap(scaled_img)

            x = (panel_size.width - new_width) // 2
            y = (panel_size.height - new_height) // 2

            dc.DrawBitmap(bitmap, x, y)
        else:
            dc.SetTextForeground(wx.WHITE)
            dc.DrawText("Waiting for render...", 10, 10)

    def update_progress(self, image_array, progress):
        if self.cancelled:
            return False

        height, width = image_array.shape[:2]
        image = Image.fromarray(image_array, 'RGB')
        wx_image = wx.Image(width, height)
        wx_image.SetData(image.tobytes())

        self.current_image = wx_image
        wx.CallAfter(self._update_ui, progress)

        return not self.cancelled

    def _update_ui(self, progress):
        self.progress.SetValue(int(progress))
        self.progress_text.SetLabel(f"{progress:.1f}%")
        self.status_text.SetLabel(f"Ray tracing... {progress:.1f}% complete")

        self.image_panel.Refresh()
        self.image_panel.Update()

        if progress >= 100:
            self.status_text.SetLabel("Render complete!")
            self.cancel_btn.SetLabel("Close")
            self.save_btn.Enable(True)

    def on_cancel(self, _):
        self.cancelled = True
        self.EndModal(wx.ID_CANCEL)

    def get_image(self):
        return self.current_image
