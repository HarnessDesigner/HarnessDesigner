from PySide6 import QtWidgets
from PySide6 import QtCore


class AutoCompleteTextCtrl(QtWidgets.QLineEdit):
    """QLineEdit with inline autocomplete (replaces wx AutoCompleteTextCtrl).

    Choice-management API is identical to the original so all call sites work
    without modification.
    """

    def __init__(self, parent=None, choices=None):
        """Initialise the :class:`AutoCompleteTextCtrl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param choices: Value for ``choices``.
        :type choices: UNKNOWN
        """
        super().__init__(parent)
        self._choices = list(choices or [])
        self._completer = QtWidgets.QCompleter(self._choices, self)
        self._completer.setCaseSensitivity(
            QtCore.Qt.CaseSensitivity.CaseInsensitive)

        self._completer.setCompletionMode(
            QtWidgets.QCompleter.CompletionMode.InlineCompletion)

        self.setCompleter(self._completer)

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
    # wx-compatible choice management
    # ------------------------------------------------------------------
    def Clear(self):
        """Execute the clear operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._choices.clear()
        self._rebuild_completer()

    def Delete(self, n: int):
        """Execute the delete operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param n: Value for ``n``.
        :type n: int
        """
        self._choices.pop(n)
        self._rebuild_completer()

    def Insert(self, item: str, pos: int):
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: str
        :param pos: Value for ``pos``.
        :type pos: int
        """
        self._choices.insert(pos, item)
        self._rebuild_completer()

    def Set(self, items):
        """Execute the set operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param items: Collection of items to process.
        :type items: UNKNOWN
        """
        self._choices = list(items)
        self._rebuild_completer()

    def SetItems(self, items):
        """Execute the set items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param items: Collection of items to process.
        :type items: UNKNOWN
        """
        self.Set(items)

    def Append(self, item):
        """Execute the append operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        """
        if isinstance(item, list):
            self._choices.extend(item)
        else:
            self._choices.append(item)
        self._rebuild_completer()

    # ------------------------------------------------------------------
    # Value access (QLineEdit already provides text()/setText())
    # ------------------------------------------------------------------
    def SetValue(self, value: str):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        # ChangeValue equivalent: set without triggering textEdited
        self.blockSignals(True)
        self.setText(value)
        self.blockSignals(False)

    def GetValue(self) -> str:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self.text()
