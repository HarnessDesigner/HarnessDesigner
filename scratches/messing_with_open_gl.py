import wx
from wx import glcanvas
from OpenGL.GL import *
from OpenGL.GLU import *
import math
from typing import Union

import wx

import numpy as np  # NOQA
from typing import Iterable as _Iterable  # NOQA
import math  # NOQA
import weakref  # NOQA
from decimal import Decimal as _Decimal  # NOQA
from scipy.spatial.transform import Rotation  # NOQA
import wx.lib.newevent  # NOQA


class Decimal(_Decimal):

    def __new__(cls, value, *args, **kwargs):
        if not isinstance(value, (str, Decimal)):
            value = str(float(value))

        return super().__new__(cls, value, *args, **kwargs)


_decimal = Decimal



def floor_tens(value):
    return _decimal(float(int(value * _decimal(10))) / 10.0)


def remap(value, old_min, old_max, new_min, new_max):
    old_range = old_max - old_min
    new_range = new_max - new_min
    new_value = (((value - old_min) * new_range) / old_range) + new_min
    return new_value



def angles_from_3_points(p1: "Point", p2: "Point") -> tuple[_decimal, _decimal, _decimal]:

    # to get the "roll" we need to have a directional vew we are looking from.
    # We always want that to be from a point looking down on the model. So we create
    # a 3rd point looking down with a z axis of 20 and then add the input
    # point that has the highest Z axis to it.
    p3 = Point(_decimal(0.0), _decimal(0.0), _decimal(20.0))

    if float(p1.z) > float(p2.z):
        p3 += p1
    else:
        p3 += p2

    # Convert to numpy arrays
    p1, p2, p3 = np.array(p1.as_float), np.array(p2.as_float), np.array(p3.as_float)

    # Direction vector (main axis)
    forward = p2 - p1
    forward /= np.linalg.norm(forward)

    # Temporary "up" vector
    up_temp = p3 - p1
    up_temp /= np.linalg.norm(up_temp)

    # Right vector (perpendicular to forward and up_temp)
    right = np.cross(up_temp, forward)
    right /= np.linalg.norm(right)

    # True up vector (recomputed to ensure orthogonality)
    up = np.cross(forward, right)

    # Build rotation matrix
    matrix = np.array([right, up, forward]).T  # 3x3 rotation matrix

    # Extract Euler angles (XYZ order)
    pitch = np.arctan2(-matrix[2, 1], matrix[2, 2])
    yaw = np.arctan2(matrix[1, 0], matrix[0, 0])
    roll = np.arctan2(matrix[2, 0],
                      np.sqrt(matrix[2, 1] ** 2 + matrix[2, 2] ** 2))

    pitch, yaw, roll = np.degrees([pitch, yaw, roll])
    return _decimal(pitch) + _decimal(90.0), _decimal(roll), _decimal(yaw) - _decimal(90.0)


