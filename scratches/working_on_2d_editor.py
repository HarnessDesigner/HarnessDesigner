
import wx
import math

from decimal import Decimal as _Decimal


class Decimal(_Decimal):

    def __new__(cls, value, *args, **kwargs):
        if not isinstance(value, (str, Decimal)):
            value = str(float(value))

        return super().__new__(cls, value, *args, **kwargs)


decimal = Decimal


class WireInfo:

    material_choices = [
        ('Cu', 'Copper'),
        ('Al', 'Aluminum'),
        ('Sn/Cu', 'Tin-plated Copper'),
        ('Ni/Cu', 'Nickel-plated Copper'),
        ('Sn/Al', 'Tin-plated Aluminum'),
        ('Ag/Cu', 'Silver-plated Copper'),
        ('Ag/Al', 'Silver-plated Aluminum')
    ]

    def __init__(self):

        mm2 = self.__awg_to_mm2(22)

        self._num_conductors = 1
        self._shielded = False
        self._color = wx.BLACK
        self._stripe_color = wx.BLACK
        self._mm2 = mm2
        self._max_voltage_drop = 2.0
        self._volts = 12.0
        self._load = 0.0
        self._length = 1
        self._material = 'Copper'
        self._resistance_1kft = None
        self._weight_1kft_lb = None

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self._color = value

    @property
    def stripe_color(self):
        return self._stripe_color

    @stripe_color.setter
    def stripe_color(self, value):
        self._stripe_color = value

    @property
    def num_conductors(self):
        return self._num_conductors

    @num_conductors.setter
    def num_conductors(self, value: int):
        self._num_conductors = value

    @property
    def is_shielded(self):
        return self._shielded

    @is_shielded.setter
    def is_shielded(self, value: bool):
        self._shielded = value

    @property
    def od_mm(self):
        if self._shielded:
            shielded = {
                4: {
                    30: 2.3114,
                    28: 2.4892,
                    26: 2.7940,
                    24: 3.1242,
                    22: 3.4798,
                    20: 3.9116,
                    18: 4.5212,
                    16: 5.0292,
                    14: 6.1214,
                    12: 7.2136
                },
                3: {
                    26: 2.6924,
                    24: 3.0226,
                    22: 3.4290,
                    20: 3.8608,
                    18: 4.4450,
                    16: 4.8514,
                    14: 5.7658,
                    12: 6.8000
                },
                2: {
                    30: 2.23,
                    28: 2.38,
                    26: 2.59,
                    24: 2.99,
                    22: 3.35,
                    20: 3.76,
                    18: 4.32,
                    16: 4.67,
                    14: 5.53,
                    12: 6.0
                },
                1: {
                    24: 2.26,
                    22: 2.57,
                    20: 2.77,
                    18: 3.02,
                    16: 3.25,
                    14: 3.73,
                    12: 4.19
                }
            }
            return shielded.get(self._num_conductors, {}).get(self.awg, 0.0)

        wire_ods = {
            30: 0.635,
            28: 0.6858,
            26: 0.8128,
            24: 0.9398,
            22: 1.0922,
            20: 1.2700,
            18: 1.5240,
            16: 1.7272,
            14: 2.1590,
            12: 2.6162
        }
        wire_od = wire_ods.get(self.awg, 0.0)

        core_dia_factors = {
            1: 1.0,
            2: 2.0,
            3: 2.15,
            4: 2.41,
            5: 2.7,
            6: 3.0,
            7: 3.0
        }

        diameter = decimal(wire_od) * decimal(core_dia_factors[self._num_conductors])
        return float(diameter)

    def __eq__(self, other):
        if not isinstance(other, WireInfo):
            return False

        return other.awg == self.awg and other.num_conductors == self.num_conductors and other.is_shielded == self.is_shielded

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        if not isinstance(other, WireInfo):
            raise RuntimeError

        return other.awg > self.awg and other.num_conductors <= self.num_conductors

    def __lt__(self, other):
        if not isinstance(other, WireInfo):
            raise RuntimeError

        return other.awg < self.awg and other.num_conductors >= self.num_conductors

    def __ge__(self, other):
        if not isinstance(other, WireInfo):
            raise RuntimeError

        return other.awg >= self.awg and other.num_conductors <= self.num_conductors

    def __le__(self, other):
        if not isinstance(other, WireInfo):
            raise RuntimeError

        return other.awg <= self.awg and other.num_conductors >= self.num_conductors

    @property
    def length_m(self):
        return self._length

    @length_m.setter
    def length_m(self, value):
        self._length = value

    @property
    def length_ft(self):
        return float(decimal(self._length) * decimal(3.28084))

    @length_ft.setter
    def length_ft(self, value):
        self._length = float(decimal(value) * decimal(0.3048))

    @property
    def recommended_mm2(self):
        awg = self.recommended_awg
        if awg is None:
            return None

        return self.__awg_to_mm2(awg)

    @property
    def recommended_awg(self):
        v_drop = self.voltage_drop
        awg = self.awg
        while awg != -1 and v_drop > self.allowed_voltage_drop:
            awg -= 1

            if awg not in self.awg_to_resistance:
                awg1 = awg - 1
                awg2 = awg + 1

                res1 = self.awg_to_resistance.get(awg1, self.awg_to_resistance.get(awg2, 0.0))
                res2 = self.awg_to_resistance.get(awg2, self.awg_to_resistance.get(awg1, 0.0))
                res = (decimal(res1) + decimal(res2)) / decimal(2.0)
            else:
                res = decimal(self.awg_to_resistance[awg])

            res /= decimal(1000)
            res *= decimal(self.length_ft)
            v_drop = decimal(2.0) * decimal(self.load) * res

        return None if awg == -1 else awg

    @property
    def volts(self):
        return self._volts

    @volts.setter
    def volts(self, value):
        self._volts = value

    @property
    def load(self):
        return self._load

    @load.setter
    def load(self, value):
        self._load = value

    awg_to_resistance = {
        # 22759/16
        0: 0.126,
        1: 0.149,
        2: 0.183,
        4: 0.280,
        6: 0.445,
        8: 0.701,
        10: 1.26,
        # 22759/32
        12: 2.02,
        14: 3.06,
        16: 4.81,
        18: 6.23,
        20: 9.88,
        22: 16.2,
        24: 26.2,
        26: 41.3,
        28: 68.6,
        30: 108.4
    }

    awg_to_weight = {
        # 22759/16
        0: 380.00,
        1: 293.00,
        2: 231.00,
        4: 152.00,
        6: 96.90,
        8: 61.50,
        10: 34.00,
        # 22759/32
        12: 19.70,
        14: 13.00,
        16: 8.30,
        18: 6.50,
        20: 4.30,
        22: 2.80,
        24: 2.00,
        26: 1.40,
        28: 0.91,
        30: 0.66
    }

    @property
    def resistance_1kft(self):
        if self._resistance_1kft is not None:
            return self._resistance_1kft

        awg = self.awg
        if awg not in self.awg_to_resistance:
            awg1 = awg - 1
            awg2 = awg + 1

            res1 = self.awg_to_resistance.get(awg1, self.awg_to_resistance.get(awg2, 0.0))
            res2 = self.awg_to_resistance.get(awg2, self.awg_to_resistance.get(awg1, 0.0))
            res = (decimal(res1) + decimal(res2)) / decimal(2.0)
        else:
            res = decimal(self.awg_to_resistance[awg])

        return float(res)

    @resistance_1kft.setter
    def resistance_1kft(self, value):
        self._resistance_1kft = value

    @property
    def resistance(self):
        res_per_foot = decimal(self.resistance_1kft) / decimal(1000)
        return float(decimal(self.length_ft) * res_per_foot)

    @property
    def weight_1kft_lb(self):
        if self._weight_1kft_lb is not None:
            return self._weight_1kft_lb

        awg = self.awg
        if awg not in self.awg_to_weight:
            awg1 = awg - 1
            awg2 = awg + 1

            weight1 = self.awg_to_weight.get(awg1, self.awg_to_weight.get(awg2, 0.0))
            weight2 = self.awg_to_weight.get(awg2, self.awg_to_weight.get(awg1, 0.0))
            weight = (decimal(weight1) + decimal(weight2)) / decimal(2.0)
        else:
            weight = decimal(self.awg_to_weight[awg])

        return float(weight)

    @weight_1kft_lb.setter
    def weight_1kft_lb(self, value):
        self._weight_1kft_lb = value

    @property
    def weight_kg(self):
        return float(decimal(self.weight_lb) * decimal(0.453592))

    @property
    def weight_lb(self):
        weight_per_foot = decimal(self.weight_1kft_lb) / decimal(1000)
        return float((decimal(self.length_ft) * weight_per_foot) * decimal(self._num_conductors))

    @property
    def voltage_drop(self):
        return float((decimal(2) * decimal(self.resistance) * decimal(self.load)) / decimal(self._num_conductors))

    @property
    def allowed_voltage_drop(self) -> float:
        return self._max_voltage_drop

    @allowed_voltage_drop.setter
    def allowed_voltage_drop(self, value: float):
        self._max_voltage_drop = value

    @property
    def conductivity_symbol(self):
        return 'S/m'

    @property
    def conductivity(self):
        return float(decimal(1.0) / decimal(self.resistivity))

    @property
    def resistivity_symbol(self):
        return '(Ω x mm2)/m'

    @property
    def resistivity(self) -> float:
        factor = decimal(10) ** decimal(8)
        mapping = {
            'Al': decimal(2.82) * factor,
            'Cu': decimal(1.7) * factor,
            'Sn/Cu': decimal(1.796) * factor,
            'Ni/Cu': decimal(1.8947) * factor,
            'Ag/Cu': decimal(1.7241) * factor,
            'Aluminum': decimal(2.82) * factor,
            'Copper': decimal(1.7) * factor,
            'Tin-plated Copper': decimal(1.796) * factor,
            'Nickel-plated Copper': decimal(1.8947) * factor,
            'Silver-plated Copper': decimal(1.7241) * factor
        }

        return mapping[self._material]

    @property
    def material(self):
        return self._material

    @material.setter
    def material(self, value: str):

        for item in self.material_choices:
            if value in item:
                break
        else:
            raise RuntimeError

        self._material = value

    @staticmethod
    def __awg_to_mm2(awg: int) -> float:
        d_in = decimal(0.005) * (decimal(92) ** ((decimal(36) - decimal(awg)) / decimal(39)))
        d_mm = d_in * decimal(25.4)
        area_mm2 = (decimal(math.pi) / decimal(4)) * (d_mm ** decimal(2))
        return float(round(area_mm2, 4))

    @property
    def mm2(self) -> float:
        return self._mm2

    @mm2.setter
    def mm2(self, value: float):
        self._mm2 = value

    @property
    def in2(self):
        d_in = decimal(0.005) * (decimal(92) ** ((decimal(36) - decimal(self.awg)) / decimal(39)))
        d_mm = d_in * decimal(25.4)
        area_mm2 = (decimal(math.pi) / decimal(4)) * (d_mm ** decimal(2))
        area_in2 = area_mm2 / decimal(25.4) / decimal(25.4)
        return float(round(area_in2, 4))

    @property
    def in2_symbol(self):
        return 'in²'

    @property
    def mm2_symbol(self):
        return 'mm²'

    @property
    def awg(self):
        d_mm = decimal(2) * decimal(math.sqrt(decimal(self._mm2) / decimal(math.pi)))
        d_in = d_mm / decimal(25.4)
        awg = decimal(36) - decimal(39) * decimal(math.log(float(d_in / decimal(0.005)), 92))
        return int(round(awg))

    @awg.setter
    def awg(self, value: int):
        self._mm2 = self.__awg_to_mm2(value)

    @property
    def diameter_inch(self):
        d_in = decimal(0.005) * (decimal(92) ** ((decimal(36) - decimal(self.awg)) / decimal(39)))
        return float(round(d_in, 4))

    @property
    def diameter_mm(self):
        d_in = decimal(0.005) * (decimal(92) ** ((decimal(36) - decimal(self.awg)) / decimal(39)))
        d_mm = d_in * decimal(25.4)
        return float(round(d_mm, 4))

    @property
    def pixel_width(self):
        width_map = {
            30: 1, 29: 1, 28: 1, 27: 1, 26: 2, 25: 2, 24: 2, 23: 2, 22: 3,
            21: 3, 20: 4, 19: 4, 18: 5, 17: 5, 16: 6, 15: 6, 14: 7, 13: 7,
            12: 8, 11: 8, 10: 9, 9: 9, 8: 10, 7: 10, 6: 10, 5: 10, 4: 11,
            3: 11, 2: 11, 1: 11, 0: 12
        }

        return width_map.get(self.awg, 6)


