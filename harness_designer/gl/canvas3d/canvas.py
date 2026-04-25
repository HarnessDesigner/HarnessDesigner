from typing import Self

import wx

import numpy as np
from wx import glcanvas
from wx import aui
from OpenGL import GL
from OpenGL import GLU
import math
import ctypes
import weakref

from . import headlight as _headlight
from . import focal_target as _focal_target
from .. import shaders as _shaders
from ... import debug as _debug
from ... import config as _config
from ...image import utils as _image_utils
from . import floor as _floor
from . import culling as _culling


MOUSE_REVERSE_Y_AXIS = _config.MOUSE_REVERSE_Y_AXIS
MOUSE_REVERSE_X_AXIS = _config.MOUSE_REVERSE_X_AXIS


_debug_config = _config.Config.debug.rendering3d


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
    def __init__(self, parent, config: _config.Config.editor3d, size=wx.DefaultSize,
                 pos=wx.DefaultPosition, axis_overlay=False):
        glcanvas.GLCanvas.__init__(self, parent, -1, size=size, pos=pos)

        try:
            self.mainframe = aui.AuiManager.GetManager(parent).GetManagedWindow()
        except AttributeError:
            self.mainframe = parent

        self.config = config
        self._mode = None

        from .. import context as _context
        from . import camera as _camera
        from . import axis_overlay as _axis_overlay

        if axis_overlay:
            self._axis_overlay = _axis_overlay.Overlay(self, config.axis_overlay)
        else:
            self._axis_overlay = None

        self._init = False
        self.context = _context.GLContext(self)
        self.camera = _camera.Camera(self)
        self._angle_overlay = None

        self._faces_program = None
        self._edges_program = None
        self._vertices_program = None
        self._floor_program = None

        self.floor: _floor.Floor = None
        self._view_culling = _culling.CullingThreadPool()
        self._last_culled = []
        self._object_refs = []
        self._objects_in_view = []
        self._object_addr_mapping = {}

        self._object_data = [[], [], [], [], [], [], [], [], [], []]

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

        self._angle_view_bitmap = wx.NullBitmap

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

    @property
    def axis_overlay(self):
        return self._axis_overlay

    @property
    def objects_in_view(self):
        return self._objects_in_view

    def set_mode(self, mode: int) -> None:
        self._mode = mode

    @property
    def objects_in_view(self) -> list:
        return self._objects_in_view

    @_debug.logfunc
    def set_angle_view(self, x, y, z):
        if None in (x, y, z):
            self._angle_view_bitmap = wx.NullBitmap
            return

        angle_overlay = f'X: {round(x, 6)}  Y: {round(y, 6)}  Z: {round(z, 6)}'

        w, h = self.GetTextExtent(angle_overlay)
        w += 14
        h += 4

        buf = bytearray([0] * (w * h * 4))
        bitmap = wx.Bitmap.FromBufferRGBA(w, h, buf)  # NOQA
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

        self._angle_view_bitmap = bitmap

    def set_selected(self, obj):
        self._selected = obj

    def get_selected(self):
        return self._selected

    def add_object(self, obj):
        if isinstance(obj, _focal_target.FocalPoint):
            return

        found_container = self._object_data[0]
        container_len = 9999999999

        for container in self._object_data:
            if len(container) < container_len:
                found_container = container
                container_len = len(container)

        aabb_min, aabb_max = obj.obj3d.aabb
        pos = obj.obj3d.position.as_numpy
        is_opaque = obj.obj3d.is_opaque

        # because the GIL is not used during the culling process a python object
        # is not able to pass through it. How this is being handled is by getting
        # the memory location for the python object (which is an integer) and
        # passing that through. On the back side we use ctypes to cast the address
        # back into the python object.
        #
        # The reason why we create a weakref of the object and pass the memory
        # address to that is because of how weakref handles the deletion of an
        # object. it allows is to remove the object data form the culling lists
        # during the rendering process so no explicit searching over those lists
        # needs to be done. The entire process becomes simpler to manage that way
        # the weakref will get removed from the weakref list as well.
        obj_ref = weakref.ref(obj, self.__remove_obj_ref)
        obj_address = id(obj_ref)

        # we need to hold a reference to the weakref so it doesn't get GC'd
        # which would cause the memory address for the wekref to be invalid
        self._object_refs.append(obj_ref)
        self._object_addr_mapping[obj] = obj_address

        found_container.append([aabb_min, aabb_max, pos, is_opaque, obj_address])
        self._objects.append(obj)

    def __remove_obj_ref(self, ref):
        try:
            self._object_refs.remove(ref)
        except ValueError:
            pass

    def remove_object(self, obj):
        print('removing object:', obj)

        # we don't need to do any specific cleanup for the data in
        # self._object_data that is handled by the weakref and the render process.

        try:
            self._objects.remove(obj)
            print('removed from objects')

        except ValueError:
            pass

        try:
            self._objects_in_view.remove(obj)
            print('removed from objects in view')

        except ValueError:
            pass

        if obj in self._object_addr_mapping:
            obj_address = self._object_addr_mapping.pop(obj)
            print('object address:', obj, ':', obj_address)

            for container in self._object_data:
                for line in container:
                    if line[-1] == obj_address:
                        print('removing from container')
                        container.remove(line)
                        break
                else:
                    continue

                break

        self.Refresh()

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

        self.context.acquire()
        if not self._init:
            self._init_gl()
            self._init = True

        self._on_draw()

        if self._angle_view_bitmap.IsOk():
            w, h = self._angle_view_bitmap.GetSize()

            img = _image_utils.wx_bitmap_2_pil_image(self._angle_view_bitmap)
            
            pw, ph = self.GetParent().GetSize()
            sw, sh = self.GetSize()

            x = (sw - pw) // 2
            y = (sh - ph) // 2
            
            x += 30
            y += 20
            gl_y = sh - y

            GL.glReadBuffer(GL.GL_FRONT)
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
        
        self.context.release()

    @staticmethod
    def _normalize(v: np.ndarray) -> np.ndarray:
        n = np.linalg.norm(v)
        return v if n == 0.0 else v / n

    @_debug.logfunc
    def _init_gl(self):
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glClearColor(*self.config.background_color)

        self._faces_program = _shaders.compile_faces_program()
        self._edges_program = _shaders.compile_edges_program()
        self._vertices_program = _shaders.compile_vertices_program()
        self._floor_program = _shaders.compile_floor_program()

        self.floor = _floor.Floor(self, self._floor_program)

        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_BLEND)

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

    def set_focal_target(self, flag):
        with self.context:
            if flag and self._focal_target is None:
                self._focal_target = _focal_target.FocalPoint(self)
            elif not flag and self._focal_target is not None:
                self._focal_target = None

    def set_draw_grid(self, flag):
        self.floor.set(flag)

    @_debug.logfunc
    def _draw_scene(self, obj_data):
        projection_matrix = GL.glGetFloatv(GL.GL_PROJECTION_MATRIX)
        view_matrix = GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX)

        GL.glUseProgram(self._faces_program)

        view_position_loc = GL.glGetUniformLocation(self._faces_program, "viewPosition")
        projection_loc = GL.glGetUniformLocation(self._faces_program, "projection")
        view_loc = GL.glGetUniformLocation(self._faces_program, "view")
        floor_y_loc = GL.glGetUniformLocation(self._faces_program, "floorY")
        object_has_reflection_loc = GL.glGetUniformLocation(self._faces_program, "objectHasReflection")

        GL.glUniform3fv(view_position_loc, 1, self.camera.position.as_numpy)
        GL.glUniformMatrix4fv(projection_loc, 1, GL.GL_FALSE, projection_matrix)
        GL.glUniformMatrix4fv(view_loc, 1, GL.GL_FALSE, view_matrix)
        GL.glUniform1f(floor_y_loc, self.config.floor.ground_height)
        GL.glUniform1i(object_has_reflection_loc, int(self.config.floor.reflections.enable and self.config.floor.enable_floor_lock))

        GL.glUseProgram(self._edges_program)
        projection_loc = GL.glGetUniformLocation(self._edges_program, "projection")
        view_loc = GL.glGetUniformLocation(self._edges_program, "view")
        GL.glUniformMatrix4fv(projection_loc, 1, GL.GL_FALSE, projection_matrix)
        GL.glUniformMatrix4fv(view_loc, 1, GL.GL_FALSE, view_matrix)

        GL.glUseProgram(self._vertices_program)
        projection_loc = GL.glGetUniformLocation(self._vertices_program, "projection")
        view_loc = GL.glGetUniformLocation(self._vertices_program, "view")
        GL.glUniformMatrix4fv(projection_loc, 1, GL.GL_FALSE, projection_matrix)
        GL.glUniformMatrix4fv(view_loc, 1, GL.GL_FALSE, view_matrix)

        GL.glUseProgram(self._faces_program)

        self._scene_light.set(self._faces_program)
        self._headlight(self._faces_program)

        removed_objects = []
        objects_in_view = []

        for row in obj_data:
            ref_address = row[-1]

            obj_ref = ctypes.cast(ref_address, ctypes.py_object).value
            obj = obj_ref()

            if obj is None:
                try:
                    self._object_refs.remove(obj_ref)
                except ValueError:
                    pass

                removed_objects.append(row)

                continue

            objects_in_view.append(obj)

            obj.obj3d.render(self._faces_program, self._edges_program, self._vertices_program)

        GL.glUseProgram(0)
        self._objects_in_view = objects_in_view

        for row in removed_objects:
            for container in self._object_data:
                try:
                    container.remove(row)
                    break
                except ValueError:
                    continue

    @_debug.logfunc
    def _on_draw(self):
        self.context.acquire()
        w, h = self.GetSize()
        aspect = w / float(h)

        f_size = self.config.floor.grid.size ** 2

        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_PROGRAM_POINT_SIZE)
        GL.glLineWidth(2.0)

        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GLU.gluPerspective(65, aspect, 0.1, float(math.sqrt(f_size * f_size)))

        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

        self.camera.Set()

        if self._axis_overlay is not None:
            self.context.release()
            self._axis_overlay.set_angle((self.camera.position - self.camera.focal_position).inverse)
            self.context.acquire()

        objs = self._view_culling.cull(
            self._object_data, self.camera.frustum_normals,
            self.camera.frustum_distances, self.camera.position.as_numpy)

        self._draw_scene(objs)

        if self.config.focal_target.enable:
            GL.glUseProgram(self._faces_program)
            self._focal_target.obj3d.render(self._faces_program, self._edges_program, self._vertices_program)
            GL.glUseProgram(0)

        self.floor.render(self._floor_program)

        self.SwapBuffers()

        self.context.release()

    def take_snapshot(self):
        self.SetCurrent(self.context)

        # Get viewport size
        size = self.GetClientSize()
        width, height = size.width, size.height

        # Read pixels from OpenGL
        GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)
        data = GL.glReadPixels(0, 0, width, height, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)

        # Convert to numpy array and flip vertically (OpenGL origin is bottom-left)
        image_array = np.frombuffer(data, dtype=np.uint8)
        image_array = image_array.reshape((height, width, 3))
        image_array = np.flipud(image_array)

        # Create wx.Image from array
        image = wx.Image(width, height)
        image.SetData(image_array.tobytes())

        return wx.Bitmap(image)

