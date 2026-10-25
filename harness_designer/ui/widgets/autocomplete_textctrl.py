# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6 import QtCore
from ... import check_types as _check_types


class AutoCompleteTextCtrl(QtWidgets.QLineEdit):
    """QLineEdit with inline autocomplete (replaces wx AutoCompleteTextCtrl).

    Choice-management API is identical to the original so all call sites work
    without modification.
    """

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None = None, choices: list[str] | None = None):
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
    @_check_types.do
    def _rebuild_completer(self) -> None:
        """Execute the rebuild completer operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._completer.setModel(
            QtCore.QStringListModel(self._choices, self._completer))

    # ------------------------------------------------------------------
    # wx-compatible choice management
    # ------------------------------------------------------------------
    @_check_types.do
    def Clear(self) -> None:
        """Execute the clear operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._choices.clear()
        self._rebuild_completer()

    @_check_types.do
    def Delete(self, n: int) -> None:
        """Execute the delete operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param n: Value for ``n``.
        :type n: int
        """
        self._choices.pop(n)
        self._rebuild_completer()

    @_check_types.do
    def Insert(self, item: str, pos: int) -> None:
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: str
        :param pos: Value for ``pos``.
        :type pos: int
        """
        self._choices.insert(pos, item)
        self._rebuild_completer()

    @_check_types.do
    def Set(self, items: list[str]) -> None:
        """Execute the set operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param items: Collection of items to process.
        :type items: UNKNOWN
        """
        self._choices = list(items)
        self._rebuild_completer()

    @_check_types.do
    def SetItems(self, items: list[str]) -> None:
        """Execute the set items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param items: Collection of items to process.
        :type items: UNKNOWN
        """
        self.Set(items)

    @_check_types.do
    def Append(self, item: str) -> None:
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
    @_check_types.do
    def SetValue(self, value: str) -> None:
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        # ChangeValue equivalent: set without triggering textEdited
        self.blockSignals(True)
        self.setText(value)
        self.blockSignals(False)

    @_check_types.do
    def GetValue(self) -> str:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self.text()


class AutoCompleteTextEdit(QtWidgets.QPlainTextEdit):
    """Multi-line sibling of :class:`AutoCompleteTextCtrl`.

    A ``QPlainTextEdit`` inserts a newline for every Enter and has no Enter signal, so this control decides which Enter commits. The
    first two Enters insert newlines as usual. A third Enter in a row (pressed with the cursor at the end of text that already ends
    in two newlines) emits :attr:`returnPressed` instead, and that Enter is NOT added to the text. The newlines at the end are cut
    down to a single one, which is the only thing ever removed from the text: spaces, and the newlines inside the text, stay.

    The completer matches the line being typed (the text from the start of the cursor's line up to the cursor) and lists its matches
    in a popup. While the popup is open Enter, Tab and Escape belong to it, so choosing a completion never commits. The
    choice-management API is the same as :class:`AutoCompleteTextCtrl`'s.
    """

    # how many Enters in a row save the text
    COMMIT_ENTERS: int = 3

    returnPressed: QtCore.SignalInstance = QtCore.Signal()

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None = None, choices: list[str] | None = None):
        """Initialise the :class:`AutoCompleteTextEdit` instance.

        :param parent: Parent object.
        :type parent: QtWidgets.QWidget | None
        :param choices: The strings the completer offers.
        :type choices: list[str] | None
        """
        super().__init__(parent)
        self._choices = list(choices or [])
        self._completer = QtWidgets.QCompleter(self._choices, self)
        self._completer.setWidget(self)
        self._completer.setCaseSensitivity(
            QtCore.Qt.CaseSensitivity.CaseInsensitive)

        self._completer.setCompletionMode(
            QtWidgets.QCompleter.CompletionMode.PopupCompletion)

        self._completer.activated.connect(self._insert_completion)

    # ------------------------------------------------------------------
    # Enter handling and completion
    # ------------------------------------------------------------------
    @_check_types.do
    def _line_prefix(self) -> str:
        """Return the text from the start of the cursor's line up to the cursor.

        :returns: The text the completer matches against.
        :rtype: str
        """
        cursor = self.textCursor()
        cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.StartOfBlock,
            QtGui.QTextCursor.MoveMode.KeepAnchor)

        return cursor.selectedText()

    @_check_types.do
    def _insert_completion(self, completion: str) -> None:
        """Replace the line being typed with the chosen completion.

        :param completion: The completion the user picked.
        :type completion: str
        """
        cursor = self.textCursor()
        cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.StartOfBlock,
            QtGui.QTextCursor.MoveMode.KeepAnchor)

        cursor.insertText(completion)
        self.setTextCursor(cursor)

    @_check_types.do
    def _is_commit_enter(self, event: QtGui.QKeyEvent) -> bool:
        """Return whether *event* is the Enter that commits.

        That is a plain Enter (the keypad's counts) pressed with the cursor at the end of text that already ends in
        ``COMMIT_ENTERS - 1`` newlines, so it is the third Enter in a row.

        :param event: The key event.
        :type event: QtGui.QKeyEvent
        :returns: ``True`` for the committing Enter.
        :rtype: bool
        """
        if event.key() not in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            return False

        modifiers = event.modifiers() & ~QtCore.Qt.KeyboardModifier.KeypadModifier
        if modifiers != QtCore.Qt.KeyboardModifier.NoModifier:
            return False

        cursor = self.textCursor()
        return (not cursor.hasSelection() and cursor.atEnd()
                and self.toPlainText().endswith('\n' * (self.COMMIT_ENTERS - 1)))

    @_check_types.do
    def _leave_single_newline(self) -> None:
        """Cut the newlines at the end of the text down to one. This is the only thing ever removed from the text."""
        text = self.toPlainText()
        extra = len(text) - len(text.rstrip('\n')) - 1

        if extra > 0:
            cursor = self.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            cursor.movePosition(
                QtGui.QTextCursor.MoveOperation.Left,
                QtGui.QTextCursor.MoveMode.KeepAnchor, extra)

            cursor.removeSelectedText()

    @_check_types.do
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Commit on the third Enter, otherwise type normally and update the completion popup.

        :param event: The key event.
        :type event: QtGui.QKeyEvent
        """
        popup = self._completer.popup()

        if popup.isVisible() and event.key() in (
                QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter,
                QtCore.Qt.Key.Key_Escape, QtCore.Qt.Key.Key_Tab,
                QtCore.Qt.Key.Key_Backtab):
            # the open popup takes these keys
            event.ignore()
            return

        if self._is_commit_enter(event):
            # this Enter is not added to the text, and the newlines the earlier Enters typed are cut down to one
            self._leave_single_newline()
            self.returnPressed.emit()
            return

        super().keyPressEvent(event)

        if not event.text():
            # a modifier or navigation key: leave the popup as it is
            return

        prefix = self._line_prefix()
        if not prefix:
            popup.hide()
            return

        if prefix != self._completer.completionPrefix():
            self._completer.setCompletionPrefix(prefix)
            popup.setCurrentIndex(self._completer.completionModel().index(0, 0))

        rect = self.cursorRect()
        rect.setWidth(
            popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width())

        self._completer.complete(rect)

    # ------------------------------------------------------------------
    # Choice management (same API as AutoCompleteTextCtrl)
    # ------------------------------------------------------------------
    @_check_types.do
    def _rebuild_completer(self) -> None:
        """Rebuild the completer's model from the current choices."""
        self._completer.setModel(
            QtCore.QStringListModel(self._choices, self._completer))

    @_check_types.do
    def Clear(self) -> None:
        """Remove every choice (not the text)."""
        self._choices.clear()
        self._rebuild_completer()

    @_check_types.do
    def Delete(self, n: int) -> None:
        """Remove choice *n*.

        :param n: Index of the choice.
        :type n: int
        """
        self._choices.pop(n)
        self._rebuild_completer()

    @_check_types.do
    def Insert(self, item: str, pos: int) -> None:
        """Insert a choice at *pos*.

        :param item: The choice.
        :type item: str
        :param pos: Where to insert it.
        :type pos: int
        """
        self._choices.insert(pos, item)
        self._rebuild_completer()

    @_check_types.do
    def Set(self, items: list[str]) -> None:
        """Replace every choice.

        :param items: The new choices.
        :type items: list[str]
        """
        self._choices = list(items)
        self._rebuild_completer()

    @_check_types.do
    def SetItems(self, items: list[str]) -> None:
        """Replace every choice (same as :meth:`Set`).

        :param items: The new choices.
        :type items: list[str]
        """
        self.Set(items)

    @_check_types.do
    def Append(self, item: str) -> None:
        """Add a choice, or each choice of a list.

        :param item: The choice, or a list of them.
        :type item: str
        """
        if isinstance(item, list):
            self._choices.extend(item)
        else:
            self._choices.append(item)

        self._rebuild_completer()

    # ------------------------------------------------------------------
    # Value access
    # ------------------------------------------------------------------
    @_check_types.do
    def SetValue(self, value: str) -> None:
        """Set the text without emitting signals, with the cursor at the end.

        :param value: The text.
        :type value: str
        """
        self.blockSignals(True)
        self.setPlainText(value)
        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self.blockSignals(False)

    @_check_types.do
    def GetValue(self) -> str:
        """Return the text exactly as it is (nothing stripped).

        :returns: The text.
        :rtype: str
        """
        return self.toPlainText()
