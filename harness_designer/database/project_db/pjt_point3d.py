# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
import uuid

from typing import Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from ...geometry import point as _point
from ... import check_types as _check_types


class PJTPoints3DTable(PJTTableBase):
    """Represent a PJT points 3dtable in :mod:`harness_designer.database.project_db.pjt_point3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_points3d'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import points3d

        return points3d.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import points3d

        points3d.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import points3d

        points3d.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTPoint3D"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTPoint3D']
        """
        for db_id in PJTTableBase.__iter__(self):
            point = PJTPoint3D(self, db_id, self.project_id)
            yield point

    @_check_types.do
    def __getitem__(self, item) -> "PJTPoint3D":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTPoint3D`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes, uuid.UUID)):
            if item in self:
                return PJTPoint3D(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(self, x: float, y: float, z: float,
               wire_id: int = None, bundle_id: int = None, idx: int = None) -> "PJTPoint3D":
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
        :type wire_id: int | None
        :param bundle_id: Owning bundle, for an interior waypoint row --
            ``None`` for an anchor's own position row or a wire waypoint.
        :type bundle_id: int | None
        :param idx: 0-based order along the wire's/bundle's waypoint
            chain, for a waypoint row -- ``None`` for an anchor's own
            position row.
        :type idx: int | None
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTPoint3D`
        """
        db_id = PJTTableBase.insert(
            self, x=x, y=y, z=z, wire_id=wire_id, bundle_id=bundle_id, idx=idx)
        return PJTPoint3D(self, db_id, self.project_id)

    @_check_types.do
    def for_wire(self, wire_id: int) -> list["PJTPoint3D"]:
        """Return every interior waypoint on a wire, ordered by ``idx`` ascending.

        :param wire_id: Identifier of the wire whose waypoints to fetch.
        :type wire_id: int
        :returns: The wire's interior waypoints, in chain order.
        :rtype: list['PJTPoint3D']
        """
        rows = self.select('id', 'idx', wire_id=wire_id)
        rows = sorted(rows, key=lambda row: row[1])

        return [self[row[0]] for row in rows]

    @_check_types.do
    def for_bundle(self, bundle_id: int) -> list["PJTPoint3D"]:
        """Return every interior waypoint on a bundle, ordered by ``idx`` ascending.

        :param bundle_id: Identifier of the bundle whose waypoints to fetch.
        :type bundle_id: int
        :returns: The bundle's interior waypoints, in chain order.
        :rtype: list['PJTPoint3D']
        """
        rows = self.select('id', 'idx', bundle_id=bundle_id)
        rows = sorted(rows, key=lambda row: row[1])

        return [self[row[0]] for row in rows]


class PJTPoint3D(PJTEntryBase):
    """ORM entry for a single row in ``pjt_points3d``, with a reactive geometry Point.

    NORMAL LIFECYCLE
    ----------------
    ``PJTPoint3D`` is a singleton keyed by ``(project_id, db_id)`` via
    ``_PJTEntrySingleton``.  The first call to ``.point`` creates a
    :class:`~harness_designer.geometry.point.Point` singleton (keyed on
    ``str(db_id) + '3d'`` via ``PointMeta``) and binds ``_update_point``
    as a callback.  From that moment on, every coordinate mutation on the
    geometry Point automatically writes ``x / y / z`` back to the database
    row — no explicit save call is ever needed::

        pjt = project.points3d[5]
        pjt.point.x = 10.0   # fires _update_point → UPDATE pjt_points3d SET x=10 WHERE id=5

    ATTACH / CLONE LIFECYCLE (the voodoo part)
    -------------------------------------------
    The wire handler creates a *preview* ``PJTPoint3D`` row (e.g. db_id=99)
    so the user can drag a stop position before committing.  When the user
    drops the wire onto an existing terminal, the preview geometry Point must
    be merged with the terminal's real Point (e.g. ``"53d"``).  That merge is
    done via :meth:`~harness_designer.geometry.point.Point.attach`::

        terminal_point.attach(pjt_preview.point)

    From that moment ``pjt_preview.point.db_id`` returns ``"53d"`` — the root's
    id — because all ``db_id`` lookups on a delegating Point forward to the
    root.  ``pjt_preview._db_id`` is still ``99`` at this point.

    SELF-HEALING VIA _update_point
    --------------------------------
    The very next time the root moves (or any coordinate change propagates
    through the delegation chain), ``_update_point`` fires on the preview
    instance.  At that point it compares::

        db_id = int(point.db_id[:-2])   # → 5  (root's row id)
        if db_id != self._db_id:        # 5 != 99  → mismatch

    The mismatch branch runs exactly once:

    1. ``point.unbind(self._update_point)`` — removes this callback from the
       shared root's callback list so it never fires again.
    2. ``self._stored_point3d = None`` — invalidates the cached geometry Point.
    3. ``self._db_id = db_id`` — updates this instance's row id to 5.
    4. ``self._is_clone = True`` — marks this instance permanently as a clone.

    After this, ``pjt_preview`` is effectively an alias for row 5.  Any code
    that still holds a reference to ``pjt_preview`` (e.g. a wire's cached
    endpoint entry) will now get the real shared Point on the next ``.point``
    access, because ``str(self.db_id) + '3d'`` resolves to ``"53d"`` and
    ``PointMeta`` returns the live root instance.

    CLONE GUARD IN .point
    ----------------------
    The ``.point`` property checks ``_is_clone`` before binding
    ``_update_point``::

        if not self._is_clone:
            self._stored_point3d.bind(self._update_point)

    This prevents a second DB-write callback from being registered on the
    real shared Point — the row-5 ``PJTPoint3D`` already has its own
    ``_update_point`` bound and is the sole writer for that row.

    SINGLETON CACHE CLEANUP
    ------------------------
    After the self-heal, ``_PJTEntrySingleton._instances`` still holds a
    stale entry ``(project_id, 99)`` → ``weakref(pjt_preview)``.  This is
    harmless: ``pjt_preview`` now reports db_id=5 and ``_is_clone=True``, so
    everything it exposes is correct.  When the preview DB row is eventually
    deleted and the last Python reference to ``pjt_preview`` is dropped, the
    garbage collector collects the instance and the weakref finalizer
    registered by ``_PJTEntrySingleton.__call__`` removes the stale cache
    entry automatically.  No manual cache surgery is required.
    """
    _table: PJTPoints3DTable = None

    @property
    @_check_types.do
    def table(self) -> PJTPoints3DTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTPoints3DTable`
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
    # per-point DB callback is suppressed while 3D render callbacks still fire.
    _skip_db_write: bool = False

    @_check_types.do
    def _update_point(self, point: _point.Point):
        """Update the point.

        UNKNOWN details are inferred from the callable name and signature.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
        db_id = int(point.db_id[:-2])
        if db_id != self._db_id:
            point.unbind(self._update_point)
            self._stored_point3d = None
            self._db_id = db_id
            self._is_clone = True
            self._stored_x = DefaultStoredValue
            self._stored_y = DefaultStoredValue
            self._stored_z = DefaultStoredValue
            return
        if PJTPoint3D._skip_db_write:
            return
        x, y, z = point.as_float
        self._stored_x = x
        self._stored_y = y
        self._stored_z = z
        self._table.update(self._db_id, x=x, y=y, z=z)

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

    _stored_bundle_id: int | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def bundle_id(self) -> int | None:
        """Return the id of the bundle this waypoint belongs to, or
        ``None`` for an anchor's own position row or a wire waypoint.

        :returns: The referenced ``pjt_bundles`` row id, or ``None``.
        :rtype: int | None
        """
        if self._stored_bundle_id is DefaultStoredValue:
            self._stored_bundle_id = self._table.select('bundle_id', id=self._db_id)[0][0]

        return self._stored_bundle_id

    @bundle_id.setter
    @_check_types.do
    def bundle_id(self, value: int | None):
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

    _stored_point3d: _point.Point = None
    _is_clone: bool = False

    @property
    @_check_types.do
    def point(self) -> _point.Point:
        """Return the point.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_point3d is None:
            self._stored_point3d = _point.Point(self.x, self.y, self.z, db_id=str(self.db_id) + '3d')
            if not self._is_clone:
                self._stored_point3d.bind(self._update_point)

        return self._stored_point3d
