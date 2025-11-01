
import matplotlib
import itertools
import matplotlib.cbook
import numpy as np
from mpl_toolkits.mplot3d import axes3d, art3d

from ..geometry import point as _point
from ..wrappers.decimal import Decimal as _decimal
from ..wrappers import color as _color
from ..geometry import rotation as _rotation
from ..geometry.constants import ONE_65, NINE_0, ZERO_1666, ONEHUN_0


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


class Hemisphere:

    def __init__(self, center: _point.Point, diameter: _decimal,
                 color: _color.Color, hole_diameter: _decimal | None):

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

        self._sections = int((ONE_65 / (NINE_0 / (diameter ** ZERO_1666))) * ONEHUN_0)

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
            self.color = _color.Color(153, 51, 51, 255)
        else:
            self.color = self._saved_color

    @property
    def color(self) -> _color.Color:
        return self._color

    @color.setter
    def color(self, value: _color.Color):
        self._color = value
        self._update_artist()

    @property
    def center(self) -> _point.Point:
        return self._center

    @center.setter
    def center(self, value: _point.Point):
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
        self._sections = int((ONE_65 / (NINE_0 / (value ** ZERO_1666))) * ONEHUN_0)

        self._verts = None
        self._update_artist()

    @property
    def is_added(self) -> bool:
        return self.artist is not None

    def move(self, point: _point.Point) -> None:
        self._center += point

    def set_angles(self, x_angle: _decimal, y_angle: _decimal,
                   z_angle: _decimal, origin: _point.Point):

        if origin != self.center:
            self._center.set_angles(x_angle, y_angle, z_angle, origin)
            return

        self._x_angle = x_angle
        self._y_angle = y_angle
        self._z_angle = z_angle
        self._update_artist()

    def set_x_angle(self, angle: _decimal, origin: _point.Point) -> None:
        if origin != self._center:
            self.set_angles(angle, _decimal(0.0), _decimal(0.0), origin)
        else:
            self.set_angles(angle, self._y_angle, self._z_angle, origin)

    def set_y_angle(self, angle: _decimal, origin: _point.Point) -> None:
        if origin != self._center:
            self.set_angles(_decimal(0.0), angle, _decimal(0.0), origin)
        else:
            self.set_angles(self._x_angle, angle, self._z_angle, self._center)

    def set_z_angle(self, angle: _decimal, origin: _point.Point) -> None:
        if origin != self._center:
            self.set_angles(_decimal(0.0), _decimal(0.0), angle, origin)
        else:
            self.set_angles(self._x_angle, self._y_angle, angle, origin)

    def get_angles(self) -> tuple[_decimal, _decimal, _decimal]:
        return self._x_angle, self._y_angle, self._z_angle

    @property
    def _line_space(self):
        return np.pi / 2

    def _get_verts(self) -> tuple[np.array, np.array, np.array]:
        if self._verts is None:
            radius = float(self._diameter / _decimal(2.0))

            u = np.linspace(0, 2 * np.pi, int(self._sections / 1.5))
            v = np.linspace(0, self._line_space, self._sections // 3)
            X = radius * np.outer(np.cos(u), np.sin(v))
            Y = radius * np.outer(np.sin(u), np.sin(v))
            Z = radius * np.outer(np.ones(np.size(u)), np.cos(v))

            if self._hole_diameter:
                hole_dia = float(self._hole_diameter / _decimal(2.0) / _decimal(1.15))

                mask = np.sqrt(X ** 2 + Y ** 2) >= hole_dia
                X = np.where(mask, X, np.nan)
                Y = np.where(mask, Y, np.nan)
                Z = np.where(mask, Z, np.nan)

                z_max = np.nanmax(Z.flatten())
                self._hc = _point.Point(_decimal(0.0), _decimal(0.0), _decimal(z_max))

            self._verts = [X, Y, Z]

        x, y, z = self._verts

        x_angle, y_angle, z_angle = self.get_angles()
        if x_angle or y_angle or z_angle:
            R = _rotation.Rotation(x_angle, y_angle, z_angle)

            X, Y, Z = R(self._center, x, y, z)

            if self._hc is None:
                hole_center = self._center
            else:
                local_points = R(self._center, self._hc)
                hole_center = _point.Point(*[_decimal(float(item)) for item in local_points])
        else:
            if self._hc is None:
                hole_center = self._center
            else:
                hole_center = self._hc

            X, Y, Z = x, y, z

        if self._hole_center is None:
            self._hole_center = hole_center
        elif self._hole_center != hole_center:
            hc = self._hole_center
            diff = hole_center - hc
            hc += diff

        return X, Y, Z

    @property
    def hole_center(self) -> _point.Point:
        if self._hole_center is None:
            _ = self._get_verts()

        return self._hole_center

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

        normals = art3d._generate_normals(polys)  # NOQA
        facecolors = art3d._shade_colors(self._color.matplotlib, normals, None)  # NOQA
        self.artist.set_facecolor(facecolors)

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
                                        color=self._color, antialiaseds=False)
        self._update_artist()

    def set_py_data(self, py_data):
        if not self.is_added:
            raise ValueError('sanity check')

        self.artist.set_py_data(py_data)
