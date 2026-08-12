# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import math
import uuid

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType
from ....geometry import angle as _angle
from .... import check_types as _check_types


class Angle2DMixin(BaseMixin):
    """Represent an angle 2dmixin in :mod:`harness_designer.database.project_db.mixins.angle2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _angle2d_db_id: bytes | None = None
    _stored_angle2d: _angle.Angle | DefaultStoredValueType = DefaultStoredValue

    @_check_types.do
    def _update_angle2d(self, angle: _angle.Angle):
        """Update the angle 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        quat = str(list(angle.as_quat_float))
        euler = str(list(angle.as_euler_float))

        if 'nan' in euler or 'nan' in quat:
            return

        self._table.update(self._db_id, quat2d=quat)
        self._table.update(self._db_id, angle2d=euler)
        self._populate('angle2d')

    @property
    @_check_types.do
    def angle2d(self) -> _angle.Angle:
        """Return the angle 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_angle.Angle`
        """
        
        if self._stored_angle2d is DefaultStoredValue:
            quat = eval(self._table.select('quat2d', id=self._db_id)[0][0])
            euler = eval(self._table.select('angle2d', id=self._db_id)[0][0])

            if self._angle2d_db_id is None:
                self._angle2d_db_id = uuid.uuid4().bytes

            angle = _angle.Angle.from_quat(quat, euler, db_id=self._angle2d_db_id)
            angle.bind(self._update_angle2d)
            
            self._stored_angle2d = angle

        return self._stored_angle2d


class Angle2DControl(_prop_ctrls.FloatProperty):
    """Represent an angle 2dcontrol in :mod:`harness_designer.database.project_db.mixins.angle2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, parent):
        """Initialise the :class:`Angle2DControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Angle2DMixin | None = None

        super().__init__(parent, '2D Angle', min_value=-180.0, max_value=180.0, increment=90.0, units='°')

        self.propertyChanged.connect(self._on_angle)

    @_check_types.do
    def _on_angle(self, evt):
        """Handle the angle event.

        Rotation in the 2D editor is about world Y (see ``angle2d.y``'s
        axis convention, used everywhere in ``objects2d/``), and locked
        to 90° increments (matches ``objects2d/housing.py``'s ``# TODO:
        Lock a housing to only be able to be rotated in 90° increments``
        note) -- round the typed/spun value to the nearest multiple of
        90 rather than writing it verbatim, so this free-text field can't
        put a housing at an angle the rotate menu itself never produces.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        y = round(evt.GetValue() / 90.0) * 90.0
        if y > 180.0:
            y -= 360.0
        elif y < -180.0:
            y += 360.0

        self.db_obj.angle2d.y = y

    @_check_types.do
    def set_obj(self, db_obj: Angle2DMixin | None):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`Angle2DMixin`
        """
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue(0.0)
            self.setEnabled(False)
        else:
            self.SetValue(db_obj.angle2d.y)
            self.setEnabled(True)
