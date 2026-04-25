from typing import TYPE_CHECKING

import wx
import os
import sys

from .. import utils as _utils
from ..ui import headers as _headers
from ..ui.dialogs import render_setings as _render_settings
from . import renderer as _renderer
from . import scene as _scene
from .. import config as _config

if TYPE_CHECKING:
    from .. import ui as _ui


Config = _config.Config.ray_trace


class RayTracingDialog(wx.Dialog):
    """Dialog showing live ray tracing progress"""

    def __init__(self, parent: "_ui.MainFrame", title="Ray Tracing Progress"):
        self._parent = parent
        super().__init__(parent, title='', size=(1200, 650))

        if sys.platform.startswith('win'):
            last_saved_dir = '~/Pictures'
        else:
            last_saved_dir = '~'

        self.last_saved_dir = os.path.expandvars(last_saved_dir)
        self.last_saved_file = 'new_render.png'

        self.header = _headers.Header1200x80(self, title)

        self.cancelled = False
        self.current_image: wx.Image = None

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.header, 0, wx.EXPAND)

        self.status_text = wx.StaticText(panel, label="Initializing ray tracer...")
        self.status_text.SetFont(self.status_text.GetFont().Bold())
        sizer.Add(self.status_text, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        self.image_panel = wx.Panel(panel, size=(1180, 480))
        self.image_panel.SetBackgroundColour(wx.Colour(45, 49, 53))
        self.image_panel.Bind(wx.EVT_PAINT, self.on_paint)
        self.image_panel.Bind(wx.EVT_ERASE_BACKGROUND, lambda x: None)

        sizer.Add(self.image_panel, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        self.progress = wx.Gauge(panel, range=100)

        progress_sizer = wx.BoxSizer(wx.HORIZONTAL)
        progress_sizer.Add(self.progress, 1, wx.ALL, 5)

        self.progress_text = wx.StaticText(panel, label="0%")
        progress_sizer.Add(self.progress_text, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        sizer.Add(progress_sizer, 0, wx.EXPAND)

        hline = wx.StaticLine(self, wx.ID_ANY, size=(-1, 1), style=wx.LI_HORIZONTAL)
        sizer.Add(hline, 0, wx.ALL | wx.EXPAND, 10)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.AddStretchSpacer(1)

        self.settings_btn = wx.Button(panel, wx.ID_ANY, "Settings")
        self.settings_btn.Bind(wx.EVT_BUTTON, self.on_settings)
        button_sizer.Add(self.settings_btn, 0, wx.ALL, 5)

        vline = wx.StaticLine(self, wx.ID_ANY, size=(1, -1), style=wx.LI_VERTICAL)
        button_sizer.Add(vline, 0, wx.ALL, 5)

        self.mfb1 = wx.Button(panel, wx.ID_ANY, "Close")
        self.mfb1.Bind(wx.EVT_BUTTON, self.on_mfb1)
        button_sizer.Add(self.mfb1, 0, wx.ALL, 5)

        self.mfb2 = wx.Button(panel, wx.ID_ANY, "Start")
        self.mfb2.Bind(wx.EVT_BUTTON, self.on_mfb2)
        button_sizer.Add(self.mfb2, 0, wx.ALL, 5)

        sizer.Add(button_sizer, 0, wx.ALL | wx.EXPAND, 5)

        panel.SetSizer(sizer)
        self.CenterOnScreen()

    def on_settings(self, evt):
        dlg = _render_settings.RenderSettingsDialog(self)
        dlg.ShowModal()

    def on_mfb2(self, _):
        label = self.mfb2.GetLabel()
        if label == 'Start':
            # start rendering
            self.mfb2.SetLabel('Cancel')
            self.mfb1.SetLabel('Save')
            self.mfb1.Enable(False)
            self.settings_btn.Enable(False)

            for res in Config.resolutions:
                if res['label'] == Config.default_resolution:
                    break
            else:
                res = dict(width=1920, height=1080)

            width = res['width']
            height = res['height']

            self.current_image = wx.Image(width, height)

            scene = _scene.Scene(width, height, self._parent.editor3d.camera)

            if Config.environment_map.enable:
                if Config.environment_map.generate or not Config.environment_map.path:
                    scene.generate_environment((width, height))

                elif Config.environment_map.path:
                    scene.load_environment_map(Config.environment_map.path)

            for obj in self._parent.editor3d.camera.objects_in_view:
                scene.add_object(obj.obj3d)

            renderer = _renderer.Renderer(scene, self.update_progress)

            renderer.start()

        elif label == 'Cancel':
            self.cancelled = True
            self.mfb2.SetLabel('Start')
            self.mfb1.SetLabel('Close')
            self.current_image = None
            self.mfb1.Enable(True)
            self.settings_btn.Enable(True)

    def on_mfb1(self, _):
        label = self.mfb1.GetLabel()

        if label == 'Close':
            self.cancelled = True
            self.EndModal(wx.ID_CANCEL)
        elif label == 'Save':
            # dialog for saving file
            self.mfb1.SetLabel('Close')
            self.mfb2.SetLabel('Start')

            dlg = wx.FileDialog(
                self, message='Save Render', defaultDir=self.last_saved_dir,
                defaultFile=self.last_saved_file, wildcard=_utils.IMAGE_FILE_WILDCARDS,
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()

                self.last_saved_dir, self.last_saved_file = os.path.split(path)

                if self.current_image:
                    self.current_image.SaveFile(path)

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

    def update_progress(self, start_y, image_array, progress):
        if self.cancelled:
            self.cancelled = False
            return False

        height, width = image_array.shape[:2]
        image = wx.Image(width, height, image_array)

        self.current_image.Paste(image, 0, start_y)
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
            self.mfb1.SetLabel('Save')
            self.mfb1.Enable(True)
            self.mfb2.SetLabel('Start')
            self.settings_btn.Enable(True)

    def get_image(self):
        return self.current_image
