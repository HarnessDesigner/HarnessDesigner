# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import zipfile
import os
import tempfile
import io

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QWidget, QTreeWidget,
    QTreeWidgetItem, QAbstractItemView, QApplication
)
from PySide6.QtCore import Qt

from . import preview as _preview
from . import loader as _loader
from .... import utils as _utils


import requests


class FileBrowser(QWidget):
    """Represent a file browser in :mod:`harness_designer.database.global_db.model3d.model_download`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent: "ModelDownloadDialog", extensions: list[str]):
        """Initialise the :class:`FileBrowser` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`ModelDownloadDialog`
        :param extensions: Value for ``extensions``.
        :type extensions: list[str]
        """
        QWidget.__init__(self, parent)
        self.parent_dialog = parent
        self.extensions = extensions

        self.tree_ctrl = QTreeWidget(self)
        self.tree_ctrl.setHeaderHidden(True)
        self.tree_ctrl.setRootIsDecorated(True)
        self.tree_ctrl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.root = QTreeWidgetItem(self.tree_ctrl, ['files'])
        self.tree_ctrl.addTopLevelItem(self.root)

        self.zipfile: zipfile.ZipFile = None

        self.tree_ctrl.currentItemChanged.connect(self.on_item_selected)
        self.file_type = None
        self.file_data = None

        layout = QVBoxLayout(self)
        layout.addWidget(self.tree_ctrl)

    def GetValues(self):
        """Execute the get values operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.file_data, self.file_type

    def on_item_selected(self, item: QTreeWidgetItem, _):
        """Handle the item selected event.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: :class:`QTreeWidgetItem`
        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        if item is None:
            return
        if item.childCount() > 0:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data is None:
            return

        if self.zipfile is None:
            filename = item.text(0)
            ext = os.path.splitext(filename)[-1]
            self.file_data = data
        else:
            filename = data.filename
            ext = None
            for e in self.extensions:
                if filename.endswith(e):
                    ext = e
                    break
            else:
                self.file_data = None
                self.file_type = None
                return

            with self.zipfile.open(data) as f:
                self.file_data = f.read()

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        tempdir = tempfile.tempdir or tempfile.gettempdir()
        temp_file = os.path.join(tempdir, 'hd_model' + ext)
        with open(temp_file, 'wb') as f:
            f.write(self.file_data)

        self.file_type = ext

        try:
            mdata = _loader.load(temp_file)
            triangles = []
            for vertices, faces in mdata:
                tris, _, nrmls, count = _utils.compute_normals(vertices, faces)
                triangles.append([tris, nrmls, count])

            QApplication.restoreOverrideCursor()
        except:  # NOQA
            try:
                os.remove(temp_file)
            except OSError:
                pass

            QApplication.restoreOverrideCursor()

            self.file_data = None
            self.file_type = None
            return

        self.parent_dialog.preview.set_model(triangles)

        try:
            os.remove(temp_file)
        except OSError:
            pass

        QApplication.restoreOverrideCursor()

    def load_zipfile(self, file: zipfile.ZipFile):
        """Load the zipfile.

        UNKNOWN details are inferred from the callable name and signature.

        :param file: Value for ``file``.
        :type file: :class:`zipfile.ZipFile`
        """
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
                        child = QTreeWidgetItem(parent, [d])
                        child.setChildIndicatorPolicy(
                            QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
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
                        child = QTreeWidgetItem(parent, [d])
                        child.setChildIndicatorPolicy(
                            QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
                        items[d] = {
                            'tree_item': child,
                            'children': {}
                        }
                        parent = child
                        tree = items[d]['children']

                child = QTreeWidgetItem(parent, [filename])
                child.setData(0, Qt.ItemDataRole.UserRole, f)

    def load_file(self, filename, data):
        """Load the file.

        UNKNOWN details are inferred from the callable name and signature.

        :param filename: Value for ``filename``.
        :type filename: UNKNOWN
        :param data: Data payload.
        :type data: UNKNOWN
        """
        child = QTreeWidgetItem(self.root, [filename])
        child.setData(0, Qt.ItemDataRole.UserRole, data)


class ModelDownloadDialog(QDialog):
    """Represent a model download dialog in :mod:`harness_designer.database.global_db.model3d.model_download`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, url, extensions):
        """Initialise the :class:`ModelDownloadDialog` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param url: Value for ``url``.
        :type url: UNKNOWN
        :param extensions: Value for ``extensions``.
        :type extensions: UNKNOWN
        :raises ValueError: Raised when the operation cannot be completed.
        """
        QDialog.__init__(self, parent,
                         Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint |
                         Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowStaysOnTopHint)

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

        h_layout = QHBoxLayout()
        h_layout.addWidget(self.preview)
        h_layout.addWidget(self.browser)

        v_layout = QVBoxLayout(self)
        v_layout.addLayout(h_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        v_layout.addWidget(button_box)

    def GetValues(self) -> tuple[bytes, str] | tuple[None, None]:
        """Execute the get values operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: tuple[bytes, str] | tuple[None, None]
        """
        return self.browser.GetValues()
