# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QLabel, QHBoxLayout
from PySide6.QtCore import Qt, QTimer

from . import prop_base as _prop_base
from ._path_ctrl_base import PathCtrl


class PathProperty(_prop_base.Property):
    """Represent a path property in :mod:`harness_designer.ui.prop_ctrls.path_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, label):
        """Initialise the :class:`PathProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        """
        _prop_base.Property.__init__(self, parent, label)
        self._value = ''

        self._st = QLabel(label + ':', self)
        self._ctrl = PathCtrl(self, '', wildcard='', http_browse=False)

        row = QHBoxLayout()
        row.setContentsMargins(5, 2, 5, 2)
        row.addWidget(self._st)
        row.addWidget(self._ctrl, stretch=1)
        self._sizer.addLayout(row)

        # on_path_char equivalent: enable/disable browse button based on 'http' prefix
        self._ctrl.path_ctrl.textEdited.connect(self._on_text_edited)
        self._ctrl.path_changed.connect(self._on_path_changed)

    def _on_text_edited(self, text):
        """Handle the text edited event.

        UNKNOWN details are inferred from the callable name and signature.

        :param text: Text value.
        :type text: UNKNOWN
        """
        QTimer.singleShot(0, lambda: self._ctrl.path_button.setEnabled(
            not self._ctrl.path_ctrl.text().startswith('http')))

    def _on_path_changed(self, path):
        """Handle the path changed event.

        UNKNOWN details are inferred from the callable name and signature.

        :param path: Filesystem path.
        :type path: UNKNOWN
        """
        if path == self._value:
            return
        self._value = path
        self._send_changed_event(str, path)

    def SetWildcards(self, value):
        """Execute the set wildcards operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        self._ctrl.SetWildcards(value)

    def GetValue(self) -> str:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self._value

    def SetValue(self, value: str):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._value = value
        self._ctrl.SetValue(value)
        self._ctrl.path_button.setEnabled(not value.startswith('http'))
