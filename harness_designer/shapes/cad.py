import os
import numpy as np
from mpl_toolkits.mplot3d import axes3d


from ..wrappers.decimal import Decimal as _decimal
from ..geometry import point as _point
from .. import bases
from ..wrappers import color as _color
from ..wrappers import art3d


stl = __import__('stl')
mesh = __import__('stl', fromlist=['mesh'])


class CAD(bases.SetAngleBase, bases.GetAngleBase, bases.ContextBase):

    def __init__(self, point: _point.Point, length: _decimal, width: _decimal,
                 height: _decimal, color: _color.Color, shade: bool, filename: str):

        self._length = length
        self._width = width
        self._height = height
        self._shade = shade
        self._filename = filename

        self._center = point
        self._color = color
        self._original_vect = None

        point.Bind(self._update_artist)
        color.Bind(self._update_artist)

        self.artist = None
        self._x_angle = _decimal(0.0)
        self._y_angle = _decimal(0.0)
        self._z_angle = _decimal(0.0)

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, value):
        self._filename = value
        self._original_vect = self._get_mesh()
        self._update_artist()

    @property
    def center(self) -> _point.Point:
        return self._center

    @center.setter
    def center(self, value: _point.Point):
        self._center.UnBind(self._update_artist)

        self._center = value

        value.Bind(self._update_artist)
        self._update_artist()

    @property
    def color(self) -> _color.Color:
        return self._color

    @color.setter
    def color(self, value: _color.Color):
        self._color.UnBind(self._update_artist)
        self._color = value
        value.Bind(self._update_artist)
        self._update_artist()

    @property
    def edge_color(self) -> _color.Color:
        return None

    @edge_color.setter
    def edge_color(self, value: _color.Color):
        pass

    @property
    def length(self) -> _decimal:
        return self._length

    @length.setter
    def length(self, value: _decimal):
        pass

    @property
    def width(self) -> _decimal:
        return self._length

    @width.setter
    def width(self, value: _decimal):
        pass

    @property
    def height(self) -> _decimal:
        return self._height

    @height.setter
    def height(self, value: _decimal):
        pass

    def _get_mesh(self):
        if self._filename.endswith('.3mf'):
            for m in stl.Mesh.from_3mf_file(self._filename):
                return m.vectors

        elif self._filename.endswith('.stl'):
            m = mesh.Mesh.from_file(self._filename)
            return m.vectors

        else:
            raise ValueError(
                f'Unsupported file type "{os.path.splitext(self._filename)[-1][1:]}"')

    @property
    def _vect(self):
        x_angle = np.radians(float(self._x_angle))
        y_angle = np.radians(float(self._y_angle))
        z_angle = np.radians(float(self._z_angle))

        Rx = np.array(
            [[1, 0, 0],
             [0, np.cos(x_angle), -np.sin(x_angle)],
             [0, np.sin(x_angle), np.cos(x_angle)]]
        )

        Ry = np.array(
            [[np.cos(y_angle), 0, np.sin(y_angle)],
             [0, 1, 0],
             [-np.sin(y_angle), 0, np.cos(y_angle)]]
        )

        Rz = np.array(
            [[np.cos(z_angle), -np.sin(z_angle), 0],
             [np.sin(z_angle), np.cos(z_angle), 0],
             [0, 0, 1]]
        )

        R = Rz @ Ry @ Rx
        xyz = np.array(self._center.as_float, dtype=float)

        vect = (self._original_vect @ R) + xyz

        return vect

    def add_to_plot(self, axes: axes3d.Axes3D) -> None:
        if self.is_added:
            return

        self._original_vect = self._get_mesh()

        self.artist = art3d.Poly3DCollection(self._vect, facecolors=self._color.matplotlib,
                                             shade=self._shade, linewidth=0.001,
                                             antialiaseds=False)
        axes.add_collection3d(self.artist)

    def set_py_data(self, py_data):
        if not self.is_added:
            raise ValueError('sanity check')

        self.artist.set_py_data(py_data)

    @property
    def is_added(self) -> bool:
        return self.artist is not None

    def _update_artist(self) -> None:
        if not self.is_added:
            return

        self.artist.set_verts(self._vect)

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, _) -> None:
        self._x_angle = x_angle
        self._y_angle = y_angle
        self._z_angle = z_angle
        self._update_artist()

    def get_x_angle(self) -> _decimal:
        return self._x_angle

    def set_x_angle(self, angle: _decimal, _) -> None:
        self._x_angle = angle
        self._update_artist()

    def get_y_angle(self) -> _decimal:
        return self._y_angle

    def set_y_angle(self, angle: _decimal, _) -> None:
        self._y_angle = angle
        self._update_artist()

    def get_z_angle(self) -> _decimal:
        return self._z_angle

    def set_z_angle(self, angle: _decimal, _) -> None:
        self._z_angle = angle
        self._update_artist()

    def move(self, point: _point.Point) -> None:
        self._center += point

    def hit_test(self, point: _point.Point) -> bool:
        x, y, z = point

        length = self._length / _decimal(2.0)
        width = self._width / _decimal(2.0)
        height = self._height / _decimal(2.0)

        c = self._center

        x1 = c.x - length
        x2 = c.x + length

        y1 = c.y - width
        y2 = c.y + width

        z1 = c.z - height
        z2 = c.z + height

        return x1 <= x <= x2 and y1 <= y <= y2 and z1 <= z <= z2
