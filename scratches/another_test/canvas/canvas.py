
from typing import Self

import wx

import numpy as np
from wx import glcanvas
from OpenGL import GL
from OpenGL import GLU

# from . import free_rotate as _free_rotate
# from . import dragging as _dragging

try:
    from .. import debug as _debug
    from .. import helpers as _helpers

    from ..geometry import point as _point
    from ..wrappers.wrap_decimal import Decimal as _decimal
    from .. import axis_indicators as _axis_indicators

except ImportError:
    import debug as _debug  # NOQA
    import helpers as _helpers  # NOQA

    from geometry import point as _point  # NOQA
    from wrappers.wrap_decimal import Decimal as _decimal  # NOQA
    import axis_indicators as _axis_indicators  # NOQA


MOUSE_NONE = 0x00000000
MOUSE_LEFT = 0x00000001
MOUSE_MIDDLE = 0x00000002
MOUSE_RIGHT = 0x00000004
MOUSE_AUX1 = 0x00000008
MOUSE_AUX2 = 0x00000010
MOUSE_WHEEL = 0x00000020

MOUSE_REVERSE_X_AXIS = 0x80000000
MOUSE_REVERSE_Y_AXIS = 0x40000000
MOUSE_REVERSE_WHEEL_AXIS = 0x20000000
MOUSE_SWAP_AXIS = 0x10000000
# ********************* CONFIG SETTINGS *********************


class Config:

    class virtual_canvas:
        width = 0
        height = 0

    class movement:
        angle_detent = 10.0
        move_detent = 5.0

        angle_snap = -1
        move_snap = -1

    class keyboard_settings:
        max_speed_factor = 10.0
        speed_factor_increment = 0.1
        start_speed_factor = 1.0

    class rotate:
        mouse = MOUSE_MIDDLE
        up_key = ord('w')
        down_key = ord('s')
        left_key = ord('a')
        right_key = ord('d')
        sensitivity = 0.4

    class pan_tilt:
        mouse = MOUSE_LEFT
        up_key = ord('o')
        down_key = ord('l')
        left_key = ord('k')
        right_key = ord(';')
        sensitivity = 0.2

    class truck_pedistal:
        mouse = MOUSE_RIGHT
        up_key = ord('8')
        down_key = ord('2')
        left_key = ord('4')
        right_key = ord('6')
        sensitivity = 0.2
        speed = 1.0

    class walk:
        mouse = MOUSE_WHEEL | MOUSE_SWAP_AXIS
        forward_key = wx.WXK_UP
        backward_key = wx.WXK_DOWN
        left_key = wx.WXK_LEFT
        right_key = wx.WXK_RIGHT
        sensitivity = 1.0
        speed = 1.0

    class zoom:
        mouse = MOUSE_NONE  # | MOUSE_REVERSE_WHEEL_AXIS
        in_key = wx.WXK_ADD
        out_key = wx.WXK_SUBTRACT
        sensitivity = 1.0

    class reset:
        key = wx.WXK_HOME
        mouse = MOUSE_NONE


# ***********************************************************


# wires are constructed along the positive Z axis
#             y+
#             |  Z+
#             | /
# x+ ------ center ------ x-
#           / |
#         Z-  |
#             Y-

