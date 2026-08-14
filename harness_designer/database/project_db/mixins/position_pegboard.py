# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType
from ....geometry import point as _point
from .. import pjt_point_pegboard as _pjt_point_pegboard
from .... import check_types as _check_types


class PositionPegboardMixin(BaseMixin):
    """Peg-board position, mirroring ``Position3DMixin`` exactly -- a
    live, bindable ``Point`` backed by a shared ``pjt_points_pegboard`` row
    (via a ``point_pegboard_id`` FK column, same pattern as ``point2d_id``/
    ``point3d_id``), lazily created (at ``(0.0, 0.0, 0.0)``, same as
    ``position3d``'s own lazy default) the first time it's needed.
    """

    _stored_position_pegboard: "_pjt_point_pegboard.PJTPointPegboard | DefaultStoredValueType | None" = DefaultStoredValue

    @property
    @_check_types.do
    def position_pegboard(self) -> _point.Point:
        """Return the peg-board position.

        :returns: Property value.
        :rtype: :class:`_point.Point`
        """
        if self._stored_position_pegboard is DefaultStoredValue:
            point_id = self.position_pegboard_id

            if point_id is None:
                self._stored_position_pegboard = None
            else:
                self._stored_position_pegboard = self._table.db.pjt_points_pegboard_table[point_id]

        if self._stored_position_pegboard is not None:
            if self._obj is not None:
                self._stored_position_pegboard.add_object(self._obj())

            point = self._stored_position_pegboard.point
        else:
            point = None

        return point

    _stored_position_pegboard_id: bytes | DefaultStoredValueType | None = DefaultStoredValue

    @property
    @_check_types.do
    def position_pegboard_id(self) -> bytes:
        """Return the peg-board position's row id.

        :returns: Property value.
        :rtype: bytes
        """
        if self._stored_position_pegboard_id is DefaultStoredValue:
            point_id = self._table.select('point_pegboard_id', id=self._db_id)[0][0]
            if point_id is None:
                point = self._table.db.pjt_points_pegboard_table.insert(x=0.0, y=0.0, z=0.0)
                point_id = point.db_id
                self._table.update(self._db_id, point_pegboard_id=point_id)

            self._stored_position_pegboard_id = point_id

        return self._stored_position_pegboard_id

    @position_pegboard_id.setter
    @_check_types.do
    def position_pegboard_id(self, value: bytes):
        """Set the peg-board position's row id.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._stored_position_pegboard_id = value
        self._stored_position_pegboard = DefaultStoredValue

        self._table.update(self._db_id, point_pegboard_id=value)
        self._populate('position_pegboard_id')
