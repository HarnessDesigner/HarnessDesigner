from typing import Self, Callable, Union
import weakref

from .. import bases
from ..wrappers.decimal import Decimal as _decimal


class Point(bases.SetAngleBase):
    _instances = {}

    def __new__(cls, x: _decimal, y: _decimal, z: _decimal,
                project_id: int | None = None, point_id: int | None = None):

        if project_id is not None and point_id is not None:
            if (project_id, point_id) in cls._instances:
                ref = cls._instances[(project_id, point_id)]
                instance = ref()
                if instance is not None:
                    return instance

                del cls._instances[(project_id, point_id)]

        instance = super().__new__(cls, x, y, z, project_id, point_id)
        if project_id is not None and point_id is not None:
            cls._instances[(project_id, point_id)] = weakref.ref(instance, cls._remove_instance)

        return instance

    @property
    def project_id(self):
        return self._project_id

    @property
    def point_id(self):
        return self._point_id

    def add_to_db(self, project_id, point_id):
        assert (project_id, point_id) not in self._instances, 'Sanity Check'

        self._instances[(project_id, point_id)] = weakref.ref(self, self._remove_instance)

    @classmethod
    def _remove_instance(cls, ref):
        for key, value in cls._instances.items():
            if ref == value:
                break
        else:
            return

        del cls._instances[key]

    def __init__(self, x: _decimal, y: _decimal, z: _decimal | None = None,
                 project_id: int | None = None, point_id: int | None = None):

        self._project_id = project_id
        self._point_id = point_id

        if z is None:
            z = _decimal(0.0)

        self._x = x
        self._y = y
        self._z = z

        self._callbacks = []
        self._cb_disabled = False

    def __enter__(self) -> Self:
        self._cb_disabled = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cb_disabled = False
        self.__do_callbacks()

    @property
    def x(self) -> _decimal:
        return self._x

    @x.setter
    def x(self, value: _decimal):
        self._x = value
        self.__do_callbacks()

    @property
    def y(self) -> _decimal:
        return self._y

    @y.setter
    def y(self, value: _decimal):
        self._y = value
        self.__do_callbacks()

    @property
    def z(self) -> _decimal:
        return self._z

    @z.setter
    def z(self, value: _decimal):
        self._z = value
        self.__do_callbacks()

    def copy(self) -> "Point":
        return Point(self._x, self._y, self._z)

    def __do_callbacks(self):
        if self._cb_disabled:
            return

        for ref in self._callbacks[:]:
            func = ref()
            if func is None:
                self._callbacks.remove(ref)
            else:
                func(self)

    def __remove_cb(self, ref):
        try:
            self._callbacks.remove(ref)
        except ValueError:
            pass

    def Bind(self, cb: Callable[["Point"], None]) -> None:
        for ref in self._callbacks[:]:
            func = ref()
            if func is None:
                self._callbacks.remove(ref)
            elif func == cb:
                break
        else:
            ref = weakref.WeakMethod(cb, self.__remove_cb)
            self._callbacks.append(ref)

    def Unbind(self, cb: Callable[["Point"], None]) -> None:
        for ref in self._callbacks[:]:
            func = ref()
            if func is None:
                self._callbacks.remove(func)
            elif func == cb:
                self._callbacks.remove(func)
                break

    def __iadd__(self, other: "Point") -> Self:
        self._x += other.x
        self._y += other.y
        self._z += other.z

        self.__do_callbacks()

        return self

    def __add__(self, other: "Point") -> "Point":
        x1, y1, z1 = tuple(self)
        x2, y2, z2 = tuple(other)

        x = x1 + x2
        y = y1 + y2
        z = z1 + z2

        return Point(x, y, z)

    def __isub__(self, other: "Point") -> Self:
        self._x -= other.x
        self._y -= other.y
        self._z -= other.z

        self.__do_callbacks()

        return self

    def __sub__(self, other: "Point") -> "Point":
        x1, y1, z1 = tuple(self)
        x2, y2, z2 = tuple(other)

        x = x1 - x2
        y = y1 - y2
        z = z1 - z2

        return Point(x, y, z)

    def __itruediv__(self, other: _decimal) -> Self:
        self._x /= other
        self._y /= other
        self._z /= other

        self.__do_callbacks()

        return self

    def __truediv__(self, other: _decimal) -> "Point":
        x1, y1, z1 = tuple(self)

        x = x1 / other
        y = y1 / other
        z = z1 / other

        return Point(x, y, z)

    def set_x_angle(self, angle: _decimal, origin: "Point") -> None:
        self._y, self.z = self._rotate_point((self._y, self._z), angle, (origin.y, origin.z))

    def set_y_angle(self, angle: _decimal, origin: "Point") -> None:
        self._z, self.x = self._rotate_point((self._z, self._x), angle, (origin.z, origin.x))

    def set_z_angle(self, angle: _decimal, origin: "Point") -> None:
        self._x, self.y = self._rotate_point((self._x, self._y), angle, (origin.x, origin.y))

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, origin: "Point") -> None:
        self._y, self._z = self._rotate_point((self._y, self._z), x_angle, (origin.y, origin.z))
        self._z, self._x = self._rotate_point((self._z, self._x), y_angle, (origin.z, origin.x))
        self._x, self._y = self._rotate_point((self._x, self._y), z_angle, (origin.x, origin.y))
        self.__do_callbacks()

    def __eq__(self, other: "Point") -> bool:
        return other.x == self._x and other.y == self._y and other.z == self._z

    def __ne__(self, other: "Point") -> bool:
        return not self.__eq__(other)

    @property
    def as_float(self):
        return float(self._x), float(self._y), float(self._z)

    @property
    def as_int(self):
        return int(round(self._x)), int(round(self._y)), int(round(self._z))

    def __iter__(self):
        yield self._x
        yield self._y
        yield self._z
