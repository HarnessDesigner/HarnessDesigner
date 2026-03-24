import uuid

from .base import BaseMixin
from ....geometry import angle as _angle


class Angle2DMixin(BaseMixin):
    _angle2d_db_id: str = None

    def __update_angle2d(self, angle: _angle.Angle):
        quat = list(angle.as_quat_float)
        euler_angle = list(angle.as_euler_float)

        self._table.update(self._db_id, quat2d=str(quat))
        self._table.update(self._db_id, angle2d=str(euler_angle))

    @property
    def angle2d(self) -> _angle.Angle:
        quat = eval(self._table.select('quat2d', id=self._db_id)[0][0])
        euler_angle = eval(self._table.select('angle2d', id=self._db_id)[0][0])

        if self._angle2d_db_id is None:
            self._angle2d_db_id = str(uuid.uuid4())

        angle = _angle.Angle.from_quat(quat, euler_angle, db_id=self._angle2d_db_id)
        angle.bind(self.__update_angle2d)

        return angle
