# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import uuid

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType
from ....geometry import angle as _angle
from .... import check_types as _check_types


class AnglePegboardMixin(BaseMixin):
    """Peg-board rotation, mirroring ``Angle3DMixin`` exactly -- a live,
    bindable ``Angle`` stored as redundant quaternion+Euler TEXT columns
    directly on the owning table (``quat_pegboard``/``angle_pegboard``),
    same pattern as ``quat2d``/``angle2d`` and ``quat3d``/``angle3d``.
    """
    _angle_pegboard_db_id: bytes | None = None
    _stored_angle_pegboard: _angle.Angle | DefaultStoredValueType = DefaultStoredValue
    # Per-instance flag: set True during bulk angle batch-writes so the individual
    # DB callback is suppressed while pegboard render callbacks still fire.
    _skip_db_write: bool = False

    @_check_types.do
    def _update_angle_pegboard(self, angle: _angle.Angle):
        """Update the peg-board angle.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        if self._skip_db_write:
            return

        quat = str(list(angle.as_quat_float))
        euler = str(list(angle.as_euler_float))

        if 'nan' in euler or 'nan' in quat:
            return

        self._table.update(self._db_id, quat_pegboard=quat)
        self._table.update(self._db_id, angle_pegboard=euler)
        self._populate('angle_pegboard')

    @property
    @_check_types.do
    def angle_pegboard(self) -> _angle.Angle:
        """Return the peg-board angle.

        :returns: Property value.
        :rtype: :class:`_angle.Angle`
        """
        if self._stored_angle_pegboard is DefaultStoredValue:
            quat = eval(self._table.select('quat_pegboard', id=self._db_id)[0][0])
            euler = eval(self._table.select('angle_pegboard', id=self._db_id)[0][0])

            if self._angle_pegboard_db_id is None:
                self._angle_pegboard_db_id = uuid.uuid4().bytes

            angle = _angle.Angle.from_quat(quat, euler, db_id=self._angle_pegboard_db_id)
            angle.bind(self._update_angle_pegboard)

            self._stored_angle_pegboard = angle

        return self._stored_angle_pegboard


class AnglePegboardControl(_prop_ctrls.AngleProperty):

    @_check_types.do
    def __init__(self, parent):
        self.db_obj: AnglePegboardMixin | None = None

        super().__init__(parent, 'Pegboard Angle', axes='y')

    @_check_types.do
    def set_obj(self, db_obj: AnglePegboardMixin | None):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`AnglePegboardMixin`
        """
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue(None)
        else:
            self.SetValue(db_obj.angle_pegboard)
