# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets

from ..widgets import combobox_ctrl as _combobox_ctrl
from . import dialog_base as _dialog_base


class OpenProjectDialog(_dialog_base.BaseDialog):
    """Represent an open project dialog in :mod:`harness_designer.ui.dialogs.project_dialog`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, last_project, project_names):
        """Initialise the :class:`OpenProjectDialog` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param last_project: Value for ``last_project``.
        :type last_project: UNKNOWN
        :param project_names: Value for ``project_names``.
        :type project_names: UNKNOWN
        """
        _dialog_base.BaseDialog.__init__(
            self, parent, 'Open Project', size=(600, 200))

        self.last_project = last_project
        self.project_names = project_names

        self.project_ctrl = _combobox_ctrl.ComboBoxCtrl(
            self.panel, 'Project:', project_names, True)

        if last_project is not None and last_project in project_names:
            self.project_ctrl.SetValue(last_project)

        # Relabel the OK button to "Open"
        ok_btn = self.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok)

        if ok_btn is not None:
            ok_btn.setText('Open')

        h_sizer = QtWidgets.QHBoxLayout()
        h_sizer.addSpacing(100)
        h_sizer.addWidget(self.project_ctrl, 1)
        h_sizer.addSpacing(100)

        sizer = QtWidgets.QVBoxLayout(self.panel)
        sizer.addLayout(h_sizer)

    def GetValue(self):
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.project_ctrl.GetValue()
