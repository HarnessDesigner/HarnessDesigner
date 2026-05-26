from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6 import QtGui


# ---------------------------------------------------------------------------
# Non-colour constants
# ---------------------------------------------------------------------------
BOX_SIZE = 20
RADIUS = 5


def _palette() -> dict:
    """
    Build a colour dict from the current QApplication palette so the widget
    automatically matches the system/platform theme (light, dark, high-contrast).

    QPalette roles used:
      Base             — standard input-widget background (white / dark surface)
      Text             — foreground text colour
      Highlight        — accent/selection colour  → checked border & fill
      HighlightedText  — text drawn on top of Highlight → mark colour (✓ / ✗)
      Mid              — mid-tone between Base and Dark → idle border
      Shadow           — darkest shade → hover border
      BrightText       — high-contrast text; used as the X colour when reddish,
                         otherwise falls back to a standard red.
    """
    qp: QtGui.QPalette = QtWidgets.QApplication.palette()

    base = qp.color(QtGui.QPalette.ColorRole.Base)
    text = qp.color(QtGui.QPalette.ColorRole.Text)
    highlight = qp.color(QtGui.QPalette.ColorRole.Highlight)
    hi_text = qp.color(QtGui.QPalette.ColorRole.HighlightedText)
    mid = qp.color(QtGui.QPalette.ColorRole.Mid)
    shadow = qp.color(QtGui.QPalette.ColorRole.Shadow)
    bright_text = qp.color(QtGui.QPalette.ColorRole.BrightText)

    # X colour: use BrightText if it looks reddish, else a fixed red that
    # still reads clearly on any theme.
    x_color = (
        bright_text
        if bright_text.red() > 180 and bright_text.green() < 120
        else QtGui.QColor("#ef4444")
    )

    return {
        "border_idle":    mid,
        "border_hover":   shadow,
        "border_checked": highlight,
        "border_x":       x_color,
        "fill_empty":     base,
        "fill_checked":   highlight,
        "fill_x":         x_color,
        "mark_color":     hi_text,
        "label_color":    text,
        "radius":         RADIUS,
        "box_size":       BOX_SIZE,
    }


