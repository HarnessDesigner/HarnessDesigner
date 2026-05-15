# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import os

from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore

from ..widgets import text_ctrl as _text_ctrl
from ... import config as _config
from . import dialog_base as _dialog_base


if TYPE_CHECKING:
    from ...database.project_db import project as _project


Config = _config.Config

FILE_WILDCARD = "3D Model Files (*.obj *.fbx *.gltf *.glb *.stl *.ply *.dae *.3ds);;All Files (*.*)"


class AddProjectDialog(_dialog_base.BaseDialog):

    def __init__(self, parent, name, table: "_project.ProjectsTable"):
        self.table = table

        _dialog_base.BaseDialog.__init__(self, parent, 'Add Project', size=(-1, 475))

        fm = self.fontMetrics()
        height = int(fm.height() * 2.5)

        self.name_ctrl = _text_ctrl.TextCtrl(
            self.panel, 'Project Name:', (-1, int(height / 1.5)),
            apply_button=False, hslider=False)

        self.creator_ctrl = _text_ctrl.TextCtrl(
            self.panel, 'Creator:', (-1, int(height / 1.5)),
            apply_button=False, hslider=False)

        self.desc_ctrl = _text_ctrl.TextCtrl(
            self.panel, 'Description:', (-1, height * 4),
            multiline=True, apply_button=False)

        self.user_model_ctrl = _text_ctrl.TextCtrl(
            self.panel, 'User Model:', (-1, height),
            apply_button=False)

        self.user_model_button = QtWidgets.QPushButton('Open File', self.panel)

        self.name_ctrl.text_changed.connect(self._on_name_text)
        self.user_model_ctrl.text_changed.connect(self._on_user_model_text)
        self.user_model_button.clicked.connect(self._on_open_file)
        self.name_ctrl.SetValue(name)

        # Directory/file path autocomplete on the user model field
        self._fs_model = QtWidgets.QFileSystemModel(self)
        self._fs_model.setRootPath('')
        self._path_completer = QtWidgets.QCompleter(self._fs_model, self)

        self._path_completer.setCompletionMode(
            QtWidgets.QCompleter.CompletionMode.InlineCompletion)

        self._path_completer.setCaseSensitivity(False)
        self.user_model_ctrl.setCompleter(self._path_completer)

        hsizer = QtWidgets.QHBoxLayout()
        hsizer.addWidget(self.user_model_ctrl, 1)
        hsizer.addSpacing(10)
        hsizer.addWidget(self.user_model_button)

        vsizer = QtWidgets.QVBoxLayout(self.panel)
        vsizer.addWidget(self.name_ctrl)
        vsizer.addWidget(self.creator_ctrl)
        vsizer.addWidget(self.desc_ctrl)
        vsizer.addLayout(hsizer)

    def GetValue(self):
        return (self.name_ctrl.GetValue(),
                self.creator_ctrl.GetValue(),
                self.desc_ctrl.GetValue(),
                self.user_model_ctrl.GetValue())

    def _on_name_text(self, _text: str = ''):

        def _do():
            name = self.name_ctrl.GetValue()
            try:
                _ = self.table[name]
                color = QtGui.QColor(255, 0, 0)
            except KeyError:
                color = QtGui.QColor(0, 0, 0)

            palette = self.name_ctrl.inputPalette()
            palette.setColor(palette.Text, color)
            self.name_ctrl.setInputPalette(palette)

        QtCore.QTimer.singleShot(0, _do)

    def _on_user_model_text(self, _text: str = ''):

        def _do():
            path = self.user_model_ctrl.GetValue()
            if os.path.isfile(path):
                color = QtGui.QColor(0, 0, 0)
            else:
                color = QtGui.QColor(255, 0, 0)

            palette = self.user_model_ctrl.inputPalette()
            palette.setColor(palette.Text, color)
            self.user_model_ctrl.setInputPalette(palette)

        QtCore.QTimer.singleShot(0, _do)

    def _on_open_file(self):
        path = self.user_model_ctrl.GetValue()
        if path:
            default_dir = os.path.dirname(path)
        else:
            default_dir = Config.project.model_dir

        chosen, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose a model", default_dir, FILE_WILDCARD)

        if chosen:
            Config.project.model_dir = os.path.dirname(chosen)
            self.user_model_ctrl.SetValue(chosen)