class Point:

    def __init__(self, x, y):
        self._x = decimal(x)
        self._y = decimal(y)
        self._block_cb = 0

        self._callbacks = []

    def Bind(self, cb):
        if cb not in self._callbacks:
            self._callbacks.append(cb)

    def Unbind(self, cb):
        try:
            self._callbacks.remove(cb)
        except ValueError:
            pass

    def copy(self):
        return Point(float(self.x), float(self.y))

    def __iadd__(self, other: "Point"):
        x, y = other.x, other.y
        self.x += x
        self.y += y

        return self

    def __add__(self, other: "Point") -> "Point":
        x1, y1 = self.x, self.y
        x2, y2 = other.x, other.y

        x = x1 + x2
        y = y1 + y2

        return Point(x, y)

    def __isub__(self, other: "Point"):
        x, y = other.x, other.y
        self.x -= x
        self.y -= y

        return self

    def __sub__(self, other: "Point") -> "Point":
        x1, y1 = self.x, self.y
        x2, y2 = other.x, other.y

        x = x1 - x2
        y = y1 - y2

        return Point(x, y)

    def __imul__(self, other):
        self.x *= other
        self.y *= other
        return self

    def __itruediv__(self, other: decimal):
        self.x /= other
        self.y /= other

        return self

    def __enter__(self):
        self._block_cb += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._block_cb -= 1

    def _do_callbacks(self):
        if self._block_cb:
            return

        for cb in self._callbacks:
            cb(self)

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, value):
        self._x = value
        self._do_callbacks()

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, value):
        self._y = value
        self._do_callbacks()

    def move(self, p):
        new_p = self + p

        x = round(new_p.x / decimal(10)) * decimal(10.0)
        y = round(new_p.y / decimal(10)) * decimal(10.0)
        if x != self.x or y != self.y:
            self._x = x
            self._y = y


