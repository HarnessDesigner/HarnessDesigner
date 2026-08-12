# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Keyboard pan/zoom/reset handling, shared by every 2D-plane editor
(schematic, peg board).

Unlike gl.canvas3d.key_handler.KeyHandler (rotate/pan-tilt/truck-pedestal/
walk -- real 3D camera navigation concepts), a 2D orthographic top-down
view only ever needs pan + zoom + reset -- exactly what
gl.canvas2d.mouse_handler.MouseHandler's own _process_mouse already
exposes via Canvas.Pan/Canvas.Zoom/camera.Reset. Both
``Config.editor2d`` and ``Config.editor_pegboard`` define the same
``pan``/``zoom``/``reset`` binding shape, so one handler class -- wired
only to ``self.canvas.config.pan``/``.zoom``/``.reset`` -- covers both
editors: unlike ``MouseHandler``, there is no per-editor subclass here at
all, and ``gl.canvas2d.canvas.Canvas.__init__`` instantiates this class
directly.

There is no ``keyboard_settings`` section on either editor's config
(unlike ``Config.editor3d.keyboard_settings``), so held-key repeat here
uses a fixed per-tick step instead of the 3D camera's accelerating-factor
ramp -- see ``_PAN_KEY_STEP``/``_ZOOM_KEY_STEP`` below.
"""

import threading

from PySide6.QtCore import Qt, QEvent, QObject

from . import canvas as _canvas
from ... import app as _app
from ... import debug as _debug
from ... import check_types as _check_types


# Same Qt-keyed equivalence table as canvas3d/key_handler.py.
# Kept in sync manually; extract to a shared module if a third handler
# needs it.

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

# Fixed per-repeat-tick step sizes (no acceleration ramp -- there is no
# Config.editor2d/editor_pegboard.keyboard_settings section to drive one
# from).

# screen pixels per tick, fed through Canvas.Pan()
# (which applies config.pan.sensitivity itself)
_PAN_KEY_STEP = 8.0

# distance units per tick, fed through Canvas.Zoom()
# (which applies config.zoom.sensitivity itself)
_ZOOM_KEY_STEP = 20.0

# seconds between repeat ticks while held
_KEY_REPEAT_INTERVAL = 0.05


@_check_types.do
def _process_key_event(keycode: int, *keys):
    """Return the canonical key from ``keys`` that matches ``keycode``.

    :param keycode: Value for ``keycode``.
    :type keycode: int
    :param keys: Candidate binding keycodes to check against.
    :type keys: UNKNOWN
    :returns: The matching canonical keycode, or ``None``.
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


