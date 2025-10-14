from mpl_toolkits.mplot3d import axes3d


from ..wrappers.decimal import Decimal as _decimal
from ..geometry import point as _point
from .. import bases
from ..wrappers import art3d
from ..wrappers import color as _color


class Box(bases.SetAngleBase, bases.GetAngleBase, bases.ContextBase):

    def __init__(self, point: _point.Point, length: _decimal, width: _decimal,
                 height: _decimal, color: _color.Color, edge_color: _color.Color):
        self._length = length
        self._width = width
        self._height = height
        
        self._center = point
        self._color = color
        self._edge_color = edge_color

        point.Bind(self._update_artist)
        color.Bind(self._update_artist)
        edge_color.Bind(self._update_artist)

        length = length / _decimal(2.0)
        width = width / _decimal(2.0)
        height = height / _decimal(2.0)
        
        # bottom is viewed from inside the cube
        # bottom bottom left
        self._corner1 = _point.Point(point.x - width, point.y - length, point.z - height)
        # bottom bottom right
        self._corner2 = _point.Point(point.x + width, point.y - length, point.z - height)
        # bottom top right
        self._corner3 = _point.Point(point.x + width, point.y + length, point.z - height)
        # bottom top left
        self._corner4 = _point.Point(point.x - width, point.y + length, point.z - height)

        # top is viewed from outide the cube
        # top bottom left
        self._corner5 = _point.Point(point.x - width, point.y - length, point.z + height)
        # top bottom right
        self._corner6 = _point.Point(point.x + width, point.y - length, point.z + height)
        # top top right
        self._corner7 = _point.Point(point.x + width, point.y + length, point.z + height)
        # top top left
        self._corner8 = _point.Point(point.x - width, point.y + length, point.z + height)
        
        self.artist = None
        self._verts = self._make_verts()

        self._x_angle = _decimal(0.0)
        self._y_angle = _decimal(0.0)
        self._z_angle = _decimal(0.0)

    def _make_verts(self):
        corners = [self._corner1, self._corner2, self._corner3, self._corner4, 
                   self._corner5, self._corner6, self._corner7, self._corner8]

        vertices = [[0, 1, 2, 3], [1, 5, 6, 2], [3, 2, 6, 7],
                    [4, 0, 3, 7], [5, 4, 7, 6], [4, 5, 1, 0]]

        return [[corners[vertices[ix][iy]] for iy in range(len(vertices[0]))] 
                for ix in range(len(vertices))]

    @property
    def center(self) -> _point.Point:
        return self._center

    @center.setter
    def center(self, value: _point.Point):
        self._center.UnBind(self._update_artist)

        for corner in (
            self._corner1, self._corner2, self._corner3, self._corner4,
            self._corner5, self._corner6, self._corner7, self._corner8
        ):
            corner -= self._center
            corner += value

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
        return self._edge_color

    @edge_color.setter
    def edge_color(self, value: _color.Color):
        self._edge_color.UnBind(self._update_artist)
        self._edge_color = value
        value.Bind(self._update_artist)
        self._update_artist()

    @property
    def length(self) -> _decimal:
        return self._length

    @length.setter
    def length(self, value: _decimal):
        new_length = value / _decimal(2.0)
        old_length = self._length / _decimal(2.0)

        self._corner1.y += old_length
        self._corner1.y -= new_length
        
        self._corner2.y += old_length
        self._corner2.y -= new_length

        self._corner3.y -= old_length
        self._corner3.y += new_length

        self._corner4.y -= old_length
        self._corner4.y += new_length

        self._corner5.y += old_length
        self._corner5.y -= new_length

        self._corner6.y += old_length
        self._corner6.y -= new_length

        self._corner7.y -= old_length
        self._corner7.y += new_length

        self._corner8.y -= old_length
        self._corner8.y += new_length

        self._length = value
        self._update_artist()

    @property
    def width(self) -> _decimal:
        return self._length

    @width.setter
    def width(self, value: _decimal):
        new_width = value / _decimal(2.0)
        old_width = self._width / _decimal(2.0)

        self._corner1.x += old_width
        self._corner1.x -= new_width
        
        self._corner2.x -= old_width
        self._corner2.x += new_width

        self._corner3.x -= old_width
        self._corner3.x += new_width

        self._corner4.x += old_width
        self._corner4.x -= new_width

        self._corner5.x += old_width
        self._corner5.x -= new_width

        self._corner6.x -= old_width
        self._corner6.x += new_width

        self._corner7.x -= old_width
        self._corner7.x += new_width

        self._corner8.x += old_width
        self._corner8.x -= new_width

        self._width = value
        self._update_artist()
        
    @property
    def height(self) -> _decimal:
        return self._height

    @height.setter
    def height(self, value: _decimal):
        new_height = value / _decimal(2.0)
        old_height = self._height / _decimal(2.0)

        self._corner1.z += old_height
        self._corner1.z -= new_height
        
        self._corner2.z += old_height
        self._corner2.z -= new_height

        self._corner3.z += old_height
        self._corner3.z -= new_height

        self._corner4.z += old_height
        self._corner4.z -= new_height

        self._corner5.z -= old_height
        self._corner5.z += new_height

        self._corner6.z -= old_height
        self._corner6.z += new_height

        self._corner7.z -= old_height
        self._corner7.z += new_height

        self._corner8.z -= old_height
        self._corner8.z += new_height

        self._height = value
        self._update_artist()

    def add_to_plot(self, axes: axes3d.Axes3D) -> None:
        if self.is_added:
            return

        verts = [[tuple(v) for v in vert] for vert in self._verts]
        self.artist = art3d.Poly3DCollection(verts, facecolors=self._color.matplotlib,
                                             edgecolor=self._edge_color.matplotlib, linewidths=1)

        self.artist.set_py_data(self)
        axes.add_collection3d(self.artist)

    @property
    def is_added(self) -> bool:
        return self.artist is not None

    def _update_artist(self) -> None:
        if not self.is_added:
            return

        if self._update_disabled:
            return

        verts = [[v.as_float for v in vert] for vert in self._verts]
        self.artist.set_verts(verts)

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, origin: "_point.Point"):
        corners = set([v for vert in self._verts for v in vert])

        for corner in list(corners):
            corner.set_angles(x_angle, y_angle, z_angle, self._center)

        self._x_angle = x_angle
        self._y_angle = y_angle
        self._z_angle = z_angle
        self._update_artist()

    def get_x_angle(self) -> _decimal:
        return self._x_angle

    def set_x_angle(self, angle: _decimal, _) -> None:
        corners = set([v for vert in self._verts for v in vert])

        with self:
            for corner in list(corners):
                corner.set_x_angle(angle, self._center)

        self._x_angle = angle
        self._update_artist()

    def get_y_angle(self) -> _decimal:
        return self._y_angle

    def set_y_angle(self, angle: _decimal, _) -> None:
        corners = set([v for vert in self._verts for v in vert])

        with self:
            for corner in list(corners):
                corner.set_y_angle(angle, self._center)

        self._y_angle = angle
        self._update_artist()

    def get_z_angle(self) -> _decimal:
        return self._z_angle

    def set_z_angle(self, angle: _decimal, _) -> None:
        corners = set([v for vert in self._verts for v in vert])

        with self:
            for corner in list(corners):
                corner.set_z_angle(angle, self._center)

        self._z_angle = angle
        self._update_artist()

    def move(self, point: _point.Point) -> None:
        corners = set([v for vert in self._verts for v in vert])
        with self:
            for corner in list(corners):
                corner += point

        self._center += point

    def hit_test(self, point: _point.Point) -> bool:
        corners = set([v for vert in self._verts for v in vert])
        x, y, z = point
        xs, ys, zs = zip(*list(corners))

        return min(xs) <= x <= max(xs) and min(ys) <= y <= max(ys) and min(zs) <= z <= max(zs)
