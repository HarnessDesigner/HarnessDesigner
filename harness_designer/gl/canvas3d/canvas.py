from typing import Self

import wx

import numpy as np
from wx import glcanvas
from wx import aui
from OpenGL import GL
from OpenGL import GLU
import ctypes
import math

from . import headlight as _headlight
from . import focal_target as _focal_target
from .. import shaders as _shaders
from ... import debug as _debug
from ... import config as _config
from ...image import utils as _image_utils
from ... import utils as _utils


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
    def __init__(self, parent, config: _config.Config.editor3d, size=wx.DefaultSize, pos=wx.DefaultPosition):
        glcanvas.GLCanvas.__init__(self, parent, -1, size=size, pos=pos)

        try:
            self.mainframe = aui.AuiManager.GetManager(parent).GetManagedWindow()
        except AttributeError:
            self.mainframe = parent

        self.config = config
        self._mode = None

        from .. import context as _context
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
        self._grid_data = None
        self._grid_lines_stipple = None
        self._grid_lines_solid = None

        self._angle_overlay_bitmap = wx.NullBitmap

        from . import key_handler as _key_handler
        from . import mouse_handler as _mouse_handler
        from . import scene_light as _scene_light

        self._key_handler = _key_handler.KeyHandler(self)
        self._mouse_handler = _mouse_handler.MouseHandler(self)
        self._headlight = _headlight.Headlight(self)
        self._scene_light = _scene_light.SceneLight(self)
        self._focal_target: _focal_target.FocalPoint = None

        font = self.GetFont()
        font.SetPointSize(15)
        self.SetFont(font)

    def set_mode(self, mode: int) -> None:
        self._mode = mode

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

    def set_selected_object(self, obj):
        self._selected = obj

    def get_selected_object(self):
        return self._selected

    def add_object(self, obj):
        self._objects.append(obj)

    def remove_object(self, obj):
        try:
            self._objects.remove(obj)
        except ValueError:
            pass

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
        if self.config.truck_pedestal.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if self.config.truck_pedestal.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = self.config.truck_pedestal.sensitivity
        dx *= sens
        dy *= sens

        self.camera.TruckPedestal(dx, dy, self.config.truck_pedestal.speed)

    @_debug.logfunc
    def Zoom(self, dx: float, _):
        dx *= self.config.zoom.sensitivity
        self.camera.Zoom(dx)

    @_debug.logfunc
    def Rotate(self, dx: float, dy: float) -> None:
        if self.config.rotate.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if self.config.rotate.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = self.config.rotate.sensitivity
        dx *= sens
        dy *= sens

        self.camera.Rotate(dx, dy)

    @_debug.logfunc
    def Walk(self, dx: float, dy: float) -> None:
        if dy == 0.0:
            self.PanTilt(dx * 6.0, 0.0)
            return

        look_dx = dx

        if self.config.walk.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if self.config.walk.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = self.config.walk.sensitivity
        dx *= sens
        dy *= sens

        self.camera.Walk(dx, dy, self.config.walk.speed)
        self.PanTilt(look_dx * 2.0, 0.0)

    @_debug.logfunc
    def PanTilt(self, dx: float, dy: float) -> None:
        if self.config.pan_tilt.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if self.config.pan_tilt.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = self.config.pan_tilt.sensitivity

        dx *= sens
        dy *= sens
        self.camera.PanTilt(dx, dy)

    def _on_erase_background(self, _):
        pass

    def _on_size(self, event):
        def _do_set_viewport(size):
            width, height = self.size = size * self.GetContentScaleFactor()
            with self.context:
                GL.glViewport(0, 0, width, height)

        wx.CallAfter(_do_set_viewport, event.GetSize())
        event.Skip()

    @_debug.logfunc
    def _on_paint(self, _):
        pdc = wx.PaintDC(self)

        with self.context:
            if not self._init:
                self._init_gl()
                self._init = True

            self._on_draw()

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

                def _cc(r_, g_, b_):
                    return 255 - r_, 255 - g_, 255 - b_

                for y_ in range(h):
                    corrected_y = h - 1 - y_
                    row = corrected_y * w
                    for x_ in range(w):
                        r, g, b, a = img.getpixel((x_, y_))
                        if a == 0:
                            continue

                        i = (row + x_) * 4
                        r, g, b = _cc(pixel_data[i], pixel_data[i + 1], pixel_data[i + 2])
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
    def _init_gl(self):
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

        self.set_draw_grid(self.config.floor.enable)
        self.set_focal_target(self.config.focal_target.enable)

        def _do():
            self.camera.Zoom(1.0)

        wx.CallAfter(_do)

    def _initialize_grid(self):
        """
        Compute the "Floor" and store it in the graphics adapter memory.

        This allows for a super fast render of the floor.

        :return:
        """
        even_color = self.config.floor.grid.primary_color
        ground_height = self.config.floor.ground_height
        size = self.config.floor.distance
        step = self.config.floor.grid.size

        def _get_vbo(verts, clrs):
            # Flatten the data
            verts = np.array(verts, dtype=np.float32).flatten()
            clrs = np.array(clrs, dtype=np.float32).flatten()

            # Combine vertices and colors into one array to pass to OpenGL
            v_data = np.concatenate((verts, clrs))

            # Calculate the number of vertices (for rendering)
            verts_count = len(verts) / 3

            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)  # Unbind the VBO

            vbo = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, v_data.nbytes,
                            v_data, GL.GL_STATIC_DRAW)

            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)  # Unbind the VBO

            return vbo, int(verts_count)

        if self.config.floor.grid.enable:
            # Grid configuration

            odd_color = self.config.floor.grid.secondary_color

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
                        [x, ground_height, y], [x, ground_height, y + step],
                        [x + step, ground_height, y + step], [x + step, ground_height, y]])

                    # Each vertex has the same color for the quad
                    colors.extend([color] * 4)
        else:
            vertices = [[size, ground_height, size], [size, ground_height, -size],
                        [-size, ground_height, -size], [-size, ground_height, size]]

            colors = [even_color] * 4

        grid_vbo, grid_vertex_count = _get_vbo(vertices, colors)

        sstep = step / 5.0
        y1 = ground_height + 0.1
        y2 = ground_height + 0.15

        def _frange(start, stop, inc):
            value = start
            while value < stop:
                yield value
                value += inc

        stipple_lines = []
        solid_lines = []

        stipple_colors = []
        solid_colors = []

        for i in _frange(-size, size + 1, sstep):
            if not i % step:
                solid_colors.extend([0.65, 0.65, 0.65, 1.0] * 4)
                solid_lines.extend([[i, y2, size], [i, y2, -size],
                                    [size, y2, i], [-size, y2, i]])
            else:
                stipple_colors.extend([0.35, 0.35, 0.35, 1.0] * 4)
                stipple_lines.extend([[i, y1, size], [i, y1, -size],
                                      [size, y1, i], [-size, y1, i]])

        stipple_vbo, stipple_vertex_count = _get_vbo(stipple_lines, stipple_colors)
        solid_vbo, solid_vertex_count = _get_vbo(solid_lines, solid_colors)

        return ((grid_vbo, grid_vertex_count),
                (stipple_vbo, stipple_vertex_count),
                (solid_vbo, solid_vertex_count))

    def set_focal_target(self, flag):
        with self.context:
            if flag and self._focal_target is None:
                self._focal_target = _focal_target.FocalPoint(self)
            elif not flag and self._focal_target is not None:
                self._focal_target = None

    def set_draw_grid(self, flag):
        with self.context:
            if self._grid_data is not None:
                try:
                    GL.glDeleteVertexArrays(1, [self._grid_data[0]])
                except:  # NOQA
                    pass
    
                try:
                    GL.glDeleteBuffers(1, [self._grid_lines_stipple[0]])
                except:  # NOQA
                    pass
    
                try:
                    GL.glDeleteBuffers(1, [self._grid_lines_solid[0]])
                except:  # NOQA
                    pass
    
                self._grid_data = None
                self._grid_lines_stipple = None
                self._grid_lines_solid = None
                
            if flag:
                (self._grid_data, self._grid_lines_stipple,
                 self._grid_lines_solid) = self._initialize_grid()

        self.Refresh(False)

    @_debug.logfunc
    def _draw_grid(self):
        """Render the precomputed grid using the VBO."""

        # type_ is either GL.GL_LINES or GL.GL_QUADS
        def _draw_vbo(vbo, count, type_):
            # Setup the VBO for rendering
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
            # Configure vertex attributes (position and color)
            # Total size of vertex data (position: x, y, z)
            vertex_size = count * 3 * 4

            # Colors start immediately after vertices
            color_offset = vertex_size

            stride = 0  # No stride between consecutive vertex positions
            GL.glEnableClientState(GL.GL_VERTEX_ARRAY)

            # First 3 floats are position
            GL.glVertexPointer(3, GL.GL_FLOAT, stride, ctypes.c_void_p(0))

            GL.glEnableClientState(GL.GL_COLOR_ARRAY)

            # Next 3 floats are color
            GL.glColorPointer(4, GL.GL_FLOAT, stride, ctypes.c_void_p(color_offset))

            # Draw
            GL.glDrawArrays(type_, 0, count)

            # Cleanup
            GL.glDisableClientState(GL.GL_COLOR_ARRAY)
            GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        # enable blending and disable the depth mask to remove the moiré that
        # occurs from the grid lines.
        # https://en.wikipedia.org/wiki/Moir%C3%A9_pattern
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glDepthMask(GL.GL_FALSE)

        # draw grid floor
        _draw_vbo(self._grid_data[0], self._grid_data[1], GL.GL_QUADS)

        # draw grid dashed lines
        GL.glLineStipple(1, 0xFF00)
        GL.glEnable(GL.GL_LINE_STIPPLE)
        _draw_vbo(self._grid_lines_stipple[0], self._grid_lines_stipple[1], GL.GL_LINES)
        GL.glDisable(GL.GL_LINE_STIPPLE)

        # draw grid solid lines
        _draw_vbo(self._grid_lines_solid[0], self._grid_lines_solid[1], GL.GL_LINES)

        GL.glDepthMask(GL.GL_TRUE)
        GL.glDisable(GL.GL_BLEND)
        
    @_debug.logfunc
    def _render_bounding_boxes(self):
        selected = None

        offset = 0

        vertices = []
        faces = []
        edges = []

        for obj in self._objects:
            p1, p2 = obj.aabb

            x1, y1, z1 = p1.as_float
            x2, y2, z2 = p2.as_float

            verts = np.array([
                [x1, y1, z1],  # 0: bottom-left-front
                [x2, y1, z1],  # 1: bottom-right-front
                [x2, y2, z1],  # 2: top-right-front
                [x1, y2, z1],  # 3: top-left-front
                [x1, y1, z2],  # 4: bottom-left-back
                [x2, y1, z2],  # 5: bottom-right-back
                [x2, y2, z2],  # 6: top-right-back
                [x1, y2, z2],  # 7: top-left-back
            ], dtype=np.float32)

            facs = np.array([
                (0, 1, 2, 3),  # front
                (5, 4, 7, 6),  # back
                (4, 0, 3, 7),  # left
                (1, 5, 6, 2),  # right
                (3, 2, 6, 7),  # top
                (4, 5, 1, 0),  # bottom
            ], dtype=np.int32)

            edgs = np.array([
                (0, 1), (1, 2), (2, 3), (3, 0),  # front face
                (4, 5), (5, 6), (6, 7), (7, 4),  # back face
                (0, 4), (1, 5), (2, 6), (3, 7),  # connecting edges
            ], dtype=np.int32)

            if obj.is_selected:
                selected = [verts, facs, edgs]
            else:
                vertices.append(verts)
                faces.append(facs + offset)
                edges.append(edgs + offset)
                offset += 8

        vertices = np.array(vertices, dtype=np.float32).reshape(-1, 3)
        faces = np.array(faces, dtype=np.int32).reshape(-1, 4)
        edges = np.array(edges, dtype=np.int32).reshape(-1, 2)

        def _render_bb(v, f):
            vers, normals, count = _utils.compute_vertex_normals(v, f)

            # Enable vertex arrays
            GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
            GL.glEnableClientState(GL.GL_NORMAL_ARRAY)

            # Set pointers
            GL.glVertexPointer(3, GL.GL_FLOAT, 0, vers)
            GL.glNormalPointer(GL.GL_FLOAT, 0, normals)

            # Draw all quads
            GL.glDrawArrays(GL.GL_QUADS, 0, count)

            # Disable vertex arrays
            GL.glDisableClientState(GL.GL_NORMAL_ARRAY)
            GL.glDisableClientState(GL.GL_VERTEX_ARRAY)

        def _render_edges(v, e):
            e = v[e].reshape(-1, 3)
            GL.glLineWidth(1.0)
            GL.glEnableClientState(GL.GL_VERTEX_ARRAY)

            GL.glVertexPointer(3, GL.GL_FLOAT, 0, e)
            GL.glDrawArrays(GL.GL_LINES, 0, len(e))

            GL.glDisableClientState(GL.GL_VERTEX_ARRAY)

        GL.glColor4f(1.0, 0.5, 0.5, 0.3)
        _render_bb(vertices, faces)

        # render edges
        GL.glColor4f(1.0, 0.2, 0.2, 1.0)
        _render_edges(vertices, edges)

        if selected is not None:
            vertices, faces, edges = selected

            GL.glColor4f(0.5, 1.0, 0.5, 0.3)
            _render_bb(vertices, faces)

            GL.glColor4f(0.5, 1.0, 0.5, 1.0)
            _render_edges(vertices, edges)

    @_debug.logfunc
    def _draw_scene(self, objects):
        # Set global shader uniforms that are the same for all objects
        GL.glUseProgram(self._shader_program)
        
        # Set view position (camera position) for specular lighting
        viewPosition_loc = GL.glGetUniformLocation(self._shader_program, "viewPosition")
        GL.glUniform3fv(viewPosition_loc, 1, self.camera.position.as_numpy)
        
        # Set projection and view matrices
        projection_loc = GL.glGetUniformLocation(self._shader_program, "projection")
        view_loc = GL.glGetUniformLocation(self._shader_program, "view")
        
        # Get current projection and view matrices from OpenGL
        projection_matrix = GL.glGetFloatv(GL.GL_PROJECTION_MATRIX)
        view_matrix = GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX)
        
        GL.glUniformMatrix4fv(projection_loc, 1, GL.GL_FALSE, projection_matrix)
        GL.glUniformMatrix4fv(view_loc, 1, GL.GL_FALSE, view_matrix)
        
        # Set scene lighting
        self._scene_light.set(self._shader_program)
        
        # Set headlight
        self._headlight(self._shader_program)
        
        # Render each object
        for obj in objects:
            obj.obj3d.render(self._shader_program)

            if obj.is_selected:
                GL.glColor4f(1.0, 0.4, 0.4, 1.0)
                GL.glLineWidth(2.0)
                p1, p2 = obj.aabb

                y = self.config.floor.ground_height + 0.20

                GL.glBegin(GL.GL_LINES)
                GL.glVertex3f(p1.x, y, p1.z)
                GL.glVertex3f(p1.x, y, p2.z)

                GL.glVertex3f(p1.x, y, p2.z)
                GL.glVertex3f(p2.x, y, p2.z)

                GL.glVertex3f(p2.x, y, p2.z)
                GL.glVertex3f(p2.x, y, p1.z)

                GL.glVertex3f(p2.x, y, p1.z)
                GL.glVertex3f(p1.x, y, p1.z)
                GL.glEnd()

    def _render_reflection(self):
        GL.glPushMatrix()
        # Reflect across the y = 0 plane (flip the Y-axis)
        GL.glScalef(1.0, -1.0, 1.0)

        # Enable clipping to avoid rendering above the floor
        GL.glEnable(GL.GL_CLIP_PLANE0)
        
        # Clipping plane: y >= 0
        clipping_plane = [0.0, 1.0, 0.0, 0.0]  
        GL.glClipPlane(GL.GL_CLIP_PLANE0, clipping_plane)
        # we have to iterate over the objects specifically for
        # the reflection because the view is different for the reflection
        objs = self.camera.GetObjectsInView(self._objects)
        self._draw_scene(objs)
        GL.glDisable(GL.GL_CLIP_PLANE0)
        GL.glPopMatrix()

    @_debug.logfunc
    def _on_draw(self):
        with self.context:
            w, h = self.GetSize()
            aspect = w / float(h)

            f_size = self.config.floor.grid.size ** 2

            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
            GL.glMatrixMode(GL.GL_PROJECTION)
            GL.glLoadIdentity()
            GLU.gluPerspective(65, aspect, 0.1, float(math.sqrt(f_size * f_size)))

            GL.glMatrixMode(GL.GL_MODELVIEW)
            GL.glLoadIdentity()

            self.camera.Set()

            if self.config.floor.enable and self.config.floor.reflections.enable:
                self._render_reflection()

            GL.glPushMatrix()
            objs = self.camera.GetObjectsInView(self._objects)
            self._draw_scene(objs)
            
            if self.config.debug.bounding_boxes:
                self._render_bounding_boxes()

            if self.config.focal_target.enable:
                self._focal_target.obj3d.render(self._shader_program)

            GL.glPopMatrix()

            if self.config.floor.enable:
                self._draw_grid()
            
            self.SwapBuffers()
