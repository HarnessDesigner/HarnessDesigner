
from PySide6 import QtWidgets
from PySide6 import QtCore


class TextCtrl(QtWidgets.QWidget):
    """Label + text input + optional Apply button composite widget.

    Replaces the wx.BoxSizer-based TextCtrl.

    Styles
    ------
    readonly     - text is read-only
    multiline    - use QTextEdit instead of QLineEdit
    hslider      - enable horizontal scrolling (default True)
    apply_button - show an Apply button (default True); when shown, the widget
                   emits apply_clicked when the button is pressed.  When hidden,
                   it emits text_committed on Enter (QLineEdit) or whenever text
                   changes (QTextEdit).

    Signals
    -------
    apply_clicked()   - Apply button pressed (only when apply_button=True)
    text_committed()  - Enter pressed (apply_button=False, single-line only)
    """

    apply_clicked: QtCore.SignalInstance = QtCore.Signal()
    text_committed: QtCore.SignalInstance = QtCore.Signal()
    text_changed: QtCore.SignalInstance = QtCore.Signal(str)

    def __init__(self, parent=None, label: str = '', size=None,
                 style: int = 0, apply_button: bool = True, # NOQA
                 hslider: bool = True, readonly: bool = False,
                 multiline: bool = False):
        """Initialise the :class:`TextCtrl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: str
        :param size: Value for ``size``.
        :type size: UNKNOWN
        :param style: Value for ``style``.
        :type style: int
        :param apply_button: Value for ``apply_button``.
        :type apply_button: bool
        :param hslider: Value for ``hslider``.
        :type hslider: bool
        :param readonly: Value for ``readonly``.
        :type readonly: bool
        :param multiline: Value for ``multiline``.
        :type multiline: bool
        """

        super().__init__(parent)
        self._show_apply_button = apply_button
        self._original_text = ''
        self._multiline = multiline

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.st = QtWidgets.QLabel(label, self)

        if multiline:
            self.ctrl = QtWidgets.QTextEdit(self)
            self.ctrl.setReadOnly(readonly)

            if not hslider:
                self.ctrl.setLineWrapMode(
                    QtWidgets.QTextEdit.LineWrapMode.WidgetWidth)
            else:
                self.ctrl.setLineWrapMode(
                    QtWidgets.QTextEdit.LineWrapMode.NoWrap)

            layout.addWidget(self.st, 1, QtCore.Qt.AlignmentFlag.AlignTop)
            layout.addWidget(self.ctrl, 4)
        else:
            self.ctrl = QtWidgets.QLineEdit(self)
            self.ctrl.setReadOnly(readonly)

            layout.addWidget(self.st, 1)
            layout.addWidget(self.ctrl, 4)
            self.ctrl.returnPressed.connect(self._on_enter)

        if apply_button:
            self.apply_button = QtWidgets.QPushButton('Apply', self)
            self.apply_button.setEnabled(False)
            layout.addWidget(self.apply_button, 1)
            self.apply_button.clicked.connect(self._on_apply)

            if multiline:
                self.ctrl.textChanged.connect(self._on_text_changed_multi)
            else:
                self.ctrl.textChanged.connect(self._on_text_changed)

        else:
            self.apply_button = None

        if size is not None:
            w, h = size

            if w > -1:
                self.ctrl.setFixedWidth(w)
            if h > -1:
                self.ctrl.setFixedHeight(w)

        # Always forward the inner control's text-change to our public signal
        # so callers never need to reach inside via .ctrl
        if multiline:
            self.ctrl.textChanged.connect(
                lambda: self.text_changed.emit(self.ctrl.toPlainText()))
        else:
            self.ctrl.textChanged.connect(self.text_changed.emit)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _on_text_changed(self, text: str):
        """Handle the text changed event.

        UNKNOWN details are inferred from the callable name and signature.

        :param text: Text value.
        :type text: str
        """
        QtCore.QTimer.singleShot(
            0, lambda: self.apply_button.setEnabled(text != self._original_text))

    def _on_text_changed_multi(self):
        """Handle the text changed multi event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        if isinstance(self.ctrl, QtWidgets.QTextEdit):
            text = self.ctrl.toPlainText()

            QtCore.QTimer.singleShot(
                0, lambda: self.apply_button.setEnabled(text != self._original_text))

    def _on_enter(self):
        """Handle the enter event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        if self._show_apply_button:
            # In single-line + apply_button mode, Enter inserts a newline in
            # the original code.  Replicate that behaviour.
            pass
        else:
            self.text_committed.emit()

    def _on_apply(self):
        """Handle the apply event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.apply_clicked.emit()

    # ------------------------------------------------------------------
    # wx-compatible public API
    # ------------------------------------------------------------------
    def Enable(self, flag: bool = True):
        """Execute the enable operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        self.ctrl.setEnabled(flag)
        self.st.setEnabled(flag)

        if self._show_apply_button:
            if flag:
                cur = self.GetValue()
                self.apply_button.setEnabled(cur != self._original_text)
            else:
                self.apply_button.setEnabled(False)

    def SetToolTip(self, text: str):
        """Execute the set tool tip operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param text: Text value.
        :type text: str
        """
        self.ctrl.setToolTip(text)
        self.st.setToolTip(text)

    SetToolTipString = SetToolTip

    def SetValue(self, value: str):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._original_text = value
        if isinstance(self.ctrl, QtWidgets.QTextEdit):
            self.ctrl.blockSignals(True)
            self.ctrl.setPlainText(value)
            self.ctrl.blockSignals(False)
        else:
            self.ctrl.blockSignals(True)
            self.ctrl.setText(value)
            self.ctrl.blockSignals(False)

        if self.apply_button is not None:
            self.apply_button.setEnabled(False)

    def GetValue(self) -> str:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        if isinstance(self.ctrl, QtWidgets.QTextEdit):
            return self.ctrl.toPlainText()

        return self.ctrl.text()

    # ------------------------------------------------------------------
    # Forwarding helpers — let callers interact with appearance / completion
    # without reaching into the private .ctrl attribute directly
    # ------------------------------------------------------------------
    def setCompleter(self, completer):
        """Forward to the inner QLineEdit (single-line only)."""
        if not self._multiline:
            self.ctrl.setCompleter(completer)

    def inputPalette(self):
        """Return the palette of the inner input control."""
        return self.ctrl.palette()

    def setInputPalette(self, palette):
        """Apply *palette* to the inner input control."""
        self.ctrl.setPalette(palette)
