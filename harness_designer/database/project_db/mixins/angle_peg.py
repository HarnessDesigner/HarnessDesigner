# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import uuid

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType
from ....geometry import angle as _angle


class AnglePegMixin(BaseMixin):
    """Peg-board rotation, mirroring ``Angle2DMixin`` exactly -- a live,
    bindable ``Angle`` stored as redundant quaternion+Euler TEXT columns
    directly on the owning table (``quatpeg``/``anglepeg``), same pattern
    as ``quat2d``/``angle2d`` and ``quat3d``/``angle3d``. Only the ``.y``
    Euler component is ever meaningful -- the peg board is always viewed
    top-down, so the only rotation that makes sense is a single spin about
    world +Y.
    """
    _anglepeg_db_id: str = None
    _stored_anglepeg: "_angle.Angle | DefaultStoredValueType" = DefaultStoredValue

    def _update_anglepeg(self, angle: "_angle.Angle"):
        """Update the peg-board angle.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        quat = str(list(angle.as_quat_float))
        euler = str(list(angle.as_euler_float))

        if 'nan' in euler or 'nan' in quat:
            return

        self._table.update(self._db_id, quatpeg=quat)
        self._table.update(self._db_id, anglepeg=euler)
        self._populate('anglepeg')

    @property
    def anglepeg(self) -> "_angle.Angle":
        """Return the peg-board angle.

        :returns: Property value.
        :rtype: :class:`_angle.Angle`
        """
        if self._stored_anglepeg is DefaultStoredValue:
            quat = eval(self._table.select('quatpeg', id=self._db_id)[0][0])
            euler = eval(self._table.select('anglepeg', id=self._db_id)[0][0])

            if self._anglepeg_db_id is None:
                self._anglepeg_db_id = str(uuid.uuid4())

            angle = _angle.Angle.from_quat(quat, euler, db_id=self._anglepeg_db_id)
            angle.bind(self._update_anglepeg)

            self._stored_anglepeg = angle

        return self._stored_anglepeg
