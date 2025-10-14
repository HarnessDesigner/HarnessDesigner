from mpl_toolkits.mplot3d import axes3d


from ..wrappers.decimal import Decimal as _decimal
from ..geometry import point as _point
from .. import bases
from ..wrappers import art3d
from ..wrappers import color as _color


class Cube(bases.SetAngleBase, bases.GetAngleBase, bases.ContextBase):

    def __init__(self, point: _point.Point, size: _decimal, color: _color.Color, edge_color: _color.Color):
        self._size = size
        self._center = point
        self._color = color
        self._edge_color = edge_color

        point.Bind(self._update_artist)
        color.Bind(self._update_artist)
        edge_color.Bind(self._update_artist)

        size = size / _decimal(2.0)

        # bottom is viewed from inside the cube
        # bottom bottom left
        corner1 = _point.Point(point.x - size, point.y - size, point.z - size)
        # bottom bottom right
        corner2 = _point.Point(point.x + size, point.y - size, point.z - size)
        # bottom top right
        corner3 = _point.Point(point.x + size, point.y + size, point.z - size)
        # bottom top left
        corner4 = _point.Point(point.x - size, point.y + size, point.z - size)

        # top is viewed from outide the cube
        # top bottom left
        corner5 = _point.Point(point.x - size, point.y - size, point.z + size)
        # top bottom right
        corner6 = _point.Point(point.x + size, point.y - size, point.z + size)
        # top top right
        corner7 = _point.Point(point.x + size, point.y + size, point.z + size)
        # top top left
        corner8 = _point.Point(point.x - size, point.y + size, point.z + size)

        corners = [corner1, corner2, corner3, corner4, corner5, corner6, corner7, corner8]

        for corner in corners:
            corner.Bind(self._update_artist)

        vertices = [[0, 1, 2, 3], [1, 5, 6, 2], [3, 2, 6, 7],
                    [4, 0, 3, 7], [5, 4, 7, 6], [4, 5, 1, 0]]

        self.verts = [[corners[vertices[ix][iy]] for iy in range(len(vertices[0]))] for ix in range(len(vertices))]

        self.artist = None

    @property
    def center(self) -> _point.Point:
        return self._center

    @center.setter
    def center(self, value: _point.Point):
        self._center.UnBind(self._update_artist)

        diff = value - self._center

        corners = set([v for vert in self.verts for v in vert])

        with self:
            for corner in list(corners):
                corner += diff

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
    def size(self) -> _decimal:
        return self._size

    @size.setter
    def size(self, value: _decimal):
        new_size = value / _decimal(2.0)
        old_size = self._size / _decimal(2.0)

        diff = new_size - old_size

        corners = set([v for vert in self.verts for v in vert])

        with self:
            for corner in list(corners):
                corner.x += diff
                corner.y += diff
                corner.z += diff

        self._size = value
        self._update_artist()

    def add_to_plot(self, axes: axes3d.Axes3D) -> None:
        if self.is_added:
            return

        verts = [[tuple(v) for v in vert] for vert in self.verts]
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

        verts = [[v.as_float for v in vert] for vert in self.verts]
        self.artist.set_verts(verts)

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, origin: "_point.Point"):
        corners = set([v for vert in self.verts for v in vert])

        with self:
            for corner in list(corners):
                corner.set_angles(x_angle, y_angle, z_angle, origin)

            self._center.set_angles(x_angle, y_angle, z_angle, origin)

    def set_x_angle(self, angle: _decimal, origin: _point.Point) -> None:
        corners = set([v for vert in self.verts for v in vert])

        with self:
            for corner in list(corners):
                corner.set_x_angle(angle, origin)

        self._center.set_x_angle(angle, origin)

    def set_y_angle(self, angle: _decimal, origin: _point.Point) -> None:
        corners = set([v for vert in self.verts for v in vert])

        with self:
            for corner in list(corners):
                corner.set_y_angle(angle, origin)

        self._center.set_y_angle(angle, origin)

    def set_z_angle(self, angle: _decimal, origin: _point.Point) -> None:
        corners = set([v for vert in self.verts for v in vert])

        with self:
            for corner in list(corners):
                corner.set_z_angle(angle, origin)

        self._center.set_z_angle(angle, origin)

    def move(self, point: _point.Point) -> None:
        corners = set([v for vert in self.verts for v in vert])
        with self:
            for corner in list(corners):
                corner += point

        self._center += point

    def hit_test(self, point: _point.Point) -> bool:
        corners = set([v for vert in self.verts for v in vert])
        x, y, z = point
        xs, ys, zs = zip(*list(corners))

        return min(xs) <= x <= max(xs) and min(ys) <= y <= max(ys) and min(zs) <= z <= max(zs)
