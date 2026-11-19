# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Pooled storage for a housing's SCHEMATIC points, and the vector move / rotate.

``SlotPoolsSchematic`` is the project's schematic point pool, every housing's slots, and the registry
that says which slot a ``pjt_points2d`` row is bound to (``build_point`` gives a ``Point`` its view).
``HousingSlotsSchematic`` is one housing: its fixed block (the housing's own point) and cavity block
(three points per cavity), what is bound to each slot, and ``move`` / ``rotate``.

What is the same as the other views is in ``housing_slots_base.py``; what is different here:

* POINTS ONLY. The schematic has no angle of its own below the housing (a cavity and a terminal have
  no ``angle2d`` that follows the housing: their names stay upright and only their anchor positions
  turn), so there is no angle pool; the housing's one ``Angle`` is an ordinary one.
* three points per cavity: the cavity's point (its name anchor; ``terminal_position2d`` is the same
  row), the terminal's wire point (the far end of the wire stub) and the terminal's point;
* a rotation to or from exactly 180 degrees is laid out differently from a plain rotation: each stored
  point has its own Z correction (``CavityGeometry.z_shift_at_180``), taken off before the rotation
  when it starts from 180 and put on after it when it ends at 180;
* the callbacks of one cavity fire in the order cavity, terminal wire point, terminal point: the
  terminal's callback reads its wire point to size the wire stub, so the wire point is fresh first
  (every value is final before the first callback fires, so the order matters only for what a
  callback reads from another point).

