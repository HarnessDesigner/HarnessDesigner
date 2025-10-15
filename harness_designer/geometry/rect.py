from typing import Self
import numpy as np
import math

from . import point as _point
from . import line as _line

from ..wrappers.decimal import Decimal as _decimal


def _unit(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    if n == 0:
        raise ValueError("Zero-length vector")

    return v / n


def _euler_R(rx, ry, rz):
    rx, ry, rz = np.deg2rad([rx, ry, rz])
    Rx = np.array(
        [[1, 0, 0],
         [0, np.cos(rx), -np.sin(rx)],
         [0, np.sin(rx), np.cos(rx)]]
    )

    Ry = np.array(
        [[np.cos(ry), 0, np.sin(ry)],
         [0, 1, 0],
         [-np.sin(ry), 0, np.cos(ry)]]
    )

    Rz = np.array(
        [[np.cos(rz), -np.sin(rz), 0],
         [np.sin(rz), np.cos(rz), 0],
         [0, 0, 1]]
    )

    return Rz @ Ry @ Rx


class Rect:

    def __init__(
        self,
        top_left_corner: _point.Point,
        width: _decimal | None = None,
        height: _decimal | None = None,
        top_right_corner: _point.Point | None = None,
        bottom_left_corner: _point.Point | None = None,
        bottom_right_corner: _point.Point | None = None,
        x_angle: _decimal = _decimal(0.0),
        y_angle: _decimal = _decimal(0.0),
        z_angle: _decimal = _decimal(0.0),
        up=(0, 0, 1),  # preference for "upright" plane when diagonal-only
        plane_normal=None,  # optional explicit plane normal to remove ambiguity
    ):

        """
            Return rectangle corners and computed width/height.

            Returns dict:
              { "corners": [TL, TR, BR, BL], "width": w, "height": h }

            Notes about diagonal mode (corner1 + corner4):
              - A diagonal alone does NOT uniquely define the rectangle plane.
              - We choose a deterministic plane by using `up` to pick a plane that
                contains the diagonal and is as 'upright' as possible w.r.t `up`.
              - You can override by supplying `plane_normal`, or explicit width/height.
            """

        if None in (top_right_corner, bottom_left_corner, bottom_right_corner):
            p1 = np.array(top_left_corner.as_float, dtype=float)

            # -------------------------
            # 1) Diagonal mode: corner1 + corner4
            # -------------------------
            if (
                bottom_right_corner is not None and
                top_right_corner is None and
                bottom_left_corner is None
            ):

                p4_in = np.array(bottom_right_corner.as_float, dtype=float)
                d = p4_in - p1
                d_norm = np.linalg.norm(d)
                if d_norm == 0:
                    raise ValueError(
                        "corner1 and corner4 cannot be the same point."
                        )

                # If explicit plane normal provided, use it (must be orthogonal to plane)
                if plane_normal is not None:
                    n = _unit(plane_normal)
                    # ensure normal is orthogonal to diagonal (they need not be orthogonal,
                    # but here we just accept the provided normal as the plane normal)
                else:
                    # Determine a plane normal by using `up` as a reference to pick the plane
                    up_v = np.array(up, dtype=float)
                    # if d roughly parallel to up, choose alternative up to avoid degeneracy
                    if abs(np.dot(_unit(d), _unit(up_v))) > 0.999:
                        up_v = np.array([0, 1, 0])

                    # normal is perpendicular to diagonal and the chosen 'up' vector:
                    n = np.cross(d, up_v)
                    if np.linalg.norm(n) < 1e-8:
                        # fallback in the rare degenerate case
                        up_v = np.array([0, 1, 0])
                        n = np.cross(d, up_v)
                    n = _unit(n)

                # Build an orthonormal basis for the plane that contains the diagonal:
                # pick e1 inside the plane (not parallel to d), and e2 so that (e1,e2) are in-plane.
                # We'll pick e1 as cross(n, some_ref) where some_ref is chosen to give a stable orientation.
                # Use world X as reference unless near-collinear with n.
                ref = np.array([1.0, 0.0, 0.0])
                if abs(np.dot(ref, n)) > 0.9:
                    ref = np.array([0.0, 1.0, 0.0])

                e1 = np.cross(n, ref)
                e1 = _unit(e1)

                # ensure e1 is in the same plane as diagonal (it is because n is plane normal)
                # e2 is also in-plane, orthonormal pair (e1,e2)
                e2 = np.cross(n, e1)
                e2 = _unit(e2)

                # Now express diagonal d in this in-plane basis: d = a*e1 + b*e2
                a = np.dot(d, e1)
                b = np.dot(d, e2)

                # Using the convention d = w*e1 - h*e2  ==> a = w, b = -h
                # therefore:
                w_est = a
                h_est = -b

                # If user provided width/height, use them (this removes the ambiguity)
                if width is not None:
                    w = float(width)
                    # recompute h from the diagonal: d - w*e1 = -h*e2  => h = -dot(d - w*e1, e2)
                    h = -np.dot(d - w * e1, e2)
                elif height is not None:
                    h = float(height)
                    w = np.dot(d + h * e2, e1)
                else:
                    # default: use the estimated components (may be negative depending on chosen orientation)
                    w = w_est
                    h = h_est

                # Make widths positive and if sign flipped, flip axis direction
                if w < 0:
                    w = -w
                    e1 = -e1

                if h < 0:
                    h = -h
                    e2 = -e2

                # Build corners using convention:
                # TL=p1, TR = TL + e1*w, BR = TR - e2*h, BL = TL - e2*h
                p2 = p1 + e1 * w  # Top-Right
                p3 = p2 - e2 * h  # Bottom-Right (should be close to corner4 if consistent)
                p4 = p1 - e2 * h  # Bottom-Left
                global_pts = np.array([p1, p2, p3, p4])

                # Minor numeric fix: if user truly supplied diagonal p4_in which should be BR,
                # we try to rotate/flip axes so that p3 is near the supplied p4_in.
                dist_to_supplied = np.linalg.norm(global_pts[2] - p4_in)
                if dist_to_supplied > 1e-6:
                    # Try swapping e1 <-> e2 roles (different decomposition) to see if we can match supplied p4_in
                    # Alternative decomposition: use different reference for e1 (use projection of world X onto plane)
                    # Project world_x onto plane:
                    world_x = np.array([1.0, 0.0, 0.0])
                    proj = world_x - np.dot(world_x, n) * n
                    if np.linalg.norm(proj) > 1e-8:
                        alt_e1 = _unit(proj)
                        alt_e2 = _unit(np.cross(n, alt_e1))
                        a_alt = np.dot(d, alt_e1)
                        b_alt = np.dot(d, alt_e2)
                        w_alt = a_alt
                        h_alt = -b_alt

                        if w_alt < 0:
                            w_alt = -w_alt
                            alt_e1 = -alt_e1

                        if h_alt < 0:
                            h_alt = -h_alt
                            alt_e2 = -alt_e2

                        p2_alt = p1 + alt_e1 * w_alt
                        p3_alt = p2_alt - alt_e2 * h_alt

                        # if alt solution is closer to provided diagonal, use it
                        if np.linalg.norm(p3_alt - p4_in) < dist_to_supplied:
                            e1, e2, w, h = alt_e1, alt_e2, w_alt, h_alt
                            p2, p3, p4 = p2_alt, p3_alt, p1 - alt_e2 * h_alt
                            global_pts = np.array([p1, p2, p3, p4])

            # -------------------------
            # 2) Rotation + size mode (no corner2)
            # -------------------------
            elif top_right_corner is None:
                if width is None or height is None:
                    raise ValueError("If corner2 is not provided you must supply width and height.")

                R = _euler_R(x_angle, y_angle, z_angle)
                local = np.array(
                    [
                        [0.0, 0.0, 0.0],  # TL
                        [width, 0.0, 0.0],  # TR
                        [width, -height, 0.0],  # BR
                        [0.0, -height, 0.0]  # BL
                    ]
                )

                global_pts = (R @ local.T).T + p1
                w = float(width)
                h = float(height)

            # -------------------------
            # 3) Adjacent corners (corner1 + corner2) possibly with corner3
            # -------------------------
            else:
                p2 = np.array(top_right_corner.as_float, dtype=float)
                top_vec = p2 - p1
                top_len = np.linalg.norm(top_vec)
                if top_len == 0:
                    raise ValueError(
                        "corner1 and corner2 cannot be the same point."
                        )

                top_dir = top_vec / top_len

                if bottom_left_corner is not None:
                    p3_in = np.array(bottom_left_corner.as_float, dtype=float)
                    v13 = p3_in - p1

                    down_dir = v13 - np.dot(v13, top_dir) * top_dir
                    if np.linalg.norm(down_dir) < 1e-8:
                        # degenerate: corner3 lies on top edge line; pick arbitrary perpendicular
                        if abs(top_dir[0]) < 0.9:
                            tmp = np.array([1., 0., 0.])
                        else:
                            tmp = np.array([0., 1., 0.])

                        down_dir = np.cross(top_dir, tmp)

                    down_dir = _unit(down_dir)
                    h = np.linalg.norm(v13 - np.dot(v13, top_dir) * top_dir)
                else:
                    # no corner3: use given height or default guess
                    if abs(top_dir[0]) < 0.9:
                        tmp = np.array([1., 0., 0.])
                    else:
                        tmp = np.array([0., 1., 0.])

                    down_dir = _unit(np.cross(top_dir, tmp))

                    if height is not None:
                        h = height
                    elif width is not None:
                        h = width
                    else:
                        h = top_len / 2

                    if width is None:
                        w = top_len
                    else:
                        w = float(width)

                p2 = p1 + top_dir * w
                p3 = p2 - down_dir * h
                p4 = p1 - down_dir * h
                global_pts = np.array([p1, p2, p3, p4])

            # Final computed width/height for output (distances)
            calc_w = np.linalg.norm(global_pts[1] - global_pts[0])
            calc_h = np.linalg.norm(global_pts[3] - global_pts[0])

            corners = [top_left_corner]
            cs = [_point.Point(*tuple(_decimal(float(item)) for item in p)) for p in global_pts]

            if top_right_corner is None:
                corners.append(cs[1])
            else:
                corners.append(top_right_corner)

            if bottom_left_corner is None:
                corners.append(cs[2])
            else:
                corners.append(bottom_left_corner)

            if bottom_right_corner is None:
                corners.append(cs[3])
            else:
                corners.append(bottom_right_corner)
        else:
            corners = [top_left_corner, top_right_corner, bottom_left_corner, bottom_right_corner]

            calc_w = _line.Line(top_left_corner, top_right_corner).length()
            calc_h = _line.Line(top_left_corner, bottom_left_corner).length()

        top_line = Line(corners[0], corners[1])
        bottom_line = Line(corners[2], corners[3])
        left_line = Line(corners[0], corners[2])
        right_line = Line(corners[1], corners[3])

        if (
            len(top_line) != len(bottom_line) or
            len(left_line) != len(right_line)
        ):
            raise RuntimeError('shape is not a rectangle')

        self._corners = tuple(corners)

        self._width = _decimal(calc_w)
        self._height = _decimal(calc_h)

        self._p1 = self._corners[0]
        self._p2 = self._corners[1]
        self._p3 = self._corners[2]
        self._p4 = self._corners[3]

        line = _line.Line(self._p1, self._p4)

        self._x_angle, self._y_angle, self._z_angle = line.get_angles()

    def __iadd__(self, other: _point.Point) -> Self:
        self._p1 += other
        self._p2 += other
        self._p3 += other
        self._p4 += other

        return self

    def __add__(self, other: _point.Point) -> "Rect":
        p1 = self._p1 + other
        p2 = self._p2 + other
        p3 = self._p3 + other
        p4 = self._p4 + other

        return Rect(top_left_corner=p1, top_right_corner=p2,
                    bottom_left_corner=p3, bottom_right_corner=p4)

    def get_angles(self) -> tuple[_decimal, _decimal, _decimal]:
        return self._x_angle, self._y_angle, self._z_angle

    def get_x_angle(self):
        return self._x_angle

    def get_y_angle(self):
        return self._y_angle

    def get_z_angle(self):
        return self._z_angle

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal,
                   origin: _point.Point | None = None):

        if origin is None:
            origin = self._p1

        R = _euler_R(x_angle, y_angle, z_angle)

        points = [p for p in (self._p1, self._p2, self._p3, self._p4) if origin != p]

        for p in points:
            p_arr = np.array(p.as_float, dtype=float)
            p_arr @= R
            x, y, z = [_decimal(float(item)) for item in p_arr.tolist()]
            p.x = x
            p.y = y
            p.z = z

    def set_x_angle(self, angle: _decimal, origin: _point.Point | None):
        self.set_angles(angle, self._y_angle, self._z_angle, origin)

    def set_y_angle(self, angle: _decimal, origin: _point.Point | None):
        self.set_angles(self._x_angle, angle, self._z_angle, origin)

    def set_z_angle(self, angle: _decimal, origin: _point.Point | None):
        self.set_angles(self._x_angle, self._y_angle, angle, origin)

    @property
    def p1(self) -> _point.Point:
        return self._p1

    @property
    def p2(self) -> _point.Point:
        return self._p2

    @property
    def p3(self) -> _point.Point:
        return self._p3

    @property
    def p4(self) -> _point.Point:
        return self._p4

    @property
    def width(self) -> _decimal:
        return self._width

    @property
    def height(self) -> _decimal:
        return self._height

    def copy(self):
        return Rect(top_left_corner=self._p1.copy(), top_right_corner=self._p2.copy(),
                    bottom_left_corner=self._p3.copy(), bottom_right_corner=self._p4.copy())

    @property
    def left_line(self) -> _line.Line:
        return _line.Line(self._p1, self._p3)

    @property
    def top_line(self) -> _line.Line:
        return _line.Line(self._p1, self._p2)

    @property
    def bottom_line(self) -> _line.Line:
        return _line.Line(self._p3, self._p4)

    @property
    def right_line(self) -> _line.Line:
        return _line.Line(self._p2, self._p4)

    @property
    def center(self):
        combined = self._p1 + self._p4
        return combined / _decimal(2.0)
