# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin
from ....geometry import point as _point
from .. import pjt_point2d as _pjt_point2d


class Position2DMixin(BaseMixin):
    """Represent a position 2dmixin in :mod:`harness_designer.database.project_db.mixins.position2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    
    _stored_position2d: _pjt_point2d.PJTPoint2D = None

    @property
    def position2d(self) -> _point.Point:
        """Return the position 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_position2d is None and self._obj is not None:
            point_id = self.position2d_id

            self._stored_position2d = self._table.db.pjt_points2d_table[point_id]
            self._stored_position2d.add_object(self._obj())

            point = self._stored_position2d.point
        elif self._stored_position2d is None:
            point = None
        else:
            point = self._stored_position2d.point

        return point

    @property
    def position2d_id(self) -> int:
        """Return the position 2D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        point_id = self._table.select('point2d_id', id=self._db_id)[0][0]
        if point_id is None:
            self._table.execute(f'INSERT INTO pjt_points2d (project_id, x, y) VALUES (?, ?, ?);',
                                (self._table.project_id, 0.0, 0.0))

            self._table.commit()
            point_id = self._table.lastrowid
            self.position2d_id = point_id

        return point_id

    @position2d_id.setter
    def position2d_id(self, value: int):
        """Set the position 2D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, point2d_id=value)
        self._populate('position2d_id')


class Position2DControl(_prop_ctrls.Position2DProperty):
    """Represent a position 2dcontrol in :mod:`harness_designer.database.project_db.mixins.position2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`Position2DControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Position2DMixin = None

        super().__init__(parent, '2D Position')

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
