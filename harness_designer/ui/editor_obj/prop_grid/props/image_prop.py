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


class PathEvent(wx.CommandEvent):

    def __init__(self, evt_type):
        wx.CommandEvent.__init__(self, evt_type)
        self._value = None

    def SetValue(self, value):
        self._value = value

    def GetValue(self):
        return self._value


class PathCtrl(wx.Panel):

    def __init__(self, parent, path):
        self._path = path
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        vsizer = wx.BoxSizer(wx.VERTICAL)

        self.path_ctrl = wx.TextCtrl(self, wx.ID_ANY, value=path, style=wx.TE_LEFT | wx.TE_PROCESS_ENTER)
        self.path_button = wx.Button(self, wx.ID_ANY, '...')

        hsizer.Add(self.path_ctrl, 1, wx.ALL, 5)
        hsizer.Add(self.path_button, 0, wx.ALL, 5)
        vsizer.Add(hsizer, 0, wx.EXPAND)
        self.SetSizer(vsizer)

        self.path_button.Bind(wx.EVT_BUTTON, self.on_open_file)
        self.path_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_enter)

    def SetValue(self, value: str):
        self._path = value
        self.path_ctrl.ChangeValue(value)

    def GetValue(self):
        return self._path

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
        event = PathEvent(wxEVT_IMAGE_PATH_CHANGED)
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

    def SetFileTypes(self, file_types):
        self.file_types = file_types

    def get_image(self, path):
        mime_types = self.file_types
        extensions = {'.' + v: k for k, v in self.file_types.items()}

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

    def __init__(self, parent, label, value: str, file_types: dict, save_path=None):
        _prop_base.Property.__init__(self, parent, label)

        self._value = value
        self._file_types = file_types
        self._save_path = save_path

        self._st = wx.StaticText(self, wx.ID_ANY, label=label + ':')

        self._ctrl = PathCtrl(self, value)
        self._image = ImageCtrl(self, file_types, value, save_path)

        self._ctrl.Bind(EVT_IMAGE_PATH_CHANGED, self._on_path_changed)

    def SetFileTypes(self, file_types):
        self._file_types = file_types
        self._image.SetFileTypes(file_types)

    def Realize(self):
        hsizer1 = wx.BoxSizer(wx.HORIZONTAL)

        hsizer1.Add(self._st, 0, wx.ALL, 5)
        hsizer1.Add(self._ctrl, 1, wx.ALL, 5)
        self._sizer.Add(hsizer1, 0, wx.EXPAND)

        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        hsizer2.Add(self._image, 1)
        self._sizer.Add(hsizer2, 0, wx.EXPAND)

    def _on_path_changed(self, _):
        path = self._ctrl.GetValue()
        if path == self._value:
            return

        if self._image.SetValue(path):
            self._value = path
            self._send_changed_event(str, path)

    def GetValue(self) -> str:
        return self._value

    def SetValue(self, value: list[str, str]):
        self._value = value[0]
        self._save_path = value[1]

        if value[1] is None:
            self._image.SetValue(value[0])
        else:
            self._image.SetValue(value[1])

        self._ctrl.SetValue(value[0])