class Line:

    def __init__(
        self,
        p1: Point,
        p2: Point | None,
        angle: int | float | None = None,
        length: int | float | None = None
    ):

        self._p1 = p1

        if p2 is None:
            if None in (angle, length):
                raise RuntimeError('unable to calculate end point of line')

            r = math.radians(angle)
            x2 = p1.x + decimal(length) * decimal(math.cos(r))
            y2 = p1.y + decimal(length) * decimal(math.sin(r))
            p2 = Point(x2, y2)

        self._p2 = p2

    @property
    def x1(self):
        return float(self._p1.x)

    @property
    def y1(self):
        return float(self._p1.y)

    @property
    def x2(self):
        return float(self._p2.x)

    @property
    def y2(self):
        return float(self._p2.y)

    def __iter__(self):
        yield self.x1, self.y1
        yield self.x2, self.y2

    def get_intersection(self, line: "Line") -> tuple[int, int]:
        xdiff = (self._p1.x - self._p2.x, line._p1.x - line._p2.x)
        ydiff = (self._p1.y - self._p2.y, line._p1.y - line._p2.y)

        def det(a, b):
            return a[0] * b[1] - a[1] * b[0]

        div = det(xdiff, ydiff)
        if div == 0:
            raise Exception('lines do not intersect')

        d = (det((self._p1.x, self._p1.y), (self._p2.x, self._p2.y)),
             det((line._p1.x, line._p1.y), (line._p2.x, line._p2.y)))
        x = det(d, xdiff) / div
        y = det(d, ydiff) / div
        return int(round(x)), int(round(y))

    def __len__(self):
        res = math.sqrt(math.pow(self._p2.x - self._p1.x, decimal(2)) +
                        math.pow(self._p2.y - self._p1.y, decimal(2)))
        return int(round(res))

    def length(self):
        res = math.sqrt(math.pow(self._p2.x - self._p1.x, decimal(2)) +
                        math.pow(self._p2.y - self._p1.y, decimal(2)))
        return decimal(res)

    def aslist(self):
        return [[float(self._p1.x), float(self._p1.y)], [float(self._p1.x), float(self._p2.y)]]

    @property
    def angle(self):
        r = math.atan2(self._p2.y - self._p1.y, self._p2.x - self._p1.x)
        angle = math.degrees(r)

        if angle < 0:
            angle += 360.0

        return decimal(angle)

    def point_from_start(self, distance):
        r = math.radians(self.angle)

        x = self._p1.x + decimal(distance) * decimal(math.cos(r))
        y = self._p1.y + decimal(distance) * decimal(math.sin(r))

        return Point(x, y)

    def point_from_end(self, distance):
        r = math.radians(self.angle + 180)

        x = self._p2.x + decimal(distance) * decimal(math.cos(r))
        y = self._p2.y + decimal(distance) * decimal(math.sin(r))

        return Point(x, y)

    def distance_from_start(self, p: Point):
        angle = self.angle

        line = Line(p, self._p1)
        if line.angle not in (angle, angle + 180, angle - 180):
            raise ValueError('point is not on line')

        return line.length()

    def distance_from_end(self, p: Point):
        angle = self.angle

        line = Line(p, self._p2)
        if line.angle not in (angle, angle + 180, angle - 180):
            raise ValueError('point is not on line')

        return line.length()

    def distance_from_line(self, p: Point):
        x_diff = self._p2.x - self._p1.x
        y_diff = self._p2.y - self._p1.y
        numerator = abs(y_diff * p.x - x_diff * p.y + self._p2.x * self._p1.y - self._p2.y * self._p1.x)
        denominator = decimal(math.sqrt(y_diff ** 2 + x_diff ** 2))
        return numerator / denominator

    def get_rotated_line(self, angle, pivot=None):
        if pivot is None:
            pivot = self.point_from_start(self.length() / decimal(2))

        angle = math.radians(angle)

        p1 = self._rotate_point(pivot, self._p1, angle)
        p2 = self._rotate_point(pivot, self._p2, angle)

        return Line(p1, p2)

    @property
    def start(self):
        return self.x1, self.y1

    @property
    def end(self):
        return self.x2, self.y2

    @property
    def center(self):
        return self.point_from_start(len(self) / 2)

    def get_parallel_line(self, offset):
        offset = decimal(offset)

        offset /= decimal(2)

        r = decimal(math.radians(self.angle + decimal(90)))
        center = self.center
        x, y = center.x, center.y

        x += offset * decimal(math.cos(r))
        y += offset * decimal(math.sin(r))

        line = self.get_rotated_line(decimal(180), Point(x, y))
        line._p1, line._p2 = line._p2, line._p1

        return line

    def __str__(self):
        res = [
            '',
            f'    x1: {self.x1}',
            f'    y1: {self.y1}',
            f'    x2: {self.x2}',
            f'    y2: {self.y2}',
            f'    angle: {self.angle}',
            f'    length: {len(self)}',
        ]

        return '\n'.join(res)

    @staticmethod
    def _rotate_point(origin: Point, point: Point, angle):
        ox, oy = origin.x, origin.y
        px, py = point.x, point.y

        cos = decimal(math.cos(angle))
        sin = decimal(math.sin(angle))

        x = px - ox
        y = py - oy

        qx = ox + (cos * x) - (sin * y)
        qy = oy + (sin * x) + (cos * y)
        return Point(qx, qy)


