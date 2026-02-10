
import weakref
import sys

from wxOpenGL.geometry import angle as _angle
from wxOpenGL.geometry.angle import quaternion as _quaternion


class AngleMeta(type):
    _instances = {}

    @classmethod
    def _remove_instance(cls, ref):
        for key, value in cls._instances.items():
            if ref == value:
                break
        else:
            return

        del cls._instances[key]

    def __call__(cls, q: _quaternion.Quaternion | None = None,
                 euler_angles: list[float, float, float] | None = None,
                 db_id: int | None = None):

        if db_id is not None:
            if db_id in cls._instances:
                instance = cls._instances[db_id]
            else:
                instance = super().__call__(q, euler_angles, db_id)
                cls._instances[db_id] = weakref.ref(instance, cls._remove_instance)
        else:
            instance = super().__call__(q, euler_angles, db_id)

        return instance


class Angle(_angle.Angle, metaclass=AngleMeta):

    def __init__(self, q: _quaternion.Quaternion | None = None,
                 euler_angles: list[float, float, float] | None = None,
                 db_id: int | None = None):

        self.db_id = db_id

        super().__init__(q, euler_angles)


__original_angle__ = _angle.Angle

_angle.Angle = Angle

sys.modules['wxOpenGL.geometry.angle'].Angle = Angle
