from typing import TYPE_CHECKING

import threading
import wx

from wx import glcanvas

# from ...wrappers.wxkey_event import KeyEvent
# from ...wrappers.wxmouse_event import MouseEvent
# from ...wrappers.wxartist_event import (ArtistEvent,
#                                         wxEVT_COMMAND_ARTIST_SET_SELECTED,
#                                         wxEVT_COMMAND_ARTIST_UNSET_SELECTED)
from ...wrappers.decimal import Decimal as _decimal
from ...geometry import point as _point

from . import CanvasBase


if TYPE_CHECKING:
    from .. import Editor3D as _Editor3D
    from ..renderers import RendererBase as _RendererBase


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


class GLCanvas(glcanvas.GLCanvas, CanvasBase):

    def __init__(self, parent: "_Editor3D", renderer: "_RendererBase"):
        CanvasBase.__init__(self, parent, renderer)
        glcanvas.GLCanvas.__init__(self, parent, wx.ID_ANY)
        self.update_objects = True

        self.init = False
        self.context = glcanvas.GLContext(self)

        self.viewMatrix = None
        self.size = None

        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_DCLICK, self.on_left_dclick)

        self.Bind(wx.EVT_MIDDLE_UP, self.on_middle_up)
        self.Bind(wx.EVT_MIDDLE_DOWN, self.on_middle_down)
        self.Bind(wx.EVT_MIDDLE_DCLICK, self.on_middle_dclick)

        self.Bind(wx.EVT_RIGHT_UP, self.on_right_up)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_RIGHT_DCLICK, self.on_right_dclick)

        self.Bind(wx.EVT_MOUSE_AUX1_UP, self.on_aux1_up)
        self.Bind(wx.EVT_MOUSE_AUX1_DOWN, self.on_aux1_down)
        self.Bind(wx.EVT_MOUSE_AUX1_DCLICK, self.on_aux1_dclick)

        self.Bind(wx.EVT_MOUSE_AUX2_UP, self.on_aux2_up)
        self.Bind(wx.EVT_MOUSE_AUX2_DOWN, self.on_aux2_down)
        self.Bind(wx.EVT_MOUSE_AUX2_DCLICK, self.on_aux2_dclick)

        self.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.Bind(wx.EVT_MOTION, self.on_mouse_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)

        self._running_keycodes = {}
        self._key_event = threading.Event()
        self._key_queue_lock = threading.Lock()
        self._keycode_thread = threading.Thread(target=self._key_loop)
        self._keycode_thread.daemon = True
        self._keycode_thread.start()

        # camera positioning

        #             y+ (up)
        #             |  Z- (forward)
        #             | /
        # x- ------ center ------ x+ (right)
        #           / |
        #         Z+  |
        #             Y-

        # f = np.linalg.norm(camera_pos - camera_eye);
        # temp_up = np.array([0.0, 1.0, 0.0], dtypes=np.dtypes.Float64DType)
        # r = np.linalg.norm(np.cross(temp_up, f))
        # u = np.linalg.norm(np.cross(f, r))
        # t_x = np.dot(positionOfCamera, r)
        # t_y = np.dot(positionOfCamera, u)
        # t_z = np.dot(positionOfCamera, f)
        #
        # lookat_matrix = np.array([[r[0], r[1], r[2], t_x],
        #                           [u[0], u[1], u[2], t_y],
        #                           [f[0], f[1], f[2], t_z],
        #                           [0.0,   0.0,  0.0, 1.0]],
        #                          dtype=np.dtypes.Float64DType)
        #
        # view_matrix = np.array([[r[0], u[0], f[0], 0.0],
        #                         [r[1], u[1], f[1], 0.0],
        #                         [r[2], u[2], f[2], 0.0],
        #                         [-t_x, -t_y, -t_z, 1.0]],
        #                        dtype=np.dtypes.Float64DType)

        self.selected = None
        self.wires = []

        self._grid = None
        self.is_motion = False
        self.mouse_pos = None

    def _key_loop(self):
        from .. import Config

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

    def on_key_up(self, evt: wx.KeyEvent):
        from .. import Config

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
        key = self._process_key_event(keycode, rot.up_key, rot.down_key,
                                      rot.left_key, rot.right_key)
        if key is not None:
            remove_from_queue(self._process_rotate_key, key)
            return

        look = Config.look
        key = self._process_key_event(keycode, look.up_key, look.down_key,
                                      look.left_key, look.right_key)
        if key is not None:
            remove_from_queue(self._process_look_key, key)
            return

        pan = Config.pan
        key = self._process_key_event(keycode, pan.up_key, pan.down_key,
                                      pan.left_key, pan.right_key)
        if key is not None:
            remove_from_queue(self._process_pan_key, key)
            return

        walk = Config.walk
        key = self._process_key_event(keycode, walk.forward_key, walk.backward_key,
                                      walk.left_key, walk.right_key)
        if key is not None:
            remove_from_queue(self._process_walk_key, key)
            return

        zoom = Config.zoom
        key = self._process_key_event(keycode, zoom.in_key, zoom.out_key)
        if key is not None:
            remove_from_queue(self._process_zoom_key, key)
            return

    def on_key_down(self, evt: wx.KeyEvent):
        from .. import Config

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
        key = self._process_key_event(keycode, rot.up_key, rot.down_key,
                                      rot.left_key, rot.right_key)
        if key is not None:
            add_to_queue(self._process_rotate_key, key)
            return

        look = Config.look
        key = self._process_key_event(keycode, look.up_key, look.down_key,
                                      look.left_key, look.right_key)
        if key is not None:
            add_to_queue(self._process_look_key, key)
            return

        pan = Config.pan
        key = self._process_key_event(keycode, pan.up_key, pan.down_key,
                                      pan.left_key, pan.right_key)
        if key is not None:
            add_to_queue(self._process_pan_key, key)
            return

        walk = Config.walk
        key = self._process_key_event(keycode, walk.forward_key, walk.backward_key,
                                      walk.left_key, walk.right_key)
        if key is not None:
            add_to_queue(self._process_walk_key, key)
            return

        zoom = Config.zoom
        key = self._process_key_event(keycode, zoom.in_key, zoom.out_key)
        if key is not None:
            add_to_queue(self._process_zoom_key, key)
            return

        key = self._process_key_event(keycode, Config.reset.key)
        if key is not None:
            self._process_reset_key(key)
            return

    def _process_rotate_key(self, factor, *keys):
        from .. import Config

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

        self.renderer.rotate(_decimal(dx) * _decimal(factor),
                             _decimal(dy) * _decimal(factor))

    def _process_look_key(self, factor, *keys):
        from .. import Config

        dx = 0.0
        dy = 0.0

        for key in keys:
            if key == Config.look.up_key:
                dy += 1.0
            elif key == Config.look.down_key:
                dy -= 1.0
            elif key == Config.look.left_key:
                dx -= 1.0
            elif key == Config.look.right_key:
                dx += 1.0

        self.renderer.look(_decimal(dx) * _decimal(factor),
                           _decimal(dy) * _decimal(factor))

    def _process_pan_key(self, factor, *keys):
        from .. import Config

        dx = 0.0
        dy = 0.0

        for key in keys:
            if key == Config.pan.up_key:
                dy -= 3.0
            elif key == Config.pan.down_key:
                dy += 3.0
            elif key == Config.pan.left_key:
                dx -= 3.0
            elif key == Config.pan.right_key:
                dx += 3.0

        self.renderer.pan(_decimal(dx) * _decimal(factor),
                          _decimal(dy) * _decimal(factor))

    def _process_walk_key(self, factor, *keys):
        from .. import Config

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

        self.renderer.walk(_decimal(dx) * _decimal(factor),
                           _decimal(dy) * _decimal(factor))

    def _process_zoom_key(self, factor, *keys):
        from .. import Config

        delta = 0.0

        for key in keys:
            if key == Config.zoom.in_key:
                delta += 1.0
            elif key == Config.zoom.out_key:
                delta -= 1.0

        self.renderer.zoom(_decimal(delta) * _decimal(factor))

    def _process_reset_key(self, *_):
        self.renderer.reset_camera()

    def _process_mouse(self, code):
        from .. import Config

        for config, func in (
            (Config.walk, self.renderer.walk),
            (Config.pan, self.renderer.pan),
            (Config.reset, self.renderer.reset_camera),
            (Config.rotate, self.renderer.rotate),
            (Config.look, self.renderer.look),
            (Config.zoom, self.renderer.zoom)
        ):
            if config.mouse is None:
                continue

            if config.mouse == code:
                return func

        def _do_nothing_func(_, __):
            pass

        return _do_nothing_func

    def on_left_up(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)

        if not self.is_motion:
            x, y = evt.GetPosition()
            p = self.get_world_coords(x, y)

            for wire in self.wires:
                if wire.hit_test(p):
                    if self.selected is not None and wire != self.selected:
                        self.selected.popup.Destroy()
                        self.selected.popup = None
                        self.selected.is_selected = False

                    self.selected = wire
                    wire.is_selected = True
                    w, h = self.GetSize()

                    wire.popup_window(w, h)

                    self.Refresh(False)
                    break
            else:
                if self.selected is not None:
                    self.selected.popup.Destroy()
                    self.selected.popup = None
                    self.selected.is_selected = False
                    self.selected = None
                    self.Refresh(False)

        if not evt.RightIsDown():
            if self.HasCapture():
                self.ReleaseMouse()
            self.mouse_pos = None

        self.is_motion = False

        evt.Skip()

    def on_left_down(self, evt: wx.MouseEvent):
        self.is_motion = False

        if not self.HasCapture():
            self.CaptureMouse()

        x, y = evt.GetPosition()
        self.mouse_pos = [x, y]

        evt.Skip()

    def on_left_dclick(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)
        evt.Skip()

    def on_middle_up(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)

        evt.Skip()

    def on_middle_down(self, evt: wx.MouseEvent):
        self.is_motion = False

        if not self.HasCapture():
            self.CaptureMouse()

        x, y = evt.GetPosition()
        self.mouse_pos = [x, y]

        evt.Skip()

    def on_middle_dclick(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)
        evt.Skip()

    def on_right_up(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)
        evt.Skip()

    def on_right_down(self, evt: wx.MouseEvent):
        self.is_motion = False

        if not self.HasCapture():
            self.CaptureMouse()

        x, y = evt.GetPosition()
        self.mouse_pos = [x, y]

        evt.Skip()

    def on_right_dclick(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)
        evt.Skip()

    def on_mouse_wheel(self, evt: wx.MouseEvent):
        if evt.GetWheelRotation() > 0:
            self.zoom(_decimal(1.0))
        else:
            self.zoom(-_decimal(1.0))

        self.Refresh(False)
        evt.Skip()

    def on_mouse_motion(self, evt: wx.MouseEvent):
        from .. import (
            MOUSE_LEFT, MOUSE_MIDDLE, MOUSE_RIGHT,
            MOUSE_AUX1, MOUSE_WHEEL, MOUSE_AUX2
        )

        if self.HasCapture():
            x, y = evt.GetPosition()
            last_x, last_y = self.mouse_pos
            dx = _decimal(x - last_x)
            dy = _decimal(y - last_y)
            self.mouse_pos = [x, y]

            if evt.LeftIsDown():
                self.is_motion = True
                self._process_mouse(MOUSE_LEFT)(-dx, -dy)
            if evt.MiddleIsDown():
                self.is_motion = True
                self._process_mouse(MOUSE_MIDDLE)(dx, dy)
            if evt.RightIsDown():
                self.is_motion = True
                self._process_mouse(MOUSE_RIGHT)(-dx, -dy)
            if evt.Aux1IsDown():
                self.is_motion = True
                self._process_mouse(MOUSE_AUX1)(dx, dy)
            if evt.Aux2IsDown():
                self.is_motion = True
                self._process_mouse(MOUSE_AUX2)(dx, dy)

        evt.Skip()

    def _process_mouse_release(self, evt: wx.MouseEvent):
        if True not in (
            evt.LeftIsDown(),
            evt.MiddleIsDown(),
            evt.RightIsDown(),
            evt.Aux1IsDown(),
            evt.Aux2IsDown()
        ):
            if self.HasCapture():
                self.ReleaseMouse()

    def on_aux1_up(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)
        evt.Skip()

    def on_aux1_down(self, evt: wx.MouseEvent):
        self.is_motion = False

        if not self.HasCapture():
            self.CaptureMouse()

        x, y = evt.GetPosition()
        self.mouse_pos = [x, y]

        evt.Skip()

    def on_aux1_dclick(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)
        evt.Skip()

    def on_aux2_up(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)
        evt.Skip()

    def on_aux2_down(self, evt: wx.MouseEvent):
        self.is_motion = False

        if not self.HasCapture():
            self.CaptureMouse()

        x, y = evt.GetPosition()
        self.mouse_pos = [x, y]

        evt.Skip()

    def on_aux2_dclick(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)
        evt.Skip()

    def get_world_coords(self, mx, my) -> _point.Point:
        self.SetCurrent(self.context)
        return self.renderer.get_world_coords(mx, my)

    def on_erase_background(self, _):
        pass

    def on_size(self, event):
        if self.selected is not None:
            w, h = event.GetSize()
            w_h = self.selected.popup.GetBestHeight(w)
            y = h - w_h
            self.selected.popup.SetPosition((0, y))

        wx.CallAfter(self.DoSetViewport)
        event.Skip()

    def DoSetViewport(self):
        width, height = self.size = self.GetClientSize() * self.GetContentScaleFactor()
        self.SetCurrent(self.context)
        self.renderer.set_viewport(width, height)

    def on_paint(self, _):
        _ = wx.PaintDC(self)
        self.SetCurrent(self.context)

        if not self.init:
            w, h = self.GetSize()
            self.renderer.init(w, h)
            self.init = True

        with self.renderer.draw() as draw:
            for obj in self.editor3d.objects:
                obj.draw(self.renderer)

            # draw.grid()

        self.SwapBuffers()
