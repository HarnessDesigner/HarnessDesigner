# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from ...geometry import point as _point
from ... import check_types as _check_types


class PJTPoints2DTable(PJTTableBase):
    """Represent a PJT points 2dtable in :mod:`harness_designer.database.project_db.pjt_point2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_points2d'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import points2d

        return points2d.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import points2d

        points2d.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import points2d

        had_z = 'z' in self._con.get_table_column_names(self.__table_name__)

        points2d.pjt_table.update_fields(self)

        if not had_z:
            # One-time migration. Before ``z`` existed, the schematic
            # plane's second axis lived in ``y`` and was mapped onto
            # ``Point.z`` (with ``Point.y`` locked to 0.0). Move every
            # existing row's value into ``z`` so ``Point`` reads the same
            # position it always did, then zero ``y`` to match.
            self._con.execute(f'UPDATE {self.__table_name__} SET z = y, y = 0.0;')
            self._con.commit()

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTPoint2D"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTPoint2D']
        """

        for db_id in PJTTableBase.__iter__(self):
            point = PJTPoint2D(self, db_id)
            yield point

    @_check_types.do
    def __getitem__(self, item) -> "PJTPoint2D":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTPoint2D`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes)):
            if item in PJTPoint2D or item in self:
                return PJTPoint2D(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(self, x: float | int, y: float | int, z: float | int) -> "PJTPoint2D":
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
        return PJTPoint2D(self, db_id)


class PJTPoint2D(PJTEntryBase):
    """Represent a PJT point 2D in :mod:`harness_designer.database.project_db.pjt_point2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: PJTPoints2DTable = None

    @property
    @_check_types.do
    def table(self) -> PJTPoints2DTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTPoints2DTable`
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

        :returns: Property value.
        :rtype: float
        """
        if self._stored_z is DefaultStoredValue:
            self._stored_z = self._table.select('z', id=self._db_id)[0][0]

        return self._stored_z

    @z.setter
    @_check_types.do
    def z(self, value: float):
        """Set the z.

        :param value: Value to store or process.
        :type value: float
        """
        self._stored_z = value
        self._table.update(self._db_id, z=value)

    _stored_point2d: _point.Point = None

    # Class-level flag: set True during bulk position batch-writes so the
    # per-point DB callback is suppressed while render callbacks still fire.
    _skip_db_write: bool = False

    @property
    @_check_types.do
    def point(self) -> _point.Point:
        """Return the point.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_point2d is None:
            x, y, z = self._table.select('x', 'y', 'z', id=self._db_id)[0]

            self._stored_point2d = _point.Point(x, y, z, db_id=self.db_id + b'2d')
            self._stored_point2d.bind(self._update_point)

        return self._stored_point2d

    @_check_types.do
    def _update_point(self, point: _point.Point):
        """Update the point.

        UNKNOWN details are inferred from the callable name and signature.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
        if PJTPoint2D._skip_db_write:
            return

        x, y, z = point.as_float
        self._stored_x = x
        self._stored_y = y
        self._stored_z = z
        self._table.update(self._db_id, x=x, y=y, z=z)

    @_check_types.do
    def is_referenced(self) -> bool:
        """Whether anything still references this point row -- checked by
        :meth:`delete` before actually removing it.

        **Phased rollout (see TODO.md's "Safe point-deletion / ownership
        design spec" entry) -- wired in so far:**

        - Phase 1 (2026-09-02): ``pjt_concentric_wires``/``pjt_notes``.
        - Phase 5 (2026-09-02): the hub tables' own 2D columns --
          ``pjt_housings.point2d_id`` (identity anchor), ``pjt_cavities.
          point2d_id`` (identity anchor), ``pjt_terminals.point2d_id``
          (identity anchor -- this terminal's own name-anchor position,
          distinct from ``wire_point2d_id`` below) and
          ``pjt_terminals.wire_point2d_id`` (the far end of the wire-stub
          line in the schematic view -- see ``objects/terminal.py``'s own
          docstring on why that's a separate point from ``point2d_id``).
        - Phase 6 (2026-09-02): ``pjt_wires`` -- own start/stop (forward
          reference) plus this point's own ``wire_id`` self-tag (checked
          for whether that wire still actually exists). No ``bundle_id``
          here -- bundles have no 2D/schematic presence at all.
        - Phase 8 (2026-09-02): ``pjt_wire_layouts``/``pjt_wire_markers``
          (own ``point2d_id``) and ``pjt_splices`` (own ``point2d_id``).

        See :meth:`pjt_point3d.PJTPoint3D.is_referenced`'s own docstring
        for the full caveat about later phases still to land.
        """
        db = self._table.db

        if db.pjt_concentric_wires_table.select('id', point2d_id=self.db_id):
            return True

        if db.pjt_notes_table.select(
            'id', OR=True, point2d_id=self.db_id, scale2d_id=self.db_id
        ):
            return True

        if db.pjt_housings_table.select('id', point2d_id=self.db_id):
            return True

        if db.pjt_cavities_table.select('id', point2d_id=self.db_id):
            return True

        if db.pjt_terminals_table.select(
            'id', OR=True, point2d_id=self.db_id, wire_point2d_id=self.db_id
        ):
            return True

        # Interior waypoints: a wire's own ordered waypoint list is stored
        # as rows in pjt_wire_paths that reference this point (any number
        # of wires can share it), not as an owner tag on the point itself.
        # A route row is deleted with its wire (PJTWire.delete), so a row
        # that exists always means the point is still in use. No bundle
        # paths here -- bundles have no 2D/schematic presence at all.
        if db.pjt_wire_paths_table.select('id', point2d_id=self.db_id):
            return True

        if db.pjt_wires_table.select(
            'id', OR=True, start_point2d_id=self.db_id, stop_point2d_id=self.db_id
        ):
            return True

        # Phase 8 (2026-09-02): pjt_wire_layouts/pjt_wire_markers (own
        # point2d_id, ordinary forward references) and pjt_splices (own
        # point2d_id -- often the same id as a wire's own start/stop
        # point2d, already caught above, checked again for
        # defensiveness). No bundle_layouts/wire_service_loops here --
        # neither has any 2D/schematic presence at all.
        if db.pjt_wire_layouts_table.select('id', point2d_id=self.db_id):
            return True

        if db.pjt_wire_markers_table.select('id', point2d_id=self.db_id):
            return True

        if db.pjt_splices_table.select('id', point2d_id=self.db_id):
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
