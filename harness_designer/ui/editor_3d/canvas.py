from typing import Self

import wx

import numpy as np
from wx import glcanvas
from OpenGL import GL
from OpenGL import GLU
import ctypes


from ...geometry import point as _point
from . import headlight as _headlight
from . import shaders as _shaders
from ... import debug as _debug
from ... import config as _config
from ...image import utils as _image_utils


Config = _config.Config
MOUSE_REVERSE_Y_AXIS = _config.MOUSE_REVERSE_Y_AXIS
MOUSE_REVERSE_X_AXIS = _config.MOUSE_REVERSE_X_AXIS


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
    def __init__(self, parent, size=wx.DefaultSize, pos=wx.DefaultPosition):
        glcanvas.GLCanvas.__init__(self, parent, -1, size=size, pos=pos)

        self._view_offset = None

        from . import context as _context
        from . import camera as _camera

        self._init = False
        self.context = _context.GLContext(self)
        self.camera = _camera.Camera(self)
        self._angle_overlay = None
        self._shader_program = None

        self.size = None

        self.Bind(wx.EVT_SIZE, self._on_size)
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self._on_erase_background)

        self._selected = None
        self._objects = []
        self._ref_count = 0
        self.grid_data = None
        self.grid_lines_stipple = None
        self.grid_lines_solid = None

        self._angle_overlay_bitmap = wx.NullBitmap

        from . import key_handler as _key_handler
        from . import mouse_handler as _mouse_handler

        self._key_handler = _key_handler.KeyHandler(self)
        self._mouse_handler = _mouse_handler.MouseHandler(self)
        self._headlight: _headlight.Headlight = None

        font = self.GetFont()
        font.SetPointSize(15)
        self.SetFont(font)

    @_debug.logfunc
    def set_angle_overlay(self, x, y, z):
        if None in (x, y, z):
            self._angle_overlay_bitmap = wx.NullBitmap
            return

        angle_overlay = f'X: {round(x, 6)}  Y: {round(y, 6)}  Z: {round(z, 6)}'

        w, h = self.GetTextExtent(angle_overlay)
        w += 14
        h += 4

        buf = bytearray([0] * (w * h * 4))
        bitmap = wx.Bitmap.FromBufferRGBA(w, h, buf)
        dc = wx.MemoryDC()
        dc.SelectObject(bitmap)
        gcdc = wx.GCDC(dc)
        gcdc.SetFont(self.GetFont())
        gcdc.SetTextForeground(wx.Colour(255, 255, 255, 255))
        gcdc.SetTextBackground(wx.Colour(0, 0, 0, 0))
        gcdc.DrawText(angle_overlay, 2, 2)
        # gcdc.SetBrush(wx.Brush(wx.Colour(255, 255, 255, 255)))
        # gcdc.DrawRectangle(0, 0, w, h)
        dc.SelectObject(wx.NullBitmap)

        gcdc.Destroy()
        del gcdc

        dc.Destroy()
        del dc

        self._angle_overlay_bitmap = bitmap

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        self._selected = value

    @classmethod
    def GetViewSize(cls) -> _point.Point:
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

        return _point.Point(Config.virtual_canvas.width, Config.virtual_canvas.height)

    def AddObject(self, obj):
        with self:
            self._objects.insert(0, obj)

        self.Refresh(False)

    def RemoveObject(self, obj):
        try:
            self._objects.remove(obj)
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

    @_debug.logfunc
    def TruckPedestal(self, dx: float, dy: float) -> None:
        if Config.truck_pedestal.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if Config.truck_pedestal.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = Config.truck_pedestal.sensitivity
        dx *= sens
        dy *= sens

        self.camera.TruckPedestal(dx, dy, Config.truck_pedestal.speed)

    @_debug.logfunc
    def Zoom(self, dx: float, _):
        dx *= Config.zoom.sensitivity
        self.camera.Zoom(dx)

    @_debug.logfunc
    def Rotate(self, dx: float, dy: float) -> None:
        if Config.rotate.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if Config.rotate.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = Config.rotate.sensitivity
        dx *= sens
        dy *= sens

        self.camera.Rotate(dx, dy)

    @_debug.logfunc
    def Walk(self, dx: float, dy: float) -> None:
        if dy == 0.0:
            self.PanTilt(dx * 6.0, 0.0)
            return

        look_dx = dx

        if Config.walk.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if Config.walk.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = Config.walk.sensitivity
        dx *= sens
        dy *= sens

        self.camera.Walk(dx, dy, Config.walk.speed)
        self.PanTilt(look_dx * 2.0, 0.0)

    @_debug.logfunc
    def PanTilt(self, dx: float, dy: float) -> None:
        if Config.pan_tilt.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if Config.pan_tilt.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = Config.pan_tilt.sensitivity

        dx *= sens
        dy *= sens
        self.camera.PanTilt(dx, dy)

    def _on_erase_background(self, _):
        pass

    def _on_size(self, event):
        wx.CallAfter(self.DoSetViewport, event.GetSize())
        event.Skip()

    def DoSetViewport(self, size):
        width, height = self.size = size * self.GetContentScaleFactor()
        with self.context:
            GL.glViewport(0, 0, width, height)

    @_debug.logfunc
    def _on_paint(self, _):
        pdc = wx.PaintDC(self)

        with self.context:
            if not self._init:
                self.InitGL()
                self._init = True

            self.OnDraw()

            if self._angle_overlay_bitmap.IsOk():
                w, h = self._angle_overlay_bitmap.GetSize()

                img = _image_utils.wx_bitmap_2_pil_image(self._angle_overlay_bitmap)

                pw, ph = self.GetParent().GetSize()
                sw, sh = self.GetSize()

                x = (sw - pw) // 2
                y = (sh - ph) // 2

                x += 30
                y += 20
                gl_y = sh - y

                # Read pixel data from the front buffer (now visible on the screen)
                GL.glReadBuffer(GL.GL_FRONT)  # Set read buffer explicitly
                pixel_data = GL.glReadPixels(x, gl_y, w, h, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)

                def cc(r_, g_, b_):
                    return 255 - r_, 255 - g_, 255 - b_

                for y_ in range(h):
                    corrected_y = h - 1 - y_
                    row = corrected_y * w
                    for x_ in range(w):
                        r, g, b, a = img.getpixel((x_, y_))
                        if a == 0:
                            continue

                        i = (row + x_) * 4
                        r, g, b = cc(pixel_data[i], pixel_data[i + 1], pixel_data[i + 2])
                        img.putpixel((x_, y_), (r, g, b, a))

                gcdc = wx.GCDC(pdc)
                gc = gcdc.GetGraphicsContext()
                bitmap = _image_utils.pil_image_2_wx_bitmap(img)
                gc.DrawBitmap(bitmap, float(x + 5), float(y - 35), float(w), float(h))

                gcdc.Destroy()
                del gcdc

    @staticmethod
    def _normalize(v: np.ndarray) -> np.ndarray:
        n = np.linalg.norm(v)
        return v if n == 0.0 else v / n

    @_debug.logfunc
    def InitGL(self):
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glClearColor(0.20, 0.20, 0.20, 1.0)
        self._shader_program = _shaders.create_program()

        # GL.glEnable(GL.GL_LIGHTING)
        # GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        # GL.glEnable(GL.GL_BLEND)
        # GL.glEnable(GL.GL_DITHER)
        # GL.glEnable(GL.GL_MULTISAMPLE)
        # GL.glDepthMask(GL.GL_TRUE)
        # GL.glShadeModel(GL.GL_SMOOTH)
        # GL.glColorMaterial(GL.GL_FRONT, GL.GL_AMBIENT_AND_DIFFUSE)
        # GL.glEnable(GL.GL_COLOR_MATERIAL)
        # GL.glEnable(GL.GL_RESCALE_NORMAL)
        #
        # GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, [0.5, 0.5, 0.5, 1.0])
        # GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.3, 0.3, 0.3, 1.0])
        # GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])
        #
        # GL.glMaterialfv(GL.GL_FRONT, GL.GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        # GL.glMaterialfv(GL.GL_FRONT, GL.GL_DIFFUSE, [0.5, 0.5, 0.5, 1.0])
        # GL.glMaterialfv(GL.GL_FRONT, GL.GL_SPECULAR, [0.8, 0.8, 0.8, 1.0])
        # GL.glMaterialf(GL.GL_FRONT, GL.GL_SHININESS, 80.0)

        # GL.glEnable(GL.GL_LIGHT0)
        self.camera.Set()

        w, h = self.GetSize()

        aspect = w / float(h)

        GL.glMatrixMode(GL.GL_PROJECTION)
        GLU.gluPerspective(65, aspect, 0.1, 1000.0)
        GL.glMatrixMode(GL.GL_MODELVIEW)

        def _do():
            self.camera.Zoom(1.0)

        wx.CallAfter(_do)

    @staticmethod
    def initialize_grid():
        """
        Compute the "Floor" and store it in the graphics adapter memory.

        This allows for a super fast render of the floor.

        :return:
        """
        even_color = Config.floor.primary_color
        ground_height = Config.floor.ground_height
        size = Config.floor.distance
        step = Config.floor.grid_size

        def get_vbo(verts, clrs):
            # Flatten the data
            verts = np.array(verts, dtype=np.float32).flatten()
            clrs = np.array(clrs, dtype=np.float32).flatten()

            # Combine vertices and colors into one array to pass to OpenGL
            v_data = np.concatenate((verts, clrs))

            # Calculate the number of vertices (for rendering)
            verts_count = len(verts) // 3

            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)  # Unbind the VBO

            vbo = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, v_data.nbytes,
                            v_data, GL.GL_STATIC_DRAW)

            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)  # Unbind the VBO

            return vbo, verts_count

        if Config.floor.show_grid:
            # Grid configuration

            odd_color = Config.floor.secondary_color

            # Precompute vertices and colors
            vertices = []
            colors = []

            for x in range(-size, size, step):
                for y in range(-size, size, step):
                    # Alternate coloring for checkerboard effect
                    is_even = ((x // step) + (y // step)) % 2 == 0
                    color = even_color if is_even else odd_color

                    # Each quad consists of 4 vertices
                    vertices.extend([
                        [x, ground_height, y],              # Bottom-left
                        [x, ground_height, y + step],      # Top-left
                        [x + step, ground_height, y + step],  # Top-right
                        [x + step, ground_height, y],      # Bottom-right
                    ])

                    # Each vertex has the same color for the quad
                    colors.extend([color] * 4)
        else:
            vertices = [[size, ground_height, size],
                        [size, ground_height, -size],
                        [-size, ground_height, -size],
                        [-size, ground_height, size]]

            colors = [even_color] * 4

        grid_vbo, grid_vertex_count = get_vbo(vertices, colors)

        sstep = step / 5.0
        y1 = ground_height + 0.1
        y2 = ground_height + 0.15

        def frange(start, stop, inc):
            value = start
            while value < stop:
                yield value
                value += inc

        stipple_lines = []
        solid_lines = []

        stipple_colors = []
        solid_colors = []

        for i in frange(-size, size, sstep):
            if not i % step:
                solid_colors.extend([0.8, 0.8, 0.8, 1.0] * 4)
                solid_lines.extend([
                    [i, y2, size],
                    [i, y2, -size],
                    [size, y2, i],
                    [-size, y2, i]
                ])
            else:
                stipple_colors.extend([0.4, 0.4, 0.4, 1.0] * 4)
                stipple_lines.extend(
                    [
                        [i, y1, size],
                        [i, y1, -size],
                        [size, y1, i],
                        [-size, y1, i]
                    ]
                )

        stipple_vbo, stipple_vertex_count = get_vbo(stipple_lines, stipple_colors)
        solid_vbo, solid_vertex_count = get_vbo(solid_lines, solid_colors)

        return ((grid_vbo, grid_vertex_count),
                (stipple_vbo, stipple_vertex_count),
                (solid_vbo, solid_vertex_count))

    @_debug.logfunc
    def DrawGrid(self):
        """Render the precomputed grid using the VBO."""

        if self.grid_data is None:
            # Ensure the VBO is initialized
            (
                self.grid_data,
                self.grid_lines_stipple,
                self.grid_lines_solid
            ) = self.initialize_grid()

        # Setup the VBO for rendering
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.grid_data[0])

        # Configure vertex attributes (position and color)
        vertex_size = self.grid_data[1] * 3 * 4  # Total size of vertex data (position: x, y, z)
        color_offset = vertex_size  # Colors start immediately after vertices

        stride = 0  # No stride between consecutive vertex positions
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glVertexPointer(3, GL.GL_FLOAT, stride, ctypes.c_void_p(0))  # First 3 floats are position

        GL.glEnableClientState(GL.GL_COLOR_ARRAY)
        GL.glColorPointer(4, GL.GL_FLOAT, stride, ctypes.c_void_p(color_offset))  # Next 3 floats are color

        # Draw the grid
        GL.glDrawArrays(GL.GL_QUADS, 0, self.grid_data[1])

        # Cleanup
        GL.glDisableClientState(GL.GL_COLOR_ARRAY)
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        # stipple lines
        # Setup the VBO for rendering
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.grid_lines_stipple[0])

        # Configure vertex attributes (position and color)
        vertex_size = self.grid_lines_stipple[1] * 3 * 4  # Total size of vertex data (position: x, y, z)
        color_offset = vertex_size  # Colors start immediately after vertices

        GL.glLineStipple(1, 0xFF00)
        GL.glEnable(GL.GL_LINE_STIPPLE)

        stride = 0  # No stride between consecutive vertex positions
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glVertexPointer(3, GL.GL_FLOAT, stride, ctypes.c_void_p(0))  # First 3 floats are position

        GL.glEnableClientState(GL.GL_COLOR_ARRAY)
        GL.glColorPointer(4, GL.GL_FLOAT, stride, ctypes.c_void_p(color_offset))  # Next 3 floats are color

        # Draw the grid
        GL.glDrawArrays(GL.GL_LINES, 0, self.grid_lines_stipple[1])

        # Cleanup
        GL.glDisableClientState(GL.GL_COLOR_ARRAY)
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        GL.glDisable(GL.GL_LINE_STIPPLE)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        # solid lines
        # Setup the VBO for rendering
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.grid_lines_solid[0])

        # Configure vertex attributes (position and color)
        vertex_size = self.grid_lines_solid[1] * 3 * 4  # Total size of vertex data (position: x, y, z)
        color_offset = vertex_size  # Colors start immediately after vertices

        stride = 0  # No stride between consecutive vertex positions
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glVertexPointer(3, GL.GL_FLOAT, stride, ctypes.c_void_p(0))  # First 3 floats are position

        GL.glEnableClientState(GL.GL_COLOR_ARRAY)
        GL.glColorPointer(4, GL.GL_FLOAT, stride, ctypes.c_void_p(color_offset))  # Next 3 floats are color

        # Draw the grid
        GL.glDrawArrays(GL.GL_LINES, 0, self.grid_lines_solid[1])

        # Cleanup
        GL.glDisableClientState(GL.GL_COLOR_ARRAY)
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    @_debug.logfunc
    def _render_bounding_boxes(self):

        for obj in self._objects:
            if obj.is_selected:
                GL.glColor4f(0.5, 1.0, 0.5, 0.3)
            else:
                GL.glColor4f(1.0, 0.5, 0.5, 0.3)

            for p1, p2 in obj.rect:

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

    @staticmethod
    @_debug.logfunc
    def draw_scene(objects):
        for obj in objects:
            for renderer in obj.triangles:
                renderer()

            if obj.is_selected and obj.rect:
                GL.glColor4f(1.0, 0.4, 0.4, 1.0)
                GL.glLineWidth(2.0)
                p1, p2 = obj.rect[0]

                GL.glBegin(GL.GL_LINES)
                GL.glVertex3f(p1.x, 0.20, p1.z)
                GL.glVertex3f(p1.x, 0.20, p2.z)

                GL.glVertex3f(p1.x, 0.20, p2.z)
                GL.glVertex3f(p2.x, 0.20, p2.z)

                GL.glVertex3f(p2.x, 0.20, p2.z)
                GL.glVertex3f(p2.x, 0.20, p1.z)

                GL.glVertex3f(p2.x, 0.20, p1.z)
                GL.glVertex3f(p1.x, 0.20, p1.z)
                GL.glEnd()

    @_debug.logfunc
    def OnDraw(self):
        with self.context:
            w, h = self.GetSize()
            aspect = w / float(h)

            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
            GL.glMatrixMode(GL.GL_PROJECTION)
            GL.glLoadIdentity()
            GLU.gluPerspective(65, aspect, 0.1, 1000.0)

            GL.glMatrixMode(GL.GL_MODELVIEW)
            GL.glLoadIdentity()

            self.camera.Set()

            if Config.headlight.turn_on and self._headlight is None:
                self._headlight = _headlight.Headlight(self)
            elif not Config.headlight and self._headlight is not None:
                self._headlight = None

            if self._headlight is not None:
                self._headlight()

            GL.glPushMatrix()

            # Reflect across the y = 0 plane (flip the Y-axis)
            GL.glScalef(1.0, -1.0, 1.0)

            # Enable clipping to avoid rendering below the floor
            GL.glEnable(GL.GL_CLIP_PLANE0)
            clipping_plane = [0.0, 1.0, 0.0, 0.0]  # Clipping plane: y >= 0
            GL.glClipPlane(GL.GL_CLIP_PLANE0, clipping_plane)
            objs = self.camera.GetObjectsInView(self._objects)
            self.draw_scene(objs)
            GL.glDisable(GL.GL_CLIP_PLANE0)
            GL.glPopMatrix()

            GL.glPushMatrix()
            objs = self.camera.GetObjectsInView(self._objects)
            self.DrawGrid()
            self.draw_scene(objs)
            # self._render_bounding_boxes()
            GL.glPopMatrix()

            self.SwapBuffers()