THE WHOLE DESIGN is in the module docstring of ``database/project_db/pjt_housing.py`` ("POOLED 3D
STORAGE", section 15). Change that text in the same edit as any change here.
"""

from typing import TYPE_CHECKING

import numpy as np

from ...geometry import batch as _batch
from ... import check_types as _check_types
from . import housing_slots_base as _base

if TYPE_CHECKING:
    from . import pjt_bases as _pjt_bases
    from . import pjt_housing as _pjt_housing


# Fixed block: the housing's own point.
FIXED_HOUSING = 0
FIXED_POINTS = 1

# Points of one cavity.
POINT_CAVITY = 0
POINT_TERMINAL_WIRE = 1
POINT_TERMINAL = 2
POINTS_PER_CAVITY = 3

# A chunk holds 10 housings of 100 cavities each (a larger housing still fits in one chunk; one larger
# than a whole chunk gets a chunk of its own).
CHUNK_HOUSINGS = 10
CHUNK_CAVITIES = 100
POINT_CHUNK_SLOTS = CHUNK_HOUSINGS * (FIXED_POINTS + POINTS_PER_CAVITY * CHUNK_CAVITIES)

# Point-id columns that rebind a slot when they change, by table.
_HOUSING_POINT_COLUMNS = (('point2d_id', FIXED_HOUSING),)

_CAVITY_POINT_COLUMNS = (('point2d_id', POINT_CAVITY),)

_TERMINAL_POINT_COLUMNS = (
    ('point2d_id', POINT_TERMINAL),
    ('wire_point2d_id', POINT_TERMINAL_WIRE))

# The point-id column names of each table, for the tables' ``update`` hooks.
HOUSING_POINT_COLUMNS = frozenset(name for name, _ in _HOUSING_POINT_COLUMNS)
CAVITY_POINT_COLUMNS = frozenset(name for name, _ in _CAVITY_POINT_COLUMNS)
TERMINAL_POINT_COLUMNS = frozenset(name for name, _ in _TERMINAL_POINT_COLUMNS)


class HousingSlotsSchematic(_base.SlotsBase):
    """The schematic slots of one housing: its blocks, which row is bound to which slot, and the vector move / rotate."""

    FIXED_POINTS = FIXED_POINTS
    POINTS_PER_CAVITY = POINTS_PER_CAVITY
    POINT_SUFFIX = b'2d'
    TERMINAL_COLUMNS = _TERMINAL_POINT_COLUMNS

    # ----------------------------------------------------------------- binding

    @_check_types.do
    def _bind_fixed(self) -> None:
        """Bind the housing's own point."""

        row = self._db.pjt_housings_table.select('point2d_id', id=self._id)[0]

        self.bind_point(FIXED_HOUSING, row[0])

    @_check_types.do
    def _bind_cavities(self) -> None:
        """Bind every cavity's point and its terminal's two points."""

        db = self._db
        rows = db.pjt_cavities_table.select('id', 'point2d_id', housing_id=self._id)

        for cavity_id, point_id in rows:
            self.bind_point(self.cavity_point_slot(cavity_id, POINT_CAVITY), point_id)

            terminal_rows = db.pjt_terminals_table.select(
                'point2d_id', 'wire_point2d_id', cavity_id=cavity_id)

            if terminal_rows:
                terminal_point_id, wire_point_id = terminal_rows[0]

                self.bind_point(self.cavity_point_slot(cavity_id, POINT_TERMINAL), terminal_point_id)
                self.bind_point(self.cavity_point_slot(cavity_id, POINT_TERMINAL_WIRE), wire_point_id)

    @_check_types.do
    def column_changed(self, table_name: str, row_id: bytes, columns: dict[str, bytes | None]) -> None:
        """
        A point-id column of the housing, a cavity or a terminal was written: rebind the slot that
        column belongs to.

        :param table_name: ``pjt_housings``, ``pjt_cavities`` or ``pjt_terminals``.
        :type table_name: str
        :param row_id: The row that was written.
        :type row_id: bytes
        :param columns: The point-id columns that were written and their new values.
        :type columns: dict[str, bytes | None]
        """

        if table_name == 'pjt_housings':
            for name, slot in _HOUSING_POINT_COLUMNS:
                if name in columns:
                    self.bind_point(slot, columns[name])

            return

        if table_name == 'pjt_cavities':
            cavity_id = row_id
            names = _CAVITY_POINT_COLUMNS
        else:
            cavity_id = self._db.pjt_terminals_table.select('cavity_id', id=row_id)[0][0]
            names = _TERMINAL_POINT_COLUMNS

        for name, role in names:
            if name in columns:
                self.bind_point(self.cavity_point_slot(cavity_id, role), columns[name])

    # ------------------------------------------------------------ the cascades

    @_check_types.do
    def move(self, delta: np.ndarray) -> None:
        """
        Move every point of the housing except its own by ``delta``, bring the database cache up to
        date and fire the callbacks.

        :param delta: The move, ``(3,)``.
        :type delta: :class:`numpy.ndarray`
        """

        if self._cavity_points is not None:
            cavity = self._pools.points.array(self._cavity_points, 'data')
            cavity += delta.astype(np.float32)

        self._write_points()
        self._fire_point_callbacks()

    @_check_types.do
    def rotate(self, housing: "_pjt_housing.PJTHousing", delta: np.ndarray, center: np.ndarray,
               from_180: bool, to_180: bool) -> None:
        """
        Rotate every point of the housing about ``center`` by ``delta`` (a unit quaternion
        ``(w, x, y, z)``), bring the database cache up to date and fire the callbacks.

        :param housing: The housing's row object (its cavity geometry gives the 180 degree corrections).
        :type housing: :class:`_pjt_housing.PJTHousing`
        :param delta: The rotation, ``(4,)``.
        :type delta: :class:`numpy.ndarray`
        :param center: The housing's position, ``(3,)``.
        :type center: :class:`numpy.ndarray`
        :param from_180: The rotation starts from exactly 180 degrees.
        :type from_180: bool
        :param to_180: The rotation ends at exactly 180 degrees.
        :type to_180: bool
        """

        if self._cavity_points is not None:
            cavity = self._pools.points.array(self._cavity_points, 'data')

            shifts = None
            if from_180 or to_180:
                shifts = self._z_shifts(housing)

            if from_180:
                cavity[:, 2] -= shifts

            cavity[:] = _batch.rotate_points(cavity, center, delta)

            if to_180:
                cavity[:, 2] += shifts

        self._write_points()
        self._fire_point_callbacks()

    @_check_types.do
    def _z_shifts(self, housing: "_pjt_housing.PJTHousing") -> np.ndarray:
        """
        The Z correction of every cavity-block slot at exactly 180 degrees (``CavityGeometry.z_shift_at_180``):
        the cavity's name anchor, the end of the terminal's wire stub and the terminal's own point.

        :param housing: The housing's row object.
        :type housing: :class:`_pjt_housing.PJTHousing`
        :returns: One value per slot of the cavity block, float32.
        :rtype: :class:`numpy.ndarray`
        """

        shifts = np.zeros(len(self._cavity_ids) * POINTS_PER_CAVITY, dtype=np.float32)

        for cavity_id, geometry in housing.cavity_geometry.items():
            index = self._cavity_index.get(cavity_id)

            if index is None:
                continue

            base = index * POINTS_PER_CAVITY

            shifts[base + POINT_CAVITY] = geometry.z_shift_at_180(geometry.name_position[1])
            shifts[base + POINT_TERMINAL_WIRE] = geometry.z_shift_at_180(geometry.cylinder_stop[1])
            shifts[base + POINT_TERMINAL] = geometry.z_shift_at_180(geometry.position[1])

        return shifts

    @_check_types.do
    def _fire_point_callbacks(self) -> None:
        """
        Fire the callbacks of every pooled point that has an object, cavity by cavity in the order
        cavity point, terminal wire point, terminal point.
        """

        fixed, cavity = self._members()

        for index in range(len(self._cavity_ids)):
            base = index * POINTS_PER_CAVITY

            for role in (POINT_CAVITY, POINT_TERMINAL_WIRE, POINT_TERMINAL):
                member = cavity[base + role]

                if member is not None:
                    member._process_callbacks()  # NOQA


class SlotPoolsSchematic(_base.PoolsBase):
    """The schematic point pool of one project, and every housing's slots."""

    POINT_CHUNK_SLOTS = POINT_CHUNK_SLOTS

    @_check_types.do
    def points_table(self) -> "_pjt_bases.PJTTableBase":
        """The ``pjt_points2d`` table."""

        return self.db.pjt_points2d_table

    @_check_types.do
    def new_slots(self, housing_id: bytes) -> HousingSlotsSchematic:
        """Build the slots of a housing."""

        return HousingSlotsSchematic(housing_id, self)

    @_check_types.do
    def column_changed(self, table_name: str, row_id: bytes, columns: dict[str, bytes | None]) -> None:
        """
        A point-id column of a housing, cavity or terminal row was written: find the housing the row
        belongs to and rebind the slot. A terminal that is in no cavity has no slots.

        :param table_name: ``pjt_housings``, ``pjt_cavities`` or ``pjt_terminals``.
        :type table_name: str
        :param row_id: The row that was written.
        :type row_id: bytes
        :param columns: The point-id columns that were written, with their new values.
        :type columns: dict[str, bytes | None]
        """

        db = self.db

        if table_name == 'pjt_housings':
            housing_id = row_id
        elif table_name == 'pjt_cavities':
            housing_id = db.pjt_cavities_table.select('housing_id', id=row_id)[0][0]
        else:
            housing_id = self.housing_of_terminal(row_id)

            if housing_id is None:
                return

        self.housing(housing_id).column_changed(table_name, row_id, columns)
