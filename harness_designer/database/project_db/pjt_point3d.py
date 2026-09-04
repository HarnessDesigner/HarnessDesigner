# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

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
            point = PJTPoint3D(self, db_id)
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
        if isinstance(item, (int, bytes)):
            if item in PJTPoint3D or item in self:
                return PJTPoint3D(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(self, x: float | int, y: float | int, z: float | int,
               wire_id: bytes = None, bundle_id: bytes = None, idx: int = None) -> "PJTPoint3D":
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
        :rtype: :class:`PJTPoint3D`
        """
        db_id = PJTTableBase.insert(
            self, x=float(x), y=float(y), z=float(z), wire_id=wire_id, bundle_id=bundle_id, idx=idx)
        return PJTPoint3D(self, db_id)

    @_check_types.do
    def for_wire(self, wire_id: bytes) -> list["PJTPoint3D"]:
        """Return every interior waypoint on a wire, ordered by ``idx`` ascending.

        :param wire_id: Identifier of the wire whose waypoints to fetch.
        :type wire_id: bytes
        :returns: The wire's interior waypoints, in chain order.
        :rtype: list['PJTPoint3D']
        """
        rows = self.select('id', 'idx', wire_id=wire_id)
        rows = sorted(rows, key=lambda row: row[1])

        return [self[row[0]] for row in rows]

    @_check_types.do
    def for_bundle(self, bundle_id: bytes) -> list["PJTPoint3D"]:
        """Return every interior waypoint on a bundle, ordered by ``idx`` ascending.

        :param bundle_id: Identifier of the bundle whose waypoints to fetch.
        :type bundle_id: bytes
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
    ``PJTPoint3D`` is a singleton keyed by ``db_id`` via
    ``_PJTEntrySingleton``.  The first call to ``.point`` creates a
    :class:`~harness_designer.geometry.point.Point` singleton (keyed on
    ``db_id + b'3d'`` via ``PointMeta``) and binds ``_update_point``
    as a callback.  From that moment on, every coordinate mutation on the
    geometry Point automatically writes ``x / y / z`` back to the database
    row — no explicit save call is ever needed::

        pjt = project.points3d[row_id]
        pjt.point.x = 10.0   # fires _update_point → UPDATE pjt_points3d SET x=10 WHERE id=row_id

    ATTACH / CLONE LIFECYCLE (the voodoo part)
    -------------------------------------------
    The wire handler creates a *preview* ``PJTPoint3D`` row (its own row id,
    call it ``preview_id``) so the user can drag a stop position before
    committing.  When the user drops the wire onto an existing terminal, the
    preview geometry Point must be merged with the terminal's real Point
    (row id ``real_id``).  That merge is done via
    :meth:`~harness_designer.geometry.point.Point.attach`::

        terminal_point.attach(pjt_preview.point)

    From that moment ``pjt_preview.point.db_id`` returns ``real_id + b'3d'``
    — the root's id — because all ``db_id`` lookups on a delegating Point
    forward to the root.  ``pjt_preview._db_id`` is still ``preview_id`` at
    this point.

    SELF-HEALING VIA _update_point
    --------------------------------
    The very next time the root moves (or any coordinate change propagates
    through the delegation chain), ``_update_point`` fires on the preview
    instance.  At that point it compares::

        db_id = point.db_id[:-2]        # → real_id  (root's row id)
        if db_id != self._db_id:        # real_id != preview_id  → mismatch

    The mismatch branch runs exactly once:

    1. ``point.unbind(self._update_point)`` — removes this callback from the
       shared root's callback list so it never fires again.
    2. ``self._stored_point3d = None`` — invalidates the cached geometry Point.
    3. ``self._db_id = db_id`` — updates this instance's row id to ``real_id``.
    4. ``self._is_clone = True`` — marks this instance permanently as a clone.

    After this, ``pjt_preview`` is effectively an alias for ``real_id``. Any
    code that still holds a reference to ``pjt_preview`` (e.g. a wire's
    cached endpoint entry) will now get the real shared Point on the next
    ``.point`` access, because ``self.db_id + b'3d'`` resolves to
    ``real_id + b'3d'`` and ``PointMeta`` returns the live root instance.

    CLONE GUARD IN .point
    ----------------------
    The ``.point`` property checks ``_is_clone`` before binding
    ``_update_point``::

        if not self._is_clone:
            self._stored_point3d.bind(self._update_point)

    This prevents a second DB-write callback from being registered on the
    real shared Point — the ``real_id`` ``PJTPoint3D`` already has its own
    ``_update_point`` bound and is the sole writer for that row.

    SINGLETON CACHE CLEANUP
    ------------------------
    After the self-heal, ``_PJTEntrySingleton._instances`` still holds a
    stale entry ``preview_id`` → ``weakref(pjt_preview)``.  This is
    harmless: ``pjt_preview`` now reports ``db_id=real_id`` and
    ``_is_clone=True``, so everything it exposes is correct.  When the
    preview DB row is eventually deleted and the last Python reference to
    ``pjt_preview`` is dropped, the garbage collector collects the instance
    and the weakref finalizer registered by ``_PJTEntrySingleton.__call__``
    removes the stale cache entry automatically.  No manual cache surgery
    is required.
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
        db_id = point.db_id[:-2]
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
        needs its own tagged waypoint row (a ``pjt_points3d`` row's
        ``wire_id``/``idx`` can only belong to one wire's own ordered
        waypoint list at a time, so it can't literally share the
        canonical row -- this is how the clone still tracks that
        canonical point's own movement instead of being left behind: see
        ``pjt_housing.PJTHousing._update_position3d``/``_update_angle3d``,
        which look up every clone of a terminal's/cavity's own wire-side
        points by this column and move them along with their parent in
        the same batch).

        :returns: The referenced ``pjt_points3d`` row id, or ``None``.
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
            self._stored_point3d = _point.Point(self.x, self.y, self.z, db_id=self.db_id + b'3d')
            if not self._is_clone:
                self._stored_point3d.bind(self._update_point)

            # Child-point tracking (see parent_point_id/_sync_from_parent) --
            # distinct from the _is_clone/.attach() alias mechanism above:
            # this row is a real, independently-written row (tagged with its
            # own wire's wire_id/idx, e.g. a second/third/fourth wire
            # attached to the same terminal -- see objects.terminal.
            # Terminal._own_or_cloned_point_id), not a dead alias forwarding
            # entirely to another row. It keeps its own _update_point
            # binding (so it still persists its own x/y/z when moved
            # directly); it just also follows its parent's own position
            # whenever THAT moves outside of a housing move/rotate, via a
            # second, one-directional binding on the parent's own Point.
            #
            # Deliberately NOT relied on for a whole-housing move/rotate --
            # PJTHousing._update_position3d/_update_angle3d instead collect
            # every child directly (_find_child_points) and fold them into
            # the same single vectorized numpy delta + one batch_update
            # call everything else in that cascade already goes through,
            # to avoid one individual UPDATE per child point on every drag
            # frame when a housing has many terminals/wires. This binding
            # covers every OTHER way a parent point can move instead (a
            # terminal repositioned within its cavity, wherever in the code
            # that happens) -- confirmed acceptable to leave both active
            # simultaneously (a housing move may redundantly re-fire this
            # for children it already just batch-moved, a harmless no-op
            # delta) since a parent realistically only ever has a handful
            # of children (e.g. 3-4 ground wires tied into one ring
            # terminal), never housing-cascade-scale numbers.
            parent_id = self.parent_point_id
            if parent_id is not None:
                parent_point = self._table.db.pjt_points3d_table[parent_id].point
                parent_point.bind(self._sync_from_parent)

        return self._stored_point3d

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
        delta = parent_point - self._stored_point3d
        self._stored_point3d += delta

    @_check_types.do
    def is_referenced(self) -> bool:
        """Whether anything still references this point row -- checked by
        :meth:`delete` before actually removing it.

        **Phased rollout (see TODO.md's "Safe point-deletion / ownership
        design spec" entry) -- wired in so far:**

        - Phase 1 (2026-09-02): ``pjt_notes``.
        - Phase 2 (2026-09-02): ``pjt_boots``/``pjt_covers``/
          ``pjt_cpa_locks``/``pjt_tpa_locks`` (each accessory's own
          ``point3d_id``/``scale3d_id``) and ``pjt_housings``' own
          ``boot_point3d_id``/``cover_point3d_id``/``cpa_lock_point3d_id``/
          ``tpa_lock_1_point3d_id``/``tpa_lock_2_point3d_id`` -- the
          accessory's ``point3d_id`` and the owning housing's own column
          are always the SAME shared point id (the housing owns it, the
          accessory reuses it directly, never a clone), so in practice
          either check alone would already catch it; both are checked
          anyway for defensiveness/completeness rather than relying on
          that invariant never being violated.
        - Phase 3 (2026-09-02): ``pjt_seals`` (its own ``point3d_id``/
          ``scale3d_id``) and both possible owners' own columns --
          ``pjt_housings.seal_point3d_id`` (a housing-level MAT seal) and
          ``pjt_terminals.seal_point3d_id`` (a terminal-seated SWS/
          single-wire-seal) -- same shared-id reasoning as Phase 2.
        - Phase 5 (2026-09-02): the hub tables' own remaining point
          columns -- ``pjt_housings.point3d_id`` (its own identity
          anchor, never shared with anything else); ``pjt_cavities``'
          own ``point3d_id`` (identity anchor), ``terminal_point3d_id``
          (shared with ``pjt_terminals.point3d_id`` -- a cavity's own
          pre-visualization guess at where a terminal will sit, before
          one is actually seated) and ``wire_point3d_id`` (the cavity's
          wire-exit routing point, reused as an interior waypoint on any
          wire routed through it -- see ``Terminal.add_wire``; the wire
          side of this sharing isn't wired in here until Phase 6);
          ``pjt_terminals``' own ``point3d_id`` (identity anchor, shared
          with ``pjt_cavities.terminal_point3d_id``), ``wire_point3d_id``
          (the terminal's own back-routing point, same interior-waypoint
          reuse as the cavity's), and ``attach_point3d_id`` (the crimp
          point, reused directly as a wire's own start/stop -- the wire
          side isn't wired in until Phase 6 either).
        - Phase 6 (2026-09-02): ``pjt_wires``/``pjt_bundles`` -- both
          their own start/stop endpoints (forward references, named
          directly by ``start_point3d_id``/``stop_point3d_id``) AND the
          backward, count-unknown case that started this whole design
          spec -- a point's own ``wire_id``/``bundle_id`` tag, checked
          for whether that wire/bundle still actually EXISTS (not just
          whether the tag is set -- see the inline comment at the check
          itself for why a stale tag must not read as "referenced").
        - Phase 7 (2026-09-02): ``pjt_transitions`` (its own identity
          anchor ``point3d_id``) and ``pjt_transition_branches`` (its own
          ``point3d_id`` -- a branch's own row is itself the same
          backward, count-unknown shape against its owning transition
          that Phase 6 covers for wire/bundle waypoints, just via a whole
          row's ``transition_id`` instead of a point's own tag -- see
          ``PJTTransition.delete()``'s own docstring).
        - Phase 8 (2026-09-02): the remaining markers/multi-point
          objects -- ``pjt_wire_layouts``/``pjt_bundle_layouts`` (own
          ``point3d_id``), ``pjt_wire_markers`` (own ``point3d_id``),
          ``pjt_splices`` (own ``start_point3d_id``/``stop_point3d_id``/
          ``branch_point3d_id`` -- often the SAME id as a wire's own
          start/stop, already caught by Phase 6, checked again for
          defensiveness), and ``pjt_wire_service_loops`` (own
          ``start_point3d_id``/``stop_point3d_id``, an ordinary forward
          reference -- no self-tagging column exists for service loops).

        Until every phase lands, this can still return ``False`` for a
        point that's actually in live use via a column this method
        doesn't know about yet -- do not treat a ``False`` result as a
        global guarantee of safety before the rollout is complete.
        """
        db = self._table.db

        if db.pjt_notes_table.select(
            'id', OR=True, point3d_id=self.db_id, scale3d_id=self.db_id
        ):
            return True

        for table in (
            db.pjt_boots_table, db.pjt_covers_table,
            db.pjt_cpa_locks_table, db.pjt_tpa_locks_table,
            db.pjt_seals_table,
        ):
            if table.select('id', OR=True, point3d_id=self.db_id, scale3d_id=self.db_id):
                return True

        if db.pjt_housings_table.select(
            'id', OR=True,
            boot_point3d_id=self.db_id, cover_point3d_id=self.db_id,
            cpa_lock_point3d_id=self.db_id,
            tpa_lock_1_point3d_id=self.db_id, tpa_lock_2_point3d_id=self.db_id,
            seal_point3d_id=self.db_id, point3d_id=self.db_id,
        ):
            return True

        if db.pjt_cavities_table.select(
            'id', OR=True, point3d_id=self.db_id,
            terminal_point3d_id=self.db_id, wire_point3d_id=self.db_id,
        ):
            return True

        if db.pjt_terminals_table.select(
            'id', OR=True, seal_point3d_id=self.db_id, point3d_id=self.db_id,
            wire_point3d_id=self.db_id, attach_point3d_id=self.db_id,
        ):
            return True

        # Phase 6 (2026-09-02): backward, count-unknown references -- a
        # wire/bundle has no fixed column naming each of its own interior
        # waypoints (there can be any number of them), so a waypoint
        # point instead self-identifies via its OWN wire_id/bundle_id
        # column (see create_database/points3d.py). wire_id/bundle_id
        # being set does NOT by itself mean still-in-use: PJTWire.delete()/
        # PJTBundle.delete() deliberately never clear a waypoint's own
        # wire_id/bundle_id tag when they delete the wire/bundle itself
        # (see their own docstrings -- the point may still be owned by a
        # terminal/cavity, already covered above), so a stale tag
        # pointing at an already-deleted wire/bundle must NOT read as
        # "referenced" here -- hence the existence check, not just a
        # None check.
        if self.wire_id is not None and self.wire_id in db.pjt_wires_table:
            return True

        if self.bundle_id is not None and self.bundle_id in db.pjt_bundles_table:
            return True

        # A wire/bundle's own start/stop endpoint is a forward reference
        # (unlike its interior waypoints above) -- named directly by
        # start_point3d_id/stop_point3d_id, not self-tagged.
        if db.pjt_wires_table.select(
            'id', OR=True, start_point3d_id=self.db_id, stop_point3d_id=self.db_id
        ):
            return True

        if db.pjt_bundles_table.select(
            'id', OR=True, start_point3d_id=self.db_id, stop_point3d_id=self.db_id
        ):
            return True

        # Phase 7 (2026-09-02): pjt_transitions' own identity anchor, and
        # pjt_transition_branches' own point (each branch is itself a
        # backward, count-unknown reference against its OWNING
        # transition -- transition_id, no fixed branch1_id..branch6_id
        # columns -- but its own point3d_id here is an ordinary forward
        # reference, same shape as everything else in this block).
        if db.pjt_transitions_table.select('id', point3d_id=self.db_id):
            return True

        if db.pjt_transition_branches_table.select('id', point3d_id=self.db_id):
            return True

        # Phase 8 (2026-09-02): markers and the remaining multi-point
        # objects. WireLayout/BundleLayout are pure markers (a bend/seam
        # already tagged as a waypoint elsewhere, or a snap-target) --
        # their own point3d_id is a forward reference, same as always.
        # WireMarker likewise (its own wire_id is a forward reference TO
        # a wire, not a point self-tag -- unlike Phase 6's wire_id on the
        # point itself). Splice's own start/stop/branch points are often
        # literally the SAME point id as some wire's own start/stop
        # (already caught by Phase 6's pjt_wires check), checked again
        # here for defensiveness/completeness, same as every other
        # shared-point pair in this design. Wire-service-loop start/stop
        # are ordinary forward references, no self-tagging shape at all
        # (no wire_service_loop_id column exists on the points tables).
        if db.pjt_wire_layouts_table.select('id', point3d_id=self.db_id):
            return True

        if db.pjt_bundle_layouts_table.select('id', point3d_id=self.db_id):
            return True

        if db.pjt_wire_markers_table.select('id', point3d_id=self.db_id):
            return True

        if db.pjt_splices_table.select(
            'id', OR=True, start_point3d_id=self.db_id,
            stop_point3d_id=self.db_id, branch_point3d_id=self.db_id,
        ):
            return True

        if db.pjt_wire_service_loops_table.select(
            'id', OR=True, start_point3d_id=self.db_id, stop_point3d_id=self.db_id
        ):
            return True

        return False

    @_check_types.do
    def delete(self) -> None:
        """Delete this point row -- but only if :meth:`is_referenced`
        says nothing still needs it. A safety-checked override of
        ``PJTEntryBase.delete``, so nothing (including the many existing
        call sites that already delete a stale/placeholder point
        directly, e.g. after a hover/click moves a wire's growing point
        on to a fresh one) can silently pull a point out from under some
        other row's own stored reference to it.

        No-op (not an exception) when still referenced -- a caller that
        creates and immediately discards a throwaway placeholder point
        already expects ``delete()`` to just work; a point that's still
        genuinely in use shouldn't have been asked to delete itself at
        all (that's a caller-side bug elsewhere), and raising here would
        just crash on top of that instead of surfacing it usefully.
        """
        if self.is_referenced():
            return

        super().delete()
