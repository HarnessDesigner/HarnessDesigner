# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Peg-board-only bend points, ordered along a bundle chain.

These waypoints have no 3D counterpart -- they exist purely to let a
bundle's routing bend in the 2D peg-board view. Each row belongs to a
bundle and is ordered along that bundle's chain by ``sequence``.
"""

from typing import Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType


class PJTPegboardWaypointsTable(PJTTableBase):
    """Table of peg-board-only bend points for bundle chains."""

    __table_name__ = 'pjt_pegboard_waypoints'

    def _table_needs_update(self) -> bool:
        """Return whether the table is missing any schema fields.

        :returns: ``True`` when the table is missing a defined field.
        :rtype: bool
        """
        from ..create_database import pegboard_waypoints

        return pegboard_waypoints.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Create the ``pjt_pegboard_waypoints`` table in the database."""
        from ..create_database import pegboard_waypoints

        pegboard_waypoints.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Add any missing fields to the ``pjt_pegboard_waypoints`` table."""
        from ..create_database import pegboard_waypoints

        pegboard_waypoints.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTPegboardWaypoint"]:
        """Iterate over every waypoint row for the open project.

        :returns: An iterator of :class:`PJTPegboardWaypoint` rows.
        :rtype: _Iterable['PJTPegboardWaypoint']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTPegboardWaypoint(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTPegboardWaypoint":
        """Return the waypoint row for the given database id.

        :param item: Row id to look up.
        :type item: int
        :returns: The matching row.
        :rtype: :class:`PJTPegboardWaypoint`
        :raises KeyError: Raised when ``item`` is not an ``int``.
        :raises IndexError: Raised when no row with that id exists.
        """
        if isinstance(item, int):
            if item in self:
                return PJTPegboardWaypoint(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def for_bundle(self, bundle_id: int) -> list["PJTPegboardWaypoint"]:
        """Return every waypoint on a bundle, ordered by ``sequence`` ascending.

        :param bundle_id: Identifier of the bundle whose waypoints to fetch.
        :type bundle_id: int
        :returns: The bundle's waypoints, in chain order.
        :rtype: list['PJTPegboardWaypoint']
        """
        rows = self.select('id', 'sequence', bundle_id=bundle_id)
        rows = sorted(rows, key=lambda row: row[1])

        return [self[row[0]] for row in rows]

    def insert(self, bundle_id: int, sequence: int, x: float, y: float,
              max_length_before_mm: float) -> "PJTPegboardWaypoint":
        """Create a new waypoint on a bundle chain.

        :param bundle_id: Identifier of the bundle this waypoint belongs to.
        :type bundle_id: int
        :param sequence: 0-based order of this waypoint along the chain.
        :type sequence: int
        :param x: Peg-board X coordinate.
        :type x: float
        :param y: Peg-board Y coordinate.
        :type y: float
        :param max_length_before_mm: Fixed length budget of the edge ending
            at this waypoint.
        :type max_length_before_mm: float
        :returns: The newly created row.
        :rtype: :class:`PJTPegboardWaypoint`
        """
        db_id = PJTTableBase.insert(self, bundle_id=bundle_id, sequence=sequence,
                                    x=x, y=y, max_length_before_mm=max_length_before_mm)

        return PJTPegboardWaypoint(self, db_id, self.project_id)


class PJTPegboardWaypoint(PJTEntryBase):
    """A single peg-board-only bend point along a bundle chain."""

    _table: PJTPegboardWaypointsTable = None

    @property
    def table(self) -> PJTPegboardWaypointsTable:
        """Return the owning table.

        :returns: The table this row belongs to.
        :rtype: :class:`PJTPegboardWaypointsTable`
        """
        return self._table

    _stored_bundle_id: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def bundle_id(self) -> int:
        """Return the id of the bundle this waypoint belongs to.

        :returns: The referenced ``pjt_bundles`` row id.
        :rtype: int
        """
        if self._stored_bundle_id is DefaultStoredValue:
            self._stored_bundle_id = self._table.select('bundle_id', id=self._db_id)[0][0]

        return self._stored_bundle_id

    @bundle_id.setter
    def bundle_id(self, value: int):
        """Set the id of the bundle this waypoint belongs to.

        :param value: New bundle row id.
        :type value: int
        """
        self._stored_bundle_id = value
        self._table.update(self._db_id, bundle_id=value)
        self._populate('bundle_id')

    _stored_sequence: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def sequence(self) -> int:
        """Return this waypoint's 0-based order along the bundle chain.

        :returns: The sequence index.
        :rtype: int
        """
        if self._stored_sequence is DefaultStoredValue:
            self._stored_sequence = self._table.select('sequence', id=self._db_id)[0][0]

        return self._stored_sequence

    @sequence.setter
    def sequence(self, value: int):
        """Set this waypoint's 0-based order along the bundle chain.

        :param value: New sequence index.
        :type value: int
        """
        self._stored_sequence = value
        self._table.update(self._db_id, sequence=value)
        self._populate('sequence')

    _stored_x: float | DefaultStoredValueType = DefaultStoredValue

    @property
    def x(self) -> float:
        """Return the peg-board X coordinate.

        :returns: The X coordinate.
        :rtype: float
        """
        if self._stored_x is DefaultStoredValue:
            self._stored_x = self._table.select('x', id=self._db_id)[0][0]

        return self._stored_x

    @x.setter
    def x(self, value: float):
        """Set the peg-board X coordinate.

        :param value: New X coordinate.
        :type value: float
        """
        self._stored_x = value
        self._table.update(self._db_id, x=value)
        self._populate('x')

    _stored_y: float | DefaultStoredValueType = DefaultStoredValue

    @property
    def y(self) -> float:
        """Return the peg-board Y coordinate.

        :returns: The Y coordinate.
        :rtype: float
        """
        if self._stored_y is DefaultStoredValue:
            self._stored_y = self._table.select('y', id=self._db_id)[0][0]

        return self._stored_y

    @y.setter
    def y(self, value: float):
        """Set the peg-board Y coordinate.

        :param value: New Y coordinate.
        :type value: float
        """
        self._stored_y = value
        self._table.update(self._db_id, y=value)
        self._populate('y')

    _stored_max_length_before_mm: float | DefaultStoredValueType = DefaultStoredValue

    @property
    def max_length_before_mm(self) -> float:
        """Return the fixed length budget of the edge ending at this waypoint.

        :returns: Length budget, in millimeters.
        :rtype: float
        """
        if self._stored_max_length_before_mm is DefaultStoredValue:
            self._stored_max_length_before_mm = self._table.select(
                'max_length_before_mm', id=self._db_id)[0][0]

        return self._stored_max_length_before_mm

    @max_length_before_mm.setter
    def max_length_before_mm(self, value: float):
        """Set the fixed length budget of the edge ending at this waypoint.

        :param value: New length budget, in millimeters.
        :type value: float
        """
        self._stored_max_length_before_mm = value
        self._table.update(self._db_id, max_length_before_mm=value)
        self._populate('max_length_before_mm')
