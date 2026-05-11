# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import (
    QDialog, QLineEdit, QPushButton, QScrollArea, QWidget,
    QVBoxLayout, QHBoxLayout, QDialogButtonBox, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt


class _ArrayDialog(QDialog):
    """Shared base for ArrayFloat/Int/String dialogs."""

    _char_filter = None  # subclass sets to a callable(key_int) -> bool

    def __init__(self, parent, values, title='Modify Array'):
        QDialog.__init__(
            self, parent,
            Qt.Dialog | Qt.WindowStaysOnTopHint |
            Qt.WindowCloseButtonHint | Qt.WindowTitleHint
        )
        self.setWindowTitle(title)
        self.resize(300, 500)
        self.setSizeGripEnabled(True)

        # toolbar buttons
        self.add_item_button = QPushButton('+', self)
        self.remove_item_button = QPushButton('-', self)
        self.move_item_up_button = QPushButton('\u25b2', self)
        self.move_item_down_button = QPushButton('\u25bc', self)
        for btn in (self.add_item_button, self.remove_item_button):
            f = btn.font()
            f.setPointSize(f.pointSize() + 4)
            btn.setFont(f)
        self.add_item_button.setFixedSize(30, 30)
        self.remove_item_button.setFixedSize(30, 30)
        self.move_item_up_button.setFixedSize(30, 30)
        self.move_item_down_button.setFixedSize(30, 30)
        self.add_item_button.setToolTip('Add Item')
        self.remove_item_button.setToolTip('Remove Item')
        self.move_item_up_button.setToolTip('Move Item Up')
        self.move_item_down_button.setToolTip('Move Item Down')
        self.move_item_up_button.setEnabled(False)
        self.move_item_down_button.setEnabled(False)
        self.remove_item_button.setEnabled(False)

        self.add_item_button.clicked.connect(self._on_add_item)
        self.remove_item_button.clicked.connect(self._on_remove_item)
        self.move_item_up_button.clicked.connect(self._on_move_item_up)
        self.move_item_down_button.clicked.connect(self._on_move_item_down)

        # scroll area
        self._scroll_container = QWidget()
        self._item_layout = QVBoxLayout(self._scroll_container)
        self._item_layout.setContentsMargins(5, 5, 5, 5)
        self._item_layout.addStretch(1)

        scroll = QScrollArea(self)
        scroll.setWidget(self._scroll_container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Panel)
        scroll.setFrameShadow(QFrame.Sunken)

        self.selected_item = None
        self._items = []

        for v in values:
            self._add_ctrl(str(v))

        # button bar
        btn_bar = QHBoxLayout()
        btn_bar.addStretch(1)
        for b in (self.add_item_button, self.remove_item_button,
                  self.move_item_up_button, self.move_item_down_button):
            btn_bar.addWidget(b)

        sep = QFrame(self)
        sep.setFrameShape(QFrame.HLine)

        dialog_btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        dialog_btns.accepted.connect(self.accept)
        dialog_btns.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(btn_bar)
        layout.addWidget(sep)
        layout.addWidget(scroll, stretch=1)
        layout.addWidget(dialog_btns)
        self.setLayout(layout)

    def _add_ctrl(self, text=''):
        ctrl = QLineEdit(text, self._scroll_container)
        if self._char_filter:
            ctrl.textEdited.connect(self._filter_input)
        ctrl.focusInEvent = lambda e, c=ctrl: self._on_item_focus(c, e)
        ctrl.focusOutEvent = lambda e, c=ctrl: self._on_item_kill_focus(c, e)
        # insert before the trailing stretch
        pos = self._item_layout.count() - 1
        self._item_layout.insertWidget(pos, ctrl)
        self._items.append(ctrl)
        return ctrl

    def _filter_input(self, text):
        ctrl = self.sender()
        filtered = ''.join(ch for ch in text if self._char_filter(ord(ch)))
        if filtered != text:
            ctrl.blockSignals(True)
            ctrl.setText(filtered)
            ctrl.blockSignals(False)

    def _on_item_focus(self, ctrl, event):
        QLineEdit.focusInEvent(ctrl, event)
        self.selected_item = ctrl
        ctrl.selectAll()
        idx = self._items.index(ctrl)
        n = len(self._items)
        self.move_item_up_button.setEnabled(idx > 0)
        self.move_item_down_button.setEnabled(idx < n - 1)
        self.remove_item_button.setEnabled(True)

    def _on_item_kill_focus(self, ctrl, event):
        QLineEdit.focusOutEvent(ctrl, event)
        fw = self.focusWidget()
        if fw not in self._items and fw not in (
            self.add_item_button, self.remove_item_button,
            self.move_item_up_button, self.move_item_down_button
        ):
            self.move_item_up_button.setEnabled(False)
            self.move_item_down_button.setEnabled(False)
            self.remove_item_button.setEnabled(False)
            self.selected_item = None

    def _on_move_item_up(self):
        if self.selected_item is None:
            return
        idx = self._items.index(self.selected_item)
        if idx == 0:
            return
        v1 = self.selected_item.text()
        v2 = self._items[idx - 1].text()
        self.selected_item.setText(v2)
        self._items[idx - 1].setText(v1)
        self._items[idx - 1].setFocus()

    def _on_move_item_down(self):
        if self.selected_item is None:
            return
        idx = self._items.index(self.selected_item)
        if idx >= len(self._items) - 1:
            return
        v1 = self.selected_item.text()
        v2 = self._items[idx + 1].text()
        self.selected_item.setText(v2)
        self._items[idx + 1].setText(v1)
        self._items[idx + 1].setFocus()

    def _on_remove_item(self):
        if self.selected_item is None:
            return
        idx = self._items.index(self.selected_item)
        ctrl = self._items.pop(idx)
        self._item_layout.removeWidget(ctrl)
        ctrl.deleteLater()
        self.selected_item = None
        self.move_item_up_button.setEnabled(False)
        self.move_item_down_button.setEnabled(False)
        self.remove_item_button.setEnabled(False)

    def _on_add_item(self):
        ctrl = self._add_ctrl('')
        ctrl.setFocus()

    def _raw_values(self) -> list:
        return [c.text() for c in self._items if c.text() != '']