class Point:
    _instances = {}

    @property
    def project_id(self):
        return self._project_id

    @property
    def point_id(self):
        return self._point_id

    def add_to_db(self, project_id, point_id):
        assert (project_id, point_id) not in self._instances, 'Sanity Check'

        self._instances[(project_id, point_id)] = weakref.ref(self, self._remove_instance)

    @classmethod
    def _remove_instance(cls, ref):
        for key, value in cls._instances.items():
            if ref == value:
                break
        else:
            return

        del cls._instances[key]

    def __init__(self, x: _decimal, y: _decimal, z: _decimal | None = None,
                 project_id: int | None = None, point_id: int | None = None):

        self._project_id = project_id
        self._point_id = point_id

        if z is None:
            z = _decimal(0.0)

        self._x = x
        self._y = y
        self._z = z

        self._callbacks = []
        self._cb_disabled = False

    def __enter__(self):
        self._cb_disabled = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cb_disabled = False
        self.__do_callbacks()

    def Bind(self, cb):
        for ref in self._callbacks[:]:
            if ref() is None:
                self._callbacks.remove(ref)
            elif ref() == cb:
                return False
        else:
            self._callbacks.append(weakref.WeakMethod(cb, self.__remove_ref))

        return True

    def Unbind(self, cb):
        for ref in self._callbacks[:]:
            if ref() is None:
                self._callbacks.remove(ref)
            elif ref() == cb:
                self._callbacks.remove(ref)
                break

    def __remove_ref(self, ref):
        if ref in self._callbacks:
            self._callbacks.remove(ref)

    @property
    def x(self) -> _decimal:
        return self._x

    @x.setter
    def x(self, value: _decimal):
        self._x = value
        self.__do_callbacks()

    @property
    def y(self) -> _decimal:
        return self._y

    @y.setter
    def y(self, value: _decimal):
        self._y = value
        self.__do_callbacks()

    @property
    def z(self) -> _decimal:
        return self._z

    @z.setter
    def z(self, value: _decimal):
        self._z = value
        self.__do_callbacks()

    def copy(self) -> "Point":
        return Point(_decimal(self._x), _decimal(self._y), _decimal(self._z))

    def __do_callbacks(self):
        if self._cb_disabled:
            return

        for ref in self._callbacks[:]:
            func = ref()
            if func is None:
                self._callbacks.remove(ref)
            else:
                func(self)

    def __iadd__(self, other: "Point"):
        x, y, z = other
        self.x += x
        self.y += y
        self.z += z

        self.__do_callbacks()

        return self

    def __add__(self, other: "Point") -> "Point":
        x1, y1, z1 = self
        x2, y2, z2 = other

        x = x1 + x2
        y = y1 + y2
        z = z1 + z2

        return Point(x, y, z)

    def __isub__(self, other: "Point"):
        x, y, z = other
        self.x -= x
        self.y -= y
        self.z -= z
        self.__do_callbacks()

        return self

    def __sub__(self, other: "Point") -> "Point":
        x1, y1, z1 = self
        x2, y2, z2 = other

        x = x1 - x2
        y = y1 - y2
        z = z1 - z2

        return Point(x, y, z)

    def __itruediv__(self, other: _decimal):
        self.x /= other
        self.y /= other
        self.z /= other

        self.__do_callbacks()

        return self

    def __truediv__(self, other: _decimal) -> "Point":
        x, y, z = self
        return Point(x / other, y / other, z / other)

    def set_x_angle(self, angle: _decimal, origin: "Point") -> None:
        self.set_angles(angle, _decimal(0.0), _decimal(0.0), origin)

    def set_y_angle(self, angle: _decimal, origin: "Point") -> None:
        self.set_angles(_decimal(0.0), angle, _decimal(0.0), origin)

    def set_z_angle(self, angle: _decimal, origin: "Point") -> None:
        self.set_angles(_decimal(0.0), _decimal(0.0), angle, origin)

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, origin: "Point") -> None:

        R = Rotation.from_euler('xyz',
                                [x_angle, y_angle, z_angle], degrees=True)

        p1 = self.as_numpy
        p2 = origin.as_numpy

        p1 -= p2
        p1 = R.apply(p1.T).T
        p1 += p2
        self._x, self._y, self._z = [_decimal(float(item)) for item in p1]
        self.__do_callbacks()

    def __eq__(self, other: "Point") -> bool:
        x1, y1, z1 = self
        x2, y2, z2 = other

        return x1 == x2 and y1 == y2 and z1 == z2

    def __ne__(self, other: "Point") -> bool:
        return not self.__eq__(other)

    @property
    def as_float(self):
        return float(self._x), float(self._y), float(self._z)

    @property
    def as_int(self):
        return int(self._x), int(self._y), int(self._z)

    @property
    def as_numpy(self):
        return np.array(self.as_float, dtype=float)

    def __iter__(self):
        yield self._x
        yield self._y
        yield self._z

    def __str__(self):
        return f'X: {self.x}, Y: {self.y}, Z: {self.z}'


