# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import uuid

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin
from ....geometry import angle as _angle


class Angle3DMixin(BaseMixin):
    """Represent an angle 3dmixin in :mod:`harness_designer.database.project_db.mixins.angle3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _angle3d_db_id: str = None
    _stored_angle3d: "_angle.Angle" = None
    # Per-instance flag: set True during bulk angle batch-writes so the individual
    # DB callback is suppressed while 3D render callbacks still fire.
    _skip_db_write: bool = False

    def _update_angle3d(self, angle: _angle.Angle):
        """Update the angle 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        if self._skip_db_write:
            return

        quat = str(list(angle.as_quat_float))
        euler = str(list(angle.as_euler_float))

        if 'nan' in euler or 'nan' in quat:
            return

        self._table.update(self._db_id, quat3d=quat)
        self._table.update(self._db_id, angle3d=euler)
        self._populate('angle3d')

    @property
    def angle3d(self) -> _angle.Angle:
        """Return the angle 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_angle.Angle`
        """
        if self._stored_angle3d is not None:
            return self._stored_angle3d

        quat = eval(self._table.select('quat3d', id=self._db_id)[0][0])
        euler = eval(self._table.select('angle3d', id=self._db_id)[0][0])

        if self._angle3d_db_id is None:
            self._angle3d_db_id = str(uuid.uuid4())

        angle = _angle.Angle.from_quat(quat, euler, db_id=self._angle3d_db_id)
        angle.bind(self._update_angle3d)
        self._stored_angle3d = angle

        return angle


class Angle3DControl(_prop_ctrls.Angle3DProperty):
    """Represent an angle 3dcontrol in :mod:`harness_designer.database.project_db.mixins.angle3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`Angle3DControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Angle3DMixin = None

        super().__init__(parent, '3D Angle')

    def set_obj(self, db_obj: Angle3DMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`Angle3DMixin`
        """
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue(None)
        else:
            self.SetValue(db_obj.angle3d)
