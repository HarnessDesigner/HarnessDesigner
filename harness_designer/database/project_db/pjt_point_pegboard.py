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
            if item in PJTPointPegboard or item in self:
                return PJTPointPegboard(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(self, x: float | int, y: float | int, z: float | int) -> "PJTPointPegboard":
        """Add a point row.

        A point is pure geometry: it carries no owner and no order. Which
        wires/bundles use it, and where in their routes, is stored in
        ``pjt_wire_paths``/``pjt_bundle_paths``, not here.

        :param x: X-coordinate value.
        :param y: Y-coordinate value.
        :param z: Z-coordinate value.
        :returns: The new point row.
        """
        db_id = PJTTableBase.insert(self, x=float(x), y=float(y), z=float(z))
        return PJTPointPegboard(self, db_id)


class PJTPointPegboard(PJTEntryBase):
    """ORM entry for a single row in ``pjt_points_pegboard``, with a reactive geometry Point.

    Structurally identical to :class:`~harness_designer.database.project_db.
    pjt_point3d.PJTPoint3D` -- same singleton/attach/clone/self-heal
    lifecycle, same ``parent_point_id`` column, same ``_skip_db_write``
    batch-suppression flag. See
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
        db_id = point.db_id[:-2]
        if db_id != self._db_id:
            point.unbind(self._update_point)
            self._stored_point_pegboard = None
            self._db_id = db_id
            self._is_clone = True
            self._stored_x = DefaultStoredValue
            self._stored_y = DefaultStoredValue
            self._stored_z = DefaultStoredValue
            return
        # KNOWN POTENTIAL ISSUE (2026-09-06) -- see PJTPoint3D._update_point's
        # own comment for the full writeup: this early return also skips
        # refreshing _stored_x/_stored_y/_stored_z, not just the redundant
        # DB write, which can leave this singleton row's cache stale
        # relative to the real DB row/live .point after a housing move/
        # rotate. A fix was tried and reverted because it broke cavity
        # selection right after a fresh housing placement (unrelated,
        # pre-existing construction-ordering issue) -- don't re-attempt
        # without also solving that.
        if PJTPointPegboard._skip_db_write:
            return
        x, y, z = point.as_float
        self._stored_x = x
        self._stored_y = y
        self._stored_z = z
        self._table.update(self._db_id, x=x, y=y, z=z)

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
                self.x, self.y, self.z, db_id=self.db_id + b'pg')
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

    @_check_types.do
    def is_referenced(self) -> bool:
        """Whether anything still references this point row -- checked by
        :meth:`delete` before actually removing it.

        **Phased rollout (see TODO.md's "Safe point-deletion / ownership
        design spec" entry) -- wired in so far:**

        - Phase 1 (2026-09-02): ``pjt_notes``.
        - Phase 2 (2026-09-02): none -- boot/cover/cpa_lock/tpa_lock have
          no peg-board presence at all (3D-only accessories), so nothing
          to add here for that phase.
        - Phase 3 (2026-09-02): ``pjt_seals`` (its own
          ``point_pegboard_id``/``scale_pegboard_id``) and both possible
          owners' own columns -- ``pjt_housings.seal_point_pegboard_id``
          and ``pjt_terminals.seal_point_pegboard_id`` -- same shared-id
          reasoning as :meth:`pjt_point3d.PJTPoint3D.is_referenced`'s own
          Phase 2/3 entries.
        - Phase 4 (2026-09-02): ``pjt_pegboard_tables`` (its own
          ``point_pegboard_id``, keyed 1:1 to whichever anchor's own
          ``table_point_peg_id`` this same point id also is) and every
          anchor type that can have a peg-board data-table overlay --
          ``pjt_housings``/``pjt_transitions``/
          ``pjt_transition_branches``/``pjt_bundles``/``pjt_splices``'
          own ``table_point_peg_id`` columns (see
          ``TablePositionPegMixin``).
        - Phase 5 (2026-09-02): the hub tables' own remaining peg-board
          columns -- ``pjt_housings.point_pegboard_id`` (identity
          anchor); ``pjt_cavities``' own ``point_pegboard_id`` (identity
          anchor), ``terminal_point_pegboard_id`` and
          ``wire_point_pegboard_id`` (peg-board mirrors of
          ``terminal_point3d_id``/``wire_point3d_id``, same sharing
          reasoning); ``pjt_terminals``' own ``point_pegboard_id``
          (identity anchor), ``wire_point_pegboard_id``, and
          ``attach_point_pegboard_id`` -- see
          :meth:`pjt_point3d.PJTPoint3D.is_referenced`'s own Phase 5
          entry for the full reasoning, mirrored here for peg-board.
        - Phase 6 (2026-09-02): ``pjt_wires``/``pjt_bundles`` -- own
          start/stop (forward reference) plus this point's own
          ``wire_id``/``bundle_id`` self-tag (checked for whether that
          wire/bundle still actually exists) -- see
          :meth:`pjt_point3d.PJTPoint3D.is_referenced`'s own Phase 6
          entry for the full reasoning.
        - Phase 7 (2026-09-02): ``pjt_transitions``' own identity anchor
          and ``pjt_transition_branches``' own point -- see
          :meth:`pjt_point3d.PJTPoint3D.is_referenced`'s own Phase 7
          entry for the full reasoning.
        - Phase 8 (2026-09-02): ``pjt_wire_layouts``/``pjt_bundle_layouts``/
          ``pjt_wire_markers`` (own ``point_pegboard_id``), ``pjt_splices``
          (own ``start_point_pegboard_id``/``stop_point_pegboard_id``/
          ``branch_point_pegboard_id``), and ``pjt_wire_service_loops``
          (own ``start_point_pegboard_id``/``stop_point_pegboard_id``).

        Until every phase lands, this can still return ``False`` for a
        point that's actually in live use via a column this method
        doesn't know about yet -- do not treat a ``False`` result as a
        global guarantee of safety before the rollout is complete.
        """
        db = self._table.db

        if db.pjt_notes_table.select(
            'id', OR=True, point_pegboard_id=self.db_id, scale_pegboard_id=self.db_id
        ):
            return True

        if db.pjt_seals_table.select(
            'id', OR=True, point_pegboard_id=self.db_id, scale_pegboard_id=self.db_id
        ):
            return True

        if db.pjt_housings_table.select('id', seal_point_pegboard_id=self.db_id):
            return True

        if db.pjt_terminals_table.select('id', seal_point_pegboard_id=self.db_id):
            return True

        if db.pjt_pegboard_tables_table.select('id', point_pegboard_id=self.db_id):
            return True

        for table in (
            db.pjt_housings_table, db.pjt_transitions_table,
            db.pjt_transition_branches_table, db.pjt_bundles_table,
            db.pjt_splices_table,
        ):
            if table.select('id', table_point_peg_id=self.db_id):
                return True

        if db.pjt_housings_table.select('id', point_pegboard_id=self.db_id):
            return True

        if db.pjt_cavities_table.select(
            'id', OR=True, point_pegboard_id=self.db_id,
            terminal_point_pegboard_id=self.db_id, wire_point_pegboard_id=self.db_id,
        ):
            return True

        if db.pjt_terminals_table.select(
            'id', OR=True, point_pegboard_id=self.db_id,
            wire_point_pegboard_id=self.db_id, attach_point_pegboard_id=self.db_id,
        ):
            return True

        # Interior waypoints: a wire's or a bundle's own ordered waypoint
        # list is stored as rows in pjt_wire_paths/pjt_bundle_paths that
        # reference this point (any number of wires can share it), not as
        # owner tags on the point itself. A route row is deleted with its
        # wire/bundle (PJTWire.delete/PJTBundle.delete), so a row that
        # exists always means the point is still in use.
        if db.pjt_wire_paths_table.select('id', point_pegboard_id=self.db_id):
            return True

        if db.pjt_bundle_paths_table.select('id', point_pegboard_id=self.db_id):
            return True

        if db.pjt_wires_table.select(
            'id', OR=True,
            start_point_pegboard_id=self.db_id, stop_point_pegboard_id=self.db_id,
        ):
            return True

        if db.pjt_bundles_table.select(
            'id', OR=True,
            start_point_pegboard_id=self.db_id, stop_point_pegboard_id=self.db_id,
        ):
            return True

        # Phase 7 (2026-09-02): pjt_transitions' own identity anchor, and
        # pjt_transition_branches' own point -- see
        # pjt_point3d.PJTPoint3D.is_referenced's own Phase 7 entry for
        # the full reasoning.
        if db.pjt_transitions_table.select('id', point_pegboard_id=self.db_id):
            return True

        if db.pjt_transition_branches_table.select('id', point_pegboard_id=self.db_id):
            return True

        # Phase 8 (2026-09-02): the remaining markers/multi-point
        # objects -- see pjt_point3d.PJTPoint3D.is_referenced's own
        # Phase 8 entry for the full reasoning, mirrored here for
        # peg-board.
        if db.pjt_wire_layouts_table.select('id', point_pegboard_id=self.db_id):
            return True

        if db.pjt_bundle_layouts_table.select('id', point_pegboard_id=self.db_id):
            return True

        if db.pjt_wire_markers_table.select('id', point_pegboard_id=self.db_id):
            return True

        if db.pjt_splices_table.select(
            'id', OR=True, start_point_pegboard_id=self.db_id,
            stop_point_pegboard_id=self.db_id, branch_point_pegboard_id=self.db_id,
        ):
            return True

        if db.pjt_wire_service_loops_table.select(
            'id', OR=True,
            start_point_pegboard_id=self.db_id, stop_point_pegboard_id=self.db_id,
        ):
            return True

        return False

    @_check_types.do
    def delete(self) -> None:
        """Delete this point row -- but only if :meth:`is_referenced`
        says nothing still needs it. See
        :meth:`pjt_point3d.PJTPoint3D.delete`'s own docstring for the
        full reasoning (same safety-checked override, mirrored here).
        """
        if self.is_referenced():
            return

        super().delete()
