# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin
from ....geometry import point as _point
from .. import pjt_point3d as _pjt_point3d


class Position3DMixin(BaseMixin):
    """Represent a position 3dmixin in :mod:`harness_designer.database.project_db.mixins.position3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_position3d: _pjt_point3d.PJTPoint3D = None

    @property
    def position3d(self) -> _point.Point:
        """Return the position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_position3d is None and self._obj is not None:
            point_id = self.position3d_id

            self._stored_position3d = self._table.db.pjt_points3d_table[point_id]
            self._stored_position3d.add_object(self._obj())
            point = self._stored_position3d.point
        elif self._stored_position3d is None:
            point = None
        else:
            point = self._stored_position3d.point

        return point

    @property
    def position3d_id(self) -> int:
        """Return the position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        point_id = self._table.select('point3d_id', id=self._db_id)[0][0]
        if point_id is None:
            self._table.execute(f'INSERT INTO pjt_points3d (project_id, x, y, z) VALUES (?, ?, ?, ?);',
                                (self._table.project_id, 0.0, 0.0, 0.0))

            self._table.commit()
            point_id = self._table.lastrowid
            self.position3d_id = point_id

        return point_id

    @position3d_id.setter
    def position3d_id(self, value: int):
        """Set the position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, point3d_id=value)
        self._populate('position3d_id')


class Position3DControl(_prop_ctrls.Position3DProperty):
    """Represent a position 3dcontrol in :mod:`harness_designer.database.project_db.mixins.position3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`Position3DControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Position3DMixin = None

        super().__init__(parent, '3D Position')

    def set_obj(self, db_obj: Position3DMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`Position3DMixin`
        """
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue(None)
        else:
            self.SetValue(db_obj.position3d)