class WireSection:

    def __init__(self, parent, p1: Point, p2: Point):
        self.parent: "Wire" = parent
        self.p1 = p1
        self.p2 = p2

    def update_wire_info(self):
        self.parent.update_wire_info()

    def is_p1_end_grabbed(self, p):
        x, y = self.p1.x, self.p1.y
        x1 = x - 5
        x2 = x + 5
        y1 = y - 5
        y2 = y + 5
        x, y = p.x, p.y
        return x1 <= x <= x2 and y1 <= y <= y2

    def is_p2_end_grabbed(self, p):
        x, y = self.p2.x, self.p2.y
        x1 = x - 5
        x2 = x + 5
        y1 = y - 5
        y2 = y + 5
        x, y = p.x, p.y
        return x1 <= x <= x2 and y1 <= y <= y2

    def __contains__(self, other: Point):
        line1 = Line(self.p1, self.p2)
        half_size = decimal(self.parent.wire_info.pixel_width) / decimal(2.0) + decimal(1)

        line2 = line1.get_parallel_line(half_size)
        line3 = line1.get_parallel_line(-half_size)

        x1, y1, x2, y2 = line2.x1, line2.y1, line3.x2, line3.y2

        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)

        print(x1, x2, y1, y2, other.x, other.y)

        return x1 <= other.x <= x2 and y1 <= other.y <= y2

    def stripe_lines(self):
        line = Line(self.p1, self.p2)
        line_angle = line.angle
        stripe_line = Line(Point(68, 0), Point(68 - 32, 24))
        stripe_angle = line_angle + stripe_line.angle
        line_len = len(line)
        step = 40

        wire_size = self.parent.wire_info.pixel_width

        curr_dist = 0
        points = []

        while curr_dist < line_len - step:
            curr_dist += step

            p = line.point_from_start(curr_dist)
            s1 = Line(p, None, angle=stripe_angle, length=max(wire_size, 1))
            s2 = Line(p, None, angle=stripe_angle + 180, length=max(wire_size, 1))

            points.append([[s1.x2, s1.y2], [s2.x2, s2.y2]])

        return points

    def aslist(self):
        return Line(self.p1, self.p2).aslist()

    def length(self):
        return Line(self.p1, self.p2).length()

    def get_angle(self):
        return Line(self.p1, self.p2).angle

    @staticmethod
    def _rotate_point(origin, point, angle):
        ox, oy = origin.x, origin.y
        px, py = point.x, point.y

        cos = decimal(math.cos(angle))
        sin = decimal(math.sin(angle))

        x = px - ox
        y = py - oy

        qx = ox + (cos * x) - (sin * y)
        qy = oy + (sin * x) + (cos * y)
        return Point(qx, qy)

    def move_p2(self, p):
        line = Line(self.p1, p)
        angle = line.angle

        if 0 <= angle < 45:
            line = Line(self.p1, None, 0, line.length())
        if 45 <= angle < 135:
            line = Line(self.p1, None, 90, line.length())
        elif 135 <= angle < 225:
            line = Line(self.p1, None, 180, line.length())
        elif 225 <= angle <= 315:
            line = Line(self.p1, None, 270, line.length())
        else:
            line = Line(self.p1, None, 0, line.length())

        self.p2 = line._p2

    def move(self, p):

        p1 = self.p1.copy()
        p2 = self.p2.copy()

        p1.move(p)
        p2.move(p)

        p3 = None
        p4 = None

        for section in self.parent._sections:
            if section == self:
                continue

            if section.p2 == self.p1:
                p3 = section.p1

            if section.p1 == self.p2:
                p4 = section.p2

        if p3 is not None:
            line = Line(p3, p1)
            angle = line.angle

            if 0 <= angle < 45:
                line = Line(p3, None, 0, line.length())
            if 45 <= angle < 135:
                line = Line(p3, None, 90, line.length())
            elif 135 <= angle < 225:
                line = Line(p3, None, 180, line.length())
            elif 225 <= angle <= 315:
                line = Line(p3, None, 270, line.length())
            else:
                line = Line(p3, None, 0, line.length())

            p1.x = decimal(line.x2)
            p1.y = decimal(line.y2)
        if p4 is not None:
            line = Line(p4, p2)
            angle = line.angle

            if 0 <= angle < 45:
                line = Line(p4, None, 0, line.length())
            if 45 <= angle < 135:
                line = Line(p4, None, 90, line.length())
            elif 135 <= angle < 225:
                line = Line(p4, None, 180, line.length())
            elif 225 <= angle <= 315:
                line = Line(p4, None, 270, line.length())
            else:
                line = Line(p4, None, 0, line.length())

            p2.x = decimal(line.x2)
            p2.y = decimal(line.y2)

        line = Line(p1, p2)
        angle = line.angle

        if int(round(angle)) in (0, 90, 180, 270, 360):
            self.p1.x = decimal(p1.x)
            self.p1.y = decimal(p1.y)
            self.p2.x = decimal(p2.x)
            self.p2.y = decimal(p2.y)
        else:
            print(angle)


