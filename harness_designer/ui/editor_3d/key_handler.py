import wx
import threading

from . import canvas as _canvas
from . import config as _config
from . import debug as _debug

Config = _config.Config


KEY_MULTIPLES = {
    wx.WXK_UP: [wx.WXK_UP, wx.WXK_NUMPAD_UP],
    wx.WXK_NUMPAD_UP: [wx.WXK_UP, wx.WXK_NUMPAD_UP],

    wx.WXK_DOWN: [wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN],
    wx.WXK_NUMPAD_DOWN: [wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN],

    wx.WXK_LEFT: [wx.WXK_LEFT, wx.WXK_NUMPAD_LEFT],
    wx.WXK_NUMPAD_LEFT: [wx.WXK_LEFT, wx.WXK_NUMPAD_LEFT],

    wx.WXK_RIGHT: [wx.WXK_RIGHT, wx.WXK_NUMPAD_RIGHT],
    wx.WXK_NUMPAD_RIGHT: [wx.WXK_RIGHT, wx.WXK_NUMPAD_RIGHT],

    ord('-'): [ord('-'), wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT],
    wx.WXK_SUBTRACT: [ord('-'), wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT],
    wx.WXK_NUMPAD_SUBTRACT: [ord('-'), wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT],

    ord('+'): [ord('+'), wx.WXK_ADD, wx.WXK_NUMPAD_ADD],
    wx.WXK_ADD: [ord('+'), wx.WXK_ADD, wx.WXK_NUMPAD_ADD],
    wx.WXK_NUMPAD_ADD: [ord('+'), wx.WXK_ADD, wx.WXK_NUMPAD_ADD],

    ord('/'): [ord('/'), wx.WXK_DIVIDE, wx.WXK_NUMPAD_DIVIDE],
    wx.WXK_DIVIDE: [ord('/'), wx.WXK_DIVIDE, wx.WXK_NUMPAD_DIVIDE],
    wx.WXK_NUMPAD_DIVIDE: [ord('/'), wx.WXK_DIVIDE, wx.WXK_NUMPAD_DIVIDE],

    ord('*'): [ord('*'), wx.WXK_MULTIPLY, wx.WXK_NUMPAD_MULTIPLY],
    wx.WXK_MULTIPLY: [ord('*'), wx.WXK_MULTIPLY, wx.WXK_NUMPAD_MULTIPLY],
    wx.WXK_NUMPAD_MULTIPLY: [ord('*'), wx.WXK_MULTIPLY, wx.WXK_NUMPAD_MULTIPLY],

    ord('.'): [ord('.'), wx.WXK_DECIMAL, wx.WXK_NUMPAD_DECIMAL],
    wx.WXK_DECIMAL: [ord('.'), wx.WXK_DECIMAL, wx.WXK_NUMPAD_DECIMAL],
    wx.WXK_NUMPAD_DECIMAL: [ord('.'), wx.WXK_DECIMAL, wx.WXK_NUMPAD_DECIMAL],

    ord('|'): [ord('|'), wx.WXK_SEPARATOR, wx.WXK_NUMPAD_SEPARATOR],
    wx.WXK_SEPARATOR: [ord('|'), wx.WXK_SEPARATOR, wx.WXK_NUMPAD_SEPARATOR],
    wx.WXK_NUMPAD_SEPARATOR: [ord('|'), wx.WXK_SEPARATOR, wx.WXK_NUMPAD_SEPARATOR],

    ord(' '): [ord(' '), wx.WXK_SPACE, wx.WXK_NUMPAD_SPACE],
    wx.WXK_SPACE: [ord(' '), wx.WXK_SPACE, wx.WXK_NUMPAD_SPACE],
    wx.WXK_NUMPAD_SPACE: [ord(' '), wx.WXK_SPACE, wx.WXK_NUMPAD_SPACE],

    ord('='): [ord('='), wx.WXK_NUMPAD_EQUAL],
    wx.WXK_NUMPAD_EQUAL: [ord('='), wx.WXK_NUMPAD_EQUAL],

    wx.WXK_HOME: [wx.WXK_HOME, wx.WXK_NUMPAD_HOME],
    wx.WXK_NUMPAD_HOME: [wx.WXK_HOME, wx.WXK_NUMPAD_HOME],

    wx.WXK_END: [wx.WXK_END, wx.WXK_NUMPAD_END],
    wx.WXK_NUMPAD_END: [wx.WXK_END, wx.WXK_NUMPAD_END],

    wx.WXK_PAGEUP: [wx.WXK_PAGEUP, wx.WXK_NUMPAD_PAGEUP],
    wx.WXK_NUMPAD_PAGEUP: [wx.WXK_PAGEUP, wx.WXK_NUMPAD_PAGEUP],

    wx.WXK_PAGEDOWN: [wx.WXK_PAGEDOWN, wx.WXK_NUMPAD_PAGEDOWN],
    wx.WXK_NUMPAD_PAGEDOWN: [wx.WXK_PAGEDOWN, wx.WXK_NUMPAD_PAGEDOWN],

    wx.WXK_RETURN: [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER],
    wx.WXK_NUMPAD_ENTER: [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER],

    wx.WXK_INSERT: [wx.WXK_INSERT, wx.WXK_NUMPAD_INSERT],
    wx.WXK_NUMPAD_INSERT: [wx.WXK_INSERT, wx.WXK_NUMPAD_INSERT],

    wx.WXK_TAB: [wx.WXK_TAB, wx.WXK_NUMPAD_TAB],
    wx.WXK_NUMPAD_TAB: [wx.WXK_TAB, wx.WXK_NUMPAD_TAB],

    wx.WXK_DELETE: [wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE],
    wx.WXK_NUMPAD_DELETE: [wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE],

    ord('0'): [ord('0'), wx.WXK_NUMPAD0],
    wx.WXK_NUMPAD0: [ord('0'), wx.WXK_NUMPAD0],

    ord('1'): [ord('1'), wx.WXK_NUMPAD1],
    wx.WXK_NUMPAD1: [ord('1'), wx.WXK_NUMPAD1],

    ord('2'): [ord('2'), wx.WXK_NUMPAD2],
    wx.WXK_NUMPAD2: [ord('2'), wx.WXK_NUMPAD2],

    ord('3'): [ord('3'), wx.WXK_NUMPAD3],
    wx.WXK_NUMPAD3: [ord('3'), wx.WXK_NUMPAD3],

    ord('4'): [ord('4'), wx.WXK_NUMPAD4],
    wx.WXK_NUMPAD4: [ord('4'), wx.WXK_NUMPAD4],

    ord('5'): [ord('5'), wx.WXK_NUMPAD5],
    wx.WXK_NUMPAD5: [ord('5'), wx.WXK_NUMPAD5],

    ord('6'): [ord('6'), wx.WXK_NUMPAD6],
    wx.WXK_NUMPAD6: [ord('6'), wx.WXK_NUMPAD6],

    ord('7'): [ord('7'), wx.WXK_NUMPAD7],
    wx.WXK_NUMPAD7: [ord('7'), wx.WXK_NUMPAD7],

    ord('8'): [ord('8'), wx.WXK_NUMPAD8],
    wx.WXK_NUMPAD8: [ord('8'), wx.WXK_NUMPAD8],

    ord('9'): [ord('9'), wx.WXK_NUMPAD9],
    wx.WXK_NUMPAD9: [ord('9'), wx.WXK_NUMPAD9],
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

        canvas.Bind(wx.EVT_KEY_UP, self._on_key_up)
        canvas.Bind(wx.EVT_KEY_DOWN, self._on_key_down)

        self._running_keycodes = {}
        self._key_event = threading.Event()
        self._key_queue_lock = threading.Lock()
        self._keycode_thread = threading.Thread(target=self._key_loop)
        self._keycode_thread.daemon = True
        self._keycode_thread.start()

    def _key_loop(self):

        while not self._key_event.is_set():
            with self._key_queue_lock:
                temp_queue = [[func, items['keys'], items['factor']]
                              for func, items in self._running_keycodes.items()]

            for func, keys, factor in temp_queue:
                wx.CallAfter(func, factor, *list(keys))

                if factor < Config.keyboard_settings.max_speed_factor:
                    factor += Config.keyboard_settings.speed_factor_increment

                    with self._key_queue_lock:
                        self._running_keycodes[func]['factor'] = factor

            self._key_event.wait(0.05)

    @_debug.logfunc
    def _on_key_up(self, evt: wx.KeyEvent):
        keycode = evt.GetKeyCode()
        evt.Skip()

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

    @_debug.logfunc
    def _on_key_down(self, evt: wx.KeyEvent):
        keycode = evt.GetKeyCode()
        evt.Skip()

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

    @_debug.logfunc
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

    @_debug.logfunc
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

    @_debug.logfunc
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

    @_debug.logfunc
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

    @_debug.logfunc
    def _process_zoom_key(self, factor, *keys):
        delta = 0.0

        for key in keys:
            if key == Config.zoom.in_key:
                delta += 1.0
            elif key == Config.zoom.out_key:
                delta -= 1.0

        self.canvas.Zoom(delta * factor, None)

    @_debug.logfunc
    def _process_reset_key(self, *_):
        self.canvas.camera.Reset()
