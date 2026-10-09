# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Dialog that shows a database error and can only be dismissed with OK."""

from typing import TYPE_CHECKING

import traceback

from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6 import QtGui

from . import dialog_base as _dialog_base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ... import ui as _ui


class DatabaseErrorDialog(_dialog_base.BaseDialog):
    """Show a database error, the context it happened in, and its traceback.

    The caller logs the error. This dialog only displays it. The only way out
    is the OK button: Escape is ignored, and the dialog has no native close
    button.
    """

    @_check_types.do
    def __init__(self, parent: "_ui.MainFrame", err: BaseException, context: str) -> None:
        """Build the dialog.

        :param parent: Main window the dialog is centred on.
        :type parent: :class:`_ui.MainFrame`
        :param err: The exception that was caught.
        :type err: BaseException
        :param context: What was being written when it failed: the table, the
            row id, and the SQL and parameters.
        :type context: str
        """
        super().__init__(
            parent, 'Database Error', size=(640, 420),
            button_ids=QtWidgets.QDialogButtonBox.StandardButton.Ok)

        summary = QtWidgets.QLabel(
            'The database reported an error. The change listed below was not saved.')
        summary.setWordWrap(True)

        details = QtWidgets.QPlainTextEdit()
        details.setReadOnly(True)
        details.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont))
        details.setPlainText(f'{context}\n\n{"".join(traceback.format_exception(err))}')

        layout = QtWidgets.QVBoxLayout(self.panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(summary)
        layout.addWidget(details, 1)

    @_check_types.do
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Ignore Escape, so the dialog can only be dismissed with OK.

        :param event: Key event.
        :type event: :class:`QtGui.QKeyEvent`
        """
        if event.key() == QtCore.Qt.Key.Key_Escape:
            event.ignore()
            return

        super().keyPressEvent(event)
