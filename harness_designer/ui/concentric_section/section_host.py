# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Off-screen hosting for one peg-board concentric section widget.

Wraps a :class:`.section_widget.ConcentricSectionWidget` in a hidden
``QMdiArea`` / ``QMdiSubWindow`` pair that is never shown on a real screen
(``WA_DontShowOnScreen``) and is grabbed on demand into a raw RGBA buffer that
``objects.objects_pegboard.section.Section`` uploads as a GL texture -- exactly
how ``ui.pegboard_table.mdi_host.PegboardTableHost`` hosts a wire table. The
``QMdiSubWindow`` is what gives the panel a real Qt-painted title bar, close
button, drag-to-move and drag-to-resize without any hand-written chrome. Read
that module's docstring and MEMORY.md's Peg Board Editor entries for the "why"
of each trick used here (the hover move that must precede a press, the
oversized area that lets the sub-window grow, the rest point that keeps the
capture rectangle honest).

Unlike the wire table's host, this one also owns the SYNTHETIC EVENT DISPATCH
(hover, press, double click, drag, release, wheel). The GL object only turns a
canvas pixel into a point in the host's own coordinate frame
(:func:`~objects.objects_pegboard.section.Section._screen_to_panel_local`) and
calls these; keeping the dispatch here means it can be exercised against the
real widget without a GL context.

