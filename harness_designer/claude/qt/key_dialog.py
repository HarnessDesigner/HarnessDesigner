# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The Claude settings dialog: the user's API key, the model, and how hard
Claude should think. Shared by everything that uses Claude -- there is one
key and one set of settings for the whole application.

Follows the dialog convention (``BaseDialog``): no native close button, it
ends only through the buttons at the bottom.
"""

from typing import TYPE_CHECKING, Any

from PySide6 import QtCore
from PySide6 import QtWidgets

from . import job as _job
from .. import client as _client
from .. import errors as _errors
from .. import keys as _keys
from .. import messages as _messages
from .. import models as _models
from .. import settings as _settings
from ...ui.dialogs import dialog_base as _dialog_base
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ... import ui as _ui

_KEYS_URL = 'https://console.anthropic.com/settings/keys'


class ApiKeyDialog(_dialog_base.BaseDialog):
    """
    :param client: The client whose key store and settings this edits.
    """

    @_check_types.do
    def __init__(self, parent: "_ui.MainFrame", client: _client.ClaudeClient) -> None:
        super().__init__(parent, 'Claude settings', size=(560, 460))
        self._client = client
        self._store = client.key_store
        self._test_job: _job.ClaudeJob | None = None

        intro = QtWidgets.QLabel(
            'Claude features use <b>your own</b> Anthropic account. Get a key at '
            f'<a href="{_KEYS_URL}">console.anthropic.com</a>. The key is kept in this computer\'s credential '
            'store, never in a project file. Text sent to Claude (page source, harness details) leaves '
            'this computer, and the usage is billed to your key.', self.panel)
        intro.setWordWrap(True)
        intro.setOpenExternalLinks(True)
        intro.setTextFormat(QtCore.Qt.TextFormat.RichText)

        self.key_edit = QtWidgets.QLineEdit(self.panel)
        self.key_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText('sk-ant-...')
        self.show_key = QtWidgets.QCheckBox('Show', self.panel)
        self.key_status = QtWidgets.QLabel(self.panel)
        self.key_status.setWordWrap(True)

        key_row = QtWidgets.QHBoxLayout()
        key_row.addWidget(self.key_edit, 1)
        key_row.addWidget(self.show_key)

        self.clear_button = QtWidgets.QPushButton('Remove saved key', self.panel)
        self.test_button = QtWidgets.QPushButton('Test', self.panel)
        self.test_button.setToolTip('Sends one tiny request (a fraction of a cent) to check the key and settings.')
        key_buttons = QtWidgets.QHBoxLayout()
        key_buttons.addWidget(self.test_button)
        key_buttons.addWidget(self.clear_button)
        key_buttons.addStretch(1)

        self.model_box = QtWidgets.QComboBox(self.panel)
        for info in _models.MODELS:
            self.model_box.addItem(info.name, info.id)
            self.model_box.setItemData(self.model_box.count() - 1, info.note, QtCore.Qt.ItemDataRole.ToolTipRole)

        self.price_label = QtWidgets.QLabel(self.panel)
        self.effort_box = QtWidgets.QComboBox(self.panel)
        for effort in _models.EFFORTS:
            self.effort_box.addItem(effort, effort)

        self.effort_box.setToolTip('How hard Claude thinks before answering. Higher is slower and costs more.')
        self.fallback_box = QtWidgets.QCheckBox('Retry refused requests on another model', self.panel)
        self.fallback_box.setToolTip(
            'If a safety check declines a request, let Anthropic retry it on another model. '
            'Turn this off if your organisation cannot use the beta it needs.')

        form = QtWidgets.QFormLayout()
        form.addRow('API key', key_row)
        form.addRow('', self.key_status)
        form.addRow('', key_buttons)
        form.addRow('Model', self.model_box)
        form.addRow('', self.price_label)
        form.addRow('Thinking effort', self.effort_box)
        form.addRow('', self.fallback_box)

        self.result_label = QtWidgets.QLabel(self.panel)
        self.result_label.setWordWrap(True)

        layout = QtWidgets.QVBoxLayout(self.panel)
        layout.addWidget(intro)
        layout.addLayout(form)
        layout.addWidget(self.result_label)
        layout.addStretch(1)

        self.show_key.toggled.connect(self._toggle_visibility)
        self.model_box.currentIndexChanged.connect(self._model_changed)
        self.clear_button.clicked.connect(self._clear_key)
        self.test_button.clicked.connect(self._test)

        self._load()

    # -- showing the current state ---------------------------------------------

    @_check_types.do
    def _load(self) -> None:
        settings = self._client.settings
        self.model_box.setCurrentIndex(max(0, self.model_box.findData(settings.model)))
        self.effort_box.setCurrentIndex(max(0, self.effort_box.findData(settings.effort)))
        self.fallback_box.setChecked(settings.refusal_fallback)
        self._model_changed()
        self._refresh_key_status()

    @_check_types.do
    def _refresh_key_status(self) -> None:
        try:
            has_key = self._store.has_key()
        except _errors.KeyStoreError as error:
            self.key_status.setText(error.user_message)
            self.clear_button.setEnabled(False)
            return

        self.clear_button.setEnabled(has_key)
        if has_key:
            self.key_status.setText('A key is saved. Type a new one only to replace it.')
        else:
            self.key_status.setText('No key saved yet.')

    @_check_types.do
    def _model_changed(self, *_args: tuple[Any]) -> None:
        info = _models.model_info(self.model_box.currentData())
        if info is None:
            self.price_label.setText('')
            return

        self.price_label.setText(
            f'${info.input_price:.2f} in / ${info.output_price:.2f} out per million tokens. {info.note}')
        self.fallback_box.setEnabled(info.supports_fallback)

    @_check_types.do
    def _toggle_visibility(self, visible: bool) -> None:
        if visible:
            self.key_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Normal)
        else:
            self.key_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

    # -- actions -----------------------------------------------------------------

    @_check_types.do
    def _chosen_settings(self) -> _settings.ClaudeSettings:
        return self._client.settings.changed(
            model=self.model_box.currentData(),
            effort=self.effort_box.currentData(),
            refusal_fallback=self.fallback_box.isChecked())

    @_check_types.do
    def _clear_key(self) -> None:
        try:
            self._store.clear_key()
        except _errors.KeyStoreError as error:
            self.result_label.setText(error.user_message)
            return

        self.key_edit.clear()
        self.result_label.setText('The saved key was removed.')
        self._refresh_key_status()

    @_check_types.do
    def _test(self) -> None:
        """Try a tiny request with the typed key (or the saved one) and the
        chosen settings, without saving anything yet."""
        if self._test_job is not None and self._test_job.is_running:
            return

        typed = self.key_edit.text().strip()
        try:
            client = self._client.derive(key=typed or None, settings=self._chosen_settings())
        except ValueError as error:
            self.result_label.setText(str(error))
            return

        self.test_button.setEnabled(False)
        self.result_label.setText('Testing...')

        job = _job.ClaudeJob(lambda token, on_text, on_tool: client.check_connection(token), self)
        job.finished.connect(self._test_succeeded)
        job.failed.connect(self._test_failed)
        self._test_job = job
        job.start()

    @_check_types.do
    def _test_succeeded(self, response: _messages.Response) -> None:
        self.test_button.setEnabled(True)
        cost = response.estimated_cost
        text = f'It works: {response.model} answered.'
        if cost is not None:
            text += f' The test cost about ${cost:.4f}.'

        self.result_label.setText(text)

    @_check_types.do
    def _test_failed(self, error: _errors.ClaudeError) -> None:
        self.test_button.setEnabled(True)
        self.result_label.setText(error.user_message)

    @_check_types.do
    def accept(self) -> None:  # NOQA -- Qt override: save, then close
        typed = self.key_edit.text().strip()

        try:
            chosen = self._chosen_settings()
            if typed:
                if not _keys.ApiKeyStore.looks_like_a_key(typed):
                    self.result_label.setText(
                        'That does not look like an Anthropic key (they start with sk-ant-). '
                        'Fix it, or clear the box to keep the saved key.')
                    return

                self._store.set_key(typed)

            _settings.update(model=chosen.model, effort=chosen.effort, refusal_fallback=chosen.refusal_fallback)
        except _errors.KeyStoreError as error:
            self.result_label.setText(error.user_message)
            return
        except ValueError as error:
            self.result_label.setText(str(error))
            return

        super().accept()
