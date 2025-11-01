import matplotlib
import itertools
import matplotlib.cbook
import numpy as np
from mpl_toolkits.mplot3d import axes3d, art3d

from ..geometry import point as _point
from ..geometry import rotation as _rotation
from ..geometry import line as _line
from ..wrappers import art3d
from ..wrappers.decimal import Decimal as _decimal
from ..wrappers import color as _color


class Cylinder:

    def __init__(self, start: _point.Point, length, diameter: _decimal, color: _color.Color):
        start.Bind(self._update_artist)
        self._color = color
        self._saved_color = color
        self._p1 = start
        self._p2 = None
        self._length = length
        self._diameter = diameter

        self._update_disabled = False
        self.artist = None
        self._show = True
        self._verts = None

    @property
    def p1(self) -> _point.Point:
        return self._p1

    @p1.setter
    def p1(self, value: _point.Point):
        if not value.Bind(self._update_artist):
            if value != self._p1:
                raise RuntimeError('sanity check')

            return

        self._p1.Unbind(self._update_artist)
        self._p1 = value
        self._verts = None
        self._update_artist()

    @property
    def p2(self) -> _point.Point:
        if self._p2 is None:
            # R = Rotation.from_euler('xyz', [0.0, 90.0, 0.0], degrees=True)
            # p = self._p1.as_numpy + R.apply([0, 0, float(self._length)])
            self._p2 = _point.Point(_decimal(self._length), _decimal(0.0), _decimal(0.0))
            self._p2 += self._p1
            self._p2.Bind(self._update_artist)

            # self._p2 = Point(_decimal(float(p[0])), _decimal(float(p[1])), _decimal(float(p[2])))

        return self._p2

    @p2.setter
    def p2(self, value: _point.Point):
        if not value.Bind(self._update_artist):
            if value != self._p2:
                raise RuntimeError('sanity check')

            return

        if self._p2 is not None:
            self._p2.Unbind(self._update_artist)

        self._p2 = value
        self._verts = None
        self._update_artist()

    @property
    def color(self) -> _color.Color:
        return self._color

    @color.setter
    def color(self, value: _color.Color):
        self._color = value
        self._update_artist()

    def set_selected_color(self, flag: bool):
        if flag:
            self.color = _color.Color(153, 51, 51, 255)
        else:
            self.color = self._saved_color

    def set_connected_color(self, flag: bool):
        if flag:
            self.color = _color.Color(51, 153, 51, 255)
        else:
            self.color = self._saved_color

    @property
    def is_added(self) -> bool:
        return self.artist is not None

    def show(self) -> None:
        self.artist.set_visible(True)

    def hide(self) -> None:
        self.artist.set_visible(False)

    def _update_artist(self, p: _point.Point | None = None) -> None:
        if not self.is_added:
            return

        if p is not None:
            self._verts = None

        x, y, z = self._build_verts()

        z = matplotlib.cbook._to_unmasked_float_array(z)  # NOQA
        z, y, z = np.broadcast_arrays(x, y, z)
        rows, cols = z.shape

        has_stride = False
        has_count = False

        rstride = 10
        cstride = 10
        rcount = 50
        ccount = 50

        if matplotlib.rcParams['_internal.classic_mode']:
            compute_strides = has_count
        else:
            compute_strides = not has_stride

        if compute_strides:
            rstride = int(max(np.ceil(rows / rcount), 1))
            cstride = int(max(np.ceil(cols / ccount), 1))

        if (rows - 1) % rstride == 0 and (cols - 1) % cstride == 0:
            polys = np.stack([matplotlib.cbook._array_patch_perimeters(a, rstride, cstride)  # NOQA
                              for a in (x, y, z)], axis=-1)
        else:
            row_inds = list(range(0, rows - 1, rstride)) + [rows - 1]
            col_inds = list(range(0, cols - 1, cstride)) + [cols - 1]

            polys = []
            for rs, rs_next in itertools.pairwise(row_inds):
                for cs, cs_next in itertools.pairwise(col_inds):
                    ps = [matplotlib.cbook._array_perimeter(a[rs:rs_next + 1, cs:cs_next + 1])  # NOQA
                          for a in (x, y, z)]
                    ps = np.array(ps).T
                    polys.append(ps)

        if not isinstance(polys, np.ndarray) or not np.isfinite(polys).all():
            new_polys = []

            for p in polys:
                new_poly = np.array(p)[np.isfinite(p).all(axis=1)]

                if len(new_poly):
                    new_polys.append(new_poly)

            polys = new_polys

        self.artist.set_verts(polys)

        normals = art3d._generate_normals(polys)  # NOQA
        facecolors = art3d._shade_colors(self._color.matplotlib, normals, None)  # NOQA
        self.artist.set_facecolor(facecolors)

    @property
    def diameter(self) -> _decimal:
        return self._diameter

    @diameter.setter
    def diameter(self, value: _decimal):
        self._diameter = value
        self._verts = None
        self._update_artist()

    def get_angles(self) -> tuple[_decimal, _decimal, _decimal]:
        return _rotation.get_angles(self._p1, self.p2)

    def get_x_angle(self) -> _decimal:
        return _rotation.get_angles(self._p1, self.p2)[0]

    def get_y_angle(self) -> _decimal:
        return _rotation.get_angles(self.p1, self.p2)[1]

    def get_z_angle(self) -> _decimal:
        return _rotation.get_angles(self._p1, self.p2)[2]

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, origin: _point.Point) -> None:
        line = _line.Line(self._p1, self.p2)
        line.set_angles(x_angle, y_angle, z_angle, origin)

    def set_x_angle(self, angle: _decimal, origin: _point.Point) -> None:
        line = _line.Line(self._p1, self.p2)
        line.set_x_angle(angle, origin)

    def set_y_angle(self, angle: _decimal, origin: _point.Point) -> None:
        line = _line.Line(self._p1, self.p2)
        line.set_y_angle(angle, origin)

    def set_z_angle(self, angle: _decimal, origin: _point.Point) -> None:
        line = _line.Line(self._p1, self.p2)
        line.set_z_angle(angle, origin)

    @property
    def length(self):
        line = _line.Line(self._p1, self.p2)
        length = line.length()
        return round(length, 1)

    def move(self, point: _point.Point) -> None:
        self._p1 += point
        self.p2 += point

    def _build_verts(self):
        if self._verts is None:
            length = float(self.length)
            radius = float(self._diameter / _decimal(2.0))

            theta = np.linspace(0, 2 * np.pi, 20)
            z = np.linspace(0, length, 5)
            theta_grid, z_grid = np.meshgrid(theta, z)

            x = radius * np.cos(theta_grid)
            y = radius * np.sin(theta_grid)
            z = z_grid

            R = _rotation.Rotation(_decimal(0.0), _decimal(90.0), _decimal(0.0))
            X, Y, Z = R(_point.ZERO_POINT, x, y, z)

            self._verts = [X, Y, Z]

        x, y, z = self._verts
        R = _rotation.Rotation(*self.get_angles())
        X, Y, Z = R(self._p1, x, y, z)

        return X, Y, Z

    def add_to_plot(self, axes: axes3d.Axes3D) -> None:
        if self.is_added:
            return

        # we create an empty artist and then update the artist due to a bug in
        # matplotlib that causes the shading to not get rendered when updating
        # the color. We want the shading light source to be the same all the time.
        # To save some processor time we do the work of calculating the verts
        # only a single time.
        self.artist = axes.plot_surface(np.array([[np.NAN]], dtype=float),
                                        np.array([[np.NAN]], dtype=float),
                                        np.array([[np.NAN]], dtype=float),
                                        color=self._color.matplotlib, antialiaseds=False)
        self._update_artist()

    def set_py_data(self, py_data):
        if not self.is_added:
            raise ValueError('sanity check')

        self.artist.set_py_data(py_data)


