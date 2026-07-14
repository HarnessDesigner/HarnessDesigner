# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Peg-board position overlay, one row per anchor's ``point3d_id``.

An anchor (housing, splice endpoint, transition, transition branch, bare
terminal, bundle-layout point, etc.) gets a row here the first time the
user drags it around in the peg-board view. This table only knows about
``point3d_id`` -- it has no idea what kind of anchor owns that point, so it
stays decoupled from every part-type table.
"""

from typing import Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType


class PJTPegboardPointsTable(PJTTableBase):
    """Table of peg-board positions, one per anchor ``point3d_id``."""

    __table_name__ = 'pjt_pegboard_points'

    def _table_needs_update(self) -> bool:
        """Return whether the table is missing any schema fields.

        :returns: ``True`` when the table is missing a defined field.
        :rtype: bool
        """
        from ..create_database import pegboard_points

        return pegboard_points.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Create the ``pjt_pegboard_points`` table in the database."""
        from ..create_database import pegboard_points

        pegboard_points.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Add any missing fields to the ``pjt_pegboard_points`` table."""
        from ..create_database import pegboard_points

        pegboard_points.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTPegboardPoint"]:
        """Iterate over every peg-board point row for the open project.

        :returns: An iterator of :class:`PJTPegboardPoint` rows.
        :rtype: _Iterable['PJTPegboardPoint']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTPegboardPoint(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTPegboardPoint":
        """Return the peg-board point row for the given database id.

        :param item: Row id to look up.
        :type item: int
        :returns: The matching row.
        :rtype: :class:`PJTPegboardPoint`
        :raises KeyError: Raised when ``item`` is not an ``int``.
        :raises IndexError: Raised when no row with that id exists.
        """
        if isinstance(item, int):
            if item in self:
                return PJTPegboardPoint(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def get_from_point3d_id(self, point3d_id: int) -> "PJTPegboardPoint":
        """Return the peg-board point row keyed by an anchor's ``point3d_id``.

        :param point3d_id: Identifier of the anchor's 3D point.
        :type point3d_id: int
        :returns: The matching row, or ``None`` when one has not been created yet.
        :rtype: :class:`PJTPegboardPoint`
        """
        rows = self.select('id', point3d_id=point3d_id)
        if rows:
            return self[rows[0][0]]

    def insert(self, point3d_id: int) -> "PJTPegboardPoint":
        """Create a peg-board point row for an anchor, using default placement.

        Only ``point3d_id`` is required -- the row is meant to be created
        lazily the first time an anchor is dragged in the peg-board view,
        with every other column left at its schema default (world origin,
        no rotation, not yet user-placed).

        :param point3d_id: Identifier of the anchor's 3D point.
        :type point3d_id: int
        :returns: The newly created row.
        :rtype: :class:`PJTPegboardPoint`
        """
        db_id = PJTTableBase.insert(self, point3d_id=point3d_id)
        return PJTPegboardPoint(self, db_id, self.project_id)


class PJTPegboardPoint(PJTEntryBase):
    """A single anchor's position on the peg-board view."""

    _table: PJTPegboardPointsTable = None

    @property
    def table(self) -> PJTPegboardPointsTable:
        """Return the owning table.

        :returns: The table this row belongs to.
        :rtype: :class:`PJTPegboardPointsTable`
        """
        return self._table

    _stored_point3d_id: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def point3d_id(self) -> int:
        """Return the id of the ``pjt_points3d`` row this row is keyed by.

        :returns: The referenced 3D point's row id.
        :rtype: int
        """
        if self._stored_point3d_id is DefaultStoredValue:
            self._stored_point3d_id = self._table.select('point3d_id', id=self._db_id)[0][0]

        return self._stored_point3d_id

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

    _stored_rotation: float | DefaultStoredValueType = DefaultStoredValue

    @property
    def rotation(self) -> float:
        """Return the user's in-plane spin adjustment, in degrees.

        :returns: Rotation, in degrees.
        :rtype: float
        """
        if self._stored_rotation is DefaultStoredValue:
            self._stored_rotation = self._table.select('rotation', id=self._db_id)[0][0]

        return self._stored_rotation

    @rotation.setter
    def rotation(self, value: float):
        """Set the user's in-plane spin adjustment, in degrees.

        :param value: New rotation, in degrees.
        :type value: float
        """
        self._stored_rotation = value
        self._table.update(self._db_id, rotation=value)
        self._populate('rotation')

    _stored_is_user_placed: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def is_user_placed(self) -> int:
        """Return whether the user has manually placed this anchor.

        :returns: ``1`` once the user has dragged this anchor, ``0`` otherwise.
        :rtype: int
        """
        if self._stored_is_user_placed is DefaultStoredValue:
            self._stored_is_user_placed = self._table.select('is_user_placed', id=self._db_id)[0][0]

        return self._stored_is_user_placed

    @is_user_placed.setter
    def is_user_placed(self, value: int):
        """Set whether the user has manually placed this anchor.

        :param value: ``1`` when user-placed, ``0`` otherwise.
        :type value: int
        """
        self._stored_is_user_placed = value
        self._table.update(self._db_id, is_user_placed=value)
        self._populate('is_user_placed')
