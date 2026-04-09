import wx
from PIL import Image
import time
import io
import zipfile
import os
import tempfile

from . import prop_base as _prop_base

from .....image import utils as _image_utils
from ..... import image as _image
from ..... import resources as _resources
from ..... import utils as _utils


wxEVT_IMAGE_PATH_CHANGED = wx.NewEventType()
EVT_IMAGE_PATH_CHANGED = wx.PyEventBinder(wxEVT_IMAGE_PATH_CHANGED, 0)


class PathCtrl(wx.BoxSizer):

    def __init__(self, parent, path):
        self._path = path
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)

        self.path_ctrl = wx.TextCtrl(parent, wx.ID_ANY, value=path, style=wx.TE_LEFT | wx.TE_PROCESS_ENTER)
        self.path_button = wx.Button(parent, wx.ID_ANY, '...')

        self.Add(self.path_ctrl, 0, wx.ALL, 5)
        self.Add(self.path_button, 0, wx.ALL, 5)

        self.path_button.Bind(wx.EVT_BUTTON, self.on_open_file)
        self.path_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_enter)

    def Bind(self, *args, **kwargs):
        self.path_ctrl.Bind(*args, **kwargs)

    def Unbind(self, *args, **kwargs):
        self.path_ctrl.Unbind(*args, **kwargs)

    def on_open_file(self, _):
        value = self.path_ctrl.GetValue()

        if not value or value.startswith('http'):
            default_dir = os.path.expandvars('~')
            default_file = ''
        else:
            default_dir, default_file = os.path.split(value)

            if not os.path.exists(value):
                default_file = ''

                if not os.path.exists(default_dir):
                    default_dir = os.path.expandvars('~')

        dlg = wx.FileDialog(
            self, '', defaultDir=default_dir, defaultFile=default_file,
            wildcard=_utils.IMAGE_FILE_WILDCARDS, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            if path != self._path:
                self._path = path
                self._send_changed_event()

        dlg.Destroy()

    def _send_changed_event(self):
        event = wx.CommandEvent(wxEVT_IMAGE_PATH_CHANGED)
        event.SetValue(self._path)
        event.SetId(self.path_ctrl.GetId())
        event.SetEventObject(self.path_ctrl)
        self.path_ctrl.GetEventHandler().ProcessEvent(event)

    def _on_enter(self, _):
        path = self.path_ctrl.GetValue()
        if path == self._path:
            return

        self._path = path
        self._send_changed_event()


class ImageCtrl(wx.Panel):

    def __init__(self, parent, file_types, original_path, saved_path):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        self.file_types = file_types
        self.bitmap = wx.NullBitmap

        self.original_path = original_path

        if saved_path is None:
            if original_path is None:
                original_path = ''

            self.get_image(original_path)

        else:
            img = Image.open(saved_path).convert('RGBA')
            img = img.resize((100, 100))
            self.bitmap = _image_utils.pil_image_2_wx_bitmap(img)

        self._path = original_path

        self.bmp_ctrl = wx.StaticBitmap(self, wx.ID_ANY, self.bitmap, style=wx.BORDER_SUNKEN)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.bmp_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        vsizer.Add(hsizer, 1, wx.EXPAND)

        self.SetSizer(vsizer)

    def get_image(self, path):
        mime_types = self.file_types
        extensions = {'.' + v: k for k, v in self.file_types}

        if path.startswith('http'):
            time.sleep(0.01)
            try:
                response, content_type = _resources.requests_get(path, timeout=1000)
            except Exception as err:  # NOQA
                self.bitmap = _image.images.no_image.resize(100, 100).bitmap
                return False

            if content_type is not None:
                if content_type in ('application/zip', 'application/x-zip-compressed'):
                    buf = io.BytesIO(response.content)
                    zf = zipfile.ZipFile(buf)
                    names = zf.namelist()
                    for file_name in names:
                        ext = os.path.splitext(file_name)[-1]
                        if ext in extensions:
                            break
                    else:
                        zf.close()
                        buf.close()
                        self.bitmap = _image.images.no_image.resize(100, 100).bitmap
                        return False

                    data = zf.read(file_name)

                elif content_type in mime_types:
                    ext = mime_types[content_type]
                    data = response.content
                else:
                    self.bitmap = _image.images.no_image.resize(100, 100).bitmap
                    return False
            else:
                ext = [e for e in extensions if e[1:] in path]
                if ext:
                    ext = ext[0]
                    data = response.content
                else:
                    self.bitmap = _image.images.no_image.resize(100, 100).bitmap
                    return False

            tempdir = tempfile.gettempdir()
            image_path = os.path.join(tempdir, 'harness_designer_temp_image' + ext)

            with open(image_path, 'wb') as f:
                f.write(data)

        else:

            for ext in extensions:
                if path.endswith(ext):
                    image_path = path
                    break
            else:
                self.bitmap = _image.images.no_image.resize(100, 100).bitmap
                return False

        try:
            img = Image.open(image_path)
        except:  # NOQA
            self.bitmap = _image.images.no_image.resize(100, 100).bitmap
            os.remove(image_path)
            return False

        w, h = img.size

        if w > h:
            aspect_ratio = h / w

            w = 100
            h = int(w * aspect_ratio)
        else:
            aspect_ratio = w / h

            h = 100
            w = int(h * aspect_ratio)

        img = img.resize((w, h), Image.Resampling.LANCZOS)

        new_img = Image.new('RGBA', (100, 100), (0, 0, 0, 0))

        offset_x = 100 - w
        offset_y = 100 - h

        new_img.paste(img, (offset_x, offset_y))

        self.bitmap = _image_utils.pil_image_2_wx_bitmap(new_img)
        return True

    def GetValue(self):
        return self._path

    def SetValue(self, value):
        if self.get_image(value):
            self._path = value
            res = True
        else:
            self._path = ''
            res = False

        self.bmp_ctrl.SetBitmap(self.bitmap)
        return res


class ImageProperty(_prop_base.Property):

    def __init__(self, label, name, value='', file_types={}, save_path=None):
        self._file_types = file_types
        self._save_path = save_path
        self._image_sizer: wx.BoxSizer = None
        self._image: ImageCtrl = None

        _prop_base.Property.__init__(label, name, value, units=None)

    def Show(self):
        self._image.Show()
        _prop_base.Property.Show(self)

    def Hide(self):
        self._image.Hide()
        _prop_base.Property.Hide(self)

    def Create(self, parent):
        _prop_base.Property.Create(self, parent)
        parent = self._parent_window

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self._st = wx.StaticText(parent, wx.ID_ANY, label=self._label + ':')

        self._ctrl = PathCtrl(parent, self._value)
        self._image = ImageCtrl(parent, self._file_types, self._value, self._saved_path)

        self._ctrl.Bind(EVT_IMAGE_PATH_CHANGED, self._on_path_changed)

        self._expand_button = wx.BitmapButton(
            parent, wx.ID_ANY, self._expand_bmp, style=wx.BORDER_NONE, size=(40, 40))

        self._expand_button.Bind(wx.EVT_BUTTON, self._on_expand_button)

        hsizer.Add(self._st, 1, wx.ALL, 5)
        hsizer.Add(self._ctrl, 1, wx.ALL, 5)
        hsizer.Add(self._expand_button, 0, wx.ALL, 5)
        vsizer.Add(hsizer, 1)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self._image, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND)
        self.Add(vsizer)
        self._image_sizer = hsizer

    def _on_path_changed(self, _):
        path = self._ctrl.GetValue()
        if path == self._value:
            return

        if self._image.SetValue(path):
            self._value = path
            self._send_changed_event(str)

    def _on_expand_button(self, _):
        bmp = self._expand_button.GetBitmap()
        if bmp == self._expand_bmp:
            self._expand_button.SetBitmap(self._collapse_bmp)
            self._image_sizer.Show()

        else:
            self._expand_button.SetBitmap(self._expand_bmp)
            self._image_sizer.Hide()

        self.Layout()

    def GetValue(self) -> str:
        return self._value

    def SetValue(self, value: str):
        self._value = value
