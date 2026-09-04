# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType
from ....geometry import point as _point
from .. import pjt_point_pegboard as _pjt_point_pegboard
from .... import check_types as _check_types


class ScalePegboardMixin(BaseMixin):
    """Peg-board scale, mirroring ``Scale3DMixin`` exactly -- a live,
    bindable ``Point`` backed by a shared ``pjt_points_pegboard`` row (via
    a ``scale_pegboard_id`` FK column), lazily created (at
    ``(1.0, 1.0, 1.0)``, same as ``scale3d``'s own lazy default) the first
    time it's needed.
    """

    _stored_scale_pegboard: "_pjt_point_pegboard.PJTPointPegboard | DefaultStoredValueType | None" = DefaultStoredValue

    @property
    @_check_types.do
    def scale_pegboard(self) -> _point.Point:
        """Return the peg-board scale.

        :returns: Property value.
        :rtype: :class:`_point.Point`
        """
        if self._stored_scale_pegboard is DefaultStoredValue:
            point_id = self.scale_pegboard_id
            if point_id is None:
                self._stored_scale_pegboard = None
            else:
                self._stored_scale_pegboard = self._table.db.pjt_points_pegboard_table[point_id]

        if self._stored_scale_pegboard is not None:
            if self._obj is not None:
                self._stored_scale_pegboard.add_object(self._obj())

            point = self._stored_scale_pegboard.point
        else:
            point = None

        return point

    _stored_scale_pegboard_id: bytes | DefaultStoredValueType | None = DefaultStoredValue

    @property
    @_check_types.do
    def scale_pegboard_id(self) -> bytes:
        """Return the peg-board scale's row id.

        :returns: Property value.
        :rtype: bytes
        """
        if self._stored_scale_pegboard_id is DefaultStoredValue:
            point_id = self._table.select('scale_pegboard_id', id=self._db_id)[0][0]
            if point_id is None:
                point = self._table.db.pjt_points_pegboard_table.insert(x=1.0, y=1.0, z=1.0)
                point_id = point.db_id
                self._table.update(self._db_id, scale_pegboard_id=point_id)

            self._stored_scale_pegboard_id = point_id

        return self._stored_scale_pegboard_id

    @scale_pegboard_id.setter
    @_check_types.do
    def scale_pegboard_id(self, value: bytes):
        """Set the peg-board scale's row id.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._stored_scale_pegboard_id = value
        self._stored_scale_pegboard = DefaultStoredValue

        self._table.update(self._db_id, scale_pegboard_id=value)
        self._populate('scale_pegboard_id')


class ScalePegboardControl(_prop_ctrls.Scale3DProperty):
    """Represent a scale pegboard control in :mod:`harness_designer.database.project_db.mixins.scale_pegboard`."""

    @_check_types.do
    def __init__(self, parent):
        """Initialise the :class:`ScalePegboardControl` instance.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: ScalePegboardMixin | None = None

        super().__init__(parent, 'Peg-board Scale')

    @_check_types.do
    def set_obj(self, db_obj: ScalePegboardMixin | None):
        """Set the obj.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`ScalePegboardMixin`
        """
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue(None)
        else:
            self.SetValue(db_obj.scale_pegboard)