class Line:

    def __init__(self, p1: Point,
                 p2: Point | None = None,
                 length: _decimal | None = None,
                 x_angle: _decimal | None = None,
                 y_angle: _decimal | None = None,
                 z_angle: _decimal | None = None):

        self._p1 = p1

        if p2 is None:
            if None in (length, x_angle, y_angle, z_angle):
                raise ValueError('If an end point is not supplied then the "length", '
                                 '"x_angle", "y_angle" and "z_angle" parameters need to be supplied')

            p2 = Point(length, _decimal(0.0), _decimal(0.0))
            p2 += p1

            p2.set_angles(x_angle, y_angle, z_angle, p1)

        self._p2 = p2

    def copy(self) -> "Line":
        p1 = self._p1.copy()
        p2 = self._p2.copy()
        return Line(p1, p2)

    @property
    def p1(self) -> Point:
        return self._p1

    @property
    def p2(self) -> Point:
        return self._p2

    def __len__(self) -> int:
        res = math.sqrt((self._p2.x - self._p1.x) ** _decimal('2') +
                        (self._p2.y - self._p1.y) ** _decimal('2') +
                        (self._p2.z - self._p1.z) ** _decimal('2'))

        return int(round(res))

    def length(self) -> _decimal:
        return _decimal(math.sqrt((self._p2.x - self._p1.x) ** _decimal(2) +
                        (self._p2.y - self._p1.y) ** _decimal(2) +
                        (self._p2.z - self._p1.z) ** _decimal(2)))

    def get_x_angle(self) -> _decimal:
        return angles_from_3_points(self._p1, self._p2)[0]

    def get_y_angle(self) -> _decimal:
        return angles_from_3_points(self._p1, self._p2)[1]

    def get_z_angle(self) -> _decimal:
        return angles_from_3_points(self._p1, self._p2)[2]

    def get_angles(self):
        return angles_from_3_points(self._p1, self._p2)

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal,
                   origin: Point | None = None) -> None:

        if origin is None:
            origin = self.center

        if origin != self.p1 and origin != self.p2:
            self.p1.set_angles(x_angle, y_angle, z_angle, origin)
            self.p2.set_angles(x_angle, y_angle, z_angle, origin)
        elif origin != self.p1:
            self.p1.set_angles(x_angle, y_angle, z_angle, origin)
        else:
            self.p2.set_angles(x_angle, y_angle, z_angle, origin)

    def set_x_angle(self, angle: _decimal, origin: Point | None = None) -> None:
        self.set_angles(angle, _decimal(0.0), _decimal(0.0), origin)

    def set_y_angle(self, angle: _decimal, origin: Point | None = None) -> None:
        self.set_angles(_decimal(0.0), angle, _decimal(0.0), origin)

    def set_z_angle(self, angle: _decimal, origin: Point | None = None) -> None:
        self.set_angles(_decimal(0.0), _decimal(0.0), angle, origin)

    @property
    def center(self) -> Point:
        return Point(
            self._p1.x + (self._p1.x - self._p2.x),
            self._p1.y + (self._p1.y - self._p2.y),
            self._p1.z + (self._p1.z - self._p2.z)
        )

    def __iter__(self):
        yield self._p1
        yield self._p2

res = [
    [
        _decimal(10.2),
        _decimal(20.0),
        _decimal(45.0),
        _decimal(22.5),
        Point(_decimal(0.0), _decimal(0.0), _decimal(0.0)),
        _decimal(-180.0),
        Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
    ],
    [
        _decimal(10.2),
        _decimal(20.0),
        _decimal(45.0),
        _decimal(22.5),
        Point(_decimal(0.0), _decimal(0.0), _decimal(0.0)),
        _decimal(0.0),
        Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
    ],
    [
        _decimal(10.2),
        _decimal(20.0),
        _decimal(45.0),
        _decimal(22.5),
        Point(_decimal(0.0), _decimal(0.0), _decimal(0.0)),
        _decimal(90.0),
        Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
    ]
]


def get_clicked_location(x, y):
    vport = glGetIntegerv(GL_VIEWPORT)
    mvmatrix = glGetDoublev(GL_MODELVIEW_MATRIX)
    projmatrix = glGetDoublev(GL_PROJECTION_MATRIX)
    realy = vport[3] - y

    depth = glReadPixels(x, realy, 1, 1, GL_DEPTH_COMPONENT, GL_FLOAT)

    worldCoordinate1 = gluUnProject(x, realy, depth, mvmatrix, projmatrix, vport)

    print(worldCoordinate1)


class Frame(wx.Frame):

    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, size=(800, 600))

        canvas = Canvas(self)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(canvas, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND)

        self.SetSizer(vsizer)


