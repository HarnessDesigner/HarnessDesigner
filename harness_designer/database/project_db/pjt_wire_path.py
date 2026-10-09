# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase
from ...geometry import point as _point
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import pjt_wire as _pjt_wire


# Which point column holds a route row's point, per view.
_VIEW_COLUMNS = {
    '3d': 'point3d_id',
    'pegboard': 'point_pegboard_id',
    '2d': 'point2d_id'
}


class PJTWirePathsTable(PJTTableBase):
    """The table of wire routes: one row per point per wire per view.

    A wire's route in one view is its rows for that view ordered by
    ``idx``. The rows reference shared point rows (a bundle waypoint, a
    transition branch position, a transition centre or a housing point is
    one point row used by every wire routed through it), so ``idx`` lives
    here, per wire and per view, and not on the point row.

    Every row always has ``wire_id``, ``idx`` and exactly one of
    ``point3d_id``/``point_pegboard_id``/``point2d_id`` (enforced by
    :meth:`insert`). ``bundle_id``, ``concentric_id``, ``transition_id``
    and ``transition_branch_id`` are optional tags describing what the row
    is -- see BUNDLE_DESIGN.md, section 2.6.
    """
    __table_name__ = 'pjt_wire_paths'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        from ..create_database import wire_paths

        return wire_paths.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self) -> None:
        from ..create_database import wire_paths

        wire_paths.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self) -> None:
        from ..create_database import wire_paths

        wire_paths.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTWirePath"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTWirePath(self, db_id)

    @_check_types.do
    def __getitem__(self, item: int | bytes | str) -> "PJTWirePath":
        if isinstance(item, (int, bytes)):
            if item in PJTWirePath or item in self:
                return PJTWirePath(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(
        self, wire_id: bytes, idx: int, point3d_id: bytes | None = None,
        point_pegboard_id: bytes | None = None, point2d_id: bytes | None = None,
        bundle_id: bytes | None = None, concentric_id: bytes | None = None,
        transition_id: bytes | None = None, transition_branch_id: bytes | None = None
    ) -> "PJTWirePath":
        """Add one point to a wire's route.

        Exactly one of *point3d_id*, *point_pegboard_id* and *point2d_id*
        must be given -- it decides which view's route the row belongs to.
        Inserting does not renumber anything: the caller picks *idx* and is
        responsible for making room (see :meth:`PJTWirePath.idx`).

        :param wire_id: The wire whose route this row belongs to.
        :param idx: The row's position in the wire's route for its view.
        :param point3d_id: The shared 3D point, for a 3D route row.
        :param point_pegboard_id: The shared peg-board point, for a
            peg-board route row.
        :param point2d_id: The shared schematic point, for a schematic
            route row.
        :param bundle_id: The bundle whose span this row lies inside.
        :param concentric_id: The concentric twist this row belongs to.
        :param transition_id: The transition this row is the centre of, or
            a branch position of.
        :param transition_branch_id: The transition branch this row is the
            position of.
        :returns: The new row.
        :raises ValueError: If not exactly one point id is given.
        """
        point_ids = (point3d_id, point_pegboard_id, point2d_id)
        given = 0
        for point_id in point_ids:
            if point_id is not None:
                given += 1

        if given != 1:
            raise ValueError(
                'insert() takes exactly one of point3d_id/point_pegboard_id/point2d_id')

        db_id = PJTTableBase.insert(
            self, wire_id=wire_id, idx=idx, point3d_id=point3d_id,
            point_pegboard_id=point_pegboard_id, point2d_id=point2d_id,
            bundle_id=bundle_id, concentric_id=concentric_id,
            transition_id=transition_id, transition_branch_id=transition_branch_id)

        return PJTWirePath(self, db_id)

    @_check_types.do
    def _route_rows(self, wire_id: bytes, view: str) -> list[tuple]:
        """A wire's route rows for one view as ``(id, idx, point_id)``
        tuples, ordered by ``idx`` ascending."""
        column = _VIEW_COLUMNS[view]
        rows = self.select('id', 'idx', column, wire_id=wire_id)

        route = []
        for row in rows:
            if row[2] is not None:
                route.append(row)

        route.sort(key=lambda row: row[1])

        return route

    @_check_types.do
    def _renumber(self, pairs: list[tuple[int, bytes]]) -> None:
        """Write new ``idx`` values for many rows in ONE transaction.

        ``idx`` has no local cache to refresh any more -- its getter
        always reads straight through -- so nothing further is needed
        once the batch write lands.

        :param pairs: ``(new_idx, row_id)`` for each row to change.
        """
        self.batch_update(['idx'], pairs)

    @_check_types.do
    def for_wire(self, wire_id: bytes, view: str) -> list["PJTWirePath"]:
        """Return a wire's route rows for *view* (``'3d'``, ``'pegboard'``
        or ``'2d'``), ordered by ``idx`` ascending."""
        return [self[row[0]] for row in self._route_rows(wire_id, view)]

    @_check_types.do
    def point_ids(self, wire_id: bytes, view: str) -> list[bytes]:
        """Return the point ids of a wire's route for *view*, in order --
        one query and no row objects, for readers that only want the
        points."""
        return [row[2] for row in self._route_rows(wire_id, view)]

    @_check_types.do
    def add(
        self, wire_id: bytes, view: str, index: int, point_id: bytes,
        bundle_id: bytes | None = None, concentric_id: bytes | None = None,
        transition_id: bytes | None = None, transition_branch_id: bytes | None = None
    ) -> "PJTWirePath":
        """Insert a point into a wire's route for *view* at position
        *index*, renumbering the rows after it.

        THE way to add a point to a route: nothing else should write
        ``idx`` by hand. Positions after *index* move up by one in a single
        ``batch_update``.

        :param wire_id: The wire whose route to change.
        :param view: ``'3d'``, ``'pegboard'`` or ``'2d'``.
        :param index: Where the point goes; ``0`` puts it first, the
            route's length puts it last.
        :param point_id: The shared point row (in *view*'s point table).
        :param bundle_id: Optional tag, see :meth:`insert`.
        :param concentric_id: Optional tag, see :meth:`insert`.
        :param transition_id: Optional tag, see :meth:`insert`.
        :param transition_branch_id: Optional tag, see :meth:`insert`.
        :returns: The new row.
        :raises ValueError: If *index* is outside the route.
        """
        route = self._route_rows(wire_id, view)

        if index < 0 or index > len(route):
            raise ValueError(f'index {index} is outside a route of {len(route)} points')

        pairs = []
        for position in range(index, len(route)):
            pairs.append((position + 1, route[position][0]))

        self._renumber(pairs)

        points = {'3d': None, 'pegboard': None, '2d': None}
        points[view] = point_id

        return self.insert(
            wire_id, index, points['3d'], points['pegboard'], points['2d'],
            bundle_id, concentric_id, transition_id, transition_branch_id)

    @_check_types.do
    def append(
        self, wire_id: bytes, view: str, point_id: bytes,
        bundle_id: bytes | None = None, concentric_id: bytes | None = None,
        transition_id: bytes | None = None, transition_branch_id: bytes | None = None
    ) -> "PJTWirePath":
        """Add a point to the end of a wire's route for *view*."""
        index = len(self._route_rows(wire_id, view))

        return self.add(
            wire_id, view, index, point_id, bundle_id, concentric_id,
            transition_id, transition_branch_id)

    @_check_types.do
    def remove(self, wire_id: bytes, view: str, point_id: bytes) -> None:
        """Remove a point from a wire's route for *view*, renumbering the
        rows after it so the route stays contiguous. The shared point row
        itself is left alone.

        :raises ValueError: If the point is not in the wire's route.
        """
        route = self._route_rows(wire_id, view)

        position = None
        for i, row in enumerate(route):
            if row[2] == point_id:
                position = i
                break

        if position is None:
            raise ValueError("that point is not in the wire's route")

        self[route[position][0]].delete()

        pairs = []
        for i in range(position + 1, len(route)):
            pairs.append((i - 1, route[i][0]))

        self._renumber(pairs)

    @_check_types.do
    def set_route(self, wire_id: bytes, view: str, point_ids: list[bytes]) -> None:
        """Replace a wire's whole route for *view* with *point_ids*, in
        order (used when a wire is split or merged). Existing rows for that
        view are deleted, and any optional tags on them are lost.
        """
        for row in self._route_rows(wire_id, view):
            self[row[0]].delete()

        for index, point_id in enumerate(point_ids):
            self.add(wire_id, view, index, point_id)

    @_check_types.do
    def for_point(self, view: str, point_id: bytes) -> list["PJTWirePath"]:
        """Return every route row, of any wire, that references *point_id*
        in *view*."""
        column = _VIEW_COLUMNS[view]
        rows = self.select('id', **{column: point_id})

        return [self[row[0]] for row in rows]

    @_check_types.do
    def wire_ids_for_point(self, view: str, point_id: bytes) -> list[bytes]:
        """Return the id of every wire whose route goes through *point_id*
        in *view*."""
        column = _VIEW_COLUMNS[view]

        return self._distinct('wire_id', column, point_id)

    @_check_types.do
    def for_wire3d(self, wire_id: bytes) -> list["PJTWirePath"]:
        """Return a wire's 3D route, ordered by ``idx`` ascending."""
        return self.for_wire(wire_id, '3d')

    @_check_types.do
    def for_wire_pegboard(self, wire_id: bytes) -> list["PJTWirePath"]:
        """Return a wire's peg-board route, ordered by ``idx`` ascending."""
        return self.for_wire(wire_id, 'pegboard')

    @_check_types.do
    def for_wire2d(self, wire_id: bytes) -> list["PJTWirePath"]:
        """Return a wire's schematic route, ordered by ``idx`` ascending."""
        return self.for_wire(wire_id, '2d')

    @_check_types.do
    def _rows_where(self, column: str, value: bytes) -> list["PJTWirePath"]:
        rows = self.select('id', 'wire_id', 'idx', **{column: value})
        rows.sort(key=lambda row: (row[1], row[2]))

        return [self[row[0]] for row in rows]

    @_check_types.do
    def for_bundle(self, bundle_id: bytes) -> list["PJTWirePath"]:
        """Return every route row, of any wire and view, tagged with *bundle_id*."""
        return self._rows_where('bundle_id', bundle_id)

    @_check_types.do
    def for_concentric(self, concentric_id: bytes) -> list["PJTWirePath"]:
        """Return every route row, of any wire and view, tagged with *concentric_id*."""
        return self._rows_where('concentric_id', concentric_id)

    @_check_types.do
    def for_transition(self, transition_id: bytes) -> list["PJTWirePath"]:
        """Return every route row, of any wire and view, tagged with *transition_id*."""
        return self._rows_where('transition_id', transition_id)

    @_check_types.do
    def for_transition_branch(self, transition_branch_id: bytes) -> list["PJTWirePath"]:
        """Return every route row, of any wire and view, tagged with *transition_branch_id*."""
        return self._rows_where('transition_branch_id', transition_branch_id)

    @_check_types.do
    def _distinct(self, return_column: str, match_column: str, value: bytes) -> list[bytes]:
        rows = self.select(return_column, **{match_column: value})

        found = []
        for row in rows:
            if row[0] is not None and row[0] not in found:
                found.append(row[0])

        return found

    @_check_types.do
    def wire_ids_for_bundle(self, bundle_id: bytes) -> list[bytes]:
        """Return the id of every wire routed through *bundle_id*."""
        return self._distinct('wire_id', 'bundle_id', bundle_id)

    @_check_types.do
    def wire_ids_for_transition(self, transition_id: bytes) -> list[bytes]:
        """Return the id of every wire routed through *transition_id*."""
        return self._distinct('wire_id', 'transition_id', transition_id)

    @_check_types.do
    def wire_ids_for_concentric(self, concentric_id: bytes) -> list[bytes]:
        """Return the id of every wire that is part of *concentric_id*."""
        return self._distinct('wire_id', 'concentric_id', concentric_id)

    @_check_types.do
    def bundle_ids_for_wire(self, wire_id: bytes) -> list[bytes]:
        """Return the id of every bundle *wire_id* is routed through."""
        return self._distinct('bundle_id', 'wire_id', wire_id)

    @_check_types.do
    def transition_ids_for_wire(self, wire_id: bytes) -> list[bytes]:
        """Return the id of every transition *wire_id* is routed through."""
        return self._distinct('transition_id', 'wire_id', wire_id)

    @_check_types.do
    def transition_branch_ids_for_wire(self, wire_id: bytes) -> list[bytes]:
        """Return the id of every transition branch *wire_id* is routed
        through."""
        return self._distinct('transition_branch_id', 'wire_id', wire_id)

    @_check_types.do
    def concentric_ids_for_wire(self, wire_id: bytes) -> list[bytes]:
        """Return the id of every concentric twist *wire_id* is part of."""
        return self._distinct('concentric_id', 'wire_id', wire_id)

    @_check_types.do
    def concentric_ids_for_bundle(self, bundle_id: bytes) -> list[bytes]:
        """Return the id of every concentric twist used by *bundle_id*."""
        return self._distinct('concentric_id', 'bundle_id', bundle_id)

    @_check_types.do
    def bundle_ids_for_concentric(self, concentric_id: bytes) -> list[bytes]:
        """Return the id of every bundle that uses *concentric_id*."""
        return self._distinct('bundle_id', 'concentric_id', concentric_id)

    @_check_types.do
    def delete_for_wire(self, wire_id: bytes) -> None:
        """Delete every route row of *wire_id*, in every view.

        The shared point rows the rows referenced are NOT deleted -- other
        wires, a bundle, a transition or a housing may still use them.
        """
        rows = self.select('id', wire_id=wire_id)
        for row in rows:
            self[row[0]].delete()


class PJTWirePath(PJTEntryBase):
    """One row of a wire's route -- see :class:`PJTWirePathsTable`."""
    _table: PJTWirePathsTable = None

    @property
    @_check_types.do
    def table(self) -> PJTWirePathsTable:
        return self._table

    @property
    @_check_types.do
    def wire_id(self) -> bytes:
        return self._table.select('wire_id', id=self._db_id)[0][0]

    @wire_id.setter
    @_check_types.do
    def wire_id(self, value: bytes) -> None:
        self._table.update(self._db_id, wire_id=value)
        self._populate('wire_id')

    @property
    @_check_types.do
    def wire(self) -> "_pjt_wire.PJTWire":
        """The wire this row belongs to."""
        return self._table.db.pjt_wires_table[self.wire_id]

    @property
    @_check_types.do
    def idx(self) -> int:
        """This row's position in its wire's route for its view. Changing
        it does not move any other row; the caller keeps the wire's route
        contiguous."""
        return self._table.select('idx', id=self._db_id)[0][0]

    @idx.setter
    @_check_types.do
    def idx(self, value: int) -> None:
        self._table.update(self._db_id, idx=value)
        self._populate('idx')

    @property
    @_check_types.do
    def point3d_id(self) -> bytes | None:
        """The shared 3D point this row references, or ``None`` when the
        row belongs to another view's route."""
        return self._table.select('point3d_id', id=self._db_id)[0][0]

    @point3d_id.setter
    @_check_types.do
    def point3d_id(self, value: bytes) -> None:
        """Point this row at a 3D point -- clears the other views' point
        columns so exactly one stays populated."""
        self._table.update(
            self._db_id, point3d_id=value, point_pegboard_id=None, point2d_id=None)
        self._populate('point3d_id')
        self._populate('point_pegboard_id')
        self._populate('point2d_id')

    @property
    @_check_types.do
    def point_pegboard_id(self) -> bytes | None:
        """The shared peg-board point this row references, or ``None``
        when the row belongs to another view's route."""
        return self._table.select('point_pegboard_id', id=self._db_id)[0][0]

    @point_pegboard_id.setter
    @_check_types.do
    def point_pegboard_id(self, value: bytes) -> None:
        """Point this row at a peg-board point -- clears the other views'
        point columns so exactly one stays populated."""
        self._table.update(
            self._db_id, point_pegboard_id=value, point3d_id=None, point2d_id=None)
        self._populate('point_pegboard_id')
        self._populate('point3d_id')
        self._populate('point2d_id')

    @property
    @_check_types.do
    def point2d_id(self) -> bytes | None:
        """The shared schematic point this row references, or ``None``
        when the row belongs to another view's route."""
        return self._table.select('point2d_id', id=self._db_id)[0][0]

    @point2d_id.setter
    @_check_types.do
    def point2d_id(self, value: bytes) -> None:
        """Point this row at a schematic point -- clears the other views'
        point columns so exactly one stays populated."""
        self._table.update(
            self._db_id, point2d_id=value, point3d_id=None, point_pegboard_id=None)
        self._populate('point2d_id')
        self._populate('point3d_id')
        self._populate('point_pegboard_id')

    @property
    @_check_types.do
    def view(self) -> str:
        """Which view's route this row belongs to: ``'3d'``,
        ``'pegboard'`` or ``'2d'``."""
        if self.point3d_id is not None:
            return '3d'

        if self.point_pegboard_id is not None:
            return 'pegboard'

        return '2d'

    @property
    @_check_types.do
    def point_id(self) -> bytes:
        """The id of the one point row this row references, whichever
        view it belongs to."""
        view = self.view

        if view == '3d':
            return self.point3d_id

        if view == 'pegboard':
            return self.point_pegboard_id

        return self.point2d_id

    @property
    @_check_types.do
    def point(self) -> _point.Point:
        """The live shared :class:`~harness_designer.geometry.point.Point`
        this row references -- the same object every other route through
        this point sees."""
        view = self.view
        db = self._table.db

        if view == '3d':
            return db.pjt_points3d_table[self.point3d_id].point

        if view == 'pegboard':
            return db.pjt_points_pegboard_table[self.point_pegboard_id].point

        return db.pjt_points2d_table[self.point2d_id].point

    @property
    @_check_types.do
    def bundle_id(self) -> bytes | None:
        """The bundle whose span this row lies inside, or ``None``."""
        return self._table.select('bundle_id', id=self._db_id)[0][0]

    @bundle_id.setter
    @_check_types.do
    def bundle_id(self, value: bytes | None) -> None:
        self._table.update(self._db_id, bundle_id=value)
        self._populate('bundle_id')

    @property
    @_check_types.do
    def concentric_id(self) -> bytes | None:
        """The concentric twist this row belongs to, or ``None``."""
        return self._table.select('concentric_id', id=self._db_id)[0][0]

    @concentric_id.setter
    @_check_types.do
    def concentric_id(self, value: bytes | None) -> None:
        self._table.update(self._db_id, concentric_id=value)
        self._populate('concentric_id')

    @property
    @_check_types.do
    def transition_id(self) -> bytes | None:
        """The transition this row is the centre of, or a branch position
        of, or ``None``."""
        return self._table.select('transition_id', id=self._db_id)[0][0]

    @transition_id.setter
    @_check_types.do
    def transition_id(self, value: bytes | None) -> None:
        self._table.update(self._db_id, transition_id=value)
        self._populate('transition_id')

    @property
    @_check_types.do
    def transition_branch_id(self) -> bytes | None:
        """The transition branch this row is the position of, or ``None``."""
        return self._table.select('transition_branch_id', id=self._db_id)[0][0]

    @transition_branch_id.setter
    @_check_types.do
    def transition_branch_id(self, value: bytes | None) -> None:
        self._table.update(self._db_id, transition_branch_id=value)
        self._populate('transition_branch_id')
