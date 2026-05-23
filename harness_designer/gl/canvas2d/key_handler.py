# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import threading

from PySide6.QtCore import Qt, QEvent, QTimer

from . import canvas as _canvas
from ... import debug as _debug


# Same Qt-keyed equivalence table as canvas3d/key_handler.py.
# Kept in sync manually; extract to a shared module if a third handler needs it.

_Q = Qt.Key

KEY_MULTIPLES = {
    _Q.Key_Up:       [_Q.Key_Up],
    _Q.Key_Down:     [_Q.Key_Down],
    _Q.Key_Left:     [_Q.Key_Left],
    _Q.Key_Right:    [_Q.Key_Right],

    ord('-'): [ord('-'), _Q.Key_Minus],
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
    """Execute the process key event operation.

    UNKNOWN details are inferred from the callable name and signature.

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
    """Represent a key handler in :mod:`harness_designer.gl.canvas2d.key_handler`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas: "_canvas.Canvas"):
        """Initialise the :class:`KeyHandler` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas`
        """
        self.canvas = canvas

        canvas.installEventFilter(self)

        self._running_keycodes = {}
        self._key_event = threading.Event()
        self._key_queue_lock = threading.Lock()
        self._keycode_thread = threading.Thread(target=self._key_loop)
        self._keycode_thread.daemon = True
        self._keycode_thread.start()

    def eventFilter(self, obj, qt_event):
        """Execute the event filter operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        :param qt_event: Value for ``qt_event``.
        :type qt_event: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if obj is self.canvas:
            if qt_event.type() == QEvent.Type.KeyPress and not qt_event.isAutoRepeat():
                self._on_key_down(qt_event)
                return False
            if qt_event.type() == QEvent.Type.KeyRelease and not qt_event.isAutoRepeat():
                self._on_key_up(qt_event)
                return False
        return False

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
                QTimer.singleShot(0, lambda f=func, fac=_factor, k=_keys: f(fac, *k))

                if factor < self.canvas.config.keyboard_settings.max_speed_factor:
                    factor += self.canvas.config.keyboard_settings.speed_factor_increment

                    with self._key_queue_lock:
                        self._running_keycodes[func]['factor'] = factor

            self._key_event.wait(0.05)

    @_debug.logfunc
    def _on_key_up(self, evt):
        """Handle the key up event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        keycode = evt.key()

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

    @_debug.logfunc
    def _on_key_down(self, evt):
        """Handle the key down event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        keycode = evt.key()

        def add_to_queue(func, k):
            """Add a to queue.

            UNKNOWN details are inferred from the callable name and signature.

            :param func: Value for ``func``.
            :type func: UNKNOWN
            :param k: Value for ``k``.
            :type k: UNKNOWN
            """
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
        """Execute the process rotate key operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param factor: Value for ``factor``.
        :type factor: UNKNOWN
        :param keys: Lookup keys.
        :type keys: UNKNOWN
        """
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
        """Execute the process pan tilt key operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param factor: Value for ``factor``.
        :type factor: UNKNOWN
        :param keys: Lookup keys.
        :type keys: UNKNOWN
        """
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
        """Execute the process truck pedestal key operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param factor: Value for ``factor``.
        :type factor: UNKNOWN
        :param keys: Lookup keys.
        :type keys: UNKNOWN
        """
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
        """Execute the process walk key operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param factor: Value for ``factor``.
        :type factor: UNKNOWN
        :param keys: Lookup keys.
        :type keys: UNKNOWN
        """
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
        """Execute the process zoom key operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param factor: Value for ``factor``.
        :type factor: UNKNOWN
        :param keys: Lookup keys.
        :type keys: UNKNOWN
        """
        delta = 0.0

        for key in keys:
            if key == self.canvas.config.zoom.in_key:
                delta += 1.0
            elif key == self.canvas.config.zoom.out_key:
                delta -= 1.0

        self.canvas.Zoom(delta * factor, None)

    @_debug.logfunc
    def _process_reset_key(self, *_):
        """Execute the process reset key operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self.canvas.camera.Reset()