class Canvas(glcanvas.GLCanvas):

    def __init__(self, parent):
        glcanvas.GLCanvas.__init__(self, parent, -1)
        self.init = False
        self.context = glcanvas.GLContext(self)

        # Initial mouse position.
        self.lastx = self.x = 30
        self.lasty = self.y = 30
        self.size = None
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnMouseUp)
        self.Bind(wx.EVT_MOTION, self.OnMouseMotion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self._scale = 1.0


        # p = Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))

        # hemi = Hemisphere(p, _decimal(2.16578), (0.4, 0.4, 0.4, 1.0), _decimal(1.67954))
        # hemi.add_to_plot(self.axes)
        # self.hemi = hemi
        self.objects = [Transition(1, Point(_decimal(0.0), _decimal(0.0), _decimal(0.0)), res)]

    def OnEraseBackground(self, event):
        pass  # Do nothing, to avoid flashing on MSW.

    def OnSize(self, event):
        wx.CallAfter(self.DoSetViewport)
        event.Skip()

    def DoSetViewport(self):
        size = self.size = self.GetClientSize() * self.GetContentScaleFactor()
        self.SetCurrent(self.context)
        glViewport(0, 0, size.width, size.height)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        self.SetCurrent(self.context)
        if not self.init:
            self.InitGL()
            self.init = True
        self.OnDraw()

    def OnMouseDown(self, event):
        if self.HasCapture():
            self.ReleaseMouse()
        self.CaptureMouse()
        self.x, self.y = self.lastx, self.lasty = event.GetPosition()

        get_clicked_location(self.x, self.y)

    def OnMouseUp(self, event):
        if self.HasCapture():
            self.ReleaseMouse()

    def OnMouseMotion(self, event):
        if event.Dragging() and event.LeftIsDown():
            self.lastx, self.lasty = self.x, self.y
            self.x, self.y = event.GetPosition()
            self.Refresh(False)

    def InitGL(self):
        glMatrixMode(GL_PROJECTION)
        # Camera frustrum setup.
        glFrustum(-0.5, 0.5, -0.5, 0.5, 1.0, 3.0)
        # glMaterial(GL_FRONT, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        # glMaterial(GL_FRONT, GL_DIFFUSE, [0.2, 0.2, 0.2, 1.0])
        # glMaterial(GL_FRONT, GL_SPECULAR, [0.2, 0.0, 0.2, 1.0])
        # glMaterial(GL_FRONT, GL_SHININESS, 50.0)
        # glLight(GL_LIGHT0, GL_AMBIENT, [1.0, 1.0, 1.0, 0.5])
        # glLight(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
        # glLight(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
        # glLight(GL_LIGHT0, GL_POSITION, [1.0, 1.0, 1.0, 0.0])
        # glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        # glEnable(GL_LIGHTING)
        # glEnable(GL_LIGHT0)
        glLight(GL_LIGHT0, GL_POSITION, (5, 5, 5, 1))  # point light from the left, top, front
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0, 0, 0, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.1, 0.1, 0.1, 1))
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_ALWAYS)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glClearColor(0.9, 0.9, 0.9, 1.0)
        # glutPostRedisplay()
        # Position viewer.
        glMatrixMode(GL_MODELVIEW)
        # Position viewer.
        glTranslatef(0.0, 0.0, -3.0)

        print('init_gl')

    def on_mouse_wheel(self, evt: wx.MouseEvent):
        self._scale += evt.GetWheelRotation() / 10000.0
        if self._scale < 0.01:
            self._scale = 0.01

        print(self._scale)

        def _do():
            self.Update()
            self.Refresh()

        wx.CallAfter(_do)
        evt.Skip()

    def OnDraw(self):
        # Clear color and depth buffers.
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        # Use a fresh transformation matrix.

        glPushMatrix()
        # Position object.
        ## glTranslate(0.0, 0.0, -2.0)
        glRotate(30.0, 1.0, 0.0, 0.0)
        glRotate(30.0, 0.0, 1.0, 0.0)

        glTranslate(0, -1, 0)
        glRotate(250, 1, 0, 0)

        glEnable(GL_BLEND)
        glEnable(GL_POLYGON_SMOOTH)
        glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, (0.5, 0.5, 1.0, 0.5))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 1.0)
        glShadeModel(GL_FLAT)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        # glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glScalef(self._scale, self._scale, self._scale)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        for artist in self.objects:
            glEnable(GL_LIGHTING)
            glEnable(GL_LIGHT0)
            glEnable(GL_COLOR_MATERIAL)
            glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

            artist.draw()

            glDisable(GL_LIGHT0)
            glDisable(GL_LIGHTING)
            glDisable(GL_COLOR_MATERIAL)

        print('on draw')

        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)

        glPopMatrix()
        glRotatef((self.y - self.lasty), 0.0, 0.0, 1.0)
        glRotatef((self.x - self.lastx), 1.0, 0.0, 0.0)
        # Push into visible buffer.
        self.SwapBuffers()


