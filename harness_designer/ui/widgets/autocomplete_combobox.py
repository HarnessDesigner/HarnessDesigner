# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtCore


class AutoCompleteComboBox(QtWidgets.QComboBox):
    """
    QComboBox with inline autocomplete and a mirrored choice list.

    Public API is a superset of the original wx AutoCompleteComboBox so all
    existing call sites continue to work unchanged.
    """

    def __init__(self, parent=None, choices=None):
        """Initialise the :class:`AutoCompleteComboBox` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param choices: Value for ``choices``.
        :type choices: UNKNOWN
        """
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)

        self._choices = list(choices or [])
        if self._choices:
            self.addItems(self._choices)

        self._completer = QtWidgets.QCompleter(self._choices, self)
        self._completer.setCaseSensitivity(
            QtCore.Qt.CaseSensitivity.CaseInsensitive)

        self._completer.setCompletionMode(
            QtWidgets.QCompleter.CompletionMode.InlineCompletion)

        self.lineEdit().setCompleter(self._completer)

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------
    def _rebuild_completer(self):
        """Execute the rebuild completer operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._completer.setModel(
            QtCore.QStringListModel(self._choices, self._completer))

    # ------------------------------------------------------------------
    # Mirrored list mutation API
    # ------------------------------------------------------------------
    def Clear(self):
        """Execute the clear operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        super().clear()
        self._choices.clear()
        self._rebuild_completer()

    def Delete(self, n: int):
        """Execute the delete operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param n: Value for ``n``.
        :type n: int
        """
        self.removeItem(n)
        self._choices.pop(n)
        self._rebuild_completer()

    def Insert(self, item: str, pos: int, _=None):
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: str
        :param pos: Value for ``pos``.
        :type pos: int
        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self.insertItem(pos, item)
        self._choices.insert(pos, item)
        self._rebuild_completer()

    def Set(self, items):
        """Execute the set operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param items: Collection of items to process.
        :type items: UNKNOWN
        """
        self.Clear()
        self._choices = list(items)
        self.addItems(self._choices)
        self._rebuild_completer()

    def SetItems(self, items):
        """Execute the set items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param items: Collection of items to process.
        :type items: UNKNOWN
        """
        self.Set(items)

    def AppendItems(self, items):
        """Execute the append items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param items: Collection of items to process.
        :type items: UNKNOWN
        """
        for item in items:
            self.Append(item)

    def Append(self, item):
        """Execute the append operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        """
        if isinstance(item, list):
            for i in item:
                self.Append(i)
            return
        super().addItem(item)
        self._choices.append(item)
        self._rebuild_completer()

    # ------------------------------------------------------------------
    # Value access
    # ------------------------------------------------------------------
    def GetValue(self) -> str:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self.currentText()

    def SetValue(self, value: str):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        idx = self.findText(value, QtCore.Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            self.lineEdit().setText(value)

    def GetItems(self):
        """Execute the get items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return [self.itemText(i) for i in range(self.count())]
