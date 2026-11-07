# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Dialog for the order the conductors of a split cable end fan out in."""

from typing import TYPE_CHECKING

from PySide6 import QtWidgets, QtCore

from . import dialog_base as _dialog_base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ... import ui as _ui


_INDEX_ROLE = QtCore.Qt.ItemDataRole.UserRole
_LABEL_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1


class FanOutOrderDialog(_dialog_base.BaseDialog):
    """Put a cable end's conductors in the order they fan out in.

    The list is the order the conductors take around the cable's end, first to last; Move Up / Move Down change it. :meth:`GetValue`
    returns, for each place in the new order, the index the conductor had in the list the dialog was given.
    """

    @_check_types.do
    def __init__(self, parent: "_ui.MainFrame", end_name: str, labels: list[str]):
        """Initialise the :class:`FanOutOrderDialog` instance.

        :param parent: Main application frame.
        :type parent: :class:`_ui.MainFrame`
        :param end_name: ``'start'`` or ``'stop'``: the cable end, for the title.
        :type end_name: str
        :param labels: One line per conductor, in the order they are in now.
        :type labels: list[str]
        """
        super().__init__(parent, f'Fan-out Order ({end_name} end)', size=(420, 360))
        self._build_ui(labels)

    @_check_types.do
    def _build_ui(self, labels: list[str]) -> None:
        layout = QtWidgets.QVBoxLayout(self.panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        layout.addWidget(QtWidgets.QLabel('The conductors take their places around the cable end in this order.', self.panel))

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(6)

        self._list = QtWidgets.QListWidget(self.panel)
        self._list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        for index, label in enumerate(labels):
            item = QtWidgets.QListWidgetItem()
            item.setData(_INDEX_ROLE, index)
            item.setData(_LABEL_ROLE, label)
            self._list.addItem(item)

        self._renumber()

        if labels:
            self._list.setCurrentRow(0)

        row.addWidget(self._list, 1)

        buttons = QtWidgets.QVBoxLayout()
        self.up_button = QtWidgets.QPushButton('Move Up', self.panel)
        self.up_button.clicked.connect(lambda: self._move(-1))
        self.down_button = QtWidgets.QPushButton('Move Down', self.panel)
        self.down_button.clicked.connect(lambda: self._move(1))

        buttons.addWidget(self.up_button)
        buttons.addWidget(self.down_button)
        buttons.addStretch(1)

        row.addLayout(buttons)
        layout.addLayout(row, 1)

    @_check_types.do
    def _renumber(self) -> None:
        """Write each item's place in the order in front of its label."""
        for row in range(self._list.count()):
            item = self._list.item(row)
            item.setText(f'{row + 1}.  {item.data(_LABEL_ROLE)}')

    @_check_types.do
    def _move(self, delta: int) -> None:
        """Move the selected conductor one place up (-1) or down (1)."""
        row = self._list.currentRow()
        target = row + delta

        if row < 0 or target < 0 or target >= self._list.count():
            return

        item = self._list.takeItem(row)
        self._list.insertItem(target, item)
        self._list.setCurrentRow(target)
        self._renumber()

    @_check_types.do
    def GetValue(self) -> list[int]:
        """The new order: for each place, the index the conductor there had in the list the dialog was given.

        :rtype: list[int]
        """
        return [self._list.item(row).data(_INDEX_ROLE) for row in range(self._list.count())]