class Transition:
    def __init__(self, id, location, data):
        self.id = id
        self.data = data
        self.wxid = wx.NewIdRef()
        self.objs = []
        self._selected = False
        self._coord_adj = None
        self._last_mouse_pos = None
        self._branch_mode = False

        self.branches = []

        origin = Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
        bulb_offset_apex = None

        for i, (min_dia, max_dia, length, bulb_length, bulb_offset, angle, offset) in enumerate(data):

            if bulb_length:
                if bulb_offset_apex is not None:
                    cyl_1_p1 = Point(bulb_offset_apex - (max_dia * _decimal(0.75)), _decimal(0.0), _decimal(0.0))
                    factor = bulb_length / length
                    b_length = length - bulb_offset_apex + (max_dia / _decimal(2.0)) * factor
                else:
                    cyl_1_p1 = bulb_offset
                    b_length = bulb_length

                cyl1 = Cylinder(cyl_1_p1, b_length - (max_dia / _decimal(2.0)), max_dia, (0.2, 0.2, 0.2, 1.0), None)
                self.objs.append(cyl1)

                if bulb_offset.x or bulb_offset.y:
                    h_sphere1 = Hemisphere(cyl1.p1, max_dia, (0.2, 0.2, 0.2, 1.0), _decimal(0.0))
                    h_sphere1.set_y_angle(_decimal(90.0), h_sphere1.center)
                    self.objs.append(h_sphere1)

                if i == 0:
                    cyl1.set_z_angle(angle, cyl1.p1)
                else:
                    cyl1.set_z_angle(angle, origin)

                h_sphere2 = Hemisphere(cyl1.p2, max_dia, (0.2, 0.2, 0.2, 1.0), min_dia)
                h_sphere2.set_y_angle(_decimal(90.0), h_sphere2.center)
                h_sphere2.set_z_angle(angle, h_sphere2.center)

                self.objs.append(h_sphere2)

                cyl2 = Cylinder(h_sphere2.hole_center, length - bulb_length + (max_dia / _decimal(2.0)), min_dia, (0.2, 0.2, 0.2, 1.0), None)

                cyl2.set_z_angle(angle, cyl2.p1)
                self.objs.append(cyl2)

                if bulb_offset.x or bulb_offset.y:
                    apex = h_sphere1.center.copy() + Point(h_sphere1.diameter / _decimal(2.0), _decimal(0.0), _decimal(0.0))

                    # bulb_offset.x -= max_dia / _decimal(2.0)
                    # bulb_length -= max_dia / _decimal(2.0)
                    bulb_offset_apex = apex.x

                self.branches.append(dict(id=i+1, cylinder=cyl2, min_dia=min_dia,
                                          max_dia=max_dia, set_dia=min_dia,
                                          hemisphere=h_sphere2, is_connected=False))

        points = []

        for obj in self.objs:
            if isinstance(obj, Cylinder):
                if obj.p1 not in points:
                    obj.p1 += location
                    points.append(obj.p1)
                if obj.p2 not in points:
                    obj.p2 += location
                    points.append(obj.p2)
            else:
                if obj.center not in points:
                    obj.center += location
                    points.append(obj.center)

        self.origin = location
        self.update_count = 0
        self.verts = None
        self.normals = None
        self.x = None
        self.y = None
        self.z = None
        self.color = (0.2, 0.2, 0.2)

        for obj in self.objs:
            obj.add_to_plot(self)

    def set_verts(self, x: np.ndarray, y: np.ndarray, z: np.ndarray):

        print(self.update_count)
        print('X:')
        print(x.tolist())
        print()
        print('Y:')
        print(y.tolist())
        print()
        print('Z:')
        print(z.tolist())
        print()
        print()

        if self.update_count == 0:
            self.x = x.flatten().tolist()
            self.y = y.flatten().tolist()
            self.z = z.flatten().tolist()
            self.update_count = 1
        else:
            self.x.extend(x.flatten().tolist())
            self.y.extend(y.flatten().tolist())
            self.z.extend(z.flatten().tolist())

            self.update_count += 1

            if self.update_count == len(self.objs):

                x = np.array(self.x, dtype=float)
                y = np.array(self.y, dtype=float)
                z = np.array(self.z, dtype=float)

                # Flatten into vertex array
                vertices = np.stack((x, y, z), axis=-1).astype(np.float32)
                normals = vertices / np.linalg.norm(vertices, axis=-1, keepdims=True)

                # Build triangles between stacks/slices
                v1 = vertices[:-1, :-1]
                v2 = vertices[1:, :-1]
                v3 = vertices[1:, 1:]
                v4 = vertices[:-1, 1:]

                n1 = normals[:-1, :-1]
                n2 = normals[1:, :-1]
                n3 = normals[1:, 1:]
                n4 = normals[:-1, 1:]

                # Two triangles per quad
                v_triangles = np.concatenate(
                    [np.stack((v1, v2, v3), axis=2),
                     np.stack((v1, v3, v4), axis=2)], axis=2
                )
                n_triangles = np.concatenate(
                    [np.stack((n1, n2, n3), axis=2),
                     np.stack((n1, n3, n4), axis=2)], axis=2
                )

                self.verts = v_triangles.reshape(-1, 3)
                self.normals = n_triangles.reshape(-1, 3)

                self.update_count = 0

    def plot_surface(self, *_, **__):
        return self

    def draw(self):
        if self.verts is None:
            return

        glColor3f(*self.color)
        glVertexPointer(3, GL_FLOAT, 0, self.verts)
        glNormalPointer(GL_FLOAT, 0, self.normals)
        glDrawArrays(GL_TRIANGLES, 0, len(self.verts))