class Canvas(glcanvas.GLCanvas):

    """
    GL Engine

    This handles putting all of the pieces together and passes them
    to opengl to be rendered. It also is responsible for interperting mouse
    input as well as the view.

    The controls to move about are much like what you would have in a first
    person shooter game. If you don't knopw what that is (lord i hope this
    isn't the case) think if it as you navigating the world around you. The
    movements are very similiar in most cases. There is one movement that while
    it is able to be done in the "real" world by a person it's not normally
    done. a person that sprays paint might be the only person to use the
    movement in a regular basis. The easiest way to describe it is if you hang
    an object to be painted at about chest height and you move your position
    around the object but keeping your eyes fixed on the object at all times.

    How the rendering is done.

    The objects that are placed into the 3D world hold the coordinates of where
    they are located. This is paramount to how the system works because those
    coordinates are also used or determining part sizes like a wire length.
    There is a 1 to 1 ratop that maps to mm's from the 3D world location.

    OpenGL provides many ways to handle how to see the 3D world and how to move
    about it. I am using 1 way and only 1 way which is using the camera position
    and the camera focal point. Object positions are always static. I do not
    transform the view when placing objects so the coordinates where an onject
    is located is always going to be the same as where the object is located in
    that 3D world. moving the camera to change what is being seen is the most
    locical thing to do for a CAD type interface. The downside is when
    performing updates is that all of the objects get passed to opengl to be
    rendered even ones that are not ble to be seen. This could cause performance
    issues if there are a lot of objects being passed to OpenGL. Once I get the
    program mostly up and operational I will perform tests t see what the
    performance degridation actually is and if there would be any benifit to
    clipping objects not in view so they don't get passed to OpenGL.
    Which brings me to my next bit...

    I have created a class that holds x, y and z coordinates. This class is
    very important and it is the heart of the system. built into that class is
    the ability to attach callbacks that will get called should the x, y or z
    values change. These changes can occur anywhere in the program so no
    specific need to couple pieces together in a direct manner in order to get
    changes to populate properly. This class is what is used to store the camera
    position and the camera focal point. Any changes to either of those will
    trigger an update of what is being seen. This mechanism is what will be used
    in the future so objects are able to know when they need to check if they
    are clipped or not. I will more than likely have 2 ranges of items. ones
    that are in view and ones that would be considered as standby or are on the
    edge of the viewable area. When the position of the camera or camera focal
    point changes the objects that are on standby would beprocessed immediatly
    to see if they are in view or not and the ones that are in view would be
    processed to see if they get moved to the standby. objects that gets placed
    into and remove from standby from areas outside of it will be done in a
    separate process. It will be done this way because of the sheer number of
    possible objects that might exist which would impact the program performance
    if it is done on the same core that the UI is running on.
    """
    def __init__(self, parent, mainframe, size=wx.DefaultSize, pos=wx.DefaultPosition):
        glcanvas.GLCanvas.__init__(self, parent, -1, size=size, pos=pos)

        self.mainframe = mainframe
        self._view_offset = None

        from . import context as _context
        from . import camera as _camera

        self.init = False
        self.context = _context.GLContext(self)
        self.camera = _camera.Camera(self)

        self.size = None

        self.WIDTH = size[0]
        self.HEIGHT = size[1]
        self.ASPECT = float(self.WIDTH) / self.HEIGHT  # desired aspect ratio

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)

        self._grid = None

        self.selected = None
        self.objects = []
        self._ref_count = 0
        # self.free_rot: _free_rotate.FreeRotate = None
        self.axis: _axis_indicators.Indicators = None

        from . import key_handler as _key_handler
        from . import mouse_handler as _mouse_handler

        self._key_handler = _key_handler.KeyHandler(self)
        self._mouse_handler = _mouse_handler.MouseHandler(self)

    @classmethod
    def get_view_size(cls) -> _point.Point:
        if (
            not Config.virtual_canvas.width or
            not Config.virtual_canvas.height
        ):

            max_x = 0
            max_y = 0
            min_x = 0
            min_y = 0
            displays = (wx.Display(i) for i in range(wx.Display.GetCount()))
            for display in displays:
                geometry = display.GetGeometry()
                x, y = geometry.GetPosition()
                w, h = geometry.GetSize()
                max_x = max(x + w, max_x)
                max_y = max(y + h, max_y)
                min_x = min(x, min_x)
                min_y = min(y, min_y)

            Config.virtual_canvas.width = max_x - min_x
            Config.virtual_canvas.height = max_y - min_y

        # return _point.Point(_decimal(w), _decimal(h))
        return _point.Point(_decimal(Config.virtual_canvas.width), _decimal(Config.virtual_canvas.height))

    def add_object(self, obj):
        # we want to force a reordering of the objects
        # when adding a new one. this can be overridden if adding multiple
        # objects elsewhere in code by using the context prior to adding
        # the objects. This way when adding multiple
        # objects it will only get reordered a single time

        with self:
            self.objects.insert(0, obj)

        self.Refresh(False)

    def remove_object(self, obj):
        try:
            self.objects.remove(obj)
        except:  # NOQA
            return

        self.Refresh(False)

    def __enter__(self) -> Self:
        self._ref_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1

    def Refresh(self, *args, **kwargs):
        if self._ref_count:
            return

        glcanvas.GLCanvas.Refresh(self, *args, **kwargs)

    def truck_pedistal(self, dx: _decimal, dy: _decimal) -> None:
        if Config.truck_pedistal.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if Config.truck_pedistal.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = _decimal(Config.truck_pedistal.sensitivity)
        dx *= sens
        dy *= sens

        self.camera.truck_pedistal(dx, dy, Config.truck_pedistal.speed)

    def zoom(self, dx, _):
        dx *= _decimal(Config.zoom.sensitivity)
        self.camera.zoom(dx)

    def rotate(self, dx: _decimal, dy: _decimal) -> None:

        if Config.rotate.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if Config.rotate.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = _decimal(Config.rotate.sensitivity)
        dx *= sens
        dy *= sens

        self.camera.rotate(dx, dy)

    def walk(self, dx: _decimal, dy: _decimal) -> None:
        if dy == 0.0:
            self.pan_tilt(dx * _decimal(6.0), _decimal(0.0))
            return

        look_dx = dx

        if Config.walk.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if Config.walk.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = _decimal(Config.walk.sensitivity)
        dx *= sens
        dy *= sens

        self.camera.walk(dx, dy, Config.walk.speed)
        self.pan_tilt(look_dx * _decimal(2.0), _decimal(0.0))

    def pan_tilt(self, dx: _decimal, dy: _decimal) -> None:
        if Config.pan_tilt.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if Config.pan_tilt.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = _decimal(Config.pan_tilt.sensitivity)

        dx *= sens
        dy *= sens
        self.camera.pan_tilt(dx, dy)

    def on_erase_background(self, _):
        pass

    def on_size(self, event):
        wx.CallAfter(self.DoSetViewport, event.GetSize())
        event.Skip()

    def DoSetViewport(self, size):
        width, height = self.size = size * self.GetContentScaleFactor()
        with self.context:
            GL.glViewport(0, 0, width, height)

    def on_paint(self, _):
        _ = wx.PaintDC(self)

        with self.context:
            if not self.init:
                self.InitGL()
                self.init = True

            self.OnDraw()

    @staticmethod
    def _normalize(v: np.ndarray) -> np.ndarray:
        n = np.linalg.norm(v)
        return v if n == 0.0 else v / n

    def InitGL(self):
        GL.glClearColor(0.20, 0.20, 0.20, 0.0)
        # GL.glViewport(0, 0, w, h)

        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_LIGHTING)
        # glEnable(GL_ALPHA_TEST)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_BLEND)

        GL.glEnable(GL.GL_DITHER)
        GL.glEnable(GL.GL_MULTISAMPLE)
        # glEnable(GL_FOG)
        GL.glDepthMask(GL.GL_TRUE)
        # glShadeModel(GL_FLAT)

        GL.glShadeModel(GL.GL_SMOOTH)
        GL.glColorMaterial(GL.GL_FRONT, GL.GL_AMBIENT_AND_DIFFUSE)
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        # glEnable(GL_NORMALIZE)
        GL.glEnable(GL.GL_RESCALE_NORMAL)
        # glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)

        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, [0.5, 0.5, 0.5, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.3, 0.3, 0.3, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])

        GL.glMaterialfv(GL.GL_FRONT, GL.GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        GL.glMaterialfv(GL.GL_FRONT, GL.GL_DIFFUSE, [0.5, 0.5, 0.5, 1.0])
        GL.glMaterialfv(GL.GL_FRONT, GL.GL_SPECULAR, [0.8, 0.8, 0.8, 1.0])
        GL.glMaterialf(GL.GL_FRONT, GL.GL_SHININESS, 80.0)

        GL.glEnable(GL.GL_LIGHT0)
        self.camera.set()

        w, h = self.GetSize()

        aspect = w / float(h)

        GL.glMatrixMode(GL.GL_PROJECTION)
        GLU.gluPerspective(65, aspect, 0.1, 1000.0)
        GL.glMatrixMode(GL.GL_MODELVIEW)

        self.axis = _axis_indicators.Indicators(self.mainframe)

    @staticmethod
    def draw_grid():
        GRID_SIZE = 1000
        GRID_STEP = 50

        # --- Tiles ---
        TILE_SIZE = GRID_STEP
        HALF = GRID_SIZE
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, [0.5, 0.5, 0.5, 0.5])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.3, 0.3, 0.3, 0.5])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, [0.5, 0.5, 0.5, 0.5])

        GL.glMaterialfv(GL.GL_FRONT, GL.GL_AMBIENT, [0.3, 0.3, 0.3, 0.5])
        GL.glMaterialfv(GL.GL_FRONT, GL.GL_DIFFUSE, [0.5, 0.5, 0.5, 0.5])
        GL.glMaterialfv(GL.GL_FRONT, GL.GL_SPECULAR, [0.8, 0.8, 0.8, 0.5])
        GL.glMaterialf(GL.GL_FRONT, GL.GL_SHININESS, 100.0)

        for x in range(-HALF, HALF, TILE_SIZE):
            for y in range(-HALF, HALF, TILE_SIZE):
                # Alternate coloring for checkerboard effect
                is_even = ((x // TILE_SIZE) + (y // TILE_SIZE)) % 2 == 0
                if is_even:
                    GL.glColor4f(0.8, 0.8, 0.8, 0.4)
                else:
                    GL.glColor4f(0.3, 0.3, 0.3, 0.4)

                GL.glBegin(GL.GL_QUADS)
                GL.glVertex3f(x, 0, y)
                GL.glVertex3f(x, 0, y + TILE_SIZE)
                GL.glVertex3f(x + TILE_SIZE, 0, y + TILE_SIZE)
                GL.glVertex3f(x + TILE_SIZE, 0, y)
                GL.glEnd()

    def _render_bounding_boxes(self):

        for obj in self.objects:
            if obj.is_selected:
                GL.glColor4f(0.5, 1.0, 0.5, 0.3)
            else:
                GL.glColor4f(1.0, 0.5, 0.5, 0.3)

            for p1, p2 in obj.hit_test_rect:

                x1, y1, z1 = p1.as_float
                x2, y2, z2 = p2.as_float

                # back
                GL.glBegin(GL.GL_QUADS)
                GL.glVertex3f(x1, y1, z1)
                GL.glVertex3f(x2, y1, z1)
                GL.glVertex3f(x2, y2, z1)
                GL.glVertex3f(x1, y2, z1)
                GL.glEnd()

                # front
                GL.glBegin(GL.GL_QUADS)
                GL.glVertex3f(x1, y1, z2)
                GL.glVertex3f(x2, y1, z2)
                GL.glVertex3f(x2, y2, z2)
                GL.glVertex3f(x1, y2, z2)
                GL.glEnd()

                # left
                GL.glBegin(GL.GL_QUADS)
                GL.glVertex3f(x1, y1, z1)
                GL.glVertex3f(x1, y2, z1)
                GL.glVertex3f(x1, y2, z2)
                GL.glVertex3f(x1, y1, z2)
                GL.glEnd()

                # right
                GL.glBegin(GL.GL_QUADS)
                GL.glVertex3f(x2, y1, z1)
                GL.glVertex3f(x2, y1, z2)
                GL.glVertex3f(x2, y2, z2)
                GL.glVertex3f(x2, y2, z1)
                GL.glEnd()

                # top
                GL.glBegin(GL.GL_QUADS)
                GL.glVertex3f(x1, y2, z1)
                GL.glVertex3f(x2, y2, z1)
                GL.glVertex3f(x2, y2, z2)
                GL.glVertex3f(x1, y2, z2)
                GL.glEnd()

                # bottom
                GL.glBegin(GL.GL_QUADS)
                GL.glVertex3f(x1, y1, z1)
                GL.glVertex3f(x2, y1, z1)
                GL.glVertex3f(x2, y1, z2)
                GL.glVertex3f(x1, y1, z2)
                GL.glEnd()

                GL.glColor4f(0.2, 0.2, 0.2, 1.0)
                # top
                GL.glLineWidth(1.0)
                GL.glBegin(GL.GL_LINES)
                GL.glVertex3f(x1, y2, z1)
                GL.glVertex3f(x2, y2, z1)
                GL.glEnd()

                GL.glBegin(GL.GL_LINES)
                GL.glVertex3f(x2, y2, z1)
                GL.glVertex3f(x2, y2, z2)
                GL.glEnd()

                GL.glBegin(GL.GL_LINES)
                GL.glVertex3f(x2, y2, z2)
                GL.glVertex3f(x1, y2, z2)
                GL.glEnd()

                GL.glBegin(GL.GL_LINES)
                GL.glVertex3f(x1, y2, z2)
                GL.glVertex3f(x1, y2, z1)
                GL.glEnd()


                # bottom
                GL.glBegin(GL.GL_LINES)
                GL.glVertex3f(x1, y1, z1)
                GL.glVertex3f(x2, y1, z1)
                GL.glEnd()

                GL.glBegin(GL.GL_LINES)
                GL.glVertex3f(x2, y1, z1)
                GL.glVertex3f(x2, y1, z2)
                GL.glEnd()

                GL.glBegin(GL.GL_LINES)
                GL.glVertex3f(x2, y1, z2)
                GL.glVertex3f(x1, y1, z2)
                GL.glEnd()

                GL.glBegin(GL.GL_LINES)
                GL.glVertex3f(x1, y1, z2)
                GL.glVertex3f(x1, y1, z1)
                GL.glEnd()

                # left
                GL.glBegin(GL.GL_LINES)
                GL.glVertex3f(x1, y1, z1)
                GL.glVertex3f(x1, y2, z1)
                GL.glEnd()

                GL.glBegin(GL.GL_LINES)
                GL.glVertex3f(x1, y1, z2)
                GL.glVertex3f(x1, y2, z2)
                GL.glEnd()

                # right
                GL.glBegin(GL.GL_LINES)
                GL.glVertex3f(x2, y1, z1)
                GL.glVertex3f(x2, y2, z1)
                GL.glEnd()

                GL.glBegin(GL.GL_LINES)
                GL.glVertex3f(x2, y1, z2)
                GL.glVertex3f(x2, y2, z2)
                GL.glEnd()



    @_debug.timeit
    def OnDraw(self):
        # self.axis_indicator.set_angle((self.camera.eye - self.camera.position).inverse)
        # self.SetCurrent(self.context)

        w, h = self.GetSize()
        aspect = w / float(h)

        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GLU.gluPerspective(65, aspect, 0.1, 1000.0)

        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        self.camera.set()

        GL.glPushMatrix()

        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glEnableClientState(GL.GL_NORMAL_ARRAY)

        objs = self.camera.get_objects_in_view(self.objects)

        triangles = []
        last_opaque_index = 0

        for obj in objs:
            for tris, nrmls, colors, count, is_opaque in obj.triangles:
                if is_opaque:
                    triangles.insert(last_opaque_index, [tris, nrmls, colors[0], count, obj.is_selected])
                    last_opaque_index += 1
                else:
                    triangles.append([tris, nrmls, colors[0], count, obj.is_selected])

        for triangles, normals, color, triangle_count, is_selected in triangles:
            # GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, color)
            # GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, color)
            # GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, color)
            GL.glMaterialfv(GL.GL_FRONT, GL.GL_AMBIENT, color)
            GL.glMaterialfv(GL.GL_FRONT, GL.GL_DIFFUSE, color)
            GL.glMaterialfv(GL.GL_FRONT, GL.GL_SPECULAR, color)
            GL.glMaterialf(GL.GL_FRONT, GL.GL_SHININESS, 20.0)

            GL.glColor4f(*color)
            GL.glVertexPointer(3, GL.GL_DOUBLE, 0, triangles)
            GL.glNormalPointer(GL.GL_DOUBLE, 0, normals)
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, triangle_count)

        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        GL.glDisableClientState(GL.GL_NORMAL_ARRAY)
        # self._render_bounding_boxes()
        self.draw_grid()
        # self._render_bounding_boxes()
        GL.glPopMatrix()

        self.SwapBuffers()
