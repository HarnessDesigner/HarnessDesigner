# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Excel-like data-table overlay geometry and scroll state.

One row per anchor that has a visible data table on the peg-board view.
Keyed purely by ``point3d_id``, the same way ``pjt_pegboard_points`` is --
this table has no knowledge of what kind of anchor owns that 3D point.
"""

from typing import Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType


class PJTPegboardTablesTable(PJTTableBase):
    """Table of peg-board data-table overlays, one per anchor ``point3d_id``."""

    __table_name__ = 'pjt_pegboard_tables'

    def _table_needs_update(self) -> bool:
        """Return whether the table is missing any schema fields.

        :returns: ``True`` when the table is missing a defined field.
        :rtype: bool
        """
        from ..create_database import pegboard_tables

        return pegboard_tables.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Create the ``pjt_pegboard_tables`` table in the database."""
        from ..create_database import pegboard_tables

        pegboard_tables.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Add any missing fields to the ``pjt_pegboard_tables`` table."""
        from ..create_database import pegboard_tables

        pegboard_tables.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTPegboardTable"]:
        """Iterate over every data-table overlay row for the open project.

        :returns: An iterator of :class:`PJTPegboardTable` rows.
        :rtype: _Iterable['PJTPegboardTable']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTPegboardTable(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTPegboardTable":
        """Return the data-table overlay row for the given database id.

        :param item: Row id to look up.
        :type item: int
        :returns: The matching row.
        :rtype: :class:`PJTPegboardTable`
        :raises KeyError: Raised when ``item`` is not an ``int``.
        :raises IndexError: Raised when no row with that id exists.
        """
        if isinstance(item, int):
            if item in self:
                return PJTPegboardTable(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def get_from_point3d_id(self, point3d_id: int) -> "PJTPegboardTable":
        """Return the data-table overlay row keyed by an anchor's ``point3d_id``.

        :param point3d_id: Identifier of the anchor's 3D point.
        :type point3d_id: int
        :returns: The matching row, or ``None`` when one has not been created yet.
        :rtype: :class:`PJTPegboardTable`
        """
        rows = self.select('id', point3d_id=point3d_id)
        if rows:
            return self[rows[0][0]]

    def insert(self, point3d_id: int, x: float, y: float, width: float,
              height: float) -> "PJTPegboardTable":
        """Create a new data-table overlay for an anchor.

        ``h_scroll``, ``v_scroll`` and ``is_collapsed`` are left at their
        schema defaults (no scroll offset, not collapsed).

        :param point3d_id: Identifier of the anchor's 3D point.
        :type point3d_id: int
        :param x: Peg-board X coordinate of the table's top-left corner.
        :type x: float
        :param y: Peg-board Y coordinate of the table's top-left corner.
        :type y: float
        :param width: Table width, in world units.
        :type width: float
        :param height: Table height, in world units.
        :type height: float
        :returns: The newly created row.
        :rtype: :class:`PJTPegboardTable`
        """
        db_id = PJTTableBase.insert(self, point3d_id=point3d_id, x=x, y=y,
                                    width=width, height=height)

        return PJTPegboardTable(self, db_id, self.project_id)


class PJTPegboardTable(PJTEntryBase):
    """A single anchor's Excel-like data-table overlay on the peg-board view."""

    _table: PJTPegboardTablesTable = None

    @property
    def table(self) -> PJTPegboardTablesTable:
        """Return the owning table.

        :returns: The table this row belongs to.
        :rtype: :class:`PJTPegboardTablesTable`
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
        """Return the peg-board X coordinate of the table's top-left corner.

        :returns: The X coordinate.
        :rtype: float
        """
        if self._stored_x is DefaultStoredValue:
            self._stored_x = self._table.select('x', id=self._db_id)[0][0]

        return self._stored_x

    @x.setter
    def x(self, value: float):
        """Set the peg-board X coordinate of the table's top-left corner.

        :param value: New X coordinate.
        :type value: float
        """
        self._stored_x = value
        self._table.update(self._db_id, x=value)
        self._populate('x')

    _stored_y: float | DefaultStoredValueType = DefaultStoredValue

    @property
    def y(self) -> float:
        """Return the peg-board Y coordinate of the table's top-left corner.

        :returns: The Y coordinate.
        :rtype: float
        """
        if self._stored_y is DefaultStoredValue:
            self._stored_y = self._table.select('y', id=self._db_id)[0][0]

        return self._stored_y

    @y.setter
    def y(self, value: float):
        """Set the peg-board Y coordinate of the table's top-left corner.

        :param value: New Y coordinate.
        :type value: float
        """
        self._stored_y = value
        self._table.update(self._db_id, y=value)
        self._populate('y')

    _stored_width: float | DefaultStoredValueType = DefaultStoredValue

    @property
    def width(self) -> float:
        """Return the table's width, in world units.

        :returns: The width.
        :rtype: float
        """
        if self._stored_width is DefaultStoredValue:
            self._stored_width = self._table.select('width', id=self._db_id)[0][0]

        return self._stored_width

    @width.setter
    def width(self, value: float):
        """Set the table's width, in world units.

        :param value: New width.
        :type value: float
        """
        self._stored_width = value
        self._table.update(self._db_id, width=value)
        self._populate('width')

    _stored_height: float | DefaultStoredValueType = DefaultStoredValue

    @property
    def height(self) -> float:
        """Return the table's height, in world units.

        :returns: The height.
        :rtype: float
        """
        if self._stored_height is DefaultStoredValue:
            self._stored_height = self._table.select('height', id=self._db_id)[0][0]

        return self._stored_height

    @height.setter
    def height(self, value: float):
        """Set the table's height, in world units.

        :param value: New height.
        :type value: float
        """
        self._stored_height = value
        self._table.update(self._db_id, height=value)
        self._populate('height')

    _stored_h_scroll: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def h_scroll(self) -> int:
        """Return the table's horizontal scroll offset.

        :returns: The horizontal scroll offset.
        :rtype: int
        """
        if self._stored_h_scroll is DefaultStoredValue:
            self._stored_h_scroll = self._table.select('h_scroll', id=self._db_id)[0][0]

        return self._stored_h_scroll

    @h_scroll.setter
    def h_scroll(self, value: int):
        """Set the table's horizontal scroll offset.

        :param value: New horizontal scroll offset.
        :type value: int
        """
        self._stored_h_scroll = value
        self._table.update(self._db_id, h_scroll=value)
        self._populate('h_scroll')

    _stored_v_scroll: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def v_scroll(self) -> int:
        """Return the table's vertical scroll offset.

        :returns: The vertical scroll offset.
        :rtype: int
        """
        if self._stored_v_scroll is DefaultStoredValue:
            self._stored_v_scroll = self._table.select('v_scroll', id=self._db_id)[0][0]

        return self._stored_v_scroll

    @v_scroll.setter
    def v_scroll(self, value: int):
        """Set the table's vertical scroll offset.

        :param value: New vertical scroll offset.
        :type value: int
        """
        self._stored_v_scroll = value
        self._table.update(self._db_id, v_scroll=value)
        self._populate('v_scroll')

    _stored_is_collapsed: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def is_collapsed(self) -> int:
        """Return whether the table overlay is collapsed.

        :returns: ``1`` when collapsed, ``0`` otherwise.
        :rtype: int
        """
        if self._stored_is_collapsed is DefaultStoredValue:
            self._stored_is_collapsed = self._table.select('is_collapsed', id=self._db_id)[0][0]

        return self._stored_is_collapsed

    @is_collapsed.setter
    def is_collapsed(self, value: int):
        """Set whether the table overlay is collapsed.

        :param value: ``1`` when collapsed, ``0`` otherwise.
        :type value: int
        """
        self._stored_is_collapsed = value
        self._table.update(self._db_id, is_collapsed=value)
        self._populate('is_collapsed')
