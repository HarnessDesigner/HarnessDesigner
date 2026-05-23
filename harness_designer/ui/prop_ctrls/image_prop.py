# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QLabel, QHBoxLayout

from . import prop_base as _prop_base
from ._path_ctrl_base import PathCtrl
from ._image_ctrl_base import ImageCtrl
from ... import utils as _utils


class ImageProperty(_prop_base.Property):
    """Represent an image property in :mod:`harness_designer.ui.prop_ctrls.image_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, label):
        """Initialise the :class:`ImageProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        """
        _prop_base.Property.__init__(self, parent, label)
        self._value = ''
        self._file_types = {}
        self._save_path = None

        self._st = QLabel(label + ':', self)
        self._ctrl = PathCtrl(self, '', wildcard=_utils.IMAGE_FILE_WILDCARDS)
        self._image = ImageCtrl(self, {}, '', None, support_pdf=False)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(5, 2, 5, 2)
        top_row.addWidget(self._st)
        top_row.addWidget(self._ctrl, stretch=1)
        self._sizer.addLayout(top_row)

        img_row = QHBoxLayout()
        img_row.setContentsMargins(5, 2, 5, 2)
        img_row.addWidget(self._image, stretch=1)
        self._sizer.addLayout(img_row)

        self._ctrl.path_changed.connect(self._on_path_changed)

    def SetFileTypes(self, file_types):
        """Execute the set file types operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param file_types: Value for ``file_types``.
        :type file_types: UNKNOWN
        """
        self._file_types = file_types
        self._image.SetFileTypes(file_types)

    def _on_path_changed(self, path):
        """Handle the path changed event.

        UNKNOWN details are inferred from the callable name and signature.

        :param path: Filesystem path.
        :type path: UNKNOWN
        """
        if path == self._value:
            return
        if self._image.SetValue(path):
            self._value = path
            self._send_changed_event(str, path)

    def GetValue(self) -> str:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self._value

    def SetValue(self, value):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        self._value = value[0]
        self._save_path = value[1]
        if value[1] is None:
            self._image.SetValue(value[0])
        else:
            self._image.SetValue(value[1])
        self._ctrl.SetValue(value[0])
