# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType
from ....geometry import point as _point
from .. import pjt_point3d as _pjt_point3d


class Scale3DMixin(BaseMixin):
    """
    Represent a position 3dmixin in :mod:`harness_designer.database.project_db.mixins.scale3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_scale3d: _pjt_point3d.PJTPoint3D | DefaultStoredValueType | None = DefaultStoredValue

    @property
    def scale3d(self) -> _point.Point:
        """
        Return the scale 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_scale3d is DefaultStoredValue:
            point_id = self.scale3d_id
            if point_id is None:
                self._stored_scale3d = None
            else:

                self._stored_scale3d = self._table.db.pjt_points3d_table[point_id]

        if self._stored_scale3d is not None:
            if self._obj is not None:
                self._stored_scale3d.add_object(self._obj())
                
            point = self._stored_scale3d.point
        else:
            point = None

        return point

    _stored_scale3d_id: int | DefaultStoredValueType | None = DefaultStoredValue

    @property
    def scale3d_id(self) -> int:
        """
        Return the scale 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_scale3d_id is DefaultStoredValue:
            point_id = self._table.select('scale3d_id', id=self._db_id)[0][0]
            if point_id is None:
                self._table.execute(f'INSERT INTO pjt_points3d (project_id, x, y, z) VALUES (?, ?, ?, ?);',
                                    (self._table.project_id, 1.0, 1.0, 1.0))

                self._table.commit()
                point_id = self._table.lastrowid
                self.scale3d_id = point_id
            
            self._stored_scale3d_id = point_id

        return self._stored_scale3d_id

    @scale3d_id.setter
    def scale3d_id(self, value: int):
        """Set the position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_scale3d_id = value
        self._stored_scale3d = DefaultStoredValue
        
        self._table.update(self._db_id, scale3d_id=value)
        self._populate('scale3d_id')


class Scale3DControl(_prop_ctrls.Scale3DProperty):
    """
    Represent a scale 3dcontrol in :mod:`harness_designer.database.project_db.mixins.scale3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """
        Initialise the :class:`Scale3DControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Scale3DMixin = None

        super().__init__(parent, '3D Scale')

    def set_obj(self, db_obj: Scale3DMixin):
        """
        Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`Scale3DMixin`
        """
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue(None)
        else:
            self.SetValue(db_obj.scale3d)
