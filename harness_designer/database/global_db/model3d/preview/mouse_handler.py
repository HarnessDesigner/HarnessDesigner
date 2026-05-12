# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QMouseEvent, QWheelEvent

from . import Preview as _Preview
from ....geometry import point as _point

from .... import config as _config

Config = _config.Config

MOUSE_NONE = _config.MOUSE_NONE
MOUSE_LEFT = _config.MOUSE_LEFT
MOUSE_MIDDLE = _config.MOUSE_MIDDLE
MOUSE_RIGHT = _config.MOUSE_RIGHT
MOUSE_AUX1 = _config.MOUSE_AUX1
MOUSE_AUX2 = _config.MOUSE_AUX2
MOUSE_WHEEL = _config.MOUSE_WHEEL

MOUSE_REVERSE_X_AXIS = _config.MOUSE_REVERSE_X_AXIS
MOUSE_REVERSE_Y_AXIS = _config.MOUSE_REVERSE_Y_AXIS
MOUSE_REVERSE_WHEEL_AXIS = _config.MOUSE_REVERSE_WHEEL_AXIS
MOUSE_SWAP_AXIS = _config.MOUSE_SWAP_AXIS


class MouseHandler:

    def __init__(self, canvas: _Preview):
        self.canvas = canvas
        self.mouse_pos = None

        # Install as event filter on canvas
        canvas.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is not self.canvas:
            return False

        t = event.type()
        if t == QEvent.Type.MouseButtonPress:
            self._on_mouse_press(event)
        elif t == QEvent.Type.MouseButtonRelease:
            self._on_mouse_release(event)
        elif t == QEvent.Type.MouseMove:
            self._on_mouse_motion(event)
        elif t == QEvent.Type.Wheel:
            self._on_mouse_wheel(event)

        return False  # don't consume

    def _process_mouse(self, code):
        for config, func in (
            (Config.walk, self.canvas.Walk),
            (Config.truck_pedestal, self.canvas.TruckPedestal),
            (Config.reset, self.canvas.camera.Reset),
            (Config.rotate, self.canvas.Rotate),
            (Config.pan_tilt, self.canvas.PanTilt),
            (Config.zoom, self.canvas.Zoom)
        ):
            if config.mouse is None:
                continue

            if config.mouse & code:
                def _wrapper(dx, dy, _config=config, _func=func):
                    if _config.mouse & MOUSE_SWAP_AXIS:
                        _func(dy, dx)
                    else:
                        _func(dx, dy)
                return _wrapper

        def _do_nothing_func(_, __):
            pass

        return _do_nothing_func

    def _on_mouse_press(self, evt: QMouseEvent):
        pos = evt.position()
        self.mouse_pos = _point.Point(pos.x(), pos.y())
        self.canvas.setFocus()
        if not self.canvas.hasMouseTracking():
            self.canvas.setMouseTracking(True)

    def _on_mouse_release(self, evt: QMouseEvent):
        pass

    def _on_mouse_wheel(self, evt: QWheelEvent):
        delta = 1.0 if evt.angleDelta().y() > 0 else -1.0
        self._process_mouse(MOUSE_WHEEL)(delta, 0.0)
        self.canvas.update()

    def _on_mouse_motion(self, evt: QMouseEvent):
        buttons = evt.buttons()
        if not (buttons & (Qt.MouseButton.LeftButton | Qt.MouseButton.MiddleButton |
                           Qt.MouseButton.RightButton | Qt.MouseButton.XButton1 |
                           Qt.MouseButton.XButton2)):
            return

        pos = evt.position()
        mouse_pos = _point.Point(pos.x(), pos.y())

        if self.mouse_pos is None:
            self.mouse_pos = mouse_pos

        delta = mouse_pos - self.mouse_pos
        self.mouse_pos = mouse_pos

        dx, dy = list(delta)[:-1]

        if buttons & Qt.MouseButton.LeftButton:
            self._process_mouse(MOUSE_LEFT)(dx, dy)
        if buttons & Qt.MouseButton.MiddleButton:
            self._process_mouse(MOUSE_MIDDLE)(dx, dy)
        if buttons & Qt.MouseButton.RightButton:
            self._process_mouse(MOUSE_RIGHT)(dx, dy)
        if buttons & Qt.MouseButton.XButton1:
            self._process_mouse(MOUSE_AUX1)(dx, dy)
        if buttons & Qt.MouseButton.XButton2:
            self._process_mouse(MOUSE_AUX2)(dx, dy)

        self.canvas.update()