class Wire:

    def __init__(self, parent):
        self.parent: "Frame" = parent
        self.wire_info = WireInfo()
        self._sections: list[WireSection] = []
        self._is_selected = False

    def new_section(self, p):
        if self._sections:
            section = self._sections[-1]
            new_section = WireSection(self, section.p2, p)
        else:
            new_section = WireSection(self, p.copy(), p)

        self._sections.append(new_section)
        return new_section

    def remove_last_section(self):
        self._sections.pop(-1)

    def draw_selected(self, gc, selected):
        x1 = selected.p1.x
        y1 = selected.p1.y
        x2 = selected.p2.x
        y2 = selected.p2.y

        path = gc.CreatePath()
        path.MoveToPoint(float(round(x1, 1)), float(round(y1, 1)))
        path.AddLineToPoint(float(round(x2, 1)), float(round(y2, 1)))
        path.CloseSubpath()
        gc.StrokePath(path)

    def draw(self, gc, mask_gc, selected):
        pen1 = wx.Pen(self.wire_info.color, self.wire_info.pixel_width)
        pen1.SetJoin(wx.JOIN_MITER)

        mask_pen = wx.Pen(wx.BLACK, self.wire_info.pixel_width)
        mask_pen.SetJoin(wx.JOIN_MITER)

        pen2 = wx.Pen(self.wire_info.stripe_color, max(int(self.wire_info.pixel_width / 3.0), 2))

        path = gc.CreatePath()
        mask_path = mask_gc.CreatePath()

        is_selected = self.is_selected()
        mask_gc.SetPen(wx.TRANSPARENT_PEN)

        for i, section in enumerate(self._sections):
            if section == selected:
                continue

            mask_path.MoveToPoint(float(round(section.p1.x, 1)), float(round(section.p1.y, 1)))
            mask_path.AddLineToPoint(float(round(section.p2.x, 1)), float(round(section.p2.y, 1)))

            path.MoveToPoint(float(round(section.p1.x, 1)), float(round(section.p1.y, 1)))
            path.AddLineToPoint(float(round(section.p2.x, 1)), float(round(section.p2.y, 1)))

            if is_selected:

                if i == 0:
                    mask_gc.DrawEllipse(float(round(section.p1.x - decimal(6), 1)),
                                        float(round(section.p1.y - decimal(6), 1)),
                                        12.0, 12.0)

                mask_gc.DrawEllipse(float(round(section.p2.x - decimal(6), 1)),
                                    float(round(section.p2.y - decimal(6), 1)),
                                    12.0, 12.0)

        mask_path.CloseSubpath()
        mask_gc.SetPen(mask_pen)
        mask_gc.StrokePath(path)

        gc.SetPen(pen1)
        path.CloseSubpath()
        gc.StrokePath(path)

        path = gc.CreatePath()

        gc.SetPen(wx.TRANSPARENT_PEN)

        for i, section in enumerate(self._sections):
            if section == selected:
                continue

            for start, stop in section.stripe_lines():
                path.MoveToPoint(*start)
                path.AddLineToPoint(*stop)

            if is_selected:
                if i == 0:
                    gc.DrawEllipse(float(round(section.p1.x - decimal(6), 1)),
                                   float(round(section.p1.y - decimal(6), 1)),
                                   12.0, 12.0)

                gc.DrawEllipse(float(round(section.p2.x - decimal(6), 1)),
                               float(round(section.p2.y - decimal(6), 1)),
                               12.0, 12.0)

        path.CloseSubpath()
        gc.SetPen(pen2)
        gc.StrokePath(path)

    def is_selected(self, flag=None):
        if flag is None:
            return self._is_selected

        self._is_selected = flag

    def update_wire_info(self):
        length = []
        for section in self._sections:
            length.append(section.length())

        length = float(sum(length) / decimal(1000.0))
        self.wire_info.length_m = length
        self.parent.wire_info_ctrl.update_wire_length()

    def get_section(self, p):
        for section in self._sections:
            if p in section:
                print(True)
                return section

    def __len__(self):
        return len(self._sections)