class _TriStateCheckBox(QtWidgets.QWidget):
    """
    Cycles Empty → Checked → X → Empty on each click.
    Emits stateChanged(int) whenever the state changes.
    """

    stateChanged: QtCore.SignalInstance = QtCore.Signal(object)

    # Human-readable names for each state
    STATE_NAMES = {0: "x", 1: "checked", 2: "empty"}

    def __init__(self, parent):
        super().__init__(parent)

        # 0=x, 1=check, 2=empty
        self._state: int = 2
        self._hovered: bool = False

        # suppress ring on click focus
        self._focus_from_mouse: bool = False

        # 0→1 used for draw scale pop
        self._anim_progress: float = 0.0

        # Animation for the mark appearing
        self._anim = QtCore.QPropertyAnimation(self, b"animProgress", self)
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QtCore.QEasingCurve.Type.OutBack)

        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.TabFocus)
        self._update_size_hint()

    # ------------------------------------------------------------------
    # Qt property for animation
    # ------------------------------------------------------------------
    def _get_anim_progress(self) -> float:
        return self._anim_progress

    def _set_anim_progress(self, v: float):
        self._anim_progress = v
        self.update()

    animProgress = QtCore.Property(float, _get_anim_progress, _set_anim_progress)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def state(self) -> int:
        return self._state

    def setState(self, state: bool | None):
        """
        Set state (0=X, 1=checked, 2=empty) programmatically.
        """

        if state is None:
            state = 2
        else:
            state = int(state)

        if state not in (0, 1, 2):
            raise ValueError("state must be 0, 1, or 2")

        if state == self._state:
            return

        self._state = state
        self._play_anim()
        self.stateChanged.emit(self.getState())
        self.update()

    def getState(self) -> bool | None:
        if self._state == 2:
            return None

        return bool(self._state)

    def stateName(self) -> str:
        return self.STATE_NAMES[self._state]

    # ------------------------------------------------------------------
    # Size
    # ------------------------------------------------------------------
    def _update_size_hint(self):
        w = BOX_SIZE
        h = max(BOX_SIZE, self._label_font_height()) + 4
        self.setMinimumSize(w, h)

    def sizeHint(self) -> QtCore.QSize:
        self._update_size_hint()
        return self.minimumSize()

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._focus_from_mouse = True
            self._cycle()

    def keyPressEvent(self, event):
        if event.key() in (
            QtCore.Qt.Key.Key_Space,
            QtCore.Qt.Key.Key_Return,
            QtCore.Qt.Key.Key_Enter
        ):
            self._focus_from_mouse = False
            self._cycle()
        else:
            super().keyPressEvent(event)

    def focusInEvent(self, event):
        # Tab/Shift-Tab → show ring; mouse click → suppress ring
        if event.reason() == QtCore.Qt.FocusReason.MouseFocusReason:
            self._focus_from_mouse = True
        else:
            self._focus_from_mouse = False

        super().focusInEvent(event)
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def _cycle(self):
        self._state = (self._state + 1) % 3
        self._play_anim()
        self.stateChanged.emit(self.getState())
        self.update()

    def _play_anim(self):
        self._anim.stop()
        self._anim_progress = 0.0
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------
    def paintEvent(self, event):
        pal = _palette()  # fresh from QApplication each paint
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        box = pal["box_size"]
        r = pal["radius"]
        rect = QtCore.QRect(0, (self.height() - box) // 2, box, box)

        # --- choose colours by state ---
        if self._state == 1:
            border_col = pal["border_checked"]
            fill_col = pal["fill_checked"]
        elif self._state == 0:
            border_col = pal["border_x"]
            fill_col = pal["fill_x"]
        else:
            border_col = pal["border_hover"] if self._hovered else pal[
                "border_idle"]
            fill_col = pal["fill_empty"]

        # --- box ---
        p.setPen(QtGui.QPen(border_col, 2))
        p.setBrush(QtGui.QBrush(fill_col))
        p.drawRoundedRect(rect, r, r)

        # --- focus ring (keyboard only) ---
        if self.hasFocus() and not self._focus_from_mouse:
            focus_pen = QtGui.QPen(pal["border_checked"], 2, QtCore.Qt.PenStyle.DotLine)
            p.setPen(focus_pen)
            p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), r + 2, r + 2)

        # --- mark (scaled by anim) ---
        if self._state != 0:
            scale = max(0.0, min(1.0, self._anim_progress))
            cx = rect.center().x()
            cy = rect.center().y()
            p.save()
            p.translate(cx, cy)
            p.scale(scale, scale)
            p.translate(-cx, -cy)
            self._draw_mark(p, rect, pal)
            p.restore()

    def _draw_mark(self, p: QtGui.QPainter, rect: QtCore.QRect, pal: dict):
        pen = QtGui.QPen(
            pal["mark_color"], 2.2,
            QtCore.Qt.PenStyle.SolidLine,
            QtCore.Qt.PenCapStyle.RoundCap,
            QtCore.Qt.PenJoinStyle.RoundJoin,
        )
        p.setPen(pen)
        p.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        m = rect.adjusted(4, 4, -4, -4)

        if self._state == 1:  # ✓ checkmark
            path = QtGui.QPainterPath()
            path.moveTo(m.left(), m.top() + m.height() * 0.5)
            path.lineTo(m.left() + m.width() * 0.38, m.bottom())
            path.lineTo(m.right(), m.top())
            p.drawPath(path)

        elif self._state == 0:  # ✗ X
            p.drawLine(m.topLeft(), m.bottomRight())
            p.drawLine(m.topRight(), m.bottomLeft())

    @staticmethod
    def _label_font() -> QtGui.QFont:
        f = QtGui.QFont()
        f.setPointSize(10)
        return f

    def _label_font_height(self) -> int:
        return QtGui.QFontMetrics(self._label_font()).height()


class TriStateCheckboxCtrl(QtWidgets.QWidget):
    """
    Label + checkbox composite widget.

    The original was a wx.BoxSizer subclass, which made it behave like a
    layout object.  In Qt the composite is a proper QWidget so it can be
    inserted into any layout with addWidget().  All public methods from the
    original are preserved.
    """

    def __init__(self, parent=None, label: str = ''):
        """Initialise the :class:`CheckboxCtrl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: str
        """
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.st = QtWidgets.QLabel(label, self)
        self.ctrl = _TriStateCheckBox(self)

        layout.addWidget(self.st, 1)
        layout.addWidget(self.ctrl, 1)

    # ------------------------------------------------------------------
    # wx-compatible API
    # ------------------------------------------------------------------
    def Enable(self, flag: bool = True):
        """
        Execute the enable operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        self.ctrl.setEnabled(flag)
        self.st.setEnabled(flag)

    def SetToolTip(self, text: str):
        """
        Execute the set tool tip operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param text: Text value.
        :type text: str
        """
        self.ctrl.setToolTip(text)
        self.st.setToolTip(text)

    # kept for call-site compatibility
    SetToolTipString = SetToolTip

    def SetValue(self, value: bool | None):
        """
        Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self.ctrl.blockSignals(True)
        self.ctrl.setState(value)
        self.ctrl.blockSignals(False)

    def GetValue(self) -> bool | None:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return self.ctrl.getState()

    # Expose the inner checkbox's signals so callers can do
    # ctrl.ctrl.checkStateChanged.connect(handler) or use the
    # convenience property below.
    @property
    def checkStateChanged(self):
        """Return the check state changed.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.ctrl.stateChanged
