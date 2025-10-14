import matplotlib
import itertools

import numpy as np
from mpl_toolkits.mplot3d import axes3d

from ..geometry import point as _point
from ..wrappers.decimal import Decimal as decimal
from ..wrappers import color as _color


class Sphere:

    def __init__(self, point: _point.Point, diameter: decimal, color: _color.Color):
        self._center = point
        self._diameter = diameter
        self._color = color
        self.artist = None

        point.Bind(self._update_artist)
        color.Bind(self._update_artist)

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
    def center(self) -> _point.Point:
        return self._center

    @center.setter
    def center(self, value: _point.Point):
        self._center.UnBind(self._update_artist)
        self._center = value
        value.Bind(self._update_artist)
        self._update_artist()

    @property
    def diameter(self) -> decimal:
        return self._diameter

    @diameter.setter
    def diameter(self, value: decimal):
        self._diameter = value
        self._update_artist()

    @property
    def is_added(self) -> bool:
        return self.artist is not None

    def move(self, point: _point.Point) -> None:
        self._point += point

    def rotate(self, x_angle: decimal, y_angle: decimal, z_angle: decimal, origin: _point.Point):
        self._point.rotate(x_angle, y_angle, z_angle, origin)

    def rotate_x(self, angle: decimal, origin: _point.Point) -> None:
        self._point.rotate_x(angle, origin)

    def rotate_y(self, angle: decimal, origin: _point.Point) -> None:
        self._point.rotate_y(angle, origin)

    def rotate_z(self, angle: decimal, origin: _point.Point) -> None:
        self._point.rotate_z(angle, origin)

    def _update_artist(self) -> None:
        if not self.is_added:
            return

        diameter = float(self._diameter)
        px, py, pz = self._point.as_float

        u = np.linspace(0, 2 * np.pi, 16)
        v = np.linspace(0, np.pi, 16)
        x = (diameter * np.outer(np.cos(u), np.sin(v))) + px
        y = (diameter * np.outer(np.sin(u), np.sin(v))) + py
        z = (diameter * np.outer(np.ones(np.size(u)), np.cos(v))) + pz

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
            polys = np.stack([matplotlib.cbook._array_patch_perimeters(a, rstride, cstride) for a in (x, y, z)], axis=-1)  # NOQA
        else:
            row_inds = list(range(0, rows - 1, rstride)) + [rows - 1]
            col_inds = list(range(0, cols - 1, cstride)) + [cols - 1]

            polys = []
            for rs, rs_next in itertools.pairwise(row_inds):
                for cs, cs_next in itertools.pairwise(col_inds):
                    ps = [matplotlib.cbook._array_perimeter(a[rs:rs_next + 1, cs:cs_next + 1]) for a in (x, y, z)]  # NOQA
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

    def add_to_plot(self, axes: axes3d.Axes3D) -> None:
        if self.is_added:
            return

        diameter = float(self._diameter)
        px, py, pz = self._point.as_float

        u = np.linspace(0, 2 * np.pi, 16)
        v = np.linspace(0, np.pi, 16)
        x = (diameter * np.outer(np.cos(u), np.sin(v))) + px
        y = (diameter * np.outer(np.sin(u), np.sin(v))) + py
        z = (diameter * np.outer(np.ones(np.size(u)), np.cos(v))) + pz

        self.artist = axes.plot_surface(x, y, z, color=self._color.matplotlib)
