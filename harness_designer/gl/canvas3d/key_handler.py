# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import threading

from PySide6.QtCore import Qt, QTimer

from . import canvas as _canvas
from ... import debug as _debug
from .. import events as _events
from ...geometry import point as _point


# wx key code → Qt.Key mapping for the numpad-equivalence groups.
# Keys that have direct Qt equivalents use Qt.Key values.
# Printable ASCII keys (32-126) are handled by ord() / Qt.Key_* directly.
#
# The KEY_MULTIPLES dict maps a canonical key to the set of Qt key codes
# that should all trigger the same action.  Config values stored as wx key
# codes will have been migrated to Qt.Key ints; if they are still old wx
# ints they will fall through to the ord()-range fallback in
# _process_key_event, which is fine for ASCII keys.

_Q = Qt.Key  # shorthand

KEY_MULTIPLES = {
    _Q.Key_Up:       [_Q.Key_Up, _Q.Key_Up],          # numpad up = Key_Up in Qt
    _Q.Key_Down:     [_Q.Key_Down, _Q.Key_Down],
    _Q.Key_Left:     [_Q.Key_Left, _Q.Key_Left],
    _Q.Key_Right:    [_Q.Key_Right, _Q.Key_Right],

    ord('-'): [ord('-'), _Q.Key_Minus, _Q.Key_Minus],
    _Q.Key_Minus: [ord('-'), _Q.Key_Minus],

    ord('+'): [ord('+'), _Q.Key_Plus],
    _Q.Key_Plus: [ord('+'), _Q.Key_Plus],

    ord('/'): [ord('/'), _Q.Key_Slash],
    _Q.Key_Slash: [ord('/'), _Q.Key_Slash],

    ord('*'): [ord('*'), _Q.Key_Asterisk],
    _Q.Key_Asterisk: [ord('*'), _Q.Key_Asterisk],

    ord('.'): [ord('.'), _Q.Key_Period],
    _Q.Key_Period: [ord('.'), _Q.Key_Period],

    ord('|'): [ord('|'), _Q.Key_Bar],
    _Q.Key_Bar: [ord('|'), _Q.Key_Bar],

    ord(' '): [ord(' '), _Q.Key_Space],
    _Q.Key_Space: [ord(' '), _Q.Key_Space],

    ord('='): [ord('='), _Q.Key_Equal],
    _Q.Key_Equal: [ord('='), _Q.Key_Equal],

    _Q.Key_Home:     [_Q.Key_Home],
    _Q.Key_End:      [_Q.Key_End],
    _Q.Key_PageUp:   [_Q.Key_PageUp],
    _Q.Key_PageDown: [_Q.Key_PageDown],
    _Q.Key_Return:   [_Q.Key_Return, _Q.Key_Enter],
    _Q.Key_Enter:    [_Q.Key_Return, _Q.Key_Enter],
    _Q.Key_Insert:   [_Q.Key_Insert],
    _Q.Key_Tab:      [_Q.Key_Tab],
    _Q.Key_Delete:   [_Q.Key_Delete],

    ord('0'): [ord('0'), _Q.Key_0],
    ord('1'): [ord('1'), _Q.Key_1],
    ord('2'): [ord('2'), _Q.Key_2],
    ord('3'): [ord('3'), _Q.Key_3],
    ord('4'): [ord('4'), _Q.Key_4],
    ord('5'): [ord('5'), _Q.Key_5],
    ord('6'): [ord('6'), _Q.Key_6],
    ord('7'): [ord('7'), _Q.Key_7],
    ord('8'): [ord('8'), _Q.Key_8],
    ord('9'): [ord('9'), _Q.Key_9],
}


