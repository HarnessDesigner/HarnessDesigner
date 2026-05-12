# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import threading

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent

from . import Preview as _Preview
from ... import config as _config

Config = _config.Config

# Map wx WXK_* equivalents to Qt.Key_* constants.
# Keys that had numpad variants collapse to canonical Qt keys;
# Qt handles numlock transparently.
KEY_MULTIPLES = {
    Qt.Key.Key_Up:       [Qt.Key.Key_Up],
    Qt.Key.Key_Down:     [Qt.Key.Key_Down],
    Qt.Key.Key_Left:     [Qt.Key.Key_Left],
    Qt.Key.Key_Right:    [Qt.Key.Key_Right],

    Qt.Key.Key_Minus:    [Qt.Key.Key_Minus],
    Qt.Key.Key_Plus:     [Qt.Key.Key_Plus],
    Qt.Key.Key_Slash:    [Qt.Key.Key_Slash],
    Qt.Key.Key_Asterisk: [Qt.Key.Key_Asterisk],
    Qt.Key.Key_Period:   [Qt.Key.Key_Period],
    Qt.Key.Key_Bar:      [Qt.Key.Key_Bar],
    Qt.Key.Key_Space:    [Qt.Key.Key_Space],
    Qt.Key.Key_Equal:    [Qt.Key.Key_Equal],
    Qt.Key.Key_Home:     [Qt.Key.Key_Home],
    Qt.Key.Key_End:      [Qt.Key.Key_End],
    Qt.Key.Key_PageUp:   [Qt.Key.Key_PageUp],
    Qt.Key.Key_PageDown: [Qt.Key.Key_PageDown],
    Qt.Key.Key_Return:   [Qt.Key.Key_Return, Qt.Key.Key_Enter],
    Qt.Key.Key_Enter:    [Qt.Key.Key_Return, Qt.Key.Key_Enter],
    Qt.Key.Key_Insert:   [Qt.Key.Key_Insert],
    Qt.Key.Key_Tab:      [Qt.Key.Key_Tab],
    Qt.Key.Key_Delete:   [Qt.Key.Key_Delete],
    **{Qt.Key(ord(str(i))): [Qt.Key(ord(str(i)))] for i in range(10)},
}


def _process_key_event(keycode, *keys):
    for expected_keycode in keys:
        if expected_keycode is None:
            continue

        expected_keycodes = KEY_MULTIPLES.get(expected_keycode, [expected_keycode])
        if keycode in expected_keycodes:
            return expected_keycode


