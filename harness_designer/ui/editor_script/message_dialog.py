# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""A message with buttons, in the application's dialog style (``BaseDialog``:
no native close button, it ends only through the buttons at the bottom).

The script editor asks "save the changes?", reports problems and warns that a
script did not stop; all of it goes through :func:`ask`.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6 import QtCore
from PySide6 import QtWidgets

from ..dialogs import dialog_base as _dialog_base
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ... import ui as _ui

_Buttons = QtWidgets.QDialogButtonBox.StandardButton


@dataclass(frozen=True)
class Answer:
    """:ivar button: The standard button that was pressed; ``None`` if the
        dialog was dismissed (Esc).
    :ivar extra: The extra button was pressed.
    """

    button: _Buttons | None
    extra: bool


class MessageDialog(_dialog_base.BaseDialog):
    """:param extra: The text of one more button, placed beside the standard ones."""

    @_check_types.do
    def __init__(self, parent: "_ui.MainFrame", title: str, text: str, buttons: _Buttons = _Buttons.Ok,
                 extra: str | None = None, size: tuple[int, int] = (560, 260)) -> None:
        super().__init__(parent, title, size=size, button_ids=buttons)
        self.chosen: _Buttons | None = None
        self.extra_chosen = False
        self._extra_button: QtWidgets.QPushButton | None = None

        label = QtWidgets.QLabel(text, self.panel)
        label.setWordWrap(True)
        label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)

        layout = QtWidgets.QVBoxLayout(self.panel)
        layout.addWidget(label, 1)

        if extra is not None:
            self._extra_button = self.button_box.addButton(extra, QtWidgets.QDialogButtonBox.ButtonRole.ActionRole)

        self.button_box.clicked.connect(self._clicked)

    @_check_types.do
    def _clicked(self, button: QtWidgets.QAbstractButton) -> None:
        if self._extra_button is not None and button == self._extra_button:
            self.extra_chosen = True
            self.accept()
            return

        self.chosen = self.button_box.standardButton(button)

        # Accept and reject buttons end the dialog through the base class;
        # a "Discard" button belongs to neither.
        if self.button_box.buttonRole(button) == QtWidgets.QDialogButtonBox.ButtonRole.DestructiveRole:
            self.accept()


@_check_types.do
def ask(parent: QtWidgets.QWidget, title: str, text: str, buttons: _Buttons = _Buttons.Ok,
        extra: str | None = None) -> Answer:
    """Show the message and wait for a button."""
    dialog = MessageDialog(parent, title, text, buttons, extra)
    dialog.exec()
    return Answer(dialog.chosen, dialog.extra_chosen)
