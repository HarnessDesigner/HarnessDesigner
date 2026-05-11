# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QDialogButtonBox

from ..widgets import combobox_ctrl as _combobox_ctrl
from . import dialog_base as _dialog_base


class OpenProjectDialog(_dialog_base.BaseDialog):

    def __init__(self, parent, last_project, project_names):
        _dialog_base.BaseDialog.__init__(
            self, parent, 'Open Project', size=(600, 200))

        self.last_project = last_project
        self.project_names = project_names

        self.project_ctrl = _combobox_ctrl.ComboBoxCtrl(
            self.panel, 'Project:', project_names, True)

        if last_project is not None and last_project in project_names:
            self.project_ctrl.SetValue(last_project)

        # Relabel the OK button to "Open"
        ok_btn = self.button_box.button(QDialogButtonBox.Ok)
        if ok_btn is not None:
            ok_btn.setText('Open')

        h_sizer = QHBoxLayout()
        h_sizer.addSpacing(100)
        h_sizer.addWidget(self.project_ctrl, 1)
        h_sizer.addSpacing(100)

        sizer = QVBoxLayout(self.panel)
        sizer.addLayout(h_sizer)

    def GetValue(self):
        return self.project_ctrl.GetValue()
