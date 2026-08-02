# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType
from ....geometry import point as _point
from .. import pjt_point2d as _pjt_point2d
from .... import check_types as _check_types


class Position2DMixin(BaseMixin):
    """Represent a position 2dmixin in :mod:`harness_designer.database.project_db.mixins.position2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    
    _stored_position2d: _pjt_point2d.PJTPoint2D | DefaultStoredValueType | None = DefaultStoredValue

    @property
    @_check_types.do
    def position2d(self) -> _point.Point:
        """Return the position 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_position2d is DefaultStoredValue:
            point_id = self.position2d_id
            
            if point_id is None:
                self._stored_position2d = None
            else:

                self._stored_position2d = self._table.db.pjt_points2d_table[point_id]
            
        if self._stored_position2d is not None:
            if self._obj is not None:
                self._stored_position2d.add_object(self._obj())

            point = self._stored_position2d.point
        else:
            point = None
       
        return point

    _stored_position2d_id: int | DefaultStoredValueType | None = DefaultStoredValue

    @property
    @_check_types.do
    def position2d_id(self) -> int:
        """Return the position 2D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_position2d_id is DefaultStoredValue:
            point_id = self._table.select('point2d_id', id=self._db_id)[0][0]
            if point_id is None:
                point_id = self._table.db.pjt_points2d_table.insert(x=0.0, y=0.0)
                self.position2d_id = point_id
            
            self._stored_position2d_id = point_id

        return self._stored_position2d_id

    @position2d_id.setter
    @_check_types.do
    def position2d_id(self, value: int):
        """Set the position 2D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        
        self._stored_position2d_id = value
        self._stored_position2d = DefaultStoredValue
        
        self._table.update(self._db_id, point2d_id=value)
        self._populate('position2d_id')


class Position2DControl(_prop_ctrls.Position2DProperty):
    """Represent a position 2dcontrol in :mod:`harness_designer.database.project_db.mixins.position2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, parent):
        """Initialise the :class:`Position2DControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Position2DMixin = None

        super().__init__(parent, '2D Position')

    @_check_types.do
    def set_obj(self, db_obj: Position2DMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`Position2DMixin`
        """
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue(None)
        else:
            self.SetValue(db_obj.position2d)
