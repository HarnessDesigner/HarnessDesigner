import uuid
from ....ui.editor_obj import prop_grid as _prop_grid

from .base import BaseMixin
from ....geometry import angle as _angle


class Angle3DMixin(BaseMixin):
    _angle3d_db_id: str = None

    def __update_angle3d(self, angle: _angle.Angle):
        quat = list(angle.as_quat_float)
        euler_angle = list(angle.as_euler_float)

        self._table.update(self._db_id, quat3d=str(quat))
        self._table.update(self._db_id, angle3d=str(euler_angle))

    @property
    def angle3d(self) -> _angle.Angle:
        quat = eval(self._table.select('quat3d', id=self._db_id)[0][0])
        euler_angle = eval(self._table.select('angle3d', id=self._db_id)[0][0])

        if self._angle3d_db_id is None:
            self._angle3d_db_id = str(uuid.uuid4())

        angle = _angle.Angle.from_quat(quat, euler_angle, db_id=self._angle3d_db_id)
        angle.bind(self.__update_angle3d)

        return angle

    @property
    def _angle3d_propgrid(self) -> _prop_grid.Property:
        angle = self.angle3d

        group = _prop_grid.Property('Angle 3D', 'angle3d')
        x = _prop_grid.FloatProperty(
            'X', 'x', angle.x, min_value=-180.0,
            max_value=180.0, increment=0.01, units='°')

        y = _prop_grid.FloatProperty(
            'Y', 'y', angle.y,  min_value=-180.0,
            max_value=180.0, increment=0.01, units='°')

        z = _prop_grid.FloatProperty(
            'Z', 'z', angle.z, min_value=-180.0,
            max_value=180.0, increment=0.01, units='°')

        group.Append(x)
        group.Append(y)
        group.Append(z)

        return group
