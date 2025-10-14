import numpy as np
from mpl_toolkits.mplot3d import axes3d


from .. import bases
from ..geometry import point as _point
from ..geometry import line as _line
from ..wrappers import color as _color
from ..wrappers.decimal import Decimal as _decimal
from ..wrappers import art3d


class Cylinder(bases.GetAngleBase, bases.SetAngleBase):

    def __init__(self, p1: _point.Point, p2: _point.Point, diameter: _decimal,
                 primary_color: _color.Color, edge_color: _color.Color | None):

        self._primary_color = primary_color
        self._edge_color = edge_color

        self._p1 = p1
        self._p2 = p2
        self._diameter = diameter

        p1.Bind(self._update_artist)
        p2.Bind(self._update_artist)

        self._update_disabled = False
        self.artist = None
        self._show = True
        self._verts = None

        self._verts, self._colors = self._build_verts()

    @property
    def p1(self) -> _point.Point:
        return self._p1

    @p1.setter
    def p1(self, value: _point.Point):
        self._p1.UnBind(self._update_artist)
        self._p1 = value
        value.Bind(self._update_artist)
        self._update_artist()

    @property
    def p2(self) -> _point.Point:
        return self._p2

    @p2.setter
    def p2(self, value: _point.Point):
        self._p2.UnBind(self._update_artist)
        self._p2 = value
        value.Bind(self._update_artist)
        self._update_artist()

    @property
    def is_added(self) -> bool:
        return self.artist is not None

    def show(self) -> None:
        self.artist.set_visible(True)
        self._update_artist()

    def hide(self) -> None:
        self.artist.set_visible(False)
        self._update_artist()

    def _update_artist(self) -> None:
        if not self.is_added:
            return

        if self._update_disabled:
            return

        verts, colors = self._build_verts()

        self.artist.set_verts(verts)
        self.artist.set_facecolors(colors)

    @property
    def diameter(self) -> _decimal:
        return self._diameter

    @diameter.setter
    def diameter(self, value: _decimal):
        self._diameter = value
        self._update_artist()

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, origin: _point.Point) -> None:
        if self._update_disabled:
            self.set_x_angle(x_angle, origin)
            self.set_y_angle(y_angle, origin)
            self.set_z_angle(z_angle, origin)
        else:
            with self:
                self.set_x_angle(x_angle, origin)
                self.set_y_angle(y_angle, origin)
                self.set_z_angle(z_angle, origin)

    def get_x_angle(self) -> _decimal:
        return self._get_angle((self._p1.z, self._p1.y), (self._p2.z, self._p2.y))

    def get_y_angle(self) -> _decimal:
        return self._get_angle((self._p1.x, self._p1.z), (self._p2.x, self._p2.z))

    def get_z_angle(self) -> _decimal:
        return self._get_angle((self._p1.x, self._p1.y), (self._p2.x, self._p2.y))

    def set_x_angle(self, angle: _decimal, origin: _point.Point) -> None:
        if origin == self._p1:
            self._p2.set_x_angle(angle, origin)
        elif origin == self._p2:
            self._p1.set_x_angle(angle, origin)
        else:
            if self._update_disabled:
                self._p1.set_x_angle(angle, origin)
                self._p2.set_x_angle(angle, origin)
            else:
                with self:
                    self._p1.set_x_angle(angle, origin)
                    self._p2.set_x_angle(angle, origin)

    def set_y_angle(self, angle: _decimal, origin: _point.Point) -> None:
        if origin == self._p1:
            self._p2.set_y_angle(angle, origin)
        elif origin == self._p2:
            self._p1.set_y_angle(angle, origin)
        else:
            if self._update_disabled:
                self._p1.set_y_angle(angle, origin)
                self._p2.set_y_angle(angle, origin)
            else:
                with self:
                    self._p1.set_y_angle(angle, origin)
                    self._p2.set_y_angle(angle, origin)

    def set_z_angle(self, angle: _decimal, origin: _point.Point) -> None:
        if origin == self._p1:
            self._p2.set_z_angle(angle, origin)
        elif origin == self._p2:
            self._p1.set_z_angle(angle, origin)
        else:
            if self._update_disabled:
                self._p1.set_z_angle(angle, origin)
                self._p2.set_z_angle(angle, origin)
            else:
                with self:
                    self._p1.set_z_angle(angle, origin)
                    self._p2.set_z_angle(angle, origin)

    def move(self, point: _point.Point) -> None:
        if self._update_disabled:
            self._p1 += point
            self._p2 += point
        else:
            with self:
                self._p1 += point
                self._p2 += point

    def _build_verts(self):

        line = _line.Line(self._p1, self._p2)
        origin = np.array(line.p1.as_float, dtype=float)

        x_angle, y_angle, z_angle = line.get_angles()

        x_angle = np.radians(float(x_angle))
        y_angle = np.radians(float(y_angle))
        z_angle = np.radians(float(z_angle))

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

        length = line.length

        N = 32  # number of sections around the circumfrance
        NX = int(round(float(length) * 2 * 10))

        length = float(length / _decimal(2.0))

        xpos = np.linspace(-length, length, NX)
        phase = np.linspace(0, np.pi, NX // 2)

        arr = [
            np.linspace(0, np.pi / 2, N // 8),
            np.linspace(np.pi / 2, np.pi, N // 8),
            np.linspace(np.pi, np.pi * 3 / 2, N // 8),
            np.linspace(np.pi * 3 / 2, 2 * np.pi, N // 8)
        ]

        target_colors = [self._edge_color.matplotlib]
        target_colors.extend([self._primary_color.matplotlib] * 3)

        colors = []
        verts = []

        for theta, color in zip(arr, target_colors):
            for x1, phi0, x2, phi1 in zip(xpos[:-1], phase[:-1], xpos[1:], phase[1:]):
                y1 = np.cos(theta + phi0)
                z1 = np.sin(theta + phi0)
                y2 = np.cos(theta + phi1)
                z2 = np.sin(theta + phi1)

                v1 = [[x1] + list(item) for item in list(zip(y1, z1))]
                v2 = [[x2] + list(item) for item in list(zip(y2, z2))]
                v2 = [list(v2[~i + 4]) for i in range(4)]

                verts.append(v1 + v2 + [v1[0]])
                colors.append(color)

        verts = np.array(verts, dtype=float)
        verts @= R
        verts += origin

        return verts, colors

    def add_to_plot(self, axes: axes3d.Axes3D) -> None:
        if self.is_added:
            return

        verts, colors = self._build_verts()

        self.artist = art3d.Poly3DCollection(verts, facecolor=colors, shade=False, antialiased=False, lw=0.1, alpha=1.0)
        axes.add_collection3d(self.artist)
        self.artist.set_py_data(self)

    def _get_angles(self, point1: _point.Point, point2: _point.Point) -> tuple[_decimal, _decimal, _decimal]:
        z_angle = self._get_angle((point1.x, point1.y), (point2.x, point2.y))
        y_angle = self._get_angle((point1.x, point1.z), (point2.x, point2.z))
        x_angle = self._get_angle((point1.z, point1.y), (point2.z, point2.y))

        return x_angle, y_angle, z_angle
