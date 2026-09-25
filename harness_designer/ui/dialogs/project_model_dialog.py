# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Dialog for choosing the project's own 3D model (the reference model the
harness is laid out around) -- the same file + color fields "Add Project"
has, for a project that already exists.
"""

from typing import TYPE_CHECKING

import os

from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore

from ..widgets import text_ctrl as _text_ctrl
from ..widgets import color_ctrl as _color_ctrl
from . import dialog_base as _dialog_base
from .add_project import FILE_WILDCARD
from ... import config as _config
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ... import ui as _ui
    from ...database.project_db import project as _project


Config = _config.Config


class ProjectModelDialog(_dialog_base.BaseDialog):
    """Pick a 3D model file and the color to draw it in.

    :meth:`GetValue` returns ``(path, color_id)``.
    """

    @_check_types.do
    def __init__(self, parent: "_ui.MainFrame", project_db: "_project.Project") -> None:
        title = 'Add Project Model'
        current_model = project_db.model

        if current_model is not None:
            title = 'Edit Project Model'

        _dialog_base.BaseDialog.__init__(self, parent, title, size=(600, 170))

        self.model_ctrl = _text_ctrl.TextCtrl(self.panel, 'Model:', apply_button=False)

        self.color_ctrl = _color_ctrl.ColorCtrl(
            self.panel, 'Model Color:', parent.global_db.colors_table)

        self.open_button = QtWidgets.QPushButton('Open File', self.panel)

        self.model_ctrl.text_changed.connect(self._on_model_text)
        self.open_button.clicked.connect(self._on_open_file)

        if current_model is not None and current_model.path:
            self.model_ctrl.SetValue(current_model.path)

        color = project_db.color
        if color is not None:
            self.color_ctrl.SetValue(color.name)
        else:
            self.color_ctrl.SetValue('Gray')

        self._fs_model = QtWidgets.QFileSystemModel(self)
        self._fs_model.setRootPath('')
        self._path_completer = QtWidgets.QCompleter(self._fs_model, self)

        self._path_completer.setCompletionMode(
            QtWidgets.QCompleter.CompletionMode.InlineCompletion)

        self._path_completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.model_ctrl.setCompleter(self._path_completer)

        hsizer = QtWidgets.QHBoxLayout()
        hsizer.addWidget(self.model_ctrl, 1)
        hsizer.addSpacing(10)
        hsizer.addWidget(self.open_button)

        vsizer = QtWidgets.QVBoxLayout(self.panel)
        vsizer.addLayout(hsizer)
        vsizer.addWidget(self.color_ctrl)

        self._on_model_text()

    @_check_types.do
    def GetValue(self) -> tuple[str, bytes]:
        """Return ``(path, color_id)`` for the chosen model file and color."""
        return self.model_ctrl.GetValue(), self.color_ctrl.GetColor().db_id

    @_check_types.do
    def _on_model_text(self, _text: str = '') -> None:
        """Flag a path that isn't an existing file in red."""

        @_check_types.do
        def _do() -> None:
            path = self.model_ctrl.GetValue()

            if os.path.isfile(path):
                color = QtGui.QColor(0, 0, 0)
            else:
                color = QtGui.QColor(255, 0, 0)

            palette = self.model_ctrl.inputPalette()
            palette.setColor(palette.Text, color)
            self.model_ctrl.setInputPalette(palette)

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def _on_open_file(self) -> None:
        """Browse for the model file."""
        path = self.model_ctrl.GetValue()

        if path:
            default_dir = os.path.dirname(path)
        else:
            default_dir = Config.project.model_dir

        chosen, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Choose a model', default_dir, FILE_WILDCARD)

        if chosen:
            Config.project.model_dir = os.path.dirname(chosen)
            self.model_ctrl.SetValue(chosen)
