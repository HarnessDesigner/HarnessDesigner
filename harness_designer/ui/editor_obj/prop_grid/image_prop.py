import wx
from wx import propgrid as wxpg

from PIL import Image
import time
import io
import zipfile
import os
import tempfile
from ....image import utils as _image_utils
from .... import image as _image
from .... import resources as _resources
from .... import utils as _utils


class ImageCtrl(wx.Panel):

    def __init__(self, parent, file_types, original_path, saved_path, size, pos):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE, size=size, pos=pos)

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

        self.new_value = original_path

        self.bmp_ctrl = wx.StaticBitmap(self, wx.ID_ANY, self.bitmap, style=wx.BORDER_SUNKEN)
        self.path_ctrl = wx.TextCtrl(self, wx.ID_ANY, value=original_path, style=wx.TE_LEFT | wx.TE_PROCESS_ENTER)
        self.path_button = wx.Button(self, wx.ID_ANY, '...')

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.bmp_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        vsizer.Add(hsizer, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.path_ctrl, 0, wx.ALL, 5)
        hsizer.Add(self.path_button, 0, wx.ALL, 5)
        vsizer.Add(hsizer, 1, wx.EXPAND)
        self.SetSizer(vsizer)

        self.path_button.Bind(wx.EVT_BUTTON, self.on_open_file)

        self.path_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_enter)

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
            dlg.Destroy()

            if self.get_image(path):
                self.path_ctrl.ChangeValue(path)
                self.new_value = path
            else:
                self.path_ctrl.ChangeValue(self.new_value)

            self.bmp_ctrl.SetBitmap(self.bitmap)
        else:
            dlg.Destroy()

    def _on_enter(self, evt):
        value = self.path_ctrl.GetValue()
        if self.get_image(value):
            self.new_value = value
        else:
            self.new_value = ''

        self.bmp_ctrl.SetBitmap(self.bitmap)

        evt.Skip()

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
        return self.new_value

    def SetValue(self, value):
        if self.get_image(value):
            self.new_value = value
        else:
            self.new_value = ''

        self.bmp_ctrl.SetBitmap(self.bitmap)


class ImageEditor(wxpg.PGEditor):

    def __init__(self):
        self.property = None
        self.statbmp: wx.StaticBitmap = None
        self.tc: wx.TextCtrl = None
        self.bmp: wx.Bitmap = None
        wxpg.PGEditor.__init__(self)

    def CreateControls(self, propgrid, prop, pos, sz):
        w, h = sz
        h = 100 + 25

        original_path = prop.GetValue()
        saved_path = prop.GetSavedPath()
        file_types = prop.GetFileTypes()

        ctrl = ImageCtrl(propgrid.GetPanel(), file_types, original_path, saved_path, (w, h), pos)

        return wxpg.PGWindowList(ctrl)

    def GetName(self):
        return self.__class__.__name__

    def UpdateControl(self, prop, ctrl):
        s = prop.GetDisplayedString()
        ctrl.SetValue(s)

    def DrawValue(self, dc, rect, prop, text):
        dc.DrawText(prop.GetDisplayedString(), rect.x + 5, rect.y)

    def OnEvent(self, propgrid, prop, ctrl, event):
        if not ctrl:
            return False

        evtType = event.GetEventType()

        if evtType == wx.wxEVT_COMMAND_TEXT_ENTER:
            if propgrid.IsEditorsValueModified():
                return True

        elif evtType == wx.wxEVT_COMMAND_TEXT_UPDATED:
            #
            # Pass this event outside wxPropertyGrid so that,
            # if necessary, program can tell when user is editing
            # a textctrl.
            event.Skip()
            event.SetId(propgrid.GetId())

            propgrid.EditorsValueWasModified()
            return False

        return False

    def GetValueFromControl(self, prop, ctrl):
        """ Return tuple (wasSuccess, newValue), where wasSuccess is True if
            different value was acquired successfully.
        """
        textVal = ctrl.GetValue()
        res, value = prop.StringToValue(textVal, wxpg.PG_EDITABLE_VALUE)

        # Changing unspecified always causes event (returning
        # True here should be enough to trigger it).
        if not res and value is None:
            res = True

        return res, value

    def SetControlStringValue(self, prop, ctrl, txt):
        ctrl.SetValue(txt)

    def CanContainCustomImage(self):
        return True


class ImageProperty(wxpg.PGProperty):

    def __init__(self, label, name, value, file_types, save_path):
        wxpg.PGProperty.__init__(self, label, name)

        self.m_value = value

        self._file_types = file_types
        self._save_path = save_path

    def GetDisplayedString(self):
        return str(self.m_value)

    def GetSavedPath(self):
        return self._save_path

    def GetFileTypes(self):
        return self._file_types

    def GetValue(self):
        return self.m_value

    def DoGetEditorClass(self):
        return wxpg.PropertyGridInterface.GetEditorByName("Image")