def _process_key_event(keycode: int, *keys):
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

    def __init__(self, canvas: "_canvas.Canvas"):
        self.canvas = canvas

        # Qt: override keyPressEvent / keyReleaseEvent on the canvas instead
        # of canvas.Bind().  The canvas delegates those overrides here.
        canvas.installEventFilter(self)

        self._running_keycodes = {}
        self._key_event = threading.Event()
        self._key_queue_lock = threading.Lock()
        self._keycode_thread = threading.Thread(target=self._key_loop)
        self._keycode_thread.daemon = True
        self._keycode_thread.start()

    # Qt event filter — called by the canvas's event loop.
    def eventFilter(self, obj, qt_event):
        from PySide6.QtCore import QEvent
        if obj is self.canvas:
            if qt_event.type() == QEvent.KeyPress and not qt_event.isAutoRepeat():
                self._on_key_down(qt_event)
                return False        # let Qt continue (focus, etc.)
            if qt_event.type() == QEvent.KeyRelease and not qt_event.isAutoRepeat():
                self._on_key_up(qt_event)
                return False
        return False

    def _key_loop(self):
        while not self._key_event.is_set():
            with self._key_queue_lock:
                temp_queue = [[func, items['keys'], items['factor']]
                              for func, items in self._running_keycodes.items()]

            for func, keys, factor in temp_queue:
                # wx.CallAfter → QTimer.singleShot(0, ...) for main-thread dispatch
                _keys = list(keys)
                _factor = factor
                QTimer.singleShot(0, lambda f=func, fac=_factor, k=_keys: f(fac, *k))

                if factor < self.canvas.config.keyboard_settings.max_speed_factor:
                    factor += self.canvas.config.keyboard_settings.speed_factor_increment

                    with self._key_queue_lock:
                        self._running_keycodes[func]['factor'] = factor

            self._key_event.wait(0.05)

    @_debug.logfunc
    def _on_key_up(self, evt):
        from PySide6.QtGui import QKeyEvent
        keycode = evt.key()

        if not self._send_event(_events.EVT_GL_KEY_UP, evt):
            return

        def remove_from_queue(func, k):
            with self._key_queue_lock:
                if func in self._running_keycodes:
                    items = self._running_keycodes.pop(func)
                    keys = list(items['keys'])
                    if k in keys:
                        keys.remove(k)

                    if keys:
                        items['keys'] = set(keys)
                        self._running_keycodes[func] = items

        rot = self.canvas.config.rotate
        key = _process_key_event(keycode, rot.up_key, rot.down_key,
                                 rot.left_key, rot.right_key)
        if key is not None:
            remove_from_queue(self._process_rotate_key, key)
            return

        pan_tilt = self.canvas.config.pan_tilt
        key = _process_key_event(keycode, pan_tilt.up_key, pan_tilt.down_key,
                                 pan_tilt.left_key, pan_tilt.right_key)
        if key is not None:
            remove_from_queue(self._process_pan_tilt_key, key)
            return

        truck_pedestal = self.canvas.config.truck_pedestal
        key = _process_key_event(keycode, truck_pedestal.up_key,
                                 truck_pedestal.down_key, truck_pedestal.left_key,
                                 truck_pedestal.right_key)
        if key is not None:
            remove_from_queue(self._process_truck_pedestal_key, key)
            return

        walk = self.canvas.config.walk
        key = _process_key_event(keycode, walk.forward_key, walk.backward_key,
                                 walk.left_key, walk.right_key)
        if key is not None:
            remove_from_queue(self._process_walk_key, key)
            return

        zoom = self.canvas.config.zoom
        key = _process_key_event(keycode, zoom.in_key, zoom.out_key)
        if key is not None:
            remove_from_queue(self._process_zoom_key, key)
            return

    def _send_event(self, event_type, qt_evt) -> bool:
        from PySide6.QtCore import Qt as _Qt

        # Screen position under the cursor — Qt key events don't carry a
        # position, so we use the current cursor position mapped to the widget.
        from PySide6.QtGui import QCursor
        local_pos = self.canvas.mapFromGlobal(QCursor.pos())
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
        event.SetAltDown(bool(mods & _Qt.AltModifier))
        event.SetControlDown(bool(mods & _Qt.ControlModifier))
        event.SetCmdDown(bool(mods & _Qt.ControlModifier))   # same as Ctrl on Windows/Linux
        event.SetModifiers(int(mods))
        event.SetMetaDown(bool(mods & _Qt.MetaModifier))
        event.SetRawControlDown(bool(mods & _Qt.ControlModifier))
        event.SetShiftDown(bool(mods & _Qt.ShiftModifier))

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

        return not event.skipped()

    @_debug.logfunc
    def _on_key_down(self, evt):
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

        rot = self.canvas.config.rotate
        key = _process_key_event(keycode, rot.up_key, rot.down_key,
                                 rot.left_key, rot.right_key)
        if key is not None:
            add_to_queue(self._process_rotate_key, key)
            return

        pan_tilt = self.canvas.config.pan_tilt
        key = _process_key_event(keycode, pan_tilt.up_key, pan_tilt.down_key,
                                 pan_tilt.left_key, pan_tilt.right_key)
        if key is not None:
            add_to_queue(self._process_pan_tilt_key, key)
            return

        truck_pedestal = self.canvas.config.truck_pedestal
        key = _process_key_event(keycode, truck_pedestal.up_key,
                                 truck_pedestal.down_key, truck_pedestal.left_key,
                                 truck_pedestal.right_key)
        if key is not None:
            add_to_queue(self._process_truck_pedestal_key, key)
            return

        walk = self.canvas.config.walk
        key = _process_key_event(keycode, walk.forward_key, walk.backward_key,
                                 walk.left_key, walk.right_key)
        if key is not None:
            add_to_queue(self._process_walk_key, key)
            return

        zoom = self.canvas.config.zoom
        key = _process_key_event(keycode, zoom.in_key, zoom.out_key)
        if key is not None:
            add_to_queue(self._process_zoom_key, key)
            return

        key = _process_key_event(keycode, self.canvas.config.reset.key)
        if key is not None:
            self._process_reset_key(key)
            return

    @_debug.logfunc
    def _process_rotate_key(self, factor, *keys):
        dx = 0.0
        dy = 0.0

        for key in keys:
            if key == self.canvas.config.rotate.up_key:
                dy += 1.0
            elif key == self.canvas.config.rotate.down_key:
                dy -= 1.0
            elif key == self.canvas.config.rotate.left_key:
                dx -= 1.0
            elif key == self.canvas.config.rotate.right_key:
                dx += 1.0

        self.canvas.Rotate(dx * factor, dy * factor)

    @_debug.logfunc
    def _process_pan_tilt_key(self, factor, *keys):
        dx = 0.0
        dy = 0.0

        for key in keys:
            if key == self.canvas.config.pan_tilt.up_key:
                dy += 1.0
            elif key == self.canvas.config.pan_tilt.down_key:
                dy -= 1.0
            elif key == self.canvas.config.pan_tilt.left_key:
                dx -= 1.0
            elif key == self.canvas.config.pan_tilt.right_key:
                dx += 1.0

        self.canvas.PanTilt(dx * factor, dy * factor)

    @_debug.logfunc
    def _process_truck_pedestal_key(self, factor, *keys):
        dx = 0.0
        dy = 0.0

        for key in keys:
            if key == self.canvas.config.truck_pedestal.up_key:
                dy -= 3.0
            elif key == self.canvas.config.truck_pedestal.down_key:
                dy += 3.0
            elif key == self.canvas.config.truck_pedestal.left_key:
                dx -= 3.0
            elif key == self.canvas.config.truck_pedestal.right_key:
                dx += 3.0

        self.canvas.TruckPedestal(dx * factor, dy * factor)

    @_debug.logfunc
    def _process_walk_key(self, factor, *keys):
        dx = 0.0
        dy = 0.0

        for key in keys:
            if key == self.canvas.config.walk.forward_key:
                dy += 2.0
            elif key == self.canvas.config.walk.backward_key:
                dy -= 2.0
            elif key == self.canvas.config.walk.left_key:
                dx += 1.0
            elif key == self.canvas.config.walk.right_key:
                dx -= 1.0

        self.canvas.Walk(dx * factor, dy * factor)

    @_debug.logfunc
    def _process_zoom_key(self, factor, *keys):
        delta = 0.0

        for key in keys:
            if key == self.canvas.config.zoom.in_key:
                delta += 1.0
            elif key == self.canvas.config.zoom.out_key:
                delta -= 1.0

        self.canvas.Zoom(delta * factor, None)

    @_debug.logfunc
    def _process_reset_key(self, *_):
        self.canvas.camera.Reset()
