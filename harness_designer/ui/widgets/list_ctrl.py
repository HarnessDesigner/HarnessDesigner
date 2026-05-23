"""
ListCtrl — A reusable PySide6 widget for managing a list of items.

Signals:
    itemAdded(index: int, value: str | int | float)
    itemRemoved(index: int, value: str | int | float)
    itemChanged(index: int, new_value: str | int | float, old_value: str | int | float)

Features:
    - Compact scrollable list (one item per row)
    - Inline QLineEdit bar (disabled until Add / Edit is active)
    - Live preview of edits in the list as the user types
    - OK / Cancel to confirm or revert; signals only fire on OK
    - Double-click a row to enter Edit mode
    - Right-click context menu: Add | Edit | Remove
    - Optional exact (case-sensitive) uniqueness (programmatic only)
    - Typed values via item_type: signals emit int/float/str, not raw strings
    - Input validated against item_type before OK is enabled
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QListWidget, QLineEdit, QMenu, QApplication,
                               QSizePolicy)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QAction


class ListCtrl(QWidget):
    itemAdded = Signal(int, object)
    itemRemoved = Signal(int, object)
    itemChanged = Signal(int, object, object)

    _MODE_NONE = "none"
    _MODE_ADD = "add"
    _MODE_EDIT = "edit"

    def __init__(
        self,
        parent: QWidget,
        items: list[str | float | int] | None = None,
        unique: bool = False,
        item_type: type[str | int | float] = str,
    ):
        super().__init__(parent)

        self._item_type = item_type
        self._unique = unique
        self._mode = self._MODE_NONE
        self._edit_row = -1
        self._edit_original = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        # --- Compact scrollable list ------------------------------------
        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.setSortingEnabled(False)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.setSpacing(0)
        self._list.setUniformItemSizes(True)
        self._list.setSizePolicy(QSizePolicy.Policy.Expanding,
                                 QSizePolicy.Policy.Expanding)
        self._list.setMinimumHeight(80)
        root.addWidget(self._list, stretch=1)

        # --- Inline edit bar (disabled until Add / Edit activated) ------
        self._edit_bar = QWidget()
        bar_layout = QHBoxLayout(self._edit_bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(4)

        self._line_edit = QLineEdit()
        self._line_edit.setPlaceholderText("Enter value…")
        bar_layout.addWidget(self._line_edit)

        self._btn_ok = QPushButton("OK")
        self._btn_cancel = QPushButton("Cancel")
        self._btn_ok.setFixedWidth(56)
        self._btn_cancel.setFixedWidth(56)
        # Prevent these buttons from stealing Return keypresses that belong
        # to the parent dialog's default button.
        self._btn_ok.setAutoDefault(False)
        self._btn_ok.setDefault(False)
        self._btn_cancel.setAutoDefault(False)
        self._btn_cancel.setDefault(False)
        bar_layout.addWidget(self._btn_ok)
        bar_layout.addWidget(self._btn_cancel)

        self._edit_bar.setEnabled(False)
        root.addWidget(self._edit_bar)

        # --- Main button bar --------------------------------------------
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(6)

        self._btn_add = QPushButton("Add")
        self._btn_edit = QPushButton("Edit")
        self._btn_remove = QPushButton("Remove")
        self._btn_edit.setEnabled(False)
        self._btn_remove.setEnabled(False)

        btn_bar.addWidget(self._btn_add)
        btn_bar.addWidget(self._btn_edit)
        btn_bar.addStretch()
        btn_bar.addWidget(self._btn_remove)
        root.addLayout(btn_bar)

        self._btn_add.clicked.connect(self._enter_add_mode)
        self._btn_edit.clicked.connect(lambda: self._enter_edit_mode())
        self._btn_remove.clicked.connect(self._do_remove)

        self._btn_ok.clicked.connect(self._on_ok)
        self._btn_cancel.clicked.connect(self._on_cancel)
        self._line_edit.textChanged.connect(self._on_text_changed)

        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        self._list.itemDoubleClicked.connect(
            lambda itm: self._enter_edit_mode(self._list.row(itm)))
        self._list.customContextMenuRequested.connect(self._show_context_menu)

        for item in sorted(items or []):
            self._list.addItem(str(item))

    def _validate(self, value):
        if value == '':
            return False, None

        try:
            return True, self._item_type(value)

        except ValueError:
            return False, None

    def _existing_values(self, exclude_row: int = -1) -> set[str]:
        return {
            self._list.item(i).text()
            for i in range(self._list.count())
            if i != exclude_row
        }

    def _is_duplicate(self, text: str, exclude_row: int = -1) -> bool:
        return self._unique and text in self._existing_values(exclude_row)

    def _enter_add_mode(self) -> None:
        self._mode = self._MODE_ADD
        self._edit_row = -1
        self._edit_original = ""
        self._list.clearSelection()
        self._line_edit.clear()
        self._line_edit.setStyleSheet("")
        self._edit_bar.setEnabled(True)
        self._line_edit.setFocus()
        self._set_main_buttons_enabled(False)
        self._btn_ok.setEnabled(False)

    def _enter_edit_mode(self, row: int | None = None) -> None:
        if row is None:
            sel = self._list.selectedItems()
            if not sel:
                return
            row = self._list.row(sel[0])

        item = self._list.item(row)
        if item is None:
            return

        self._mode = self._MODE_EDIT
        self._edit_row = row
        self._edit_original = item.text()

        self._line_edit.blockSignals(True)
        self._line_edit.setText(self._edit_original)
        self._line_edit.blockSignals(False)

        self._line_edit.setStyleSheet("")
        self._edit_bar.setEnabled(True)
        self._line_edit.setFocus()
        self._line_edit.selectAll()
        self._set_main_buttons_enabled(False)
        self._btn_ok.setEnabled(False)

    def _exit_edit_mode(self) -> None:
        """Revert any live preview and disable the edit bar."""

        if self._mode == self._MODE_EDIT and self._edit_row >= 0:
            item = self._list.item(self._edit_row)
            if item:
                item.setText(self._edit_original)
                item.setForeground(QColor("black"))

        self._mode = self._MODE_NONE
        self._edit_row = -1
        self._edit_original = ""
        self._edit_bar.setEnabled(False)
        self._line_edit.clear()
        self._line_edit.setStyleSheet("")
        self._set_main_buttons_enabled(True)
        self._on_selection_changed()

    def _set_main_buttons_enabled(self, enabled: bool) -> None:
        self._btn_add.setEnabled(enabled)
        if not enabled:
            self._btn_edit.setEnabled(False)
            self._btn_remove.setEnabled(False)

    def _on_text_changed(self, text: str) -> None:
        stripped = text.strip()
        is_valid_type, typed = self._validate(stripped)

        if self._mode == self._MODE_EDIT:
            exclude = self._edit_row
        else:
            exclude = -1

        is_duplicate = self._is_duplicate(stripped, exclude_row=exclude)
        is_unchanged = (self._mode == self._MODE_EDIT and
                        stripped == self._edit_original)

        is_ok = is_valid_type and not is_duplicate and not is_unchanged

        # Red text for duplicate or invalid type, normal otherwise
        if not is_valid_type or is_duplicate:
            self._line_edit.setStyleSheet("QLineEdit { color: red; }")
        else:
            self._line_edit.setStyleSheet("")

        # Live preview in the list while in edit mode.
        # Show the normalised display string (e.g. "10.0" not "10" for float)
        # so the preview matches what will actually be committed.
        if self._mode == self._MODE_EDIT and self._edit_row >= 0:
            item = self._list.item(self._edit_row)
            if item:
                if is_valid_type and stripped:
                    preview = str(typed)
                else:
                    preview = stripped if stripped else self._edit_original

                item.setText(preview)

                if is_duplicate or not is_valid_type:
                    item.setForeground(QColor("red"))
                elif is_unchanged or not stripped:
                    item.setForeground(QColor("gray"))
                else:
                    item.setForeground(QColor("black"))

        self._btn_ok.setEnabled(is_ok)

    def _on_ok(self) -> None:
        if not self._btn_ok.isEnabled():
            return

        stripped = self._line_edit.text().strip()
        _, typed_value = self._validate(stripped)

        # Normalise: cast to target type and back so "10" -> "10.0" for float
        display = str(typed_value)

        if self._mode == self._MODE_ADD:
            row = self._list.count()
            self._list.addItem(display)
            self._list.setCurrentRow(row)
            self._exit_edit_mode()
            self.itemAdded.emit(row, typed_value)

        elif self._mode == self._MODE_EDIT:
            row = self._edit_row
            _, old_typed = self._validate(self._edit_original)

            item = self._list.item(row)
            if item:
                item.setText(display)
                item.setForeground(QColor("black"))

            self._exit_edit_mode()
            self.itemChanged.emit(row, typed_value, old_typed)

    def _on_cancel(self) -> None:
        self._exit_edit_mode()

    def _on_selection_changed(self) -> None:
        if self._mode != self._MODE_NONE:
            return

        has_selection = bool(self._list.selectedItems())
        self._btn_edit.setEnabled(has_selection)
        self._btn_remove.setEnabled(has_selection)

    def _do_remove(self, row: int | None = None) -> None:
        if row is None:
            sel = self._list.selectedItems()
            if not sel:
                return
            row = self._list.row(sel[0])

        if 0 <= row < self._list.count():
            item = self._list.takeItem(row)
            _, typed_value = self._validate(item.text())
            self.itemRemoved.emit(row, typed_value)

    def _show_context_menu(self, pos) -> None:
        if self._mode != self._MODE_NONE:
            return

        item = self._list.itemAt(pos)
        has_item = item is not None

        menu = QMenu(self)
        act_add = QAction("Add",    self)
        act_edit = QAction("Edit",   self)
        act_rem = QAction("Remove", self)

        act_edit.setEnabled(has_item)
        act_rem.setEnabled(has_item)

        menu.addAction(act_add)
        menu.addAction(act_edit)
        menu.addSeparator()
        menu.addAction(act_rem)

        act_add.triggered.connect(self._enter_add_mode)
        act_edit.triggered.connect(
            lambda: self._enter_edit_mode(self._list.row(item)) if item else None)

        act_rem.triggered.connect(
            lambda: self._do_remove(self._list.row(item)) if item else None)

        menu.exec(self._list.mapToGlobal(pos))

    @property
    def unique(self) -> bool:
        return self._unique

    @unique.setter
    def unique(self, value: bool) -> None:
        self._unique = value

    @property
    def item_type(self) -> type:
        return self._item_type

    def add_item(self, value: str | int | float) -> bool:
        """Append programmatically; returns False if blocked by uniqueness."""

        text = str(value)
        if self._is_duplicate(text):
            return False

        row = self._list.count()
        self._list.addItem(text)
        _, typed = self._validate(text)
        self.itemAdded.emit(row, typed)

        return True

    def remove_item(self, index: int) -> None:
        """Remove by index programmatically."""

        if 0 <= index < self._list.count():
            item = self._list.takeItem(index)
            _, typed = self._validate(item.text())
            self.itemRemoved.emit(index, typed)

    def set_item(self, index: int, value: str | int | float) -> bool:
        """Replace item at index programmatically; returns False if blocked."""

        text = str(value)

        item = self._list.item(index)
        if item is None:
            return False

        if self._is_duplicate(text, exclude_row=index):
            return False

        _, old_typed = self._validate(item.text())
        _, new_typed = self._validate(text)
        item.setText(text)
        self.itemChanged.emit(index, new_typed, old_typed)

        return True

    def GetValue(self) -> list[str | int | float]:
        """Return all current values cast to item_type."""
        res = []

        for i in range(self._list.count()):
            value = self._validate(self._list.item(i).text())[1]
            if value is None:
                continue

            res.append(value)

        return res

    def clear(self) -> None:
        """Remove all items without emitting signals."""

        self._list.clear()

    def count(self) -> int:
        return self._list.count()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("ListCtrl Demo")
    window.resize(380, 280)

    from PySide6.QtWidgets import QVBoxLayout as VBox
    layout = VBox(window)

    widget = ListCtrl(
        window,
        items=[1.26, 3.24, 7.69, 5.64, 8.32, 9.21, 15.78, 19.25],
        unique=True,
        item_type=float,
    )
    layout.addWidget(widget)

    widget.itemAdded.connect(
        lambda idx, val: print(f"[ADDED]   index={idx}  value={val!r}"))
    widget.itemRemoved.connect(
        lambda idx, val: print(f"[REMOVED] index={idx}  value={val!r}"))
    widget.itemChanged.connect(
        lambda idx, new, old: print(f"[CHANGED] index={idx}  old={old!r}  new={new!r}"))

    window.show()
    sys.exit(app.exec())
