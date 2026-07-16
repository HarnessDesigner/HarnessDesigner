# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from ...geometry import point as _point


class PJTPointsPegTable(PJTTableBase):
    """Peg-board position points -- one shared table serving two roles:

    - An anchor's own position (housing/splice/transition-branch/
      terminal), mirroring ``PJTPoints2DTable`` exactly: referenced by a
      ``point_peg_id`` FK column directly on each anchor-owning table
      (``pjt_housings``, ``pjt_splices``, ``pjt_transitions``,
      ``pjt_terminals``), same as ``point2d_id``/``point3d_id`` already
      are. ``bundle_id``/``idx`` are ``NULL`` for these rows.
    - A bundle waypoint -- a peg-board-only bend point with no 3D
      counterpart, self-identifying via ``bundle_id``/``idx`` (see
      :meth:`for_bundle`) instead of being referenced from an owning row.
      Formerly a separate ``pjt_pegboard_waypoints`` table; folded in here
      so "is this an anchor or a waypoint" and "every waypoint for bundle
      X, in order" are both trivial lookups against one table.
    """
    __table_name__ = 'pjt_points_peg'

    def _table_needs_update(self) -> bool:
        from ..create_database import points_peg

        return points_peg.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import points_peg

        points_peg.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import points_peg

        points_peg.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTPointPeg"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTPointPeg(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTPointPeg":
        if isinstance(item, int):
            if item in self:
                return PJTPointPeg(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def for_bundle(self, bundle_id: int) -> list["PJTPointPeg"]:
        """Return every waypoint on a bundle, ordered by ``idx`` ascending.

        :param bundle_id: Identifier of the bundle whose waypoints to fetch.
        :type bundle_id: int
        :returns: The bundle's waypoints, in chain order.
        :rtype: list['PJTPointPeg']
        """
        rows = self.select('id', 'idx', bundle_id=bundle_id)
        rows = sorted(rows, key=lambda row: row[1])

        return [self[row[0]] for row in rows]

    def insert(self, x: float, z: float, bundle_id: int = None,
              idx: int = None) -> "PJTPointPeg":
        """Create a new peg-board point row.

        Called with only *x*/*z* for an anchor's own position
        (``bundle_id``/``idx`` default to ``NULL``); with all four for a
        bundle waypoint.

        :param x: Peg-board (world) X coordinate.
        :type x: float
        :param z: Peg-board (world) Z coordinate.
        :type z: float
        :param bundle_id: Owning bundle, for a waypoint row -- ``None``
            for an anchor's own position row.
        :type bundle_id: int | None
        :param idx: 0-based order along the bundle chain, for a waypoint
            row -- ``None`` for an anchor's own position row.
        :type idx: int | None
        :returns: The newly created row.
        :rtype: :class:`PJTPointPeg`
        """
        db_id = PJTTableBase.insert(self, x=x, z=z, bundle_id=bundle_id, idx=idx)

        return PJTPointPeg(self, db_id, self.project_id)


class PJTPointPeg(PJTEntryBase):
    """One peg-board position row, mirroring ``PJTPoint2D`` exactly."""
    _table: PJTPointsPegTable = None

    def build_monitor_packet(self):
        return {'pjt_points_peg': [self.db_id]}

    @property
    def table(self) -> PJTPointsPegTable:
        return self._table

    _stored_x: float | DefaultStoredValueType = DefaultStoredValue

    @property
    def x(self) -> float:
        if self._stored_x is DefaultStoredValue:
            self._stored_x = self._table.select('x', id=self._db_id)[0][0]

        return self._stored_x

    @x.setter
    def x(self, value: float):
        self._stored_x = value
        self._table.update(self._db_id, x=value)

    _stored_z: float | DefaultStoredValueType = DefaultStoredValue

    @property
    def z(self) -> float:
        if self._stored_z is DefaultStoredValue:
            self._stored_z = self._table.select('z', id=self._db_id)[0][0]

        return self._stored_z

    @z.setter
    def z(self, value: float):
        self._stored_z = value
        self._table.update(self._db_id, z=value)

    _stored_bundle_id: "int | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    def bundle_id(self) -> "int | None":
        """Return the id of the bundle this waypoint belongs to, or
        ``None`` for an anchor's own position row.

        :returns: The referenced ``pjt_bundles`` row id, or ``None``.
        :rtype: int | None
        """
        if self._stored_bundle_id is DefaultStoredValue:
            self._stored_bundle_id = self._table.select('bundle_id', id=self._db_id)[0][0]

        return self._stored_bundle_id

    @bundle_id.setter
    def bundle_id(self, value: "int | None"):
        self._stored_bundle_id = value
        self._table.update(self._db_id, bundle_id=value)
        self._populate('bundle_id')

    _stored_idx: "int | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    def idx(self) -> "int | None":
        """Return this waypoint's 0-based order along the bundle chain,
        or ``None`` for an anchor's own position row.

        :returns: The order index, or ``None``.
        :rtype: int | None
        """
        if self._stored_idx is DefaultStoredValue:
            self._stored_idx = self._table.select('idx', id=self._db_id)[0][0]

        return self._stored_idx

    @idx.setter
    def idx(self, value: "int | None"):
        self._stored_idx = value
        self._table.update(self._db_id, idx=value)
        self._populate('idx')

    _stored_point_peg: _point.Point = None

    @property
    def point(self) -> _point.Point:
        """Return this row's live, bindable position.

        A genuine 3D point (``is2d=False``) with Y pinned to ``0.0`` -- the
        peg board is a flat plane, but every position on it is still a
        real world position, so ``.x``/``.y``/``.z`` read directly with no
        relabeling needed anywhere this point is handed to real-3D-space
        code (shader uniforms, ``position3d`` projections, etc).

        :returns: Property value.
        :rtype: :class:`_point.Point`
        """
        if self._stored_point_peg is None:
            self._stored_point_peg = _point.Point(
                self.x, 0.0, self.z, db_id=str(self.db_id) + 'peg')
            self._stored_point_peg.bind(self._update_point)

        return self._stored_point_peg

    def _update_point(self, point: _point.Point):
        x, _y, z = point.as_float
        self._stored_x = x
        self._stored_z = z
        self._table.update(self._db_id, x=x, z=z)