class KeyHandler:

    def __init__(self, canvas: "_Preview"):
        self.canvas = canvas

        # Install self as event filter on canvas to intercept key events
        canvas.installEventFilter(self)

        self._running_keycodes = {}
        self._key_event = threading.Event()
        self._key_queue_lock = threading.Lock()
        self._keycode_thread = threading.Thread(target=self._key_loop)
        self._keycode_thread.daemon = True
        self._keycode_thread.start()

    def eventFilter(self, obj, event):
        if obj is self.canvas:
            if isinstance(event, QKeyEvent):
                if event.type() == QKeyEvent.Type.KeyPress:
                    self._on_key_down(event)
                elif event.type() == QKeyEvent.Type.KeyRelease:
                    self._on_key_up(event)
        return False  # don't consume

    def _key_loop(self):
        while not self._key_event.is_set():
            with self._key_queue_lock:
                temp_queue = [[func, items['keys'], items['factor']]
                              for func, items in self._running_keycodes.items()]

            for func, keys, factor in temp_queue:
                QTimer.singleShot(0, lambda f=func, fc=factor, ks=keys: f(fc, *list(ks)))

                if factor < Config.keyboard_settings.max_speed_factor:
                    factor += Config.keyboard_settings.speed_factor_increment

                    with self._key_queue_lock:
                        self._running_keycodes[func]['factor'] = factor

            self._key_event.wait(0.05)

    def _on_key_up(self, evt: QKeyEvent):
        keycode = Qt.Key(evt.key())

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

        rot = Config.rotate
        key = _process_key_event(keycode, rot.up_key, rot.down_key,
                                 rot.left_key, rot.right_key)
        if key is not None:
            remove_from_queue(self._process_rotate_key, key)
            return

        pan_tilt = Config.pan_tilt
        key = _process_key_event(keycode, pan_tilt.up_key, pan_tilt.down_key,
                                 pan_tilt.left_key, pan_tilt.right_key)
        if key is not None:
            remove_from_queue(self._process_pan_tilt_key, key)
            return

        truck_pedestal = Config.truck_pedestal
        key = _process_key_event(keycode, truck_pedestal.up_key,
                                 truck_pedestal.down_key, truck_pedestal.left_key,
                                 truck_pedestal.right_key)
        if key is not None:
            remove_from_queue(self._process_truck_pedestal_key, key)
            return

        walk = Config.walk
        key = _process_key_event(keycode, walk.forward_key, walk.backward_key,
                                 walk.left_key, walk.right_key)
        if key is not None:
            remove_from_queue(self._process_walk_key, key)
            return

        zoom = Config.zoom
        key = _process_key_event(keycode, zoom.in_key, zoom.out_key)
        if key is not None:
            remove_from_queue(self._process_zoom_key, key)
            return

    def _on_key_down(self, evt: QKeyEvent):
        keycode = Qt.Key(evt.key())

        def add_to_queue(func, k):
            with self._key_queue_lock:
                if func not in self._running_keycodes:
                    self._running_keycodes[func] = dict(
                        keys=set(),
                        factor=Config.keyboard_settings.start_speed_factor)
                self._running_keycodes[func]['keys'].add(k)

        rot = Config.rotate
        key = _process_key_event(keycode, rot.up_key, rot.down_key,
                                 rot.left_key, rot.right_key)
        if key is not None:
            add_to_queue(self._process_rotate_key, key)
            return

        pan_tilt = Config.pan_tilt
        key = _process_key_event(keycode, pan_tilt.up_key, pan_tilt.down_key,
                                 pan_tilt.left_key, pan_tilt.right_key)
        if key is not None:
            add_to_queue(self._process_pan_tilt_key, key)
            return

        truck_pedestal = Config.truck_pedestal
        key = _process_key_event(keycode, truck_pedestal.up_key,
                                 truck_pedestal.down_key, truck_pedestal.left_key,
                                 truck_pedestal.right_key)
        if key is not None:
            add_to_queue(self._process_truck_pedestal_key, key)
            return

        walk = Config.walk
        key = _process_key_event(keycode, walk.forward_key, walk.backward_key,
                                 walk.left_key, walk.right_key)
        if key is not None:
            add_to_queue(self._process_walk_key, key)
            return

        zoom = Config.zoom
        key = _process_key_event(keycode, zoom.in_key, zoom.out_key)
        if key is not None:
            add_to_queue(self._process_zoom_key, key)
            return

        key = _process_key_event(keycode, Config.reset.key)
        if key is not None:
            self._process_reset_key(key)
            return

    def _process_rotate_key(self, factor, *keys):
        dx = 0.0
        dy = 0.0
        for key in keys:
            if key == Config.rotate.up_key:
                dy += 1.0
            elif key == Config.rotate.down_key:
                dy -= 1.0
            elif key == Config.rotate.left_key:
                dx -= 1.0
            elif key == Config.rotate.right_key:
                dx += 1.0
        self.canvas.Rotate(dx * factor, dy * factor)

    def _process_pan_tilt_key(self, factor, *keys):
        dx = 0.0
        dy = 0.0
        for key in keys:
            if key == Config.pan_tilt.up_key:
                dy += 1.0
            elif key == Config.pan_tilt.down_key:
                dy -= 1.0
            elif key == Config.pan_tilt.left_key:
                dx -= 1.0
            elif key == Config.pan_tilt.right_key:
                dx += 1.0
        self.canvas.PanTilt(dx * factor, dy * factor)

    def _process_truck_pedestal_key(self, factor, *keys):
        dx = 0.0
        dy = 0.0
        for key in keys:
            if key == Config.truck_pedestal.up_key:
                dy -= 3.0
            elif key == Config.truck_pedestal.down_key:
                dy += 3.0
            elif key == Config.truck_pedestal.left_key:
                dx -= 3.0
            elif key == Config.truck_pedestal.right_key:
                dx += 3.0
        self.canvas.TruckPedestal(dx * factor, dy * factor)

    def _process_walk_key(self, factor, *keys):
        dx = 0.0
        dy = 0.0
        for key in keys:
            if key == Config.walk.forward_key:
                dy += 2.0
            elif key == Config.walk.backward_key:
                dy -= 2.0
            elif key == Config.walk.left_key:
                dx += 1.0
            elif key == Config.walk.right_key:
                dx -= 1.0
        self.canvas.Walk(dx * factor, dy * factor)

    def _process_zoom_key(self, factor, *keys):
        delta = 0.0
        for key in keys:
            if key == Config.zoom.in_key:
                delta += 1.0
            elif key == Config.zoom.out_key:
                delta -= 1.0
        self.canvas.Zoom(delta * factor, None)

    def _process_reset_key(self, *_):
        self.canvas.camera.Reset()
