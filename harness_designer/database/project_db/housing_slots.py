# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Pooled storage for a housing's 3D points and angles, and the vector move / rotate.

``SlotPools3D`` is the project's point pool and angle pool, every housing's slots, and the
registry that says which slot a ``pjt_points3d`` row is bound to (``build_point`` and
``build_angle`` give a ``Point`` or an ``Angle`` its view). ``HousingSlots3D`` is one housing: its
fixed block and cavity block, what is bound to each slot (``bind_point`` / ``bind_angle``), the plan
of a gesture, and ``move`` / ``rotate``. The constants below (``FIXED_*``, ``POINT_*``,
``ANGLE_*``) are the layout of section 4 of the documentation.

THE WHOLE DESIGN -- why it exists, the layout, when slots are allocated and released, how rows are
bound, the rules that keep it correct, the step-by-step move and rotate, what differs from the old
per-object cascade, how to change it, the errors you can get, what was checked and the open
work -- is documented in the module docstring of ``database/project_db/pjt_housing.py`` ("POOLED
3D STORAGE"). Change that text in the same edit as any change here.
"""

from typing import TYPE_CHECKING
import ast
import numpy as np

from ...geometry import slot_pool as _slot_pool
from ...geometry import batch as _batch
from ...geometry import point as _point
from ...geometry.angle import angle as _angle
from ... import check_types as _check_types

if TYPE_CHECKING:
    from . import pjt_bases as _pjt_bases
    from . import pjt_housing as _pjt_housing


# Fixed block, in this order (points and angles use the same order).
FIXED_HOUSING = 0
FIXED_BOOT = 1
FIXED_COVER = 2
FIXED_CPA_LOCK = 3
FIXED_SEAL = 4
FIXED_TPA_LOCK_1 = 5
FIXED_TPA_LOCK_2 = 6
FIXED_COUNT = 7

# Points of one cavity.
POINT_CAVITY = 0
POINT_CAVITY_WIRE = 1
POINT_TERMINAL = 2
POINT_TERMINAL_WIRE = 3
POINT_TERMINAL_ATTACH = 4
POINT_SEAL = 5
POINT_TERMINAL_SEAL = 6
POINTS_PER_CAVITY = 7

# Angles of one cavity.
ANGLE_CAVITY = 0
ANGLE_TERMINAL = 1
ANGLE_SEAL = 2
ANGLES_PER_CAVITY = 3

# A chunk holds 10 housings of 100 cavities each (a larger housing still fits
# in one chunk; one larger than a whole chunk gets a chunk of its own).
CHUNK_HOUSINGS = 10
CHUNK_CAVITIES = 100
POINT_CHUNK_SLOTS = CHUNK_HOUSINGS * (FIXED_COUNT + POINTS_PER_CAVITY * CHUNK_CAVITIES)
ANGLE_CHUNK_SLOTS = CHUNK_HOUSINGS * (FIXED_COUNT + ANGLES_PER_CAVITY * CHUNK_CAVITIES)

# Housing columns that hold a fixed point, by slot.
_HOUSING_POINT_COLUMNS = (
    ('point3d_id', FIXED_HOUSING),
    ('boot_point3d_id', FIXED_BOOT),
    ('cover_point3d_id', FIXED_COVER),
    ('cpa_lock_point3d_id', FIXED_CPA_LOCK),
    ('seal_point3d_id', FIXED_SEAL),
    ('tpa_lock_1_point3d_id', FIXED_TPA_LOCK_1),
    ('tpa_lock_2_point3d_id', FIXED_TPA_LOCK_2))

# Point-id columns that rebind a slot when they change, by table.
_CAVITY_POINT_COLUMNS = (
    ('point3d_id', POINT_CAVITY),
    ('terminal_point3d_id', POINT_TERMINAL),
    ('wire_point3d_id', POINT_CAVITY_WIRE))

_TERMINAL_POINT_COLUMNS = (
    ('point3d_id', POINT_TERMINAL),
    ('wire_point3d_id', POINT_TERMINAL_WIRE),
    ('attach_point3d_id', POINT_TERMINAL_ATTACH),
    ('seal_point3d_id', POINT_TERMINAL_SEAL))

# The point-id column names of each table, for the tables' ``update`` hooks.
HOUSING_POINT_COLUMNS = frozenset(name for name, _ in _HOUSING_POINT_COLUMNS)
CAVITY_POINT_COLUMNS = frozenset(name for name, _ in _CAVITY_POINT_COLUMNS)
TERMINAL_POINT_COLUMNS = frozenset(name for name, _ in _TERMINAL_POINT_COLUMNS)

# Accessory tables whose row owns one fixed angle slot.
_ACCESSORY_SLOTS = {
    'pjt_covers': FIXED_COVER,
    'pjt_boots': FIXED_BOOT,
    'pjt_cpa_locks': FIXED_CPA_LOCK}

# The order the old cascade handled the accessories in (and so the order
# their callbacks fire in).
_ACCESSORY_ORDER = (FIXED_TPA_LOCK_1, FIXED_SEAL, FIXED_TPA_LOCK_2, FIXED_BOOT, FIXED_CPA_LOCK, FIXED_COVER)
_ACCESSORY_POINT_ORDER = (FIXED_COVER, FIXED_SEAL, FIXED_BOOT, FIXED_TPA_LOCK_1, FIXED_TPA_LOCK_2, FIXED_CPA_LOCK)

_MODE_SKIP = 0
_MODE_OBB = 1
_MODE_MATRIX = 2

_ZERO = np.zeros(3)
_IDENTITY_QUAT = np.array([1.0, 0.0, 0.0, 0.0])


@_check_types.do
def _face_corners(local_obb: np.ndarray, face_idx: int) -> np.ndarray:
    """
    The four corner indices of an OBB face, the same ones
    ``pjt_housing._obb_face_direction`` reads (axis ``face_idx // 2``, the low
    or high four corners by ``face_idx % 2``).

    :param local_obb: The box corners, ``(8, 3)``.
    :type local_obb: :class:`numpy.ndarray`
    :param face_idx: Face number 0-5.
    :type face_idx: int
    :returns: Four corner indices.
    :rtype: :class:`numpy.ndarray`
    """

    axis = face_idx // 2
    ordered = np.argsort(local_obb[:, axis])

    if face_idx % 2 == 0:
        return ordered[:4]

    return ordered[4:]


class _Plan:
    """Everything a gesture works out once: part geometry per cavity and accessory, and the clone points."""

    def __init__(self, cavity_count: int):
        self.cavity_local = np.zeros((cavity_count, 8, 3), dtype=np.float64)
        self.cavity_model = np.tile(_IDENTITY_QUAT, (cavity_count, 1))
        self.cavity_fwd = np.zeros((cavity_count, 4), dtype=np.int64)
        self.cavity_up = np.zeros((cavity_count, 4), dtype=np.int64)
        self.cavity_known = np.zeros(cavity_count, dtype=bool)

        self.accessory_mode = [_MODE_SKIP] * len(_ACCESSORY_ORDER)
        self.accessory_local = np.zeros((len(_ACCESSORY_ORDER), 8, 3), dtype=np.float64)
        self.accessory_model = np.tile(_IDENTITY_QUAT, (len(_ACCESSORY_ORDER), 1))
        self.accessory_fwd = np.zeros((len(_ACCESSORY_ORDER), 4), dtype=np.int64)
        self.accessory_up = np.zeros((len(_ACCESSORY_ORDER), 4), dtype=np.int64)

        self.child_ids: list[bytes] = []
        self.children: list[_point.Point] = []


class HousingSlots3D:
    """The slots of one housing: its blocks, which row is bound to which slot, and the vector move / rotate."""

    @_check_types.do
    def __init__(self, housing_id: bytes, pools: "SlotPools3D"):
        """
        Allocate the fixed block, and the cavity block when the housing already
        has cavities, then bind every row that already exists.

        :param housing_id: The housing's row id.
        :type housing_id: bytes
        :param pools: The project's pools.
        :type pools: :class:`SlotPools3D`
        """

        self._id = housing_id
        self._pools = pools
        self._db = pools.db

        self._fixed_points = pools.points.allocate(FIXED_COUNT)
        self._fixed_angles = pools.angles.allocate(FIXED_COUNT)
        self._cavity_points: _slot_pool.SlotBlock | None = None
        self._cavity_angles: _slot_pool.SlotBlock | None = None

        self._cavity_ids: list[bytes] = []
        self._cavity_index: dict[bytes, int] = {}

        # What is bound to each slot, in "global" slot numbers: the fixed
        # block first, then the cavity block.
        self._point_rows: list[bytes | None] = [None] * FIXED_COUNT
        self._angle_owners: list[tuple[str, bytes] | None] = [None] * FIXED_COUNT

        self._plan: _Plan | None = None
        self._plan_serial = 0
        self._released = False

        self._bind_fixed()

        cavity_rows = self._db.pjt_cavities_table.select('id', housing_id=housing_id)
        if cavity_rows:
            self.cavities_created()

    # ------------------------------------------------------------------ blocks

    @_check_types.do
    def cavities_created(self) -> None:
        """
        Allocate the cavity block for the cavities the housing has now, and bind
        their rows. Called when the housing's cavity rows exist: at allocation
        for a loaded housing, and by ``insert`` / ``update_cavities`` for a new one.

        :raises RuntimeError: The cavity block already exists.
        """

        if self._cavity_points is not None:
            raise RuntimeError('this housing already has its cavity slots')

        rows = self._db.pjt_cavities_table.select('id', housing_id=self._id)
        self._cavity_ids = [row[0] for row in rows]
        self._cavity_index = {cavity_id: index for index, cavity_id in enumerate(self._cavity_ids)}

        count = len(self._cavity_ids)
        self._cavity_points = self._pools.points.allocate(POINTS_PER_CAVITY * count)
        self._cavity_angles = self._pools.angles.allocate(ANGLES_PER_CAVITY * count)

        self._point_rows.extend([None] * (POINTS_PER_CAVITY * count))
        self._angle_owners.extend([None] * (ANGLES_PER_CAVITY * count))

        self._bind_cavities()

    @_check_types.do
    def release(self) -> None:
        """Give every block back and forget every row. Called when the housing is deleted."""

        if self._released:
            return

        for row_id in self._point_rows:
            if row_id is not None:
                self._pools.forget_point(row_id)

        self._pools.points.release(self._fixed_points)
        self._pools.angles.release(self._fixed_angles)

        if self._cavity_points is not None:
            self._pools.points.release(self._cavity_points)
            self._pools.angles.release(self._cavity_angles)

        self._released = True

    @_check_types.do
    def _point_location(self, slot: int) -> tuple[_slot_pool.SlotBlock, int]:
        """The block and the offset inside it of a point slot (global numbering)."""

        if slot < FIXED_COUNT:
            return self._fixed_points, slot

        return self._cavity_points, slot - FIXED_COUNT

    @_check_types.do
    def _angle_location(self, slot: int) -> tuple[_slot_pool.SlotBlock, int]:
        """The block and the offset inside it of an angle slot (global numbering)."""

        if slot < FIXED_COUNT:
            return self._fixed_angles, slot

        return self._cavity_angles, slot - FIXED_COUNT

    @_check_types.do
    def cavity_slot(self, cavity_id: bytes, per_cavity: int, role: int) -> int:
        """
        The global slot number of one role of one cavity.

        :param cavity_id: The cavity's row id.
        :type cavity_id: bytes
        :param per_cavity: ``POINTS_PER_CAVITY`` or ``ANGLES_PER_CAVITY``.
        :type per_cavity: int
        :param role: ``POINT_*`` or ``ANGLE_*``.
        :type role: int
        :returns: The slot number.
        :rtype: int
        """

        return FIXED_COUNT + self._cavity_index[cavity_id] * per_cavity + role

    # ----------------------------------------------------------------- binding

    @_check_types.do
    def bind_point(self, slot: int, row_id: bytes | None) -> None:
        """
        Bind a ``pjt_points3d`` row to a point slot (or clear the slot with
        ``None``). The slot is seeded from the row's cached coordinates; the
        object built over the slot's previous row, if any, leaves the pool.

        :param slot: Global point slot number.
        :type slot: int
        :param row_id: The row id, or ``None``.
        :type row_id: bytes | None
        """

        old = self._point_rows[slot]
        if old == row_id:
            return

        block, offset = self._point_location(slot)
        view = self._pools.points.row(block, 'data', offset)

        if old is not None:
            self._pools.forget_point(old)
            self._pools.points.evict(block, offset)

        self._point_rows[slot] = row_id

        if row_id is None:
            view[:] = 0.0
            return

        x, y, z = self._db.pjt_points3d_table.select('x', 'y', 'z', id=row_id)[0]
        view[:] = (x, y, z)
        self._pools.remember_point(row_id, self, slot, block, offset)

        existing = _point.PointMeta._instances.get(row_id + b'3d')  # NOQA
        if existing is not None:
            live = existing()

            if live is not None and live._data is not view:  # NOQA
                raise RuntimeError(
                    'a Point for this row was built before its housing bound the slot, so it '
                    'cannot be given its pool view (its array is aliased elsewhere)')

    @_check_types.do
    def bind_angle(self, slot: int, table_name: str | None, row_id: bytes | None) -> None:
        """
        Bind the row of an object (a cavity, terminal, seal, accessory or the
        housing) to an angle slot, or clear it with ``None``. When the owner
        changed, the slot is seeded from the row and the old angle leaves the pool.

        :param slot: Global angle slot number.
        :type slot: int
        :param table_name: The owner's table name, or ``None``.
        :type table_name: str | None
        :param row_id: The owner's row id, or ``None``.
        :type row_id: bytes | None
        """

        owner = None
        if row_id is not None:
            owner = (table_name, row_id)

        if self._angle_owners[slot] == owner:
            return

        block, offset = self._angle_location(slot)

        if self._angle_owners[slot] is not None:
            self._pools.angles.evict(block, offset)

        self._angle_owners[slot] = owner

        quat = self._pools.angles.row(block, 'quat', offset)
        euler = self._pools.angles.row(block, 'euler', offset)
        matrix = self._pools.angles.row(block, 'matrix', offset)

        if owner is None:
            quat[:] = _IDENTITY_QUAT
            euler[:] = 0.0
            matrix[:] = np.eye(3)
            return

        table = self._pools.table(table_name)
        quat_text, euler_text = table.select('quat3d', 'angle3d', id=row_id)[0]
        quat[:] = ast.literal_eval(quat_text)
        euler[:] = ast.literal_eval(euler_text)
        matrix[:] = _batch.to_matrices(quat.astype(np.float64)[None, :])[0]

    @_check_types.do
    def _bind_fixed(self) -> None:
        """Bind the housing's own rows and its accessories."""

        db = self._db
        columns = [name for name, _ in _HOUSING_POINT_COLUMNS]
        row = db.pjt_housings_table.select(*columns, id=self._id)[0]

        for (_, slot), row_id in zip(_HOUSING_POINT_COLUMNS, row):
            self.bind_point(slot, row_id)

        self.bind_angle(FIXED_HOUSING, 'pjt_housings', self._id)

        for table_name, slot in _ACCESSORY_SLOTS.items():
            table = self._pools.table(table_name)
            rows = table.select('id', housing_id=self._id)
            if rows:
                self.bind_angle(slot, table_name, rows[0][0])

        for row in db.pjt_tpa_locks_table.select('id', 'idx', housing_id=self._id):
            if row[1] == 1:
                self.bind_angle(FIXED_TPA_LOCK_1, 'pjt_tpa_locks', row[0])
            else:
                self.bind_angle(FIXED_TPA_LOCK_2, 'pjt_tpa_locks', row[0])

        rows = db.pjt_seals_table.select('id', housing_id=self._id)
        if rows:
            self.bind_angle(FIXED_SEAL, 'pjt_seals', rows[0][0])

    @_check_types.do
    def _bind_cavities(self) -> None:
        """Bind every cavity row, its terminal and its seal."""

        db = self._db
        rows = db.pjt_cavities_table.select(
            'id', 'point3d_id', 'terminal_point3d_id', 'wire_point3d_id', housing_id=self._id)

        for cavity_id, point_id, terminal_point_id, wire_point_id in rows:
            self.bind_point(self.cavity_slot(cavity_id, POINTS_PER_CAVITY, POINT_CAVITY), point_id)
            self.bind_point(self.cavity_slot(cavity_id, POINTS_PER_CAVITY, POINT_TERMINAL), terminal_point_id)
            self.bind_point(self.cavity_slot(cavity_id, POINTS_PER_CAVITY, POINT_CAVITY_WIRE), wire_point_id)
            self.bind_angle(self.cavity_slot(cavity_id, ANGLES_PER_CAVITY, ANGLE_CAVITY), 'pjt_cavities', cavity_id)

            terminal_rows = db.pjt_terminals_table.select(
                'id', 'point3d_id', 'wire_point3d_id', 'attach_point3d_id', 'seal_point3d_id',
                cavity_id=cavity_id)

            seal_rows = []

            if terminal_rows:
                terminal_id, point_id, wire_id, attach_id, seal_pos_id = terminal_rows[0]

                self.bind_point(self.cavity_slot(cavity_id, POINTS_PER_CAVITY, POINT_TERMINAL), point_id)
                self.bind_point(self.cavity_slot(cavity_id, POINTS_PER_CAVITY, POINT_TERMINAL_WIRE), wire_id)
                self.bind_point(self.cavity_slot(cavity_id, POINTS_PER_CAVITY, POINT_TERMINAL_ATTACH), attach_id)
                self.bind_point(self.cavity_slot(cavity_id, POINTS_PER_CAVITY, POINT_TERMINAL_SEAL), seal_pos_id)
                self.bind_angle(self.cavity_slot(cavity_id, ANGLES_PER_CAVITY, ANGLE_TERMINAL),
                                'pjt_terminals', terminal_id)

                seal_rows = db.pjt_seals_table.select('id', 'point3d_id', terminal_id=terminal_id)

            if not seal_rows:
                seal_rows = db.pjt_seals_table.select('id', 'point3d_id', cavity_id=cavity_id)

            if seal_rows:
                self.bind_point(self.cavity_slot(cavity_id, POINTS_PER_CAVITY, POINT_SEAL), seal_rows[0][1])
                self.bind_angle(self.cavity_slot(cavity_id, ANGLES_PER_CAVITY, ANGLE_SEAL),
                                'pjt_seals', seal_rows[0][0])

    @_check_types.do
    def column_changed(self, table_name: str, row_id: bytes, columns: dict[str, bytes | None]) -> None:
        """
        A point-id column of the housing, a cavity or a terminal was written:
        rebind the slot that column belongs to.

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
                self.bind_point(self.cavity_slot(cavity_id, POINTS_PER_CAVITY, role), columns[name])

    @_check_types.do
    def bind_seal_point(self, cavity_id: bytes, point_id: bytes | None) -> None:
        """
        Bind the point of a cavity's seal (on its terminal, or a plug / dummy
        pin on the cavity). A housing's own seal point is the housing's column
        and is bound with it.

        :param cavity_id: The cavity the seal belongs to.
        :type cavity_id: bytes
        :param point_id: The seal's point row, or ``None``.
        :type point_id: bytes | None
        """

        self.bind_point(self.cavity_slot(cavity_id, POINTS_PER_CAVITY, POINT_SEAL), point_id)

    # ----------------------------------------------------------------- the plan

    @_check_types.do
    def _get_plan(self, housing: "_pjt_housing.PJTHousing") -> _Plan:
        """
        The plan for this gesture: built on the first frame, reused until the
        gesture ends. Outside a gesture a plan is built for the one call.

        :param housing: The housing's row object.
        :type housing: :class:`_pjt_housing.PJTHousing`
        :returns: The plan.
        :rtype: :class:`_Plan`
        """

        serial = self._db.gesture_serial

        if self._db.gesture_depth > 0 and self._plan is not None and self._plan_serial == serial:
            return self._plan

        plan = self._build_plan(housing)

        if self._db.gesture_depth > 0:
            self._plan = plan
            self._plan_serial = serial
        else:
            self._plan = None

        return plan

    @_check_types.do
    def _build_plan(self, housing: "_pjt_housing.PJTHousing") -> _Plan:
        """Walk the structure once: re-check who owns each angle slot and gather the part geometry."""

        count = len(self._cavity_ids)
        plan = _Plan(count)

        for cavity in housing.cavities:
            if cavity is None:
                continue

            index = self._cavity_index[cavity.db_id]
            part = cavity.part

            local_obb = np.asarray(part.obb, dtype=np.float64)
            plan.cavity_local[index] = local_obb
            plan.cavity_model[index] = part.angle3d._q.as_float
            plan.cavity_fwd[index] = _face_corners(local_obb, 4)
            plan.cavity_up[index] = _face_corners(local_obb, 3)
            plan.cavity_known[index] = True

            terminal = cavity.terminal
            seal = cavity.seal

            terminal_id = None
            if terminal is not None:
                terminal_id = terminal.db_id
                seal = terminal.seal

            seal_id = None
            if seal is not None:
                seal_id = seal.db_id

            self.bind_angle(self.cavity_slot(cavity.db_id, ANGLES_PER_CAVITY, ANGLE_TERMINAL),
                            'pjt_terminals', terminal_id)
            self.bind_angle(self.cavity_slot(cavity.db_id, ANGLES_PER_CAVITY, ANGLE_SEAL),
                            'pjt_seals', seal_id)

        accessories = (housing.tpa_lock1, housing.seal, housing.tpa_lock2,
                       housing.boot, housing.cpa_lock, housing.cover)
        tables = ('pjt_tpa_locks', 'pjt_seals', 'pjt_tpa_locks', 'pjt_boots', 'pjt_cpa_locks', 'pjt_covers')

        for position, (accessory, table_name, slot) in enumerate(zip(accessories, tables, _ACCESSORY_ORDER)):
            if accessory is None:
                self.bind_angle(slot, None, None)
                continue

            self.bind_angle(slot, table_name, accessory.db_id)

            part = accessory.part
            plan.accessory_mode[position] = _MODE_MATRIX

            if part is None:
                continue

            model3d = part.model3d
            if model3d is None:
                continue

            forward_face, up_face = model3d.forward_up
            if forward_face == -1 or up_face == -1:
                plan.accessory_mode[position] = _MODE_SKIP
                continue

            local_obb = np.asarray(model3d.obb, dtype=np.float64)
            plan.accessory_mode[position] = _MODE_OBB
            plan.accessory_local[position] = local_obb
            plan.accessory_model[position] = model3d.angle3d._q.as_float
            plan.accessory_fwd[position] = _face_corners(local_obb, forward_face)
            plan.accessory_up[position] = _face_corners(local_obb, up_face)

        wire_roles = (POINT_CAVITY_WIRE, POINT_TERMINAL_WIRE, POINT_TERMINAL_ATTACH, POINT_SEAL)
        parents = []

        for cavity_id in self._cavity_ids:
            for role in wire_roles:
                row_id = self._point_rows[self.cavity_slot(cavity_id, POINTS_PER_CAVITY, role)]
                if row_id is not None:
                    parents.append(row_id)

        plan.child_ids = housing.find_child_point_ids(parents)

        return plan

    @_check_types.do
    def _children(self, plan: _Plan) -> list[_point.Point]:
        """The clone points of this housing's wire-side points (built once per plan)."""

        if len(plan.children) != len(plan.child_ids):
            table = self._db.pjt_points3d_table
            plan.children = [table[child_id].point for child_id in plan.child_ids]

        return plan.children

    # ------------------------------------------------------------ the cascades

    @_check_types.do
    def move(self, housing: "_pjt_housing.PJTHousing", delta: np.ndarray) -> None:
        """
        Move every point of the housing except its own by ``delta``, bring the
        database cache up to date and fire the callbacks.

        :param housing: The housing's row object.
        :type housing: :class:`_pjt_housing.PJTHousing`
        :param delta: The move, ``(3,)``.
        :type delta: :class:`numpy.ndarray`
        """

        plan = self._get_plan(housing)

        fixed = self._pools.points.array(self._fixed_points, 'data')
        fixed[1:] += delta.astype(np.float32)

        if self._cavity_points is not None:
            cavity = self._pools.points.array(self._cavity_points, 'data')
            cavity += delta.astype(np.float32)

        self._write_points()
        self._move_children(plan, delta)
        self._fire_point_callbacks(plan)

    @_check_types.do
    def rotate(self, housing: "_pjt_housing.PJTHousing", delta: np.ndarray, center: np.ndarray) -> None:
        """
        Rotate every point of the housing about ``center`` and every angle by
        ``delta`` (a unit quaternion ``(w, x, y, z)``), bring the database cache
        up to date and fire the point callbacks.

        :param housing: The housing's row object.
        :type housing: :class:`_pjt_housing.PJTHousing`
        :param delta: The rotation, ``(4,)``.
        :type delta: :class:`numpy.ndarray`
        :param center: The housing's position, ``(3,)``.
        :type center: :class:`numpy.ndarray`
        """

        plan = self._get_plan(housing)

        fixed = self._pools.points.array(self._fixed_points, 'data')
        fixed[:] = _batch.rotate_points(fixed, center, delta)

        if self._cavity_points is not None:
            cavity = self._pools.points.array(self._cavity_points, 'data')
            cavity[:] = _batch.rotate_points(cavity, center, delta)

        self._write_points()
        self._rotate_children(plan, delta, center)
        self._rotate_angles(plan, delta)
        self._fire_point_callbacks(plan)

    @_check_types.do
    def _write_points(self) -> None:
        """Write the coordinates of every bound point slot into the database cache."""

        rows = []

        for slot, row_id in enumerate(self._point_rows):
            if row_id is None:
                continue

            block, offset = self._point_location(slot)
            x, y, z = self._pools.points.row(block, 'data', offset).tolist()
            rows.append((x, y, z, row_id))

        self._db.pjt_points3d_table.batch_update(['x', 'y', 'z'], rows)

    @_check_types.do
    def _move_children(self, plan: _Plan, delta: np.ndarray) -> None:
        """Move the clone points (they are ordinary points, not in the pool)."""

        for point in self._children(plan):
            with point:
                moved = np.array(point.as_float) + delta
                point.x = float(moved[0])
                point.y = float(moved[1])
                point.z = float(moved[2])

            point._process_callbacks()  # NOQA

    @_check_types.do
    def _rotate_children(self, plan: _Plan, delta: np.ndarray, center: np.ndarray) -> None:
        """Rotate the clone points about ``center``."""

        children = self._children(plan)
        if not children:
            return

        points = np.array([point.as_float for point in children], dtype=np.float64)
        rotated = _batch.rotate_points(points, center, delta)

        for point, new in zip(children, rotated.tolist()):
            with point:
                point.x = new[0]
                point.y = new[1]
                point.z = new[2]

            point._process_callbacks()  # NOQA

    @_check_types.do
    def _fire_point_callbacks(self, plan: _Plan) -> None:
        """Fire the callbacks of every pooled point that has an object, in the order the old cascade did."""

        fixed_members = self._pools.points.members(self._fixed_points)
        cavity_members = []
        if self._cavity_points is not None:
            cavity_members = self._pools.points.members(self._cavity_points)

        def fire(member: _slot_pool.PoolMember | None) -> None:
            if member is not None:
                member._process_callbacks()  # NOQA

        for role in (POINT_CAVITY,):
            for index in range(len(self._cavity_ids)):
                fire(cavity_members[index * POINTS_PER_CAVITY + role])

        for slot in _ACCESSORY_POINT_ORDER:
            fire(fixed_members[slot])

        for index in range(len(self._cavity_ids)):
            fire(cavity_members[index * POINTS_PER_CAVITY + POINT_TERMINAL])

        for role in (POINT_TERMINAL_WIRE, POINT_TERMINAL_ATTACH, POINT_CAVITY_WIRE, POINT_SEAL, POINT_TERMINAL_SEAL):
            for index in range(len(self._cavity_ids)):
                fire(cavity_members[index * POINTS_PER_CAVITY + role])

    @_check_types.do
    def _rotate_angles(self, plan: _Plan, delta: np.ndarray) -> None:
        """Rotate every angle of the cavities, terminals, seals and accessories and write the cache."""

        rows: dict[str, list[tuple[str, str, bytes]]] = {}

        count = len(self._cavity_ids)
        if count:
            quat = self._pools.angles.array(self._cavity_angles, 'quat').reshape(count, ANGLES_PER_CAVITY, 4)
            euler = self._pools.angles.array(self._cavity_angles, 'euler').reshape(count, ANGLES_PER_CAVITY, 3)
            matrix = self._pools.angles.array(self._cavity_angles, 'matrix').reshape(count, ANGLES_PER_CAVITY, 3, 3)

            q_acc = _batch.compose(quat[:, ANGLE_CAVITY].astype(np.float64), delta)
            modes = np.where(plan.cavity_known, _MODE_OBB, _MODE_SKIP)

            new_euler, keep = self._angles_from_obb(
                q_acc, plan.cavity_model, plan.cavity_local, plan.cavity_fwd, plan.cavity_up,
                euler[:, ANGLE_CAVITY].astype(np.float64), modes)

            q32 = q_acc.astype(np.float32)
            e32 = new_euler.astype(np.float32)
            m32 = _batch.to_matrices(q_acc).astype(np.float32)

            for role in (ANGLE_CAVITY, ANGLE_TERMINAL, ANGLE_SEAL):
                quat[keep, role] = q32[keep]
                euler[keep, role] = e32[keep]
                matrix[keep, role] = m32[keep]

            for index, cavity_id in enumerate(self._cavity_ids):
                if not keep[index]:
                    continue

                for role in (ANGLE_CAVITY, ANGLE_TERMINAL, ANGLE_SEAL):
                    owner = self._angle_owners[FIXED_COUNT + index * ANGLES_PER_CAVITY + role]
                    if owner is not None:
                        rows.setdefault(owner[0], []).append(
                            (str(q32[index].tolist()), str(e32[index].tolist()), owner[1]))

        fixed_quat = self._pools.angles.array(self._fixed_angles, 'quat')
        fixed_euler = self._pools.angles.array(self._fixed_angles, 'euler')
        fixed_matrix = self._pools.angles.array(self._fixed_angles, 'matrix')

        slots = np.array(_ACCESSORY_ORDER)
        modes = np.array(plan.accessory_mode)

        q_acc = _batch.compose(fixed_quat[slots].astype(np.float64), delta)
        new_euler, keep = self._angles_from_obb(
            q_acc, plan.accessory_model, plan.accessory_local, plan.accessory_fwd, plan.accessory_up,
            fixed_euler[slots].astype(np.float64), modes)

        q32 = q_acc.astype(np.float32)
        e32 = new_euler.astype(np.float32)
        m32 = _batch.to_matrices(q_acc).astype(np.float32)

        for position, slot in enumerate(_ACCESSORY_ORDER):
            owner = self._angle_owners[slot]
            if owner is None or not keep[position]:
                continue

            fixed_quat[slot] = q32[position]
            fixed_euler[slot] = e32[position]
            fixed_matrix[slot] = m32[position]
            rows.setdefault(owner[0], []).append(
                (str(q32[position].tolist()), str(e32[position].tolist()), owner[1]))

        for table_name, table_rows in rows.items():
            self._pools.table(table_name).batch_update(['quat3d', 'angle3d'], table_rows)

    @staticmethod
    @_check_types.do
    def _angles_from_obb(q_acc: np.ndarray, model: np.ndarray, local: np.ndarray, forward: np.ndarray,
                         up: np.ndarray, previous: np.ndarray, modes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        The new Euler angles of each row, the way ``PJTHousing._update_angle3d``
        found them: the orientation of a part's OBB faces under the new
        rotation, or the plain matrix when the row has no OBB or the faces are
        degenerate; rows whose faces cannot be read are left alone.

        :param q_acc: The new quaternion of each row, ``(n, 4)``.
        :type q_acc: :class:`numpy.ndarray`
        :param model: The part model's own quaternion, ``(n, 4)``.
        :type model: :class:`numpy.ndarray`
        :param local: The part's OBB corners, ``(n, 8, 3)``.
        :type local: :class:`numpy.ndarray`
        :param forward: Corner indices of the forward face, ``(n, 4)``.
        :type forward: :class:`numpy.ndarray`
        :param up: Corner indices of the up face, ``(n, 4)``.
        :type up: :class:`numpy.ndarray`
        :param previous: The Euler angles before, degrees, ``(n, 3)``.
        :type previous: :class:`numpy.ndarray`
        :param modes: ``_MODE_*`` of each row, ``(n,)``.
        :type modes: :class:`numpy.ndarray`
        :returns: The Euler angles ``(n, 3)`` and which rows were updated ``(n,)``.
        :rtype: tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`]
        """

        count = q_acc.shape[0]
        matrix_q = _batch.to_matrices(q_acc)

        q_obb = _batch.compose(model, q_acc)
        w = q_obb[:, 0]
        vector = q_obb[:, 1:]
        cross = np.cross(vector[:, None, :], local)
        rotated = local + 2.0 * w[:, None, None] * cross + 2.0 * np.cross(vector[:, None, :], cross)

        rows = np.arange(count)[:, None]
        center = rotated.mean(axis=1)
        forward_dir = rotated[rows, forward].mean(axis=1) - center
        up_dir = rotated[rows, up].mean(axis=1) - center

        forward_norm = np.linalg.norm(forward_dir, axis=1)
        up_norm = np.linalg.norm(up_dir, axis=1)
        readable = (forward_norm > 1e-8) & (up_norm > 1e-8)

        forward_dir = forward_dir / np.maximum(forward_norm, 1e-30)[:, None]
        up_dir = up_dir / np.maximum(up_norm, 1e-30)[:, None]
        right = np.cross(up_dir, forward_dir)
        right_norm = np.linalg.norm(right, axis=1)
        right = right / np.maximum(right_norm, 1e-30)[:, None]
        up_dir = np.cross(forward_dir, right)

        use_obb = (modes == _MODE_OBB) & readable & (right_norm > 1e-8)
        matrices = np.where(use_obb[:, None, None], np.stack([right, up_dir, forward_dir], axis=2), matrix_q)

        keep = (modes == _MODE_MATRIX) | ((modes == _MODE_OBB) & readable)

        return _batch.euler_from_matrices(matrices, previous), keep


class SlotPools3D:
    """The 3D point and angle pools of one project, and every housing's slots."""

    @_check_types.do
    def __init__(self, db: "_pjt_bases.PJTTables"):
        """
        :param db: The project's tables.
        :type db: :class:`_pjt_bases.PJTTables`
        """

        self.db = db

        self.points = _slot_pool.SlotPool(
            POINT_CHUNK_SLOTS, (_slot_pool.SlotField('data', (3,), _ZERO),))

        self.angles = _slot_pool.SlotPool(
            ANGLE_CHUNK_SLOTS, (_slot_pool.SlotField('quat', (4,), _IDENTITY_QUAT),
                                _slot_pool.SlotField('euler', (3,), _ZERO),
                                _slot_pool.SlotField('matrix', (3, 3), np.eye(3))))

        self._housings: dict[bytes, HousingSlots3D] = {}

        # point row id -> (the housing's slots, global slot number, block, offset)
        self._point_slots: dict[bytes, tuple[HousingSlots3D, int, _slot_pool.SlotBlock, int]] = {}

    @_check_types.do
    def reset(self) -> None:
        """Forget everything: a different project is being loaded."""

        self.points.reset()
        self.angles.reset()
        self._housings = {}
        self._point_slots = {}

    @_check_types.do
    def allocate_all(self) -> None:
        """Allocate the slots of every housing of the loaded project (rows are read from the cache)."""

        for row in self.db.pjt_housings_table.select('id'):
            self.housing(row[0])

    @_check_types.do
    def housing(self, housing_id: bytes) -> HousingSlots3D:
        """
        The slots of a housing, allocated the first time they are asked for.

        :param housing_id: The housing's row id.
        :type housing_id: bytes
        :returns: The housing's slots.
        :rtype: :class:`HousingSlots3D`
        """

        slots = self._housings.get(housing_id)

        if slots is None:
            slots = HousingSlots3D(housing_id, self)
            self._housings[housing_id] = slots

        return slots

    @_check_types.do
    def release(self, housing_id: bytes) -> None:
        """
        Give a deleted housing's slots back.

        :param housing_id: The housing's row id.
        :type housing_id: bytes
        """

        slots = self._housings.pop(housing_id, None)

        if slots is not None:
            slots.release()

    @_check_types.do
    def table(self, table_name: str) -> "_pjt_bases.PJTTableBase":
        """The project table with this name (the pooled owners' tables)."""

        db = self.db

        tables = {
            'pjt_housings': db.pjt_housings_table,
            'pjt_cavities': db.pjt_cavities_table,
            'pjt_terminals': db.pjt_terminals_table,
            'pjt_seals': db.pjt_seals_table,
            'pjt_covers': db.pjt_covers_table,
            'pjt_boots': db.pjt_boots_table,
            'pjt_cpa_locks': db.pjt_cpa_locks_table,
            'pjt_tpa_locks': db.pjt_tpa_locks_table}

        return tables[table_name]

    @_check_types.do
    def column_changed(self, table_name: str, row_id: bytes, columns: dict[str, bytes | None]) -> None:
        """
        A point-id column of a housing, cavity or terminal row was written:
        find the housing the row belongs to and rebind the slot.

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
            cavity_id = db.pjt_terminals_table.select('cavity_id', id=row_id)[0][0]
            housing_id = db.pjt_cavities_table.select('housing_id', id=cavity_id)[0][0]

        self.housing(housing_id).column_changed(table_name, row_id, columns)

    @_check_types.do
    def seal_changed(self, seal_id: bytes) -> None:
        """
        A seal row was inserted or its point or owner was set. A seal that sits
        on a terminal or plugs a cavity has a point of its own in its cavity's
        slots; a housing's seal uses the housing's own column (already bound).

        :param seal_id: The seal's row id.
        :type seal_id: bytes
        """

        db = self.db

        point_id, housing_id, terminal_id, cavity_id = db.pjt_seals_table.select(
            'point3d_id', 'housing_id', 'terminal_id', 'cavity_id', id=seal_id)[0]

        if housing_id is not None or (terminal_id is None and cavity_id is None):
            return

        if terminal_id is not None:
            cavity_id = db.pjt_terminals_table.select('cavity_id', id=terminal_id)[0][0]

        housing_id = db.pjt_cavities_table.select('housing_id', id=cavity_id)[0][0]
        self.housing(housing_id).bind_seal_point(cavity_id, point_id)

    @_check_types.do
    def point_deleted(self, row_id: bytes) -> None:
        """
        A ``pjt_points3d`` row is being deleted: if it is bound to a slot, clear
        the slot, so nothing writes to the deleted row.

        :param row_id: The ``pjt_points3d`` row id.
        :type row_id: bytes
        """

        entry = self._point_slots.get(row_id)

        if entry is not None:
            entry[0].bind_point(entry[1], None)

    @_check_types.do
    def remember_point(self, row_id: bytes, slots: HousingSlots3D, slot: int,
                       block: _slot_pool.SlotBlock, offset: int) -> None:
        """
        Note which slot a point row is bound to.

        :param row_id: The ``pjt_points3d`` row id.
        :type row_id: bytes
        :param slots: The housing's slots that own the slot.
        :type slots: :class:`HousingSlots3D`
        :param slot: The global slot number inside the housing.
        :type slot: int
        :param block: The block holding the slot.
        :type block: :class:`~harness_designer.geometry.slot_pool.SlotBlock`
        :param offset: Slot number inside the block.
        :type offset: int
        :raises RuntimeError: The row is already bound to a different slot.
        """

        current = self._point_slots.get(row_id)

        if current is not None and (current[2] is not block or current[3] != offset):
            raise RuntimeError('a point row cannot be bound to two slots')

        self._point_slots[row_id] = (slots, slot, block, offset)

    @_check_types.do
    def forget_point(self, row_id: bytes) -> None:
        """
        Forget a point row's slot.

        :param row_id: The ``pjt_points3d`` row id.
        :type row_id: bytes
        """

        self._point_slots.pop(row_id, None)

    @_check_types.do
    def build_point(self, row_id: bytes, db_id: bytes) -> _point.Point | None:
        """
        The ``Point`` of a point row over its slot's view, or ``None`` when the
        row is not in a housing's group.

        :param row_id: The ``pjt_points3d`` row id.
        :type row_id: bytes
        :param db_id: The ``Point``'s ``db_id`` (the row id with its 3D suffix).
        :type db_id: bytes
        :returns: The point, or ``None``.
        :rtype: :class:`~harness_designer.geometry.point.Point` | None
        :raises RuntimeError: A ``Point`` for the row already exists over a private array.
        """

        entry = self._point_slots.get(row_id)

        if entry is None:
            return None

        block, offset = entry[2], entry[3]
        view = self.points.row(block, 'data', offset)
        point = _point.Point(0.0, 0.0, 0.0, db_id=db_id, data=view)

        if point._data is not view:  # NOQA
            raise RuntimeError('a Point for a pooled row was built before its housing allocated the slot')

        self.points.register(block, offset, point)
        return point

    @_check_types.do
    def build_angle(self, table_name: str, row_id: bytes, db_id: bytes) -> _angle.Angle | None:
        """
        The ``Angle`` of a group member (the housing, a cavity, terminal, seal
        or accessory) over its slot's views, or ``None`` when the table is not
        part of a housing's group.

        :param table_name: The owner's table name.
        :type table_name: str
        :param row_id: The owner's row id.
        :type row_id: bytes
        :param db_id: The ``Angle``'s ``db_id``.
        :type db_id: bytes
        :returns: The angle, or ``None``.
        :rtype: :class:`~harness_designer.geometry.angle.angle.Angle` | None
        """

        resolved = self._resolve_angle(table_name, row_id)

        if resolved is None:
            return None

        slots, slot = resolved
        slots.bind_angle(slot, table_name, row_id)

        block, offset = slots._angle_location(slot)  # NOQA
        angle = _angle.Angle.from_views(
            self.angles.row(block, 'quat', offset), self.angles.row(block, 'euler', offset),
            self.angles.row(block, 'matrix', offset), db_id=db_id)

        self.angles.register(block, offset, angle)
        return angle

    @_check_types.do
    def _resolve_angle(self, table_name: str, row_id: bytes) -> tuple[HousingSlots3D, int] | None:
        """Find the housing and the global angle slot an owner row belongs to."""

        db = self.db

        if table_name == 'pjt_housings':
            return self.housing(row_id), FIXED_HOUSING

        if table_name in _ACCESSORY_SLOTS:
            housing_id = self.table(table_name).select('housing_id', id=row_id)[0][0]
            return self.housing(housing_id), _ACCESSORY_SLOTS[table_name]

        if table_name == 'pjt_tpa_locks':
            housing_id, idx = db.pjt_tpa_locks_table.select('housing_id', 'idx', id=row_id)[0]
            slots = self.housing(housing_id)

            if idx == 1:
                return slots, FIXED_TPA_LOCK_1

            return slots, FIXED_TPA_LOCK_2

        if table_name == 'pjt_cavities':
            housing_id = db.pjt_cavities_table.select('housing_id', id=row_id)[0][0]
            slots = self.housing(housing_id)
            return slots, slots.cavity_slot(row_id, ANGLES_PER_CAVITY, ANGLE_CAVITY)

        if table_name == 'pjt_terminals':
            cavity_id = db.pjt_terminals_table.select('cavity_id', id=row_id)[0][0]
            housing_id = db.pjt_cavities_table.select('housing_id', id=cavity_id)[0][0]
            slots = self.housing(housing_id)
            return slots, slots.cavity_slot(cavity_id, ANGLES_PER_CAVITY, ANGLE_TERMINAL)

        if table_name == 'pjt_seals':
            housing_id, terminal_id, cavity_id = db.pjt_seals_table.select(
                'housing_id', 'terminal_id', 'cavity_id', id=row_id)[0]

            if housing_id is not None:
                return self.housing(housing_id), FIXED_SEAL

            if terminal_id is not None:
                cavity_id = db.pjt_terminals_table.select('cavity_id', id=terminal_id)[0][0]

            housing_id = db.pjt_cavities_table.select('housing_id', id=cavity_id)[0][0]
            slots = self.housing(housing_id)
            return slots, slots.cavity_slot(cavity_id, ANGLES_PER_CAVITY, ANGLE_SEAL)

        return None
