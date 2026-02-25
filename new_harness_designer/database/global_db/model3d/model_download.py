import wx
import zipfile
import os
import tempfile
import io

from . import preview as _preview
from . import loader as _loader
from .... import utils as _utils


import requests


class FileBrowser(wx.Panel):

    def __init__(self, parent: "ModelDownloadDialog", extensions: list[str]):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        self.parent = parent
        self.extensions = extensions

        self.tree_ctrl = wx.TreeCtrl(
            self, wx.ID_ANY, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_ROW_LINES | wx.TR_SINGLE)

        self.root = self.tree_ctrl.AddRoot('files')
        self.zipfile: zipfile.ZipFile = None

        self.tree_ctrl.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_item_selected)
        self.file_type = None
        self.file_data = None

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.tree_ctrl, 0, wx.EXPAND)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(hsizer, 0, wx.EXPAND)
        self.SetSizer(vsizer)

    def GetValues(self):
        return self.file_data, self.file_type

    def on_item_selected(self, evt: wx.TreeEvent):
        evt.Skip()
        item = evt.GetItem()

        if item.IsOk() and not self.tree_ctrl.ItemHasChildren(item):
            data = self.tree_ctrl.GetItemData(item)
            if self.zipfile is None:
                filename = self.tree_ctrl.GetItemText(data)
                ext = os.path.splitext(filename)[-1]

                self.file_data = data
            else:
                filename = data.filename
                for ext in self.extensions:
                    if filename.endswith(ext):
                        break
                else:
                    self.file_data = None
                    self.file_type = None
                    return

                with self.zipfile.open(data) as f:
                    self.file_data = f.read()

            wx.BeginBusyCursor()

            tempdir = tempfile.tempdir

            temp_file = os.path.join(tempdir, 'hd_model' + ext)
            with open(temp_file, 'wb') as f:
                f.write(self.file_data)

            self.file_type = ext

            try:
                mdata = _loader.load(temp_file)
                triangles = []
                for vertices, faces in mdata:
                    tris, nrmls, count = _utils.compute_vertex_normals(vertices, faces)
                    triangles.append([tris, nrmls, count])

                wx.EndBusyCursor()
            except:  # NOQA
                try:
                    os.remove(temp_file)
                except OSError:
                    pass

                wx.EndBusyCursor()

                self.file_data = None
                self.file_type = None
                return

            self.parent.preview.set_model(triangles)

            try:
                os.remove(temp_file)
            except OSError:
                pass

            wx.EndBusyCursor()

    def load_zipfile(self, file: zipfile.ZipFile):
        self.zipfile = file

        items = {}
        files = file.infolist()

        for f in files:
            if f.is_dir():
                path = []
                head, tail = os.path.split(f.filename)
                while head:
                    path.insert(0, tail)
                    head, tail = os.path.split(head)

                parent = self.root
                tree = items
                for d in path:
                    if d in tree:
                        parent = tree[d]['tree_item']
                        tree = tree[d]['children']
                    else:
                        child = self.tree_ctrl.AppendItem(parent, d)
                        self.tree_ctrl.SetItemHasChildren(child, True)
                        items[d] = {
                            'tree_item': child,
                            'children': {}
                        }
                        parent = child
                        tree = items[d]['children']

            else:
                path = []
                head, filename = os.path.split(f.filename)
                if head:
                    head, tail = os.path.split(head)
                    while head:
                        path.insert(0, tail)
                        head, tail = os.path.split(head)

                parent = self.root
                tree = items
                for d in path:
                    if d in tree:
                        parent = tree[d]['tree_item']
                        tree = tree[d]['children']
                    else:
                        child = self.tree_ctrl.AppendItem(parent, d)
                        self.tree_ctrl.SetItemHasChildren(child, True)
                        items[d] = {
                            'tree_item': child,
                            'children': {}
                        }
                        parent = child
                        tree = items[d]['children']

                child = self.tree_ctrl.AppendItem(parent, filename)

                self.tree_ctrl.SetItemData(child, f)
                self.tree_ctrl.SetItemHasChildren(child, False)

    def load_file(self, filename, data):
        child = self.tree_ctrl.AppendItem(self.root, filename)
        self.tree_ctrl.SetItemData(child, data)
        self.tree_ctrl.SetItemHasChildren(False)


class ModelDownloadDialog(wx.Dialog):

    def __init__(self, parent, url, extensions):
        wx.Dialog.__init__(self, parent, wx.ID_ANY,
                           style=wx.CAPTION | wx.RESIZE_BORDER | wx.CLOSE_BOX | wx.STAY_ON_TOP)

        self.preview = _preview.Preview(self)
        self.browser = FileBrowser(self, extensions)

        for extension in extensions:
            if extension in url:
                break
        else:
            extension = None

        try:
            response = requests.get(url)
        except requests.RequestException:
            raise ValueError

        headers = response.headers
        if extension is None and 'Content-Type' in headers:
            mime_types = (
                ('model/3mf', '.3mf'),
                ('model/gltf-binary', '.gltf'),
                ('model/gltf+json', '.gltf'),
                ('model/iges', '.iges'),
                ('model/vnd.collada+xml', '.dae'),
                ('model/obj', '.obj'),
                ('model/step', '.stp'),
                ('model/step+xml', '.stp'),
                ('model/stl', '.stl'),
                ('model/vrml', '.vrml'),
                ('model/x3d-vrml', '.x3d'),
                ('model/x3d+xml', '.x3d'),
                ('application/gltf-buffer', '.gltf'),
                ('application/iges', '.iges'),
                ('model/step+zip', '.zip'),
                ('model/step-xml+zip', '.zip'),
                ('application/zip', '.zip'),
                ('application/x-zip-compressed', '.zip')
            )
            for mime_type, extension in mime_types:
                if mime_type in headers['Content-Type']:
                    break
            else:
                extension = None

        if extension is not None:
            data = response.content

            if extension == '.zip':
                stream = io.BytesIO(data)
                zfile = zipfile.ZipFile(stream)
                self.browser.load_zipfile(zfile)
            else:
                filename = 'model' + extension
                self.browser.load_file(filename, data)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.preview, 0, wx.EXPAND | wx.RIGHT, 20)
        hsizer.Add(self.browser, 0, wx.EXPAND)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(hsizer, 0, wx.EXPAND | wx.ALL, 10)

        button_sizer = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        vsizer.Add(button_sizer, 0, wx.ALL, 10)

        self.SetSizer(vsizer)

    def GetValues(self) -> tuple[bytes, str] | tuple[None, None]:
        return self.browser.GetValues()
