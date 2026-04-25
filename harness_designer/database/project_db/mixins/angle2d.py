import uuid
from ....ui.editor_obj import prop_grid as _prop_grid

from .base import BaseMixin
from ....geometry import angle as _angle


class Angle2DMixin(BaseMixin):
    _angle2d_db_id: str = None

    def _update_angle2d(self, angle: _angle.Angle):
        quat = list(angle.as_quat_float)
        euler_angle = list(angle.as_euler_float)

        self._table.update(self._db_id, quat2d=str(quat))
        self._table.update(self._db_id, angle2d=str(euler_angle))
        self._populate('angle2d')

    @property
    def angle2d(self) -> _angle.Angle:
        quat = eval(self._table.select('quat2d', id=self._db_id)[0][0])
        euler_angle = eval(self._table.select('angle2d', id=self._db_id)[0][0])

        if self._angle2d_db_id is None:
            self._angle2d_db_id = str(uuid.uuid4())

        angle = _angle.Angle.from_quat(quat, euler_angle, db_id=self._angle2d_db_id)
        angle.bind(self._update_angle2d)

        return angle


class Angle2DControl(_prop_grid.FloatProperty):

    def __init__(self, parent):
        self.db_obj: Angle2DMixin = None

        super().__init__(parent, '2D Angle', min_value=-180.0, max_value=180.0, increment=0.01, units='°')

        self.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_angle)

    def _on_angle(self, evt):
        self.db_obj.angle2d.z = evt.GetValue()

    def set_obj(self, db_obj: Angle2DMixin):
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue(0.0)
            self.Enable(False)
        else:
            self.SetValue(db_obj.angle2d.z)
            self.Enable(True)
