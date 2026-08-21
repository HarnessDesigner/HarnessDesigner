# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import threading

from PySide6 import QtCore
from PySide6 import QtGui

from ... import debug as _debug
from .. import events as _events
from ...geometry import point as _point
from ... import app as _app
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import canvas_base as _canvas_base


KEY_MULTIPLES = {
    QtCore.Qt.Key.Key_Up:       [QtCore.Qt.Key.Key_Up],
    QtCore.Qt.Key.Key_Down:     [QtCore.Qt.Key.Key_Down],
    QtCore.Qt.Key.Key_Left:     [QtCore.Qt.Key.Key_Left],
    QtCore.Qt.Key.Key_Right:    [QtCore.Qt.Key.Key_Right],

    ord('-'): [ord('-'), QtCore.Qt.Key.Key_Minus],
    QtCore.Qt.Key.Key_Minus: [ord('-'), QtCore.Qt.Key.Key_Minus],

    ord('+'): [ord('+'), QtCore.Qt.Key.Key_Plus],
    QtCore.Qt.Key.Key_Plus: [ord('+'), QtCore.Qt.Key.Key_Plus],

    ord('/'): [ord('/'), QtCore.Qt.Key.Key_Slash],
    QtCore.Qt.Key.Key_Slash: [ord('/'), QtCore.Qt.Key.Key_Slash],

    ord('*'): [ord('*'), QtCore.Qt.Key.Key_Asterisk],
    QtCore.Qt.Key.Key_Asterisk: [ord('*'), QtCore.Qt.Key.Key_Asterisk],

    ord('.'): [ord('.'), QtCore.Qt.Key.Key_Period],
    QtCore.Qt.Key.Key_Period: [ord('.'), QtCore.Qt.Key.Key_Period],

    ord('|'): [ord('|'), QtCore.Qt.Key.Key_Bar],
    QtCore.Qt.Key.Key_Bar: [ord('|'), QtCore.Qt.Key.Key_Bar],

    ord(' '): [ord(' '), QtCore.Qt.Key.Key_Space],
    QtCore.Qt.Key.Key_Space: [ord(' '), QtCore.Qt.Key.Key_Space],

    ord('='): [ord('='), QtCore.Qt.Key.Key_Equal],
    QtCore.Qt.Key.Key_Equal: [ord('='), QtCore.Qt.Key.Key_Equal],

    QtCore.Qt.Key.Key_Home:     [QtCore.Qt.Key.Key_Home],
    QtCore.Qt.Key.Key_End:      [QtCore.Qt.Key.Key_End],
    QtCore.Qt.Key.Key_PageUp:   [QtCore.Qt.Key.Key_PageUp],
    QtCore.Qt.Key.Key_PageDown: [QtCore.Qt.Key.Key_PageDown],
    QtCore.Qt.Key.Key_Return:   [QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter],
    QtCore.Qt.Key.Key_Enter:    [QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter],
    QtCore.Qt.Key.Key_Insert:   [QtCore.Qt.Key.Key_Insert],
    QtCore.Qt.Key.Key_Tab:      [QtCore.Qt.Key.Key_Tab],
    QtCore.Qt.Key.Key_Delete:   [QtCore.Qt.Key.Key_Delete],

    ord('0'): [ord('0'), QtCore.Qt.Key.Key_0],
    ord('1'): [ord('1'), QtCore.Qt.Key.Key_1],
    ord('2'): [ord('2'), QtCore.Qt.Key.Key_2],
    ord('3'): [ord('3'), QtCore.Qt.Key.Key_3],
    ord('4'): [ord('4'), QtCore.Qt.Key.Key_4],
    ord('5'): [ord('5'), QtCore.Qt.Key.Key_5],
    ord('6'): [ord('6'), QtCore.Qt.Key.Key_6],
    ord('7'): [ord('7'), QtCore.Qt.Key.Key_7],
    ord('8'): [ord('8'), QtCore.Qt.Key.Key_8],
    ord('9'): [ord('9'), QtCore.Qt.Key.Key_9]
}


