# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from ...geometry import point as _point
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import pjt_bundle as _pjt_bundle


# Which point column holds a route row's point, per view. No schematic view:
# bundles are never shown there.
_VIEW_COLUMNS = {
    '3d': 'point3d_id',
    'pegboard': 'point_pegboard_id'
}


class PJTBundlePathsTable(PJTTableBase):
    """The table of bundle waypoint lists: one row per interior point per
    bundle per view.

    A bundle's waypoints in one view are its rows for that view ordered by
    ``idx``; the bundle's own start and stop stay columns on
    ``pjt_bundles``, exterior to this list. Every row always has
    ``bundle_id``, ``idx`` and exactly one of ``point3d_id``/
    ``point_pegboard_id`` (enforced by :meth:`insert`). Mirrors
    :class:`~harness_designer.database.project_db.pjt_wire_path.
    PJTWirePathsTable` -- see BUNDLE_DESIGN.md, section 2.6.
    """
    __table_name__ = 'pjt_bundle_paths'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        from ..create_database import bundle_paths

        return bundle_paths.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self):
        from ..create_database import bundle_paths

        bundle_paths.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self):
        from ..create_database import bundle_paths

        bundle_paths.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTBundlePath"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTBundlePath(self, db_id)

    @_check_types.do
    def __getitem__(self, item) -> "PJTBundlePath":
        if isinstance(item, (int, bytes)):
            if item in PJTBundlePath or item in self:
                return PJTBundlePath(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(
        self, bundle_id: bytes, idx: int, point3d_id: bytes | None = None,
        point_pegboard_id: bytes | None = None
    ) -> "PJTBundlePath":
        """Add one point to a bundle's waypoint list.

        Exactly one of *point3d_id* and *point_pegboard_id* must be given
        -- it decides which view's list the row belongs to. Does not
        renumber anything; use :meth:`add`.

        :raises ValueError: If not exactly one point id is given.
        """
        if (point3d_id is None) == (point_pegboard_id is None):
            raise ValueError('insert() takes exactly one of point3d_id/point_pegboard_id')

        db_id = PJTTableBase.insert(
            self, bundle_id=bundle_id, idx=idx, point3d_id=point3d_id,
            point_pegboard_id=point_pegboard_id)

        return PJTBundlePath(self, db_id)

    @_check_types.do
    def _route_rows(self, bundle_id: bytes, view: str) -> list[tuple]:
        """A bundle's rows for one view as ``(id, idx, point_id)`` tuples,
        ordered by ``idx`` ascending."""
        column = _VIEW_COLUMNS[view]
        rows = self.select('id', 'idx', column, bundle_id=bundle_id)

        route = []
        for row in rows:
            if row[2] is not None:
                route.append(row)

        route.sort(key=lambda row: row[1])

        return route

    @_check_types.do
    def _renumber(self, pairs: list[tuple[int, bytes]]) -> None:
        """Write new ``idx`` values for many rows in ONE transaction and
        bring any live row object's cached value up to date.

        :param pairs: ``(new_idx, row_id)`` for each row to change.
        """
        self.batch_update(['idx'], pairs)

        for new_idx, row_id in pairs:
            if row_id in PJTBundlePath:
                PJTBundlePath(self, row_id)._stored_idx = new_idx  # NOQA

    @_check_types.do
    def for_bundle(self, bundle_id: bytes, view: str) -> list["PJTBundlePath"]:
        """Return a bundle's rows for *view* (``'3d'`` or ``'pegboard'``),
        ordered by ``idx`` ascending."""
        return [self[row[0]] for row in self._route_rows(bundle_id, view)]

    @_check_types.do
    def point_ids(self, bundle_id: bytes, view: str) -> list[bytes]:
        """Return the point ids of a bundle's waypoint list for *view*, in
        order -- one query and no row objects."""
        return [row[2] for row in self._route_rows(bundle_id, view)]

    @_check_types.do
    def _notify_waypoints_changed(self, bundle_id: bytes, view: str) -> None:
        """Fire the ``waypoints3d``/``waypoints_pegboard`` callback tag on
        *bundle_id*'s own row (``CallbackMixin.bind``/``_populate``, the
        same generic tag mechanism ``is_visible3d``/
        ``start_position_pegboard_id`` etc. already use elsewhere -- the
        tag need not be a real column) -- this is the ONE place a
        bundle's waypoint list actually changes shape (add/remove a
        point), so anything that needs to know WHICH point is "first"
        right now (e.g. ``objects_pegboard.table.Table``'s
        connector line, anchored on ``PJTBundle.position_pegboard``) binds
        to this tag instead of polling.

        A no-op if *bundle_id* is no longer a live row -- add/remove/
        set_route never fail on this notify step, matching this table's
        own "never let exceptions propagate" rule for cross-cutting glue
        that isn't the actual write being made.
        """
        if bundle_id not in self.db.pjt_bundles_table:
            return

        tag = 'waypoints3d' if view == '3d' else 'waypoints_pegboard'
        self.db.pjt_bundles_table[bundle_id]._populate(tag)  # NOQA

    @_check_types.do
    def add(self, bundle_id: bytes, view: str, index: int, point_id: bytes) -> "PJTBundlePath":
        """Insert a point into a bundle's waypoint list for *view* at
        position *index*, renumbering the rows after it.

        THE way to add a point to a bundle's list: nothing else should
        write ``idx`` by hand. Positions after *index* move up by one in a
        single ``batch_update``.

        :raises ValueError: If *index* is outside the list.
        """
        route = self._route_rows(bundle_id, view)

        if index < 0 or index > len(route):
            raise ValueError(f'index {index} is outside a list of {len(route)} points')

        pairs = []
        for position in range(index, len(route)):
            pairs.append((position + 1, route[position][0]))

        self._renumber(pairs)

        if view == '3d':
            result = self.insert(bundle_id, index, point3d_id=point_id)
        else:
            result = self.insert(bundle_id, index, point_pegboard_id=point_id)

        self._notify_waypoints_changed(bundle_id, view)

        return result

    @_check_types.do
    def append(self, bundle_id: bytes, view: str, point_id: bytes) -> "PJTBundlePath":
        """Add a point to the end of a bundle's waypoint list for *view*."""
        index = len(self._route_rows(bundle_id, view))

        return self.add(bundle_id, view, index, point_id)

    @_check_types.do
    def remove(self, bundle_id: bytes, view: str, point_id: bytes) -> None:
        """Remove a point from a bundle's waypoint list for *view*,
        renumbering the rows after it. The shared point row itself is left
        alone.

        :raises ValueError: If the point is not in the bundle's list.
        """
        route = self._route_rows(bundle_id, view)

        position = None
        for i, row in enumerate(route):
            if row[2] == point_id:
                position = i
                break

        if position is None:
            raise ValueError("that point is not in the bundle's waypoint list")

        self[route[position][0]].delete()

        pairs = []
        for i in range(position + 1, len(route)):
            pairs.append((i - 1, route[i][0]))

        self._renumber(pairs)
        self._notify_waypoints_changed(bundle_id, view)

    @_check_types.do
    def set_route(self, bundle_id: bytes, view: str, point_ids: list[bytes]) -> None:
        """Replace a bundle's whole waypoint list for *view* with
        *point_ids*, in order (used when bundles are merged)."""
        for row in self._route_rows(bundle_id, view):
            self[row[0]].delete()

        for index, point_id in enumerate(point_ids):
            self.add(bundle_id, view, index, point_id)

        # add() above already notifies once per point -- fire once more so
        # the empty-list case (every point removed, no add() call at all)
        # still notifies.
        self._notify_waypoints_changed(bundle_id, view)

    @_check_types.do
    def for_point(self, view: str, point_id: bytes) -> list["PJTBundlePath"]:
        """Return every row, of any bundle, that references *point_id* in *view*."""
        column = _VIEW_COLUMNS[view]
        rows = self.select('id', **{column: point_id})

        return [self[row[0]] for row in rows]

    @_check_types.do
    def bundle_ids_for_point(self, view: str, point_id: bytes) -> list[bytes]:
        """Return the id of every bundle whose waypoint list contains
        *point_id* in *view*."""
        column = _VIEW_COLUMNS[view]
        rows = self.select('bundle_id', **{column: point_id})

        found = []
        for row in rows:
            if row[0] not in found:
                found.append(row[0])

        return found

    @_check_types.do
    def delete_for_bundle(self, bundle_id: bytes) -> None:
        """Delete every row of *bundle_id*, in every view. The shared point
        rows they referenced are NOT deleted."""
        rows = self.select('id', bundle_id=bundle_id)
        for row in rows:
            self[row[0]].delete()


class PJTBundlePath(PJTEntryBase):
    """One row of a bundle's waypoint list -- see :class:`PJTBundlePathsTable`."""
    _table: PJTBundlePathsTable = None

    @property
    @_check_types.do
    def table(self) -> PJTBundlePathsTable:
        return self._table

    _stored_bundle_id: bytes | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def bundle_id(self) -> bytes:
        if self._stored_bundle_id is DefaultStoredValue:
            self._stored_bundle_id = self._table.select('bundle_id', id=self._db_id)[0][0]

        return self._stored_bundle_id

    @bundle_id.setter
    @_check_types.do
    def bundle_id(self, value: bytes):
        self._stored_bundle_id = value
        self._table.update(self._db_id, bundle_id=value)

    @property
    @_check_types.do
    def bundle(self) -> "_pjt_bundle.PJTBundle":
        """The bundle this row belongs to."""
        return self._table.db.pjt_bundles_table[self.bundle_id]

    _stored_idx: int | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def idx(self) -> int:
        """This row's position in its bundle's list for its view. Changing
        it does not move any other row."""
        if self._stored_idx is DefaultStoredValue:
            self._stored_idx = self._table.select('idx', id=self._db_id)[0][0]

        return self._stored_idx

    @idx.setter
    @_check_types.do
    def idx(self, value: int):
        self._stored_idx = value
        self._table.update(self._db_id, idx=value)

    _stored_point3d_id: bytes | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def point3d_id(self) -> bytes | None:
        """The shared 3D point this row references, or ``None`` when the
        row belongs to the peg-board list."""
        if self._stored_point3d_id is DefaultStoredValue:
            self._stored_point3d_id = self._table.select('point3d_id', id=self._db_id)[0][0]

        return self._stored_point3d_id

    @point3d_id.setter
    @_check_types.do
    def point3d_id(self, value: bytes):
        """Point this row at a 3D point -- clears the peg-board column so
        exactly one stays populated."""
        self._stored_point3d_id = value
        self._stored_point_pegboard_id = None
        self._table.update(self._db_id, point3d_id=value, point_pegboard_id=None)

    _stored_point_pegboard_id: bytes | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def point_pegboard_id(self) -> bytes | None:
        """The shared peg-board point this row references, or ``None``
        when the row belongs to the 3D list."""
        if self._stored_point_pegboard_id is DefaultStoredValue:
            self._stored_point_pegboard_id = self._table.select(
                'point_pegboard_id', id=self._db_id)[0][0]

        return self._stored_point_pegboard_id

    @point_pegboard_id.setter
    @_check_types.do
    def point_pegboard_id(self, value: bytes):
        """Point this row at a peg-board point -- clears the 3D column so
        exactly one stays populated."""
        self._stored_point_pegboard_id = value
        self._stored_point3d_id = None
        self._table.update(self._db_id, point_pegboard_id=value, point3d_id=None)

    @property
    @_check_types.do
    def view(self) -> str:
        """Which view's list this row belongs to: ``'3d'`` or ``'pegboard'``."""
        if self.point3d_id is not None:
            return '3d'

        return 'pegboard'

    @property
    @_check_types.do
    def point(self) -> _point.Point:
        """The live shared :class:`~harness_designer.geometry.point.Point`
        this row references."""
        db = self._table.db

        if self.view == '3d':
            return db.pjt_points3d_table[self.point3d_id].point

        return db.pjt_points_pegboard_table[self.point_pegboard_id].point
