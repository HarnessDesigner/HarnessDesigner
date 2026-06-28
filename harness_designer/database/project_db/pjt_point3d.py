# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase
from ...geometry import point as _point


class PJTPoints3DTable(PJTTableBase):
    """Represent a PJT points 3dtable in :mod:`harness_designer.database.project_db.pjt_point3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_points3d'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import points3d

        return points3d.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import points3d

        points3d.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import points3d

        points3d.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTPoint3D"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTPoint3D']
        """
        for db_id in PJTTableBase.__iter__(self):
            point = PJTPoint3D(self, db_id, self.project_id)
            yield point

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
        if isinstance(item, int):
            if item in self:
                return PJTPoint3D(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, x: float, y: float, z: float) -> "PJTPoint3D":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param x: X-coordinate value.
        :type x: float
        :param y: Y-coordinate value.
        :type y: float
        :param z: Z-coordinate value.
        :type z: float
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTPoint3D`
        """
        db_id = PJTTableBase.insert(self, x=x, y=y, z=z)
        return PJTPoint3D(self, db_id, self.project_id)


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

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        packet = {
            'pjt_points3d': [self.db_id],
        }

        return packet

    @property
    def table(self) -> PJTPoints3DTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTPoints3DTable`
        """
        return self._table

    @property
    def x(self) -> float:
        """Return the x.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('x', id=self._db_id)[0][0]

    @x.setter
    def x(self, value: float):
        """Set the x.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, x=value)

    @property
    def y(self) -> float:
        """Return the y.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('y', id=self._db_id)[0][0]

    @y.setter
    def y(self, value: float):
        """Set the y.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, y=value)

    @property
    def z(self) -> float:
        """Return the z.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('z', id=self._db_id)[0][0]

    @z.setter
    def z(self, value: float):
        """Set the z.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, z=value)

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
            return
        x, y, z = point.as_float
        self._table.update(self._db_id, x=x, y=y, z=z)

    _stored_point3d: _point.Point = None
    _is_clone: bool = False

    @property
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
