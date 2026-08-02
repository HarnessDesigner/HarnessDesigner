# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType
from ....geometry import point as _point
from .. import pjt_point_peg as _pjt_point_peg
from .... import check_types as _check_types


class TablePositionPegMixin(BaseMixin):
    """Peg-board data-table overlay position, mirroring ``PositionPegMixin``
    exactly -- a live, bindable ``Point`` backed by a shared
    ``pjt_points_peg`` row (via a ``table_point_peg_id`` FK column), lazily
    created (at ``(0.0, 0.0)``) the first time it's needed.

    Distinct from ``PositionPegMixin.position_peg`` -- that mixin holds
    where the *anchor itself* sits on the peg board; this one holds where
    that anchor's floating Excel-like data-table overlay
    (``gl.canvas_pegboard.tables_overlay.PegboardTableWidget``) sits,
    independently draggable away from its anchor.
    """

    _stored_table_position_peg: "_pjt_point_peg.PJTPointPeg | DefaultStoredValueType | None" = DefaultStoredValue

    @property
    @_check_types.do
    def table_position_peg(self) -> _point.Point:
        """Return the data-table overlay's peg-board position.

        :returns: Property value.
        :rtype: :class:`_point.Point`
        """
        if self._stored_table_position_peg is DefaultStoredValue:
            point_id = self.table_position_peg_id

            if point_id is None:
                self._stored_table_position_peg = None
            else:
                self._stored_table_position_peg = self._table.db.pjt_points_peg_table[point_id]

        if self._stored_table_position_peg is not None:
            if self._obj is not None:
                self._stored_table_position_peg.add_object(self._obj())

            point = self._stored_table_position_peg.point
        else:
            point = None

        return point

    _stored_table_position_peg_id: int | DefaultStoredValueType | None = DefaultStoredValue

    @property
    @_check_types.do
    def table_position_peg_id(self) -> int:
        """Return the data-table overlay's peg-board position row id.

        :returns: Property value.
        :rtype: int
        """
        if self._stored_table_position_peg_id is DefaultStoredValue:
            point_id = self._table.select('table_point_peg_id', id=self._db_id)[0][0]
            if point_id is None:
                point_id = self._table.db.pjt_points_peg_table.insert(x=0.0, z=0.0)
                self.table_position_peg_id = point_id

            self._stored_table_position_peg_id = point_id

        return self._stored_table_position_peg_id

    @table_position_peg_id.setter
    @_check_types.do
    def table_position_peg_id(self, value: int):
        """Set the data-table overlay's peg-board position row id.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_table_position_peg_id = value
        self._stored_table_position_peg = DefaultStoredValue

        self._table.update(self._db_id, table_point_peg_id=value)
        self._populate('table_position_peg_id')
