# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import os

from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore

from ..widgets import text_ctrl as _text_ctrl
from ... import config as _config
from . import dialog_base as _dialog_base
from ..widgets import color_ctrl as _color_ctrl


if TYPE_CHECKING:
    from ...database.project_db import project as _project


Config = _config.Config

FILE_WILDCARD = "3D Model Files (*.obj *.fbx *.gltf *.glb *.stl *.ply *.dae *.3ds);;All Files (*.*)"


class AddProjectDialog(_dialog_base.BaseDialog):
    """Represent an add project dialog in :mod:`harness_designer.ui.dialogs.add_project`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, name, table: "_project.ProjectsTable"):
        """Initialise the :class:`AddProjectDialog` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param name: Name value.
        :type name: UNKNOWN
        :param table: Value for ``table``.
        :type table: :class:`_project.ProjectsTable`
        """
        self.table = table

        _dialog_base.BaseDialog.__init__(self, parent, 'Add Project', size=(600, 475))

        self.name_ctrl = _text_ctrl.TextCtrl(
            self.panel, 'Project Name:',
            apply_button=False, hslider=False)

        self.creator_ctrl = _text_ctrl.TextCtrl(
            self.panel, 'Creator:',
            apply_button=False, hslider=False)

        self.desc_ctrl = _text_ctrl.TextCtrl(
            self.panel, 'Description:',
            multiline=True, apply_button=False)

        self.user_model_ctrl = _text_ctrl.TextCtrl(
            self.panel, 'User Model:',
            apply_button=False)

        self.color_ctrl = _color_ctrl.ColorCtrl(
            self.panel, 'Model Color:', table.db.global_db.colors_table)
        self.color_ctrl.SetValue('Gray')
        self.color_ctrl.Enable(False)

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

        self._path_completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
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
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        color = self.color_ctrl.GetColor()

        return (self.name_ctrl.GetValue(),
                self.creator_ctrl.GetValue(),
                self.desc_ctrl.GetValue(),
                self.user_model_ctrl.GetValue(),
                int(color.db_id)
                )

    def _on_name_text(self, _text: str = ''):
        """Handle the name text event.

        UNKNOWN details are inferred from the callable name and signature.

        :param _text: Text value.
        :type _text: str
        """

        def _do():
            """Execute the do operation.

            UNKNOWN details are inferred from the callable name and signature.
            """
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
        """Handle the user model text event.

        UNKNOWN details are inferred from the callable name and signature.

        :param _text: Text value.
        :type _text: str
        """

        def _do():
            """Execute the do operation.

            UNKNOWN details are inferred from the callable name and signature.
            """
            path = self.user_model_ctrl.GetValue()
            if os.path.isfile(path):
                color = QtGui.QColor(0, 0, 0)
                self.color_ctrl.Enable(True)
            else:
                color = QtGui.QColor(255, 0, 0)
                self.color_ctrl.Enable(False)

            palette = self.user_model_ctrl.inputPalette()
            palette.setColor(palette.Text, color)
            self.user_model_ctrl.setInputPalette(palette)

        QtCore.QTimer.singleShot(0, _do)

    def _on_open_file(self):
        """Handle the open file event.

        UNKNOWN details are inferred from the callable name and signature.
        """
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
            self.color_ctrl.Enable(True)
        else:
            path = self.user_model_ctrl.GetValue()
            if path and os.path.isfile(path):
                self.color_ctrl.Enable(True)
            else:
                self.color_ctrl.Enable(False)