class HSizer(wx.BoxSizer):

    def __init__(self, parent, text, ctrl, suffix=None, in_panel=False):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)

        if in_panel:
            panel = wx.Panel(parent, wx.ID_ANY, style=wx.BORDER_NONE)
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            if text is not None:
                st = wx.StaticText(panel, wx.ID_ANY, label=text)
                sizer.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            ctrl.Reparent(panel)
            sizer.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            if isinstance(suffix, str):
                suffix = wx.StaticText(panel, wx.ID_ANY, label=suffix)
                sizer.Add(suffix, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
            elif suffix is not None:
                suffix.Reparent(panel)
                sizer.Add(suffix, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)

            panel.SetSizer(sizer)
            self.Add(panel, 0)

        else:
            if text is not None:
                st = wx.StaticText(parent, wx.ID_ANY, label=text)
                self.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            self.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            if isinstance(suffix, str):
                suffix = wx.StaticText(parent, wx.ID_ANY, label=suffix)

            if suffix is not None:
                self.Add(suffix, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)


class WireInfoPanel(wx.Panel):

    def on_material(self, evt: wx.CommandEvent):
        value = evt.GetString()
        self.wire_info.material = value
        self.update_wire()
        evt.Skip()

    def on_shielded(self, evt: wx.CommandEvent):
        value = bool(evt.GetSelection())
        self.wire_info.is_shielded = value
        self.update_wire()
        evt.Skip()

    def on_volts(self, evt: wx.SpinDoubleEvent):
        value = evt.GetValue()
        self.wire_info.volts = value
        self.update_wire_length()
        evt.Skip()

    def on_volt_drop(self, evt: wx.SpinDoubleEvent):
        value = evt.GetValue()
        self.wire_info.allowed_voltage_drop = value
        self.update_wire_length()
        evt.Skip()

    def on_awg(self, evt: wx.SpinEvent):
        value = evt.GetInt()
        self.wire_info.awg = value
        self.update_wire()
        self.update_editor()
        evt.Skip()

    def on_load(self, evt: wx.SpinDoubleEvent):
        value = evt.GetValue()
        self.wire_info.load = value
        self.update_wire_length()
        evt.Skip()

    def on_conductor(self, evt: wx.SpinEvent):
        value = evt.GetInt()
        self.wire_info.num_conductors = value
        self.update_wire_length()
        evt.Skip()

    def on_mm2(self, evt: wx.SpinDoubleEvent):
        value = evt.GetValue()
        self.wire_info.mm2 = value
        self.update_wire()
        self.update_editor()
        evt.Skip()

    def on_color1(self, evt: wx.ColourPickerEvent):
        value = evt.GetColour()
        self.wire_info.color = value
        self.update_wire()
        self.update_editor()
        evt.Skip()

    def on_color2(self, evt: wx.ColourPickerEvent):
        value = evt.GetColour()
        self.wire_info.stripe_color = value
        self.update_wire()
        self.update_editor()
        evt.Skip()

    def update_editor(self):
        def _do():
            self.GetParent().update_bitmap()
            self.GetParent().Update()
            self.GetParent().Refresh()

        wx.CallAfter(_do)

    def update_wire_length(self):
        self.length_ft_ctrl.SetLabel(str(round(self.wire_info.length_ft, 4)))
        self.length_m_ctrl.SetLabel(str(round(self.wire_info.length_m, 4)))
        self.length_cm_ctrl.SetLabel(str(round(self.wire_info.length_m * 100.0, 4)))
        self.voltage_drop_ctrl.SetLabel(str(round(self.wire_info.voltage_drop, 2)))
        self.recommended_awg_ctrl.SetLabel(str(self.wire_info.recommended_awg))

        mm2 = self.wire_info.recommended_mm2
        if mm2 is None:
            self.recommended_mm2_ctrl.SetLabel(str(mm2))
        else:
            self.recommended_mm2_ctrl.SetLabel(str(round(mm2, 4)))

        self.weight_lb_ctrl.SetLabel(str(round(self.wire_info.weight_lb, 4)))
        self.weight_kg_ctrl.SetLabel(str(round(self.wire_info.weight_kg, 4)))
        self.resistance_ctrl.SetLabel(str(round(self.wire_info.resistance, 4)))

    def update_wire(self):
        if self.wire_info is None:
            return

        self.set_wire(self.wire_info)

    def set_wire(self, wi: WireInfo):
        self.material_ctrl.SetStringSelection(wi.material)
        self.shielded_ctrl.SetSelection(int(wi.is_shielded))
        self.volts_ctrl.SetValue(wi.volts)
        self.volt_drop_ctrl.SetValue(wi.allowed_voltage_drop)
        self.conductor_ctrl.SetValue(wi.num_conductors)
        self.awg_ctrl.SetValue(wi.awg)
        self.mm2_ctrl.SetValue(wi.mm2)
        self.od_mm_ctrl.SetLabel(str(round(wi.od_mm, 4)))
        self.voltage_drop_ctrl.SetLabel(str(round(wi.voltage_drop, 2)))
        self.recommended_awg_ctrl.SetLabel(str(wi.recommended_awg))

        mm2 = wi.recommended_mm2
        if mm2 is None:
            self.recommended_mm2_ctrl.SetLabel(str(mm2))
        else:
            self.recommended_mm2_ctrl.SetLabel(str(round(mm2, 4)))

        self.conductivity_ctrl.SetLabel(str(round(wi.conductivity, 4)))
        self.resistivity_ctrl.SetLabel(str(round(wi.resistivity, 4)))
        self.diameter_mm_ctrl.SetLabel(str(round(wi.diameter_mm, 4)))
        self.diameter_inch_ctrl.SetLabel(str(round(wi.diameter_inch, 4)))
        self.in2_ctrl.SetLabel(str(round(wi.in2, 4)))
        self.length_ft_ctrl.SetLabel(str(round(wi.length_ft, 4)))
        self.length_m_ctrl.SetLabel(str(round(wi.length_m, 4)))
        self.length_cm_ctrl.SetLabel(str(round(wi.length_m * 100.0, 4)))
        self.length_cm_ctrl.SetLabel(str(round(wi.length_m * 100.0, 4)))
        self.weight_lb_ctrl.SetLabel(str(round(wi.weight_lb, 4)))
        self.weight_kg_ctrl.SetLabel(str(round(wi.weight_kg, 4)))
        self.resistance_ctrl.SetLabel(str(round(wi.resistance, 4)))
        self.color1_ctrl.SetColour(wi.color)
        self.color2_ctrl.SetColour(wi.stripe_color)

        self.wire_info = wi

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.wire_info: WireInfo = None

        material_choices = [item[1] for item in WireInfo.material_choices]
        material_ctrl = self.material_ctrl = wx.Choice(self, wx.ID_ANY, choices=material_choices)
        material_suffix_ctrl = self.material_suffix_ctrl = wx.StaticText(self, wx.ID_ANY, label='Ag/Cu')
        material_ctrl.Bind(wx.EVT_CHOICE, self.on_material)

        shielded_ctrl = self.shielded_ctrl = wx.Choice(self, wx.ID_ANY, choices=['No', 'Yes'])
        shielded_ctrl.Bind(wx.EVT_CHOICE, self.on_shielded)

        volts_ctrl = self.volts_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value='12.0', min=3.3, max=240.0, initial=12.0, inc=0.1)
        volts_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_volts)

        load_ctrl = self.load_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', min=0.0, max=300.0, initial=0.0, inc=0.1)
        load_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_load)

        volt_drop_ctrl = self.volt_drop_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', min=0.0, max=3.0, initial=0.0, inc=0.1)
        volt_drop_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_volt_drop)

        conductor_ctrl = self.conductor_ctrl = wx.SpinCtrl(self, wx.ID_ANY, value='1', min=1, max=7, initial=1)
        conductor_ctrl.Bind(wx.EVT_SPINCTRL, self.on_conductor)

        awg_ctrl = self.awg_ctrl = wx.SpinCtrl(self, wx.ID_ANY, value='22', min=0, max=30, initial=22)
        awg_ctrl.Bind(wx.EVT_SPINCTRL, self.on_awg)

        mm2_ctrl = self.mm2_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.3255', min=0.0509, max=53.4751, initial=0.3255, inc=0.0001)
        mm2_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_mm2)

        color1_ctrl = self.color1_ctrl = wx.ColourPickerCtrl(self, wx.ID_ANY, size=(75, -1))
        color1_ctrl.Bind(wx.EVT_COLOURPICKER_CHANGED, self.on_color1)

        color2_ctrl = self.color2_ctrl = wx.ColourPickerCtrl(self, wx.ID_ANY, size=(75, -1))
        color2_ctrl.Bind(wx.EVT_COLOURPICKER_CHANGED, self.on_color2)

        od_mm_ctrl = self.od_mm_ctrl = wx.StaticText(self, wx.ID_ANY, label='0.0000')
        voltage_drop_ctrl = self.voltage_drop_ctrl = wx.StaticText(self, wx.ID_ANY, label='0.0000')
        recommended_awg_ctrl = self.recommended_awg_ctrl = wx.StaticText(self, wx.ID_ANY, label='00')
        recommended_mm2_ctrl = self.recommended_mm2_ctrl = wx.StaticText(self, wx.ID_ANY, label='00.0000')
        conductivity_ctrl = self.conductivity_ctrl = wx.StaticText(self, wx.ID_ANY, label='0.0000')
        resistivity_ctrl = self.resistivity_ctrl = wx.StaticText(self, wx.ID_ANY, label='0.0000')
        diameter_mm_ctrl = self.diameter_mm_ctrl = wx.StaticText(self, wx.ID_ANY, label='00.0000')
        diameter_inch_ctrl = self.diameter_inch_ctrl = wx.StaticText(self, wx.ID_ANY, label='0.0000')
        in2_ctrl = self.in2_ctrl = wx.StaticText(self, wx.ID_ANY, label='0.0000')
        length_ft_ctrl = self.length_ft_ctrl = wx.StaticText(self, wx.ID_ANY, label='000.0000')
        length_m_ctrl = self.length_m_ctrl = wx.StaticText(self, wx.ID_ANY, label='000.0000')
        length_cm_ctrl = self.length_cm_ctrl = wx.StaticText(self, wx.ID_ANY, label='000.0000')
        weight_lb_ctrl = self.weight_lb_ctrl = wx.StaticText(self, wx.ID_ANY, label='000.0000')
        weight_kg_ctrl = self.weight_kg_ctrl = wx.StaticText(self, wx.ID_ANY, label='000.0000')
        resistance_ctrl = self.resistance_ctrl = wx.StaticText(self, wx.ID_ANY, label='000.0000')

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddMany((
            (HSizer(self, 'Material:', material_ctrl, material_suffix_ctrl), 0),
            (HSizer(self, 'Shielded:', shielded_ctrl), 0),
            (HSizer(self, 'Conductor Count:', conductor_ctrl), 0),
            (HSizer(self, 'Load:', load_ctrl, 'A'), 0),
            (HSizer(self, 'Length:', length_ft_ctrl, 'ft', in_panel=True), 0),
            (HSizer(self, 'Length:', length_m_ctrl, 'm', in_panel=True), 0),
            (HSizer(self, 'Length:', length_cm_ctrl, 'cm', in_panel=True), 0),
            (HSizer(self, 'Volts:', volts_ctrl, 'V'), 0),
            (HSizer(self, 'Max Drop:', volt_drop_ctrl, 'V'), 0),
            (HSizer(self, 'Actual Drop:', voltage_drop_ctrl, 'V', in_panel=True), 0),
            (HSizer(self, 'Size:', awg_ctrl, 'AWG'), 0),
            (HSizer(self, 'Size:', mm2_ctrl, 'mm²'), 0),
            (HSizer(self, 'Size:', in2_ctrl, 'in²'), 0),
            (HSizer(self, 'Primary Color:', color1_ctrl), 0),
            (HSizer(self, 'Stripe Color:', color2_ctrl), 0),
            (HSizer(self, 'Diameter (total):', od_mm_ctrl, 'mm'), 0),
            (HSizer(self, 'Recommended Size:', recommended_awg_ctrl, 'AWG', in_panel=True), 0),
            (HSizer(self, 'Recommended Size:', recommended_mm2_ctrl, 'mm²', in_panel=True), 0),
            (HSizer(self, 'Conductivity:', conductivity_ctrl, 'S/m'), 0),
            (HSizer(self, 'Resistivity:', resistivity_ctrl, '(Ω x mm2)/m'), 0),
            (HSizer(self, 'Conductor Diameter:', diameter_mm_ctrl, 'mm'), 0),
            (HSizer(self, 'Conductor Diameter:', diameter_inch_ctrl, 'in'), 0),
            (HSizer(self, 'Weight:', weight_lb_ctrl, 'lb', in_panel=True), 0),
            (HSizer(self, 'Weight:', weight_kg_ctrl, 'kg', in_panel=True), 0),
            (HSizer(self, 'Resistance:', resistance_ctrl, 'Ω', in_panel=True), 0)
        ))

        self.SetSizer(sizer)


