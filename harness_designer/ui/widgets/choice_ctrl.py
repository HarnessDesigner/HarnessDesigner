# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtCore


class ChoiceCtrl(QtWidgets.QWidget):
    """
    Label + choice (non-editable dropdown) composite widget.

    A strict wx.Choice replacement: the user can only select from the
    presented options; there is no text-entry field.  The widget emits the
    custom ``valueChanged(str)`` signal whenever the selection changes;
    call sites should connect to that signal instead of binding
    ``EVT_CHOICE``.
    """

    valueChanged: QtCore.SignalInstance = QtCore.Signal(str)

    def __init__(self, parent=None, label: str = '', choices=None):
        """Initialise the :class:`ChoiceCtrl` instance.

        :param parent: Parent widget.
        :type parent: QWidget or None
        :param label: Text shown in the label to the left of the dropdown.
        :type label: str
        :param choices: Initial list of string choices.
        :type choices: list[str] or None
        """
        super().__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.st = QtWidgets.QLabel(label, self)
        self.ctrl = QtWidgets.QComboBox(self)
        self.ctrl.setEditable(False)

        if choices:
            self.ctrl.addItems(choices)

        layout.addWidget(self.st, 0)
        layout.addWidget(self.ctrl, 1)

        self.ctrl.currentIndexChanged.connect(self._on_index_changed)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_index_changed(self):
        """Emit :attr:`valueChanged` with the text of the newly selected item."""
        self.valueChanged.emit(self.ctrl.currentText())

    # ------------------------------------------------------------------
    # wx-compatible API
    # ------------------------------------------------------------------

    def Enable(self, flag: bool = True):
        """Enable or disable both the label and the dropdown.

        :param flag: ``True`` to enable; ``False`` to disable.
        :type flag: bool
        """
        self.ctrl.setEnabled(flag)
        self.st.setEnabled(flag)

    def SetToolTip(self, text: str):
        """Set the tooltip on both the label and the dropdown.

        :param text: Tooltip text.
        :type text: str
        """
        self.ctrl.setToolTip(text)
        self.st.setToolTip(text)

    SetToolTipString = SetToolTip

    def SetSelection(self, n: int):
        """Select the item at zero-based index *n*.

        :param n: Index of the item to select.
        :type n: int
        """
        self.ctrl.setCurrentIndex(n)

    def GetSelection(self) -> int:
        """Return the index of the currently selected item.

        :returns: Zero-based index, or ``-1`` if nothing is selected.
        :rtype: int
        """
        return self.ctrl.currentIndex()

    def SetStringSelection(self, value: str):
        """Select the first item whose text exactly matches *value*.

        Has no effect if *value* is not present in the list.

        :param value: Item text to select.
        :type value: str
        """
        idx = self.ctrl.findText(value, QtCore.Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            self.ctrl.setCurrentIndex(idx)

    def GetStringSelection(self) -> str:
        """Return the text of the currently selected item.

        :returns: Selected item text, or an empty string when nothing is selected.
        :rtype: str
        """
        return self.ctrl.currentText()

    def GetCount(self) -> int:
        """Return the total number of items in the dropdown.

        :returns: Item count.
        :rtype: int
        """
        return self.ctrl.count()

    def Clear(self):
        """Remove all items from the dropdown."""
        self.ctrl.clear()

    def Delete(self, n: int):
        """Remove the item at zero-based index *n*.

        :param n: Index of the item to remove.
        :type n: int
        """
        self.ctrl.removeItem(n)

    def Insert(self, item: str, pos: int):
        """Insert *item* before the item currently at index *pos*.

        :param item: Text of the new item.
        :type item: str
        :param pos: Zero-based insertion index.
        :type pos: int
        """
        self.ctrl.insertItem(pos, item)

    def Append(self, item: str) -> int:
        """Append a single item and return its new index.

        :param item: Text of the item to append.
        :type item: str
        :returns: Zero-based index of the newly appended item.
        :rtype: int
        """
        self.ctrl.addItem(item)
        return self.ctrl.count() - 1

    def AppendItems(self, items):
        """Append multiple items to the end of the dropdown.

        :param items: Items to append.
        :type items: list[str]
        """
        self.ctrl.addItems(list(items))

    def Set(self, items):
        """Replace all existing items with *items*.

        :param items: New list of item strings.
        :type items: list[str]
        """
        self.ctrl.clear()
        if items:
            self.ctrl.addItems(list(items))

    def GetItems(self) -> list[str]:
        """Return all item strings as an ordered list.

        :returns: List of item texts in display order.
        :rtype: list[str]
        """
        return [self.ctrl.itemText(i) for i in range(self.ctrl.count())]

    def SetItems(self, items: list[str]):
        """Replace all existing items with *items* (alias for :meth:`Set`).

        :param items: New list of item strings.
        :type items: list[str]
        """
        self.Set(items)
