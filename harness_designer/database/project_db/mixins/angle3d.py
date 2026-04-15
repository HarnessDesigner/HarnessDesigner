import uuid
from ....ui.editor_obj import prop_grid as _prop_grid

from .base import BaseMixin
from ....geometry import angle as _angle


class Angle3DMixin(BaseMixin):
    _angle3d_db_id: str = None

    def _update_angle3d(self, angle: _angle.Angle):
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
        angle.bind(self._update_angle3d)

        return angle


class Angle3DControl(_prop_grid.Angle3DProperty):

    def __init__(self, parent):
        self.db_obj: Angle3DMixin = None

        super().__init__(parent, '3D Angle')

    def set_obj(self, db_obj: Angle3DMixin):
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue(None)
        else:
            self.SetValue(db_obj.angle3d)