class Frame(wx.Frame):

    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, size=(1920, 1080))

        buf = bytearray([0] * (2000 * 2000 * 4))
        self.bmp = wx.Bitmap.FromBufferRGBA(2000, 2000, buf)

        self.scale = 1.0
        self.last_scale = 1.0

        self.wires: list[Wire] = []
        self._selected: WireSection = None
        self.last_pos: Point = None
        self._offset = Point(0, 0)
        self._grabbed_point = None
        self._o_grab_point = None
        self._continue_wire = False

        panel = self.panel = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_NONE)

        panel.Bind(wx.EVT_MOUSEWHEEL, self.on_mousewheel)
        panel.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        panel.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        panel.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        panel.Bind(wx.EVT_RIGHT_UP, self.on_right_up)
        panel.Bind(wx.EVT_MOTION, self.on_motion)
        panel.Bind(wx.EVT_PAINT, self.on_paint)
        panel.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)

        self.wire_info_ctrl = WireInfoPanel(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(panel, 10, wx.EXPAND)
        hsizer.Add(self.wire_info_ctrl, 2, wx.EXPAND)
        sizer.Add(hsizer, 1, wx.EXPAND)

        self.points = []
        self.point_list = []
        for x in range(0, 2020, 20):
            for y in range(0, 2020, 20):
                self.points.append(Point(x, y))
                self.point_list.append([x, y])

        self.SetSizer(sizer)
        self.update_bitmap()

    def update(self):
        def _do():
            self.Update()
            self.Refresh()

        wx.CallAfter(_do)

    def on_mousewheel(self, evt: wx.MouseEvent):
        rotation = evt.GetWheelRotation() / 2000

        self.scale += rotation

        if self.scale < 0.2:
            self.scale = 0.2
        elif self.scale > 10.0:
            self.scale = 10.0

        x, y = evt.GetPosition()

        self._offset.x -= decimal(x) * decimal(rotation) / decimal(self.scale)
        self._offset.y -= decimal(y) * decimal(rotation) / decimal(self.scale)
        # if self._offset.x > 0:
        #     self._offset.x = decimal(0)
        # if self._offset.y > 0:
        #     self._offset.y = decimal(0)
        #
        # cw, ch = self.panel.GetSize()
        # bw, bh = self.bmp.GetSize()
        # w = cw - bw
        # h = ch - bh
        #
        # if self._offset.x < w:
        #     self._offset.x = decimal(w)
        # if self._offset.y < h:
        #     self._offset.y = decimal(h)

        self.update()
        evt.Skip()

    def update_bitmap(self):
        mask_dc = wx.MemoryDC()
        buf = bytearray([0] * (2000 * 2000 * 4))
        mask_bmp = wx.Bitmap.FromBufferRGBA(2000, 2000, buf)
        mask_dc.SelectObject(mask_bmp)
        mask_gc = wx.GraphicsContext.Create(mask_dc)
        mask_gc.SetBrush(wx.Brush(wx.BLACK))

        dc = wx.MemoryDC()
        buf = bytearray([0] * (2000 * 2000 * 4))
        bmp = wx.Bitmap.FromBufferRGBA(2000, 2000, buf)
        dc.SelectObject(bmp)
        gc = wx.GraphicsContext.Create(dc)

        for wire in self.wires:
            wire.draw(gc, mask_gc, self._selected)

        mask_dc.SelectObject(wx.NullBitmap)
        mask = wx.Mask(mask_bmp, wx.BLACK)

        dc.SelectObject(wx.NullBitmap)
        bmp.SetMask(mask)

        buf = bytearray([0] * (2000 * 2000 * 4))
        new_bmp = wx.Bitmap.FromBufferRGBA(2000, 2000, buf)
        dc.SelectObject(new_bmp)
        gcdc = wx.GCDC(dc)
        gcdc.SetBrush(wx.TRANSPARENT_BRUSH)
        gcdc.SetPen(wx.Pen(wx.BLACK, 2))
        gcdc.DrawPointList(self.point_list)
        gcdc.DrawBitmap(bmp, 0, 0, useMask=True)

        dc.SelectObject(wx.NullBitmap)

        gcdc.Destroy()
        del gcdc

        self.bmp.Destroy()
        self.bmp = new_bmp

    def on_paint(self, evt):
        pdc = wx.BufferedPaintDC(self.panel)
        gcdc = wx.GCDC(pdc)
        gcdc.Clear()
        gcdc.SetUserScale(self.scale, self.scale)
        gcdc.DrawBitmap(self.bmp, int(self._offset.x * decimal(self.scale)), int(self._offset.y * decimal(self.scale)))

        if self._selected is not None:
            gcdc.SetPen(wx.Pen(wx.BLACK, width=3, style=wx.PENSTYLE_SHORT_DASH))
            gcdc.SetBrush(wx.TRANSPARENT_BRUSH)

            gc = gcdc.GetGraphicsContext()
            self._selected.parent.draw_selected(gc, self._selected)

        gcdc.Destroy()
        del gcdc

        evt.Skip()

    def on_erase_background(self, _):
        pass

    def on_left_down(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()

        p = Point(decimal(x) * decimal(self.scale) + self._offset.x, decimal(y) * decimal(self.scale) + self._offset.y)

        if self._selected is not None and self._grabbed_point is not None:
            self._continue_wire = True
            wire = self.wires[-1]
            self._selected = wire.new_section(p)
            self._grabbed_point = self._selected.p2
            self._o_grab_point = self._selected.p2.copy()
            self.last_pos = p
            self.update_bitmap()
            self.update()
        elif self._selected is None:
            for wire in self.wires:
                section = wire.get_section(p)
                if section is not None:
                    wire.is_selected(True)
                    self._selected = section
                    self.last_pos = p
                    if section.is_p1_end_grabbed(p):
                        self._grabbed_point = section.p1
                        self._o_grab_point = section.p1.copy()
                    elif section.is_p2_end_grabbed(p):
                        self._grabbed_point = section.p2
                        self._o_grab_point = section.p2.copy()
                    else:
                        self._grabbed_point = None

                    def _do():
                        self.update_bitmap()
                        self.update()

                    wx.CallAfter(_do)
                    break

        evt.Skip()

    def on_left_up(self, evt):
        if self._selected is None:
            x, y = evt.GetPosition()

            p = Point(decimal(x) * decimal(self.scale) + self._offset.x, decimal(y) * decimal(self.scale) + self._offset.y)
            wire = Wire(self)
            self.wire_info_ctrl.set_wire(wire.wire_info)
            self._selected = wire.new_section(p)
            self._grabbed_point = self._selected.p2
            self._o_grab_point = self._selected.p2.copy()
            self.last_pos = p
            self.wires.append(wire)
            self.update_bitmap()
            self.update()

        elif not self._continue_wire and self._grabbed_point is not None:
            self._selected.parent.is_selected(False)
            self._selected = None
            self._grabbed_point = None

        def _do():
            self.update_bitmap()
            self.update()

        wx.CallAfter(_do)
        evt.Skip()

    def on_right_down(self, evt):
        if self._selected is not None:
            self._selected = None
            self._grabbed_point = None
            self._continue_wire = False

            if self._grabbed_point is not None:
                self.wires[-1].remove_last_section()

            if len(self.wires[-1]) == 0:
                self.wires.pop(-1)

            def _do():
                self.update_bitmap()
                self.update()

            wx.CallAfter(_do)

        x, y = evt.GetPosition()
        self.last_pos = Point(x, y)

        evt.Skip()

    def on_right_up(self, evt):
        evt.Skip()

    def on_motion(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        p = Point(decimal(x) * decimal(self.scale) + self._offset.x, decimal(y) * decimal(self.scale) + self._offset.y)
        if evt.RightIsDown():
            diff = p - self.last_pos
            self._offset += diff
            if self._offset.x > 0:
                self._offset.x = decimal(0)
            if self._offset.y > 0:
                self._offset.y = decimal(0)

            cw, ch = self.panel.GetSize()
            bw, bh = self.bmp.GetSize()
            w = cw - bw
            h = ch - bh

            if self._offset.x < w:
                self._offset.x = decimal(w)
            if self._offset.y < h:
                self._offset.y = decimal(h)

            self.last_pos = p
            self.update()
        elif self._selected is not None and self._grabbed_point is not None:
            self._selected.move_p2(p)

            def _do():
                self._selected.update_wire_info()
            wx.CallAfter(_do)

            self.last_pos = p
            self.update()

        elif self._selected is not None and evt.LeftIsDown():
            diff = p - self.last_pos
            self._selected.move(diff)
            self.last_pos = p

            def _do():
                self.update_bitmap()
                self.update()

            wx.CallAfter(_do)

        evt.Skip()


app = wx.App()

frame = Frame()
frame.Show()

app.MainLoop()