class CylinderWithStripe(Cylinder):

    def __init__(self, start: _point.Point, length: _decimal, diameter: _decimal,
                 primary_color: _color.Color, stripe_color: _color.Color | None):

        super().__init__(start, length, diameter, primary_color)
        self._stripe_color = stripe_color
        self._colors = None

    @property
    def color(self) -> _color.Color:
        return self._color

    @color.setter
    def color(self, value: _color.Color):
        self.color = value
        self._colors = None

        self._update_artist()

    @property
    def stripe_color(self) -> _color.Color | None:
        return self._stripe_color

    @stripe_color.setter
    def stripe_color(self, value: _color.Color | None):
        self._color = value
        self._colors = None

        self._update_artist()

    def set_selected_color(self, flag: bool):
        if flag:
            self.color = _color.Color(153, 51, 51, 255)
        else:
            self.color = self._saved_color

    def set_connected_color(self, flag: bool):
        if flag:
            self.color = _color.Color(51, 153, 51, 255)
        else:
            self.color = self._saved_color

    @property
    def is_added(self) -> bool:
        return self.artist is not None

    def _update_artist(self, p: _point.Point | None = None) -> None:
        if not self.is_added:
            return

        if self._update_disabled:
            return

        if p is not None:
            self._verts = None

        verts, colors = self._build_verts()

        normals = art3d._generate_normals(verts)  # NOQA
        facecolors = art3d._shade_colors(colors, normals, None)  # NOQA
        self.artist.set_verts(verts)
        self.artist.set_facecolor(facecolors)

    def _build_verts(self):
        if self._verts is None:
            length = self.length

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

            if self._stripe_color is None:
                target_colors = [self._color.matplotlib]
            else:
                target_colors = [self._stripe_color.matplotlib]

            target_colors.extend([self._color.matplotlib] * 3)

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
            R = _rotation.Rotation(_decimal(0.0), _decimal(90.0), _decimal(0.0))
            X, Y, Z = R(_point.ZERO_POINT, verts)

            self._verts = [X, Y, Z]
            self._colors = colors

        elif self._colors is None:
            length = self.length

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

            if self._stripe_color is None:
                target_colors = [self._color.matplotlib]
            else:
                target_colors = [self._stripe_color.matplotlib]

            target_colors.extend([self._color.matplotlib] * 3)

            colors = []

            for theta, color in zip(arr, target_colors):
                zip_len = len(list(zip(xpos[:-1], phase[:-1], xpos[1:], phase[1:])))
                colors.extend([color] * zip_len)

            self._colors = colors

        x, y, z = self._verts
        R = _rotation.Rotation(*self.get_angles())
        X, Y, Z = R(self._p1, x, y, z)

        return [X, Y, Z], self._colors

    def add_to_plot(self, axes: axes3d.Axes3D) -> None:
        if self.is_added:
            return

        self.artist = art3d.Poly3DCollection([np.array([[np.NAN]], dtype=float),
                                              np.array([[np.NAN]], dtype=float),
                                              np.array([[np.NAN]], dtype=float)],
                                             color=self._color.matplotlib, antialiaseds=False)
        axes.add_collection3d(self.artist)
        self._update_artist()

    def set_py_data(self, py_data):
        if not self.is_added:
            raise ValueError('sanity check')

        self.artist.set_py_data(py_data)