@_check_types.do
def _process_key_event(keycode: int, *keys):
    """
    Execute the process key event operation.

    :param keycode: Value for ``keycode``.
    :type keycode: int

    :param keys: Lookup keys.
    :type keys: UNKNOWN

    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    for expected_keycode in keys:
        if expected_keycode is None:
            continue

        expected_keycodes = KEY_MULTIPLES.get(
            expected_keycode,
            [expected_keycode, ord(chr(expected_keycode).upper())]
            if 32 <= expected_keycode <= 126 else
            [expected_keycode]
        )

        if keycode in expected_keycodes:
            return expected_keycode


class KeyHandler:

    @_check_types.do
    def __init__(self, canvas: "_canvas_base.CanvasBase"):
        """
        Initialise the :class:`KeyHandler` instance.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas_base.CanvasBase`
        """

        self.canvas = canvas
        self.config = canvas.config.input

        self._running_keycodes = {}
        self._key_event = threading.Event()
        self._key_queue_lock = threading.Lock()
        self._keycode_thread = threading.Thread(target=self._key_loop)
        self._keycode_thread.daemon = True
        self._keycode_thread.start()

    @_check_types.do
    def clear_keys(self) -> None:
        """
        Drop every currently-tracked held key immediately.

        Called when the canvas loses keyboard focus -- see
        ``canvas3d/canvas.py``'s ``CanvasEventFilter``.
        """

        with self._key_queue_lock:
            self._running_keycodes.clear()

    @_check_types.do
    def handle_event(self, event):
        """
        Handle the event.

        :param event: Event object.
        :type event: UNKNOWN
        """

        t = event.type()

        if event.isAutoRepeat():  # ← ignore auto-repeats
            return False

        if t == QtCore.QEvent.Type.KeyPress:
            self.on_key_down(event)
        elif t == QtCore.QEvent.Type.KeyRelease:
            self.on_key_up(event)

        return False

    @_check_types.do
    def _key_loop(self):
        """Execute the key loop operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        while not self._key_event.is_set():
            with self._key_queue_lock:
                temp_queue = [[func, items['keys'], items['factor']]
                              for func, items in self._running_keycodes.items()]

            for func, keys, factor in temp_queue:
                _keys = list(keys)
                _factor = factor
                _app.CallAfter(func, _factor, *_keys)

                if factor < self.canvas.config.keyboard_settings.max_speed_factor:
                    factor += self.canvas.config.keyboard_settings.speed_factor_increment

                    with self._key_queue_lock:
                        try:
                            self._running_keycodes[func]['factor'] = factor
                        except KeyError:
                            pass

            self._key_event.wait(0.05)

    @_debug.logfunc
    @_check_types.do
    def on_key_up(self, evt):
        """Handle the key up event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        keycode = evt.key()

        if not self._send_event(_events.EVT_GL_KEY_UP, evt):
            return

        @_check_types.do
        def remove_from_queue(func, k):
            """Remove the from queue.

            UNKNOWN details are inferred from the callable name and signature.

            :param func: Value for ``func``.
            :type func: UNKNOWN
            :param k: Value for ``k``.
            :type k: UNKNOWN
            """
            with self._key_queue_lock:
                if func in self._running_keycodes:
                    items = self._running_keycodes.pop(func)
                    keys = list(items['keys'])
                    if k in keys:
                        keys.remove(k)

                    if keys:
                        items['keys'] = set(keys)
                        self._running_keycodes[func] = items

        rot = self.config.rotate
        key = _process_key_event(keycode, rot.up_key, rot.down_key,
                                 rot.left_key, rot.right_key)
        if key is not None:
            remove_from_queue(self._process_rotate_key, key)
            return

        pan_tilt = self.config.pan_tilt
        key = _process_key_event(keycode, pan_tilt.up_key, pan_tilt.down_key,
                                 pan_tilt.left_key, pan_tilt.right_key)
        if key is not None:
            remove_from_queue(self._process_pan_tilt_key, key)
            return

        truck_pedestal = self.config.truck_pedestal
        key = _process_key_event(keycode, truck_pedestal.up_key,
                                 truck_pedestal.down_key, truck_pedestal.left_key,
                                 truck_pedestal.right_key)
        if key is not None:
            remove_from_queue(self._process_truck_pedestal_key, key)
            return

        walk = self.config.walk
        key = _process_key_event(keycode, walk.forward_key, walk.backward_key,
                                 walk.left_key, walk.right_key)
        if key is not None:
            remove_from_queue(self._process_walk_key, key)
            return

        zoom = self.config.zoom
        key = _process_key_event(keycode, zoom.in_key, zoom.out_key)

        if key is not None:
            remove_from_queue(self._process_zoom_key, key)
            return

        dolly = self.config.dolly
        key = _process_key_event(keycode, dolly.forward_key, dolly.backward_key)

        if key is not None:
            remove_from_queue(self._process_dolly_key, key)
            return

    @_check_types.do
    def _send_event(self, event_type, qt_evt) -> bool:
        """
        Execute the send event operation.

        :param event_type: Value for ``event_type``.
        :type event_type: UNKNOWN

        :param qt_evt: Value for ``qt_evt``.
        :type qt_evt: UNKNOWN

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """

        # Screen position under the cursor — Qt key events don't carry a
        # position, so we use the current cursor position mapped to the widget.

        local_pos = self.canvas.mapFromGlobal(QtGui.QCursor.pos())
        position = _point.Point(local_pos.x(), local_pos.y())
        world_position = self.canvas.camera.UnprojectPoint(position)

        event = _events.GLKeyEvent(event_type)

        mouse_event = self.canvas._mouse_handler.active_event  # NOQA

        event.SetMouseEvent(mouse_event)

        event.SetKeyCode(qt_evt.key())
        event.SetRawKeyCode(qt_evt.nativeVirtualKey())
        event.SetRawKeyFlags(qt_evt.nativeScanCode())
        # UnicodeKey: first character of text(), or 0
        text = qt_evt.text()
        event.SetUnicodeKey(ord(text[0]) if text else 0)

        mods = qt_evt.modifiers()
        event.SetAltDown(bool(mods & Qt.AltModifier))  # NOQA
        event.SetControlDown(bool(mods & Qt.ControlModifier))  # NOQA
        event.SetCmdDown(bool(mods & Qt.ControlModifier))   # NOQA
        event.SetModifiers(int(mods.value))
        event.SetMetaDown(bool(mods & Qt.MetaModifier))  # NOQA
        event.SetRawControlDown(bool(mods & Qt.ControlModifier))  # NOQA
        event.SetShiftDown(bool(mods & Qt.ShiftModifier))  # NOQA

        event.SetId(id(self.canvas))
        event.SetEventObject(self.canvas)
        event.SetPosition(position)
        event.SetWorldPosition(world_position)

        # Emit the signal on the canvas — connected handlers in mainframe.py
        # receive the event object.
        if event_type is _events.EVT_GL_KEY_DOWN:
            self.canvas.gl_key_down.emit(event)
        else:
            self.canvas.gl_key_up.emit(event)

        return event.ShouldPropagate()

    @_debug.logfunc
    @_check_types.do
    def on_key_down(self, evt):
        """Handle the key down event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        keycode = evt.key()

        if not self._send_event(_events.EVT_GL_KEY_DOWN, evt):
            return

        def add_to_queue(func, k):
            with self._key_queue_lock:
                if func not in self._running_keycodes:
                    self._running_keycodes[func] = dict(
                        keys=set(),
                        factor=self.canvas.config.keyboard_settings.start_speed_factor)

                self._running_keycodes[func]['keys'].add(k)

        rot = self.config.rotate
        key = _process_key_event(keycode, rot.up_key, rot.down_key,
                                 rot.left_key, rot.right_key)
        if key is not None:
            add_to_queue(self._process_rotate_key, key)
            return

        pan_tilt = self.config.pan_tilt
        key = _process_key_event(keycode, pan_tilt.up_key, pan_tilt.down_key,
                                 pan_tilt.left_key, pan_tilt.right_key)
        if key is not None:
            add_to_queue(self._process_pan_tilt_key, key)
            return

        truck_pedestal = self.config.truck_pedestal
        key = _process_key_event(keycode, truck_pedestal.up_key,
                                 truck_pedestal.down_key, truck_pedestal.left_key,
                                 truck_pedestal.right_key)
        if key is not None:
            add_to_queue(self._process_truck_pedestal_key, key)
            return

        walk = self.config.walk
        key = _process_key_event(keycode, walk.forward_key, walk.backward_key,
                                 walk.left_key, walk.right_key)
        if key is not None:
            add_to_queue(self._process_walk_key, key)
            return

        zoom = self.config.zoom
        key = _process_key_event(keycode, zoom.in_key, zoom.out_key)
        if key is not None:
            add_to_queue(self._process_zoom_key, key)
            return

        dolly = self.config.dolly
        key = _process_key_event(keycode, dolly.forward_key, dolly.backward_key)
        if key is not None:
            add_to_queue(self._process_dolly_key, key)
            return

        reset = self.config.reset
        key = _process_key_event(keycode, reset.key)
        if key is not None:
            self._process_reset_key(key)
            return

    @_debug.logfunc
    @_check_types.do
    def _process_rotate_key(self, factor, *keys):
        """
        Execute the process rotate key operation.

        :param factor: Value for ``factor``.
        :type factor: UNKNOWN

        :param keys: Lookup keys.
        :type keys: UNKNOWN
        """

        dx = 0.0
        dy = 0.0

        for key in keys:
            if key == self.config.rotate.up_key:
                dy += 1.0
            elif key == self.config.rotate.down_key:
                dy -= 1.0
            elif key == self.config.rotate.left_key:
                dx -= 1.0
            elif key == self.config.rotate.right_key:
                dx += 1.0

        self.canvas.Rotate(dx * factor, dy * factor)

    @_debug.logfunc
    @_check_types.do
    def _process_pan_tilt_key(self, factor, *keys):
        """
        Execute the process pan tilt key operation.

        :param factor: Value for ``factor``.
        :type factor: UNKNOWN

        :param keys: Lookup keys.
        :type keys: UNKNOWN
        """

        dx = 0.0
        dy = 0.0

        for key in keys:
            if key == self.config.pan_tilt.up_key:
                dy += 1.0
            elif key == self.config.pan_tilt.down_key:
                dy -= 1.0
            elif key == self.config.pan_tilt.left_key:
                dx -= 1.0
            elif key == self.config.pan_tilt.right_key:
                dx += 1.0

        self.canvas.PanTilt(dx * factor, dy * factor)

    @_debug.logfunc
    @_check_types.do
    def _process_truck_pedestal_key(self, factor, *keys):
        """
        Execute the process truck pedestal key operation.

        :param factor: Value for ``factor``.
        :type factor: UNKNOWN

        :param keys: Lookup keys.
        :type keys: UNKNOWN
        """

        dx = 0.0
        dy = 0.0

        for key in keys:
            if key == self.config.truck_pedestal.up_key:
                dy -= 3.0
            elif key == self.config.truck_pedestal.down_key:
                dy += 3.0
            elif key == self.config.truck_pedestal.left_key:
                dx -= 3.0
            elif key == self.config.truck_pedestal.right_key:
                dx += 3.0

        self.canvas.TruckPedestal(dx * factor, dy * factor)

    @_debug.logfunc
    @_check_types.do
    def _process_walk_key(self, factor, *keys):
        """
        Execute the process walk key operation.

        :param factor: Value for ``factor``.
        :type factor: UNKNOWN

        :param keys: Lookup keys.
        :type keys: UNKNOWN
        """

        dx = 0.0
        dy = 0.0

        for key in keys:
            if key == self.config.walk.forward_key:
                dy += 2.0
            elif key == self.config.walk.backward_key:
                dy -= 2.0
            elif key == self.config.walk.left_key:
                dx += 1.0
            elif key == self.config.walk.right_key:
                dx -= 1.0

        self.canvas.Walk(dx * factor, dy * factor)

    @_debug.logfunc
    @_check_types.do
    def _process_zoom_key(self, factor, *keys):
        """
        Execute the process zoom key operation.

        :param factor: Value for ``factor``.
        :type factor: UNKNOWN

        :param keys: Lookup keys.
        :type keys: UNKNOWN
        """

        delta = 0.0

        for key in keys:
            if key == self.config.zoom.in_key:
                delta += 1.0
            elif key == self.config.zoom.out_key:
                delta -= 1.0

        self.canvas.Zoom(delta * factor, None)

    @_debug.logfunc
    @_check_types.do
    def _process_dolly_key(self, factor, *keys):
        """
        Execute the process dolly key operation.

        :param factor: Value for ``factor``.
        :type factor: UNKNOWN

        :param keys: Lookup keys.
        :type keys: UNKNOWN
        """

        delta = 0.0

        for key in keys:
            if key == self.config.dolly.forward_key:
                delta += 1.0
            elif key == self.config.dolly.backward_key:
                delta -= 1.0

        self.canvas.Dolly(delta * factor)

    @_debug.logfunc
    @_check_types.do
    def _process_reset_key(self, *_):
        """
        Execute the process reset key operation.
        """

        self.canvas.camera.Reset()
