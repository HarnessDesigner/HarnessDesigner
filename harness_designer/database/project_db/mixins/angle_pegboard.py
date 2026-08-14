# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import uuid

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
    _stored_angle_pegboard: "_angle.Angle | DefaultStoredValueType" = DefaultStoredValue
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
