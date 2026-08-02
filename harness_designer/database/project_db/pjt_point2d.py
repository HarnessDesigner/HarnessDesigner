# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
import uuid

from typing import Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from ...geometry import point as _point
from ... import check_types as _check_types


class PJTPoints2DTable(PJTTableBase):
    """Represent a PJT points 2dtable in :mod:`harness_designer.database.project_db.pjt_point2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_points2d'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import points2d

        return points2d.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import points2d

        points2d.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import points2d

        points2d.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTPoint2D"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTPoint2D']
        """

        for db_id in PJTTableBase.__iter__(self):
            point = PJTPoint2D(self, db_id, self.project_id)
            yield point

    @_check_types.do
    def __getitem__(self, item) -> "PJTPoint2D":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTPoint2D`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes, uuid.UUID)):
            if item in self:
                return PJTPoint2D(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(self, x: float, y: float, wire_id: int = None, idx: int = None) -> "PJTPoint2D":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param x: X-coordinate value.
        :type x: float
        :param y: Y-coordinate value.
        :type y: float
        :param wire_id: Owning wire, for an interior waypoint row --
            ``None`` for an anchor's own position row.
        :type wire_id: int | None
        :param idx: 0-based order along the wire's waypoint chain, for a
            waypoint row -- ``None`` for an anchor's own position row.
        :type idx: int | None
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTPoint2D`
        """
        db_id = PJTTableBase.insert(self, x=x, y=y, wire_id=wire_id, idx=idx)
        return PJTPoint2D(self, db_id, self.project_id)

    @_check_types.do
    def for_wire(self, wire_id: int) -> list["PJTPoint2D"]:
        """Return every interior waypoint on a wire, ordered by ``idx`` ascending.

        :param wire_id: Identifier of the wire whose waypoints to fetch.
        :type wire_id: int
        :returns: The wire's interior waypoints, in chain order.
        :rtype: list['PJTPoint2D']
        """
        rows = self.select('id', 'idx', wire_id=wire_id)
        rows = sorted(rows, key=lambda row: row[1])

        return [self[row[0]] for row in rows]


class PJTPoint2D(PJTEntryBase):
    """Represent a PJT point 2D in :mod:`harness_designer.database.project_db.pjt_point2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: PJTPoints2DTable = None

    @property
    @_check_types.do
    def table(self) -> PJTPoints2DTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTPoints2DTable`
        """
        return self._table

    _stored_x: float | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def x(self) -> float:
        """Return the x.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        if self._stored_x is DefaultStoredValue:
            self._stored_x = self._table.select('x', id=self._db_id)[0][0]

        return self._stored_x

    @x.setter
    @_check_types.do
    def x(self, value: float):
        """Set the x.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._stored_x = value
        self._table.update(self._db_id, x=value)

    _stored_y: float | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def y(self) -> float:
        """Return the y.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        if self._stored_y is DefaultStoredValue:
            self._stored_y = self._table.select('y', id=self._db_id)[0][0]

        return self._stored_y

    @y.setter
    @_check_types.do
    def y(self, value: float):
        """Set the y.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._stored_y = value
        self._table.update(self._db_id, y=value)

    _stored_wire_id: int | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def wire_id(self) -> int | None:
        """Return the id of the wire this waypoint belongs to, or
        ``None`` for an anchor's own position row.

        :returns: The referenced ``pjt_wires`` row id, or ``None``.
        :rtype: int | None
        """
        if self._stored_wire_id is DefaultStoredValue:
            self._stored_wire_id = self._table.select('wire_id', id=self._db_id)[0][0]

        return self._stored_wire_id

    @wire_id.setter
    @_check_types.do
    def wire_id(self, value: int | None):
        self._stored_wire_id = value
        self._table.update(self._db_id, wire_id=value)

    _stored_idx: int | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def idx(self) -> int | None:
        """Return this waypoint's 0-based order along the wire's chain,
        or ``None`` for an anchor's own position row.

        :returns: The order index, or ``None``.
        :rtype: int | None
        """
        if self._stored_idx is DefaultStoredValue:
            self._stored_idx = self._table.select('idx', id=self._db_id)[0][0]

        return self._stored_idx

    @idx.setter
    @_check_types.do
    def idx(self, value: int | None):
        self._stored_idx = value
        self._table.update(self._db_id, idx=value)

    _stored_point2d: _point.Point = None

    @property
    @_check_types.do
    def point(self) -> _point.Point:
        """Return the point.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_point2d is None:
            x, z = self._table.select('x', 'y', id=self._db_id)[0]

            self._stored_point2d = _point.Point(x, 0.0, z, db_id=str(self.db_id) + '2d')
            self._stored_point2d.bind(self._update_point)

        return self._stored_point2d

    @_check_types.do
    def _update_point(self, point: _point.Point):
        """Update the point.

        UNKNOWN details are inferred from the callable name and signature.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
        x, _, y = point.as_float
        self._stored_x = x
        self._stored_y = y
        self._table.update(self._db_id, x=x, y=y)