class KeyHandler(QObject):
    """Keyboard pan/zoom/reset handler, shared by every 2D-plane editor.

    Inherits ``QObject`` -- ``installEventFilter()`` requires its argument
    to be one, and this is registered on *canvas* directly (unlike
    ``gl.canvas3d.canvas.Canvas``, which routes both its mouse and key
    handlers through one shared ``CanvasEventFilter`` QObject instead --
    not needed here since this class already is one itself, same as
    ``gl.canvas2d.mouse_handler.MouseHandler``).
    """

    canvas: "_canvas.Canvas" = None

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas"):
        """Initialise the :class:`KeyHandler` instance.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas`
        """
        super().__init__()
        self.canvas = canvas

        canvas.installEventFilter(self)

        self._running_keycodes = {}
        self._key_event = threading.Event()
        self._key_queue_lock = threading.Lock()
        self._keycode_thread = threading.Thread(target=self._key_loop)
        self._keycode_thread.daemon = True
        self._keycode_thread.start()

    @_check_types.do
    def eventFilter(self, obj, qt_event):
        """Execute the event filter operation.

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
            if qt_event.type() == QEvent.Type.FocusOut:
                # The canvas loses keyboard focus while a movement key is
                # held (a context menu/dialog opens, another dock gets
                # clicked, etc.) -- the KeyRelease that would normally
                # clear that key goes to whichever widget has focus now,
                # never to this filter, so without this the key stays
                # "down" forever and the camera keeps moving on its own
                # after it's released.
                self.clear_keys()
                return False
        return False

    @_check_types.do
    def clear_keys(self) -> None:
        """Drop every currently-tracked held key immediately."""
        with self._key_queue_lock:
            self._running_keycodes.clear()

    @_check_types.do
    def _key_loop(self):
        """Background thread: re-fire held-key actions every repeat tick.

        Dispatches back onto the Qt main thread via ``_app.CallAfter`` (a
        real cross-thread Qt signal emission), not ``QTimer.singleShot``
        -- a singleShot timer only fires if the thread that *created* it
        is pumping a Qt event loop, which this plain
        ``threading.Thread`` never is.
        """
        while not self._key_event.is_set():
            with self._key_queue_lock:
                temp_queue = [[func, items['keys']]
                              for func, items in self._running_keycodes.items()]

            for func, keys in temp_queue:
                _keys = list(keys)
                _app.CallAfter(func, *_keys)

            self._key_event.wait(_KEY_REPEAT_INTERVAL)

    @_debug.logfunc
    @_check_types.do
    def _on_key_up(self, evt):
        """Handle the key up event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        keycode = evt.key()

        @_check_types.do
        def remove_from_queue(func, k):
            """Remove ``k`` from ``func``'s held-key set.

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

        pan = self.canvas.config.pan
        key = _process_key_event(keycode, pan.up_key, pan.down_key,
                                 pan.left_key, pan.right_key)
        if key is not None:
            remove_from_queue(self._process_pan_key, key)
            return

        zoom = self.canvas.config.zoom
        key = _process_key_event(keycode, zoom.in_key, zoom.out_key)
        if key is not None:
            remove_from_queue(self._process_zoom_key, key)
            return

    @_debug.logfunc
    @_check_types.do
    def _on_key_down(self, evt):
        """Handle the key down event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        keycode = evt.key()

        @_check_types.do
        def add_to_queue(func, k):
            """Add ``k`` to ``func``'s held-key set.

            :param func: Value for ``func``.
            :type func: UNKNOWN
            :param k: Value for ``k``.
            :type k: UNKNOWN
            """
            with self._key_queue_lock:
                if func not in self._running_keycodes:
                    self._running_keycodes[func] = dict(keys=set())

                self._running_keycodes[func]['keys'].add(k)

        pan = self.canvas.config.pan
        key = _process_key_event(keycode, pan.up_key, pan.down_key,
                                 pan.left_key, pan.right_key)
        if key is not None:
            add_to_queue(self._process_pan_key, key)
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
    @_check_types.do
    def _process_pan_key(self, *keys):
        """Execute the process pan key operation.

        :param keys: Currently-held keycodes bound to pan.
        :type keys: UNKNOWN
        """
        dx = 0.0
        dy = 0.0

        pan = self.canvas.config.pan

        for key in keys:
            if key == pan.up_key:
                dy += _PAN_KEY_STEP
            elif key == pan.down_key:
                dy -= _PAN_KEY_STEP
            elif key == pan.left_key:
                dx -= _PAN_KEY_STEP
            elif key == pan.right_key:
                dx += _PAN_KEY_STEP

        self.canvas.Pan(dx, dy)

    @_debug.logfunc
    @_check_types.do
    def _process_zoom_key(self, *keys):
        """Execute the process zoom key operation.

        :param keys: Currently-held keycodes bound to zoom.
        :type keys: UNKNOWN
        """
        delta = 0.0

        zoom = self.canvas.config.zoom

        for key in keys:
            if key == zoom.in_key:
                delta += _ZOOM_KEY_STEP
            elif key == zoom.out_key:
                delta -= _ZOOM_KEY_STEP

        self.canvas.Zoom(delta, None)

    @_debug.logfunc
    @_check_types.do
    def _process_reset_key(self, *_):
        """Execute the process reset key operation.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self.canvas.camera.Reset()
