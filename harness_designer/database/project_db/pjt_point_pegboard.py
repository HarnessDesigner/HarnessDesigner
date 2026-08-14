# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from ...geometry import point as _point
from ... import check_types as _check_types


class PJTPointsPegboardTable(PJTTableBase):
    """Represent a PJT points pegboard table in :mod:`harness_designer.database.project_db.pjt_point_pegboard`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_points_pegboard'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import points_pegboard

        return points_pegboard.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import points_pegboard

        points_pegboard.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import points_pegboard

        points_pegboard.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTPointPegboard"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTPointPegboard']
        """
        for db_id in PJTTableBase.__iter__(self):
            point = PJTPointPegboard(self, db_id)
            yield point

    @_check_types.do
    def __getitem__(self, item) -> "PJTPointPegboard":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTPointPegboard`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes)):
            if item in self:
                return PJTPointPegboard(self, item)
            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(self, x: float | int, y: float | int, z: float | int,
               wire_id: bytes = None, bundle_id: bytes = None, idx: int = None) -> "PJTPointPegboard":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param x: X-coordinate value.
        :type x: float
        :param y: Y-coordinate value.
        :type y: float
        :param z: Z-coordinate value.
        :type z: float
        :param wire_id: Owning wire, for an interior waypoint row --
            ``None`` for an anchor's own position row or a bundle waypoint.
        :type wire_id: bytes | None
        :param bundle_id: Owning bundle, for an interior waypoint row --
            ``None`` for an anchor's own position row or a wire waypoint.
        :type bundle_id: bytes | None
        :param idx: 0-based order along the wire's/bundle's waypoint
            chain, for a waypoint row -- ``None`` for an anchor's own
            position row.
        :type idx: int | None
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTPointPegboard`
        """
        db_id = PJTTableBase.insert(
            self, x=float(x), y=float(y), z=float(z), wire_id=wire_id, bundle_id=bundle_id, idx=idx)
        return PJTPointPegboard(self, db_id)

    @_check_types.do
    def for_wire(self, wire_id: bytes) -> list["PJTPointPegboard"]:
        """Return every interior waypoint on a wire, ordered by ``idx`` ascending.

        :param wire_id: Identifier of the wire whose waypoints to fetch.
        :type wire_id: bytes
        :returns: The wire's interior waypoints, in chain order.
        :rtype: list['PJTPointPegboard']
        """
        rows = self.select('id', 'idx', wire_id=wire_id)
        rows = sorted(rows, key=lambda row: row[1])

        return [self[row[0]] for row in rows]

    @_check_types.do
    def for_bundle(self, bundle_id: bytes) -> list["PJTPointPegboard"]:
        """Return every interior waypoint on a bundle, ordered by ``idx`` ascending.

        :param bundle_id: Identifier of the bundle whose waypoints to fetch.
        :type bundle_id: bytes
        :returns: The bundle's interior waypoints, in chain order.
        :rtype: list['PJTPointPegboard']
        """
        rows = self.select('id', 'idx', bundle_id=bundle_id)
        rows = sorted(rows, key=lambda row: row[1])

        return [self[row[0]] for row in rows]


class PJTPointPegboard(PJTEntryBase):
    """ORM entry for a single row in ``pjt_points_pegboard``, with a reactive geometry Point.

    Structurally identical to :class:`~harness_designer.database.project_db.
    pjt_point3d.PJTPoint3D` -- same singleton/attach/clone/self-heal
    lifecycle, same ``wire_id``/``bundle_id``/``idx``/``parent_point_id``
    waypoint columns, same ``_skip_db_write`` batch-suppression flag. See
    that class's docstring for the full mechanics (NORMAL LIFECYCLE,
    ATTACH/CLONE LIFECYCLE, SELF-HEALING VIA ``_update_point``, CLONE GUARD,
    SINGLETON CACHE CLEANUP) -- none of it is repeated here since it applies
    unchanged, just against ``pjt_points_pegboard`` instead of
    ``pjt_points3d``.
    """
    _table: PJTPointsPegboardTable = None

    @property
    @_check_types.do
    def table(self) -> PJTPointsPegboardTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTPointsPegboardTable`
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

    _stored_z: float | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def z(self) -> float:
        """Return the z.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        if self._stored_z is DefaultStoredValue:
            self._stored_z = self._table.select('z', id=self._db_id)[0][0]

        return self._stored_z

    @z.setter
    @_check_types.do
    def z(self, value: float):
        """Set the z.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._stored_z = value
        self._table.update(self._db_id, z=value)

    # Class-level flag: set True during bulk position batch-writes so that the
    # per-point DB callback is suppressed while pegboard render callbacks still fire.
    _skip_db_write: bool = False

    @_check_types.do
    def _update_point(self, point: _point.Point):
        """Update the point.

        UNKNOWN details are inferred from the callable name and signature.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
        db_id = point.db_id[:-8]
        if db_id != self._db_id:
            point.unbind(self._update_point)
            self._stored_point_pegboard = None
            self._db_id = db_id
            self._is_clone = True
            self._stored_x = DefaultStoredValue
            self._stored_y = DefaultStoredValue
            self._stored_z = DefaultStoredValue
            return
        if PJTPointPegboard._skip_db_write:
            return
        x, y, z = point.as_float
        self._stored_x = x
        self._stored_y = y
        self._stored_z = z
        self._table.update(self._db_id, x=x, y=y, z=z)

    _stored_wire_id: bytes | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def wire_id(self) -> bytes | None:
        """Return the id of the wire this waypoint belongs to, or
        ``None`` for an anchor's own position row.

        :returns: The referenced ``pjt_wires`` row id, or ``None``.
        :rtype: bytes | None
        """
        if self._stored_wire_id is DefaultStoredValue:
            self._stored_wire_id = self._table.select('wire_id', id=self._db_id)[0][0]

        return self._stored_wire_id

    @wire_id.setter
    @_check_types.do
    def wire_id(self, value: bytes | None):
        self._stored_wire_id = value
        self._table.update(self._db_id, wire_id=value)

    _stored_bundle_id: bytes | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def bundle_id(self) -> bytes | None:
        """Return the id of the bundle this waypoint belongs to, or
        ``None`` for an anchor's own position row or a wire waypoint.

        :returns: The referenced ``pjt_bundles`` row id, or ``None``.
        :rtype: bytes | None
        """
        if self._stored_bundle_id is DefaultStoredValue:
            self._stored_bundle_id = self._table.select('bundle_id', id=self._db_id)[0][0]

        return self._stored_bundle_id

    @bundle_id.setter
    @_check_types.do
    def bundle_id(self, value: bytes | None):
        self._stored_bundle_id = value
        self._table.update(self._db_id, bundle_id=value)

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

    _stored_parent_point_id: bytes | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def parent_point_id(self) -> bytes | None:
        """Return the id of the "real"/canonical point this one was cloned
        from, or ``None`` for a canonical point (or any point that was
        never cloned at all).

        Set only by ``objects.terminal.Terminal._own_or_cloned_point_id``
        when a second-or-later wire attaching to the same terminal/cavity
        needs its own tagged waypoint row -- mirrors ``PJTPoint3D.
        parent_point_id`` exactly (see ``pjt_housing.PJTHousing.
        _update_position_pegboard``/``_update_angle_pegboard``, which look
        up every clone of a terminal's/cavity's own wire-side points by
        this column and move them along with their parent in the same
        batch).

        :returns: The referenced ``pjt_points_pegboard`` row id, or ``None``.
        :rtype: bytes | None
        """
        if self._stored_parent_point_id is DefaultStoredValue:
            self._stored_parent_point_id = self._table.select(
                'parent_point_id', id=self._db_id)[0][0]

        return self._stored_parent_point_id

    @parent_point_id.setter
    @_check_types.do
    def parent_point_id(self, value: bytes | None):
        self._stored_parent_point_id = value
        self._table.update(self._db_id, parent_point_id=value)

    _stored_point_pegboard: _point.Point = None
    _is_clone: bool = False

    @property
    @_check_types.do
    def point(self) -> _point.Point:
        """Return the point.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_point_pegboard is None:
            self._stored_point_pegboard = _point.Point(
                self.x, self.y, self.z, db_id=self.db_id + b'pegboard')
            if not self._is_clone:
                self._stored_point_pegboard.bind(self._update_point)

            # Child-point tracking -- mirrors PJTPoint3D.point exactly, see
            # that property's own docstring for the full rationale
            # (deliberately NOT relied on for a whole-housing move/rotate --
            # PJTHousing._update_position_pegboard/_update_angle_pegboard
            # instead collect every child directly and fold them into the
            # same single vectorized batch, to avoid one individual UPDATE
            # per child point on every drag frame).
            parent_id = self.parent_point_id
            if parent_id is not None:
                parent_point = self._table.db.pjt_points_pegboard_table[parent_id].point
                parent_point.bind(self._sync_from_parent)

        return self._stored_point_pegboard

    @_check_types.do
    def _sync_from_parent(self, parent_point: _point.Point) -> None:
        """Follow *parent_point*'s own movement -- bound (see ``.point``
        above) on the canonical point this row was created as a child of
        (``parent_point_id``). Applying the delta via ``+=`` (rather than
        assigning x/y/z directly) fires this row's own already-bound
        ``_update_point`` the exact same way any other direct move would,
        so it persists to this row's own database entry normally -- no
        special-cased write path needed here.
        """
        delta = parent_point - self._stored_point_pegboard
        self._stored_point_pegboard += delta
