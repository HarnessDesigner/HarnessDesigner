
import matplotlib
import itertools
import matplotlib.cbook
import numpy as np
from mpl_toolkits.mplot3d import axes3d

from ..geometry import point as _point
from ..wrappers.decimal import Decimal as _decimal
from ..wrappers import color as _color
from .. import bases as _bases


# How this works is the hemisphere is created at point 0, 0, 0 and when applying
# rotation it needs to be done 2 times. The first time is to adjust a transition angle
# as a whole This simply sets the center point location the origin for this rotation
# is going to be the center point of the transition. The second time the rotation
# gets fed in is what sets the hemisphere rotation relative to it's senter point.
# this one the center point of the hemisphere is what gets passed in for the origin
# setting the angle of the hemisphere like this allows for positioning of the hemisphere
# to meet with the body cylinder and the branch cylinders proeprly.
# I still have to monkey around with doing angle calculations for branges that are
# not 90° to the transition center point. It should be as simple as angle + 90 for the
# calculation because we are always building the transition at 0, 0, 0 and then setting
# any transition rotation and then moving the transition into place. This all occurs in
# numpy arrays and it's not rendered for each step. The reason why it is important to
# utilize these hemispheres is because it reduces the poly count that matplotlib needs
# to render this allows me to bump up the number of polygons on other objects to give
# a smoother appearance.

class Hemisphere(_bases.GetAngleBase, _bases.SetAngleBase):

    def __init__(self, point: _point.Point, diameter: _decimal, color: _color.Color, hole_diameter: _decimal | None):
        self._center = point
        self._diameter = diameter
        self._color = color
        self.artist = None

        self._x_angle = _decimal(0.0)
        self._y_angle = _decimal(0.0)
        self._z_angle = _decimal(0.0)

        point.Bind(self._update_artist)
        color.Bind(self._update_artist)

        self._sections = int((_decimal(1.65) /
                             (_decimal(9.0) /
                             (diameter ** (_decimal(1.0) / _decimal(6.0))))) *
                             _decimal(100.0))

        self._hole_diameter = hole_diameter

    @property
    def hole_diameter(self) -> _decimal | None:
        return self._hole_diameter

    @hole_diameter.setter
    def hole_diameter(self, value: _decimal | None):
        self._hole_diameter = value
        self._update_artist()

    @property
    def color(self) -> _color.Color:
        return self._color

    @color.setter
    def color(self, value: _color.Color):
        self._color.Unbind(self._update_artist)
        self._color = value
        value.Bind(self._update_artist)
        self._update_artist()

    @property
    def center(self) -> _point.Point:
        return self._center

    @center.setter
    def center(self, value: _point.Point):
        self._center.Unbind(self._update_artist)
        self._center = value
        value.Bind(self._update_artist)
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
        self._update_artist()

    @property
    def is_added(self) -> bool:
        return self.artist is not None

    def move(self, point: _point.Point) -> None:
        self._center += point

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, origin: _point.Point):
        if origin != self.center:
            self._center.set_angles(x_angle, y_angle, z_angle, origin)
            return

        self._x_angle = x_angle
        self._y_angle = y_angle
        self._z_angle = z_angle
        self._update_artist(origin)

    def rotate_x(self, angle: _decimal, origin: _point.Point) -> None:
        if origin != self._center:
            return

        self.set_angles(angle, self._y_angle, self._z_angle, origin)

    def rotate_y(self, angle: _decimal, origin: _point.Point) -> None:
        if origin != self._center:
            return

        self.set_angles(self._x_angle, angle, self._z_angle, origin)

    def rotate_z(self, angle: _decimal, origin: _point.Point) -> None:
        if origin != self._center:
            return

        self.set_angles(self._x_angle, self._y_angle, angle, origin)

    def _get_verts(self) -> tuple[np.array, np.array, np.array]:
        R = self._get_rotation_matrix(self._x_angle, self._y_angle, self._z_angle)

        radius = float(self._diameter / _decimal(2.0))

        u = np.linspace(0, 2 * np.pi, self._sections)
        v = np.linspace(0, np.pi / 2, self._sections)
        x = radius * np.outer(np.cos(u), np.sin(v))
        y = radius * np.outer(np.sin(u), np.sin(v))
        z = radius * np.outer(np.ones(np.size(u)), np.cos(v))

        if self._hole_diameter is not None:
            hole_dia = float(self._hole_diameter / _decimal(2.0) / _decimal(1.15))

            mask = np.sqrt(x ** 2 + y ** 2) >= hole_dia
            x = np.where(mask, x, np.nan)
            y = np.where(mask, y, np.nan)
            z = np.where(mask, z, np.nan)

        new_x = []
        new_y = []
        new_z = []

        for i in range(len(x)):
            arry = np.array(list(zip(x[i], y[i], z[i])), dtype=float) @ R

            new_x.append(arry[:, 0])
            new_y.append(arry[:, 1])
            new_z.append(arry[:, 2])

        x = np.array(new_x, dtype=float) + float(self._center.x)
        y = np.array(new_y, dtype=float) + float(self._center.y)
        z = np.array(new_z, dtype=float) + float(self._center.z)
        return x, y, z

    def _update_artist(self, *_) -> None:
        if not self.is_added:
            return

        x, y, z = self._get_verts()

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

    def add_to_plot(self, axes: axes3d.Axes3D) -> None:
        if self.is_added:
            return

        x, y, z = self._get_verts()
        self.artist = axes.plot_surface(x, y, z, color=self._color.matplotlib)
