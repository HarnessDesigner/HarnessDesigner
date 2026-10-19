# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The "generated script" pane under the inspector.

Snippets accumulate here as the user clicks around, so the inspector is
useful on its own. When the script editor dock is open, snippets go there
instead (see ``ScraperInspector.set_sink``) and this pane is hidden.
"""

from PySide6 import QtCore
from PySide6 import QtWidgets

from . import insertion as _insertion
from ..widgets import code_editor_ctrl as _code_editor_ctrl
from ..widgets import wrap_label as _wrap_label
from ...scraping import snippets as _snippets
from ... import check_types as _check_types


class SnippetPane(QtWidgets.QWidget, _insertion.SnippetSink):

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        self._editor = _code_editor_ctrl.CodeEditorCtrl(self)
        self._editor.setPlaceholderText('Code you generate from the page appears here.')
        self._copy = QtWidgets.QPushButton('Copy all', self)
        self._clear = QtWidgets.QPushButton('Clear', self)
        self._label = _wrap_label.WrapLabel('Generated script', self, wrap=False)

        bar = QtWidgets.QHBoxLayout()
        bar.addWidget(self._label, 1)
        bar.addWidget(self._copy)
        bar.addWidget(self._clear)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(bar)
        layout.addWidget(self._editor, 1)

        self._copy.clicked.connect(self._copy_all)
        self._clear.clicked.connect(self._editor.clear)

    @_check_types.do
    def text(self) -> str:
        return self._editor.toPlainText()

    @_check_types.do
    def taken_names(self) -> set[str]:
        return _snippets.taken_names(self._editor.toPlainText())

    @_check_types.do
    def insert_snippet(self, snippet: _snippets.Snippet) -> None:
        _insertion.insert_snippet(self._editor, snippet)
        self._label.setText(f'Generated script - added: {snippet.description}')

    @_check_types.do
    def _copy_all(self) -> None:
        QtWidgets.QApplication.clipboard().setText(self._editor.toPlainText())
        self._label.setText('Generated script - copied to the clipboard')