class Hemisphere:

    def __init__(self, center: Point, diameter: _decimal, color, hole_diameter: _decimal | None):
        center.Bind(self._update_artist)
        self._center = center
        self._diameter = diameter
        self._color = color
        self._saved_color = self._color
        self.artist = None
        self._verts = None

        self._x_angle = _decimal(0.0)
        self._y_angle = _decimal(0.0)
        self._z_angle = _decimal(0.0)

        self._sections = int((_decimal(1.65) /
                             (_decimal(9.0) /
                             (diameter ** (_decimal(1.0) / _decimal(6.0))))) *
                             _decimal(100.0))

        self._hole_diameter = hole_diameter
        self._hole_center = None
        self._hc = None


    @property
    def hole_diameter(self) -> _decimal | None:
        return self._hole_diameter

    @hole_diameter.setter
    def hole_diameter(self, value: _decimal | None):
        self._hole_diameter = value
        self._verts = None

        self._update_artist()

    def set_selected_color(self, flag):
        if flag:
            self.color = (0.6, 0.2, 0.2, 1.0)
        else:
            self.color = self._saved_color

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value: tuple[float, float, float, float]):
        self._color = value
        self._update_artist()

    @property
    def center(self) -> Point:
        return self._center

    @center.setter
    def center(self, value: Point):
        if not value.Bind(self._update_artist):
            if value != self._center:
                raise RuntimeError('sanity check')

            return

        self._center.Unbind(self._update_artist)
        self._center = value
        self._update_artist()

    @property
    def diameter(self) -> _decimal:
        return self._diameter

    @diameter.setter
    def diameter(self, value: _decimal):
        self._diameter = value
        self._sections = int((_decimal(1.65) /
                             (_decimal(9.0) /
                             (value ** (_decimal(1.0) / _decimal(6.0))))) *
                             _decimal(100.0))

        self._verts = None
        self._update_artist()

    @property
    def is_added(self) -> bool:
        return self.artist is not None

    def move(self, point: Point) -> None:
        self._center += point

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, origin: Point):
        if origin != self.center:
            self._center.set_angles(x_angle, y_angle, z_angle, origin)
            return

        self._x_angle = x_angle
        self._y_angle = y_angle
        self._z_angle = z_angle
        self._update_artist()

    def set_x_angle(self, angle: _decimal, origin: Point) -> None:
        if origin != self._center:
            self.set_angles(angle, _decimal(0.0), _decimal(0.0), origin)
        else:
            self.set_angles(angle, self._y_angle, self._z_angle, origin)

    def set_y_angle(self, angle: _decimal, origin: Point) -> None:
        if origin != self._center:
            self.set_angles(_decimal(0.0), angle, _decimal(0.0), origin)
        else:
            self.set_angles(self._x_angle, angle, self._z_angle, self._center)

    def set_z_angle(self, angle: _decimal, origin: Point) -> None:
        if origin != self._center:
            self.set_angles(_decimal(0.0), _decimal(0.0), angle, origin)
        else:
            self.set_angles(self._x_angle, self._y_angle, angle, origin)

    def get_angles(self) -> tuple[_decimal, _decimal, _decimal]:
        return self._x_angle, self._y_angle, self._z_angle

    def _get_verts(self) -> tuple[np.ndarray, np.ndarray]:
        if self._verts is None:
            radius = float(self._diameter / _decimal(2.0))

            theta = np.linspace(0, np.pi / 2, 41)  # polar angle (0..pi/2)
            phi = np.linspace(0, 2 * np.pi, 81)    # azimuth angle (0..2pi)

            theta, phi = np.meshgrid(theta, phi)

            # Cartesian coordinates
            X = radius * np.sin(theta) * np.cos(phi)
            Y = radius * np.sin(theta) * np.sin(phi)
            Z = radius * np.cos(theta)

            if self._hole_diameter:
                hole_dia = float(self._hole_diameter / _decimal(2.0) / _decimal(1.15))

                mask = np.sqrt(X ** 2 + Y ** 2) > hole_dia
                X = np.where(mask, X, np.nan)
                Y = np.where(mask, Y, np.nan)
                Z = np.where(mask, Z, np.nan)

                z_max = np.nanmax(Z.flatten())
                self._hc = Point(_decimal(0.0), _decimal(0.0), z_max)

            # local_points = np.vstack((X.flatten(), Y.flatten(), Z.flatten()))
            # print('vert1')
            # print(local_points)
            #
            # local_points = local_points[~np.isnan(local_points)]
            # print()
            # print('vert2')
            # print(local_points)
            # print()
            # print()

            self._verts = [X, Y, Z]

        x, y, z = self._verts

        x_angle, y_angle, z_angle = self.get_angles()
        R = Rotation.from_euler('xyz',
                                [x_angle, y_angle, z_angle], degrees=True)
        local_points = np.vstack((x.flatten(), y.flatten(), z.flatten()))
        rp = R.apply(local_points.T).T

        origin = self._center.as_float

        # Translate to start point
        X = rp[0].reshape(x.shape) + origin[0]
        Y = rp[1].reshape(y.shape) + origin[1]
        Z = rp[2].reshape(z.shape) + origin[2]

        if self._hc is None:
            hole_center = self._center
        else:
            local_points = self._hc.as_numpy
            rp = R.apply(local_points.T).T

            origin = np.array(origin, dtype=float)

            new_point = rp + origin
            hole_center = Point(*[_decimal(float(item)) for item in new_point])

        if self._hole_center is None:
            self._hole_center = hole_center
        elif self._hole_center != hole_center:
            hc = self._hole_center
            diff = hole_center - hc
            hc += diff

        return X, Y, Z

    @property
    def hole_center(self):
        if self._hole_center is None:
            _ = self._get_verts()

        return self._hole_center

    def _update_artist(self, *_) -> None:
        if not self.is_added:
            return

        self.artist.set_verts(*self._get_verts())

    def add_to_plot(self, axes) -> None:
        if self.is_added:
            return

        # we create an empty artist and then update the artist due to a bug in
        # matplotlib that causes the shading to not get rendered when updating
        # the color. We want the shading light source to be the same all the time.
        # To save some processor time we do the work of calculating the verts
        # only a single time.
        self.artist = axes.plot_surface(color=self._color)
        self._update_artist()

    def set_py_data(self, py_data):
        if not self.is_added:
            raise ValueError('sanity check')

        self.artist.set_py_data(py_data)


