# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType
from ....geometry import point as _point
from .. import pjt_point2d as _pjt_point2d
from .... import check_types as _check_types


class Scale2DMixin(BaseMixin):
    """
    Represent a position 2d mixin in :mod:`harness_designer.database.project_db.mixins.scale2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_scale2d: _pjt_point2d.PJTPoint2D | DefaultStoredValueType | None = DefaultStoredValue

    @property
    @_check_types.do
    def scale2d(self) -> _point.Point:
        """
        Return the scale 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_scale2d is DefaultStoredValue:
            point_id = self.scale2d_id
            if point_id is None:
                self._stored_scale2d = None
            else:

                self._stored_scale2d = self._table.db.pjt_points2d_table[point_id]

        if self._stored_scale2d is not None:
            if self._obj is not None:
                self._stored_scale2d.add_object(self._obj())

            point = self._stored_scale2d.point
        else:
            point = None

        return point

    _stored_scale2d_id: bytes | DefaultStoredValueType | None = DefaultStoredValue

    @property
    @_check_types.do
    def scale2d_id(self) -> bytes:
        """
        Return the scale 2D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes
        """
        if self._stored_scale2d_id is DefaultStoredValue:
            point_id = self._table.select('scale2d_id', id=self._db_id)[0][0]
            if point_id is None:
                point = self._table.db.pjt_points2d_table.insert(x=1.0, y=1.0, z=1.0)
                point_id = point.db_id
                self._table.update(self._db_id, scale2d_id=point_id)

            self._stored_scale2d_id = point_id

        return self._stored_scale2d_id

    @scale2d_id.setter
    @_check_types.do
    def scale2d_id(self, value: bytes):
        """Set the position 2D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._stored_scale2d_id = value
        self._stored_scale2d = DefaultStoredValue

        self._table.update(self._db_id, scale2d_id=value)
        self._populate('scale2d_id')


class Scale2DControl(_prop_ctrls.ScaleProperty):
    """
    Represent a scale 2d control in :mod:`harness_designer.database.project_db.mixins.scale2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, parent):
        """
        Initialise the :class:`Scale2DControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Scale2DMixin | None = None

        super().__init__(parent, 'Schematic Scale')

    @_check_types.do
    def set_obj(self, db_obj: Scale2DMixin | None):
        """
        Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`Scale2DMixin`
        """
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue(None)
        else:
            self.SetValue(db_obj.scale2d)