The coordinate constants are the wire tables' own, imported rather than
copied, so a section and a table share one coordinate frame.
"""

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from . import section_widget as _section_widget
from ..pegboard_table import mdi_host as _mdi_host
from ... import check_types as _check_types


PIXELS_PER_MM = _mdi_host.PIXELS_PER_MM
SUB_WINDOW_ANCHOR = _mdi_host.SUB_WINDOW_ANCHOR

_MDI_AREA_SIZE = _mdi_host._MDI_AREA_SIZE  # NOQA
_SUB_WINDOW_REST_POINT = _mdi_host._SUB_WINDOW_REST_POINT  # NOQA
_CursorAndCloseFilter = _mdi_host._CursorAndCloseFilter  # NOQA


class ConcentricSectionHost(QtWidgets.QMdiArea):
    """Hidden ``QMdiArea`` hosting one :class:`~.section_widget.
    ConcentricSectionWidget` in a ``QMdiSubWindow`` -- title bar, close
    button, move and resize are all real Qt widget behaviour, and all work
    with synthetic events (see the dispatch methods)."""

    close_requested: QtCore.SignalInstance = QtCore.Signal()
    cursor_changed: QtCore.SignalInstance = QtCore.Signal(QtGui.QCursor)

    @_check_types.do
    def __init__(self, title: str, width_mm: float, height_mm: float):
        """
        :param title: Title bar text of the hosted sub-window.
        :param width_mm: Width, in world mm (``pjt_pegboard_sections.size``).
        :param height_mm: Height, in world mm.
        """
        super().__init__()

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        # a real alpha channel through the paint pipeline, so what is not drawn
        # stays transparent in the captured image (see mdi_host.PegboardTableHost)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)

        self.section = _section_widget.ConcentricSectionWidget()

        self._hover_target: QtWidgets.QWidget | None = None
        self._press_target: QtWidgets.QWidget | None = None

        self.sub_window = QtWidgets.QMdiSubWindow()
        self.sub_window.setWidget(self.section)
        self.sub_window.setWindowTitle(title)

        # a fully transparent (never null) icon stops Qt substituting its own
        # title-bar icon -- see mdi_host.PegboardTableHost
        transparent_icon = QtGui.QPixmap(16, 16)
        transparent_icon.fill(QtCore.Qt.GlobalColor.transparent)
        self.sub_window.setWindowIcon(QtGui.QIcon(transparent_icon))
        self.sub_window.setSystemMenu(None)

        # title bar + close button only
        self.sub_window.setWindowFlags(
            QtCore.Qt.WindowType.CustomizeWindowHint
            | QtCore.Qt.WindowType.WindowTitleHint
            | QtCore.Qt.WindowType.WindowCloseButtonHint)

        self._sub_window_filter = _CursorAndCloseFilter(self)
        self._sub_window_filter.cursor_changed.connect(self.cursor_changed.emit)
        self._sub_window_filter.close_requested.connect(self.close_requested.emit)
        self.sub_window.installEventFilter(self._sub_window_filter)

        self.addSubWindow(self.sub_window)

        self.sub_window.resize(int(width_mm * PIXELS_PER_MM), int(height_mm * PIXELS_PER_MM))
        self.sub_window.move(_SUB_WINDOW_REST_POINT)

        self.sub_window.show()
        self.setActiveSubWindow(self.sub_window)

        self.setBackground(QtGui.QBrush(QtGui.QColor(0, 0, 0, 0)))
        self.resize(_MDI_AREA_SIZE)

    # ── the buffer ────────────────────────────────────────────────────────
    @_check_types.do
    def sub_window_moved(self) -> QtCore.QPoint:
        """How far the sub-window has drifted from its rest point -- nonzero
        after the user dragged its title bar or an edge. The caller folds it
        into the world position and calls :meth:`reset_sub_window_position`."""
        return self.sub_window.pos() - _SUB_WINDOW_REST_POINT

    @_check_types.do
    def reset_sub_window_position(self) -> None:
        """Put the sub-window back at its rest point."""
        self.sub_window.move(_SUB_WINDOW_REST_POINT)

    @_check_types.do
    def resize_sub_window(self, width_px: int, height_px: int) -> None:
        """Resize the sub-window, for an edge drag on the peg board.

        After a programmatic resize in a scripted run (2026-10-25) the title
        bar's close button stopped answering clicks -- it stayed drawn in its
        hover colour and no click reached it -- until the sub-window was
        activated again; a hover, a repaint, ``processEvents`` and
        ``hide()`` / ``show()`` did not bring it back. So it is deactivated and
        re-activated here. That run was a scratch script, not the real app, so
        whether the app needs this is unconfirmed.

        :param width_px: New width, in the host's logical pixels.
        :param height_px: New height.
        """
        self.sub_window.resize(width_px, height_px)
        self.setActiveSubWindow(None)
        self.setActiveSubWindow(self.sub_window)

    @_check_types.do
    def grab_rgba(self) -> tuple[bytes, int, int]:
        """Capture the sub-window's current appearance.

        :returns: Raw RGBA8888 bytes, width, height -- ready for
            ``glTexImage2D``.
        :rtype: tuple[bytes, int, int]
        """
        # flush deferred layout / style work first, so the capture is current
        QtWidgets.QApplication.processEvents()

        rect = QtCore.QRect(SUB_WINDOW_ANCHOR, self.sub_window.size())
        pixmap = self.grab(rect)
        image = pixmap.toImage().convertToFormat(QtGui.QImage.Format.Format_RGBA8888)

        return bytes(image.constBits()), image.width(), image.height()

    # ── synthetic event dispatch ──────────────────────────────────────────
    @_check_types.do
    def has_press(self) -> bool:
        """Whether a press is in progress (its drag / release is expected)."""
        return self._press_target is not None

    @_check_types.do
    def cancel_press(self) -> None:
        """Forget an in-progress press (the OS broke the mouse grab)."""
        self._press_target = None

    @_check_types.do
    def _target_at(self, point: QtCore.QPoint) -> QtWidgets.QWidget:
        """The widget under *point* (host coordinates). The sub-window's own
        title bar and border belong to no child widget, so a miss means the
        sub-window itself, whose mouse handling does the real move / resize
        hit-testing -- not the ``QMdiArea``, which ignores them."""
        target = self.childAt(point)
        if target is None:
            return self.sub_window

        return target

    @_check_types.do
    def hover_cursor(self) -> QtGui.QCursor:
        """The cursor the widget currently under the pointer asks for."""
        if self._hover_target is None:
            return QtGui.QCursor()

        return self._hover_target.cursor()

    @_check_types.do
    def dispatch_hover(self, panel_local: QtCore.QPointF,
                       modifiers: QtCore.Qt.KeyboardModifier = QtCore.Qt.KeyboardModifier.NoModifier) -> None:
        """Move the (button-less) pointer to *panel_local*, entering / leaving
        widgets on the way, so native hover feedback works."""
        point = panel_local.toPoint()
        target = self._target_at(point)

        local_point = target.mapFrom(self, point)
        global_point = target.mapToGlobal(local_point)

        if target is not self._hover_target:
            if self._hover_target is not None:
                QtWidgets.QApplication.sendEvent(
                    self._hover_target, QtCore.QEvent(QtCore.QEvent.Type.Leave))

            enter = QtGui.QEnterEvent(
                QtCore.QPointF(local_point), QtCore.QPointF(global_point), QtCore.QPointF(global_point))
            QtWidgets.QApplication.sendEvent(target, enter)
            self._hover_target = target

        move = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseMove, QtCore.QPointF(local_point), QtCore.QPointF(global_point),
            QtCore.Qt.MouseButton.NoButton, QtCore.Qt.MouseButton.NoButton, modifiers)
        QtWidgets.QApplication.sendEvent(target, move)

    @_check_types.do
    def clear_hover(self) -> None:
        """The pointer left the panel."""
        if self._hover_target is None:
            return

        QtWidgets.QApplication.sendEvent(
            self._hover_target, QtCore.QEvent(QtCore.QEvent.Type.Leave))
        self._hover_target = None

    @_check_types.do
    def _press_like(self, panel_local: QtCore.QPointF, event_type: QtCore.QEvent.Type) -> None:
        point = panel_local.toPoint()
        target = self._target_at(point)

        local_point = target.mapFrom(self, point)
        global_point = target.mapToGlobal(local_point)

        self._press_target = target

        # A MouseMove to the target's own position must reach it BEFORE the
        # press: QMdiSubWindow reads hoveredSubControl, which only a hover
        # move establishes, not the press itself (see mdi_host).
        hover = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseMove, QtCore.QPointF(local_point), QtCore.QPointF(global_point),
            QtCore.Qt.MouseButton.NoButton, QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier)
        QtWidgets.QApplication.sendEvent(target, hover)

        press = QtGui.QMouseEvent(
            event_type, QtCore.QPointF(local_point), QtCore.QPointF(global_point),
            QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier)
        QtWidgets.QApplication.sendEvent(target, press)

    @_check_types.do
    def dispatch_press(self, panel_local: QtCore.QPointF) -> None:
        """A left press at *panel_local*; the widget it landed on keeps
        receiving the drag and the release, as a real mouse grab would."""
        self._press_like(panel_local, QtCore.QEvent.Type.MouseButtonPress)

    @_check_types.do
    def dispatch_double_click(self, panel_local: QtCore.QPointF) -> None:
        self._press_like(panel_local, QtCore.QEvent.Type.MouseButtonDblClick)

    @_check_types.do
    def dispatch_drag_move(self, panel_local: QtCore.QPointF) -> None:
        """Move the held left button to *panel_local*."""
        target = self._press_target
        if target is None:
            return

        # deliberately mapped through the host, NOT clamped to the target's own
        # rect: a real drag carries the pointer outside the widget that grabbed it
        local_point = target.mapFrom(self, panel_local.toPoint())
        global_point = target.mapToGlobal(local_point)

        move = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseMove, QtCore.QPointF(local_point), QtCore.QPointF(global_point),
            QtCore.Qt.MouseButton.NoButton, QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier)
        QtWidgets.QApplication.sendEvent(target, move)

    @_check_types.do
    def dispatch_release(self, panel_local: QtCore.QPointF) -> None:
        """Release the left button at *panel_local*."""
        target = self._press_target
        if target is None:
            return

        local_point = target.mapFrom(self, panel_local.toPoint())
        global_point = target.mapToGlobal(local_point)

        release = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonRelease, QtCore.QPointF(local_point), QtCore.QPointF(global_point),
            QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier)
        QtWidgets.QApplication.sendEvent(target, release)

        self._press_target = None

    @_check_types.do
    def _scroll_area_at(self, point: QtCore.QPoint) -> QtWidgets.QAbstractScrollArea | None:
        """The scroll area under *point* (the information pane), if any. The
        walk stops before the ``QMdiArea`` itself, which is a scroll area
        too but has nothing to scroll."""
        current = self._target_at(point)
        while current is not None and current is not self:
            if isinstance(current, QtWidgets.QAbstractScrollArea):
                return current

            current = current.parentWidget()

        return None

    @_check_types.do
    def dispatch_wheel(self, panel_local: QtCore.QPointF, qt_wheel_event: QtGui.QWheelEvent) -> bool:
        """Scroll whatever scroll area is under *panel_local* (the wheel is
        delivered to its viewport -- a wheel sent to a child inside it does
        not propagate up for a synthetic event).

        :returns: ``True`` if a scroll area took it; ``False`` over anything
            else, so the caller can let the camera zoom instead.
        """
        point = panel_local.toPoint()
        scroll_area = self._scroll_area_at(point)
        if scroll_area is None:
            return False

        viewport = scroll_area.viewport()
        local_point = viewport.mapFrom(self, point)
        global_point = viewport.mapToGlobal(local_point)

        wheel = QtGui.QWheelEvent(
            QtCore.QPointF(local_point), QtCore.QPointF(global_point),
            qt_wheel_event.pixelDelta(), qt_wheel_event.angleDelta(),
            qt_wheel_event.buttons(), qt_wheel_event.modifiers(),
            qt_wheel_event.phase(), qt_wheel_event.inverted(), qt_wheel_event.source())
        wheel.setTimestamp(qt_wheel_event.timestamp())
        QtWidgets.QApplication.sendEvent(viewport, wheel)
        return True