class Artist:

    def __init__(self, color, renderer):
        self.vertices = None
        self.normals = None
        self.color = color
        self.renderer = renderer

    def set_verts(self, verts, normals):
        self.vertices = verts
        self.normals = normals

        print(verts)
        print()
        print(normals)
        print()
        print()

    def set_color(self, color):
        self.color = color

    def set_py_data(self, value):
        pass

    def draw(self):
        if self.vertices is None:
            return

        glColor3f(*self.color[:-1])
        glVertexPointer(3, GL_FLOAT, 0, self.vertices)
        glNormalPointer(GL_FLOAT, 0, self.normals)
        glDrawArrays(GL_TRIANGLES, 0, len(self.vertices))


class Renderer:

    def __init__(self, canvas):
        self.canvas = canvas
        self.artists = []

    def draw_idle(self):
        self.canvas.Update()
        self.canvas.Refresh()

    def plot_surface(self, color):
        artist = Artist(color, self)

        self.artists.append(artist)

        return artist


class Cylinder:

    def __init__(self, start: Point, length, diameter: _decimal, primary_color, edge_color, p2=None):
        start.Bind(self._update_artist)
        self._primary_color = primary_color
        self._saved_color = self._primary_color
        self._edge_color = edge_color
        self._p1 = start
        self._p2 = p2
        self._length = length
        self._diameter = diameter

        self._update_disabled = False
        self.artist = None
        self._show = True
        self._verts = None

        if p2 is not None:
            p2.Bind(self._update_artist)

    @property
    def p1(self) -> Point:
        return self._p1

    @p1.setter
    def p1(self, value: Point):
        if not value.Bind(self._update_artist):
            if value != self._p1:
                raise RuntimeError('sanity check')

            return

        self._p1.Unbind(self._update_artist)
        self._p1 = value
        self._verts = None
        self._update_artist()

    @property
    def p2(self) -> Point:
        if self._p2 is None:
            self._p2 = Point(_decimal(self._length), _decimal(0.0), _decimal(0.0))
            self._p2 += self._p1
            self._p2.Bind(self._update_artist)

        return self._p2

    @p2.setter
    def p2(self, value: Point):
        if not value.Bind(self._update_artist):
            if value != self._p2:
                raise RuntimeError('sanity check')

            return

        if self._p2 is not None:
            self._p2.Unbind(self._update_artist)

        print('P1:', self.p1)
        print('P2:', self.p2)

        self._p2 = value
        self._verts = None
        self._update_artist()

    @property
    def color(self):
        return self._primary_color

    @color.setter
    def color(self, value):
        self._primary_color = value
        self._update_artist()

    def set_selected_color(self, flag):
        if flag:
            self.color = (0.6, 0.2, 0.2, 1.0)
        else:
            self.color = self._saved_color

    def set_connected_color(self, flag):
        if flag:
            self.color = (0.2, 0.6, 0.2, 1.0)
        else:
            self.color = self._saved_color

    @property
    def is_added(self) -> bool:
        return self.artist is not None

    def show(self) -> None:
        self.artist.set_visible(True)

    def hide(self) -> None:
        self.artist.set_visible(False)

    def _update_artist(self, p=None) -> None:
        if not self.is_added:
            return

        if p is not None:
            self._verts = None

        self.artist.set_verts(*self._get_verts())

    @property
    def diameter(self) -> _decimal:
        return self._diameter

    @diameter.setter
    def diameter(self, value: _decimal):
        self._diameter = value
        self._verts = None
        self._update_artist()

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, origin: Point) -> None:
        line = Line(self._p1, self.p2)
        line.set_angles(x_angle, y_angle, z_angle, origin)

    def get_angles(self):
        x, y, z = angles_from_3_points(self._p1, self.p2)
        return x, y, z

    def get_x_angle(self) -> _decimal:
        return angles_from_3_points(self._p1, self.p2)[0]

    def get_y_angle(self) -> _decimal:
        return angles_from_3_points(self.p1, self.p2)[1]

    def get_z_angle(self) -> _decimal:
        return angles_from_3_points(self._p1, self.p2)[2]

    def set_x_angle(self, angle: _decimal, origin: Point) -> None:
        line = Line(self._p1, self.p2)
        line.set_x_angle(angle, origin)

    def set_y_angle(self, angle: _decimal, origin: Point) -> None:
        line = Line(self._p1, self.p2)
        line.set_y_angle(angle, origin)

    def set_z_angle(self, angle: _decimal, origin: Point) -> None:
        line = Line(self._p1, self.p2)
        line.set_z_angle(angle, origin)

    @property
    def length(self):
        line = Line(self._p1, self.p2)
        length = line.length()
        return round(length, 1)

    def move(self, point: Point) -> None:
        self._p1 += point
        self.p2 += point

    def _get_verts(self):
        if self._verts is None:
            length = float(self.length)
            radius = float(self._diameter / _decimal(2.0))

            theta = np.linspace(0, 2 * np.pi, 80)
            z = np.linspace(0, length, 80)
            theta_grid, z_grid = np.meshgrid(theta, z)

            x = radius * np.cos(theta_grid)
            y = radius * np.sin(theta_grid)
            z = z_grid

            # Stack local coordinates
            local_points = np.vstack((x.flatten(), y.flatten(), z.flatten()))

            # Rotation from Euler angles
            R = Rotation.from_euler('xyz',
                                    [0.0, 90.0, 0.0], degrees=True)
            rp = R.apply(local_points.T).T

            # Translate to start point
            X = rp[0].reshape(x.shape)
            Y = rp[1].reshape(y.shape)
            Z = rp[2].reshape(z.shape)

            self._verts = [X, Y, Z]

        x, y, z = self._verts

        x_angle, y_angle, z_angle = self.get_angles()
        R = Rotation.from_euler('xyz',
                                [x_angle, y_angle, z_angle], degrees=True)
        local_points = np.vstack((x.flatten(), y.flatten(), z.flatten()))
        rp = R.apply(local_points.T).T

        origin = self._p1.as_float

        # Translate to start point
        X = rp[0].reshape(x.shape) + origin[0]
        Y = rp[1].reshape(y.shape) + origin[1]
        Z = rp[2].reshape(z.shape) + origin[2]

        return X, Y, Z

    def add_to_plot(self, axes) -> None:
        if self.is_added:
            return

        # we create an empty artist and then update the artist due to a bug in
        # matplotlib that causes the shading to not get rendered when updating
        # the color. We want the shading light source to be the same all the time.
        # To save some processor time we do the work of calculating the verts
        # only a single time.
        self.artist = axes.plot_surface(self._primary_color)
        self._update_artist()

    def set_py_data(self, py_data):
        if not self.is_added:
            raise ValueError('sanity check')

        self.artist.set_py_data(py_data)



app = wx.App()

frame = Frame()
frame.Show()

app.MainLoop()
