# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Pooled storage for a housing's PEG BOARD points and angles, and the vector move / rotate.

``SlotPoolsPegboard`` is the project's peg board point pool and angle pool, every housing's slots,
and the registry that says which slot a ``pjt_points_pegboard`` row is bound to (``build_point`` and
``build_angle`` give a ``Point`` or an ``Angle`` its view). ``HousingSlotsPegboard`` is one housing:
its fixed block and cavity block, what is bound to each slot, the plan of a gesture, and ``move`` /
``rotate``. The constants below are the layout (section 15 of the documentation).

What is the same as the 3D view (``housing_slots.py``) is in ``housing_slots_base.py``; what is
different here:

* the layout (no accessories but the housing seal; one more point per cavity);
* the angles turn PLAINLY: a cavity's new quaternion is its old one composed with the housing's
  rotation, its Euler angles come from that matrix, and its terminal and its seal take the cavity's
  values; there is no part geometry (no OBB faces) on the peg board to align against;
* the housing's seal point is TWO rows, the housing's ``seal_point_pegboard_id`` (the root) and the
  seal's own ``point_pegboard_id`` (attached to it by ``Point.attach`` when the seal is placed), both
  of them pooled; a terminal's seal likewise;
* the peg board wires are rebuilt once for the whole move, not once per point (``suspend_updates`` /
  ``resume_updates`` on every chain bound to a moved point, as the old cascade did).

THE WHOLE DESIGN is in the module docstring of ``database/project_db/pjt_housing.py`` ("POOLED 3D
STORAGE", section 15). Change that text in the same edit as any change here.
"""

from typing import TYPE_CHECKING

import ast
import numpy as np

from ...geometry import slot_pool as _slot_pool
from ...geometry import batch as _batch
from ...geometry import point as _point
from ...geometry.angle import angle as _angle
from ... import check_types as _check_types
from . import housing_slots_base as _base

if TYPE_CHECKING:
    from . import pjt_bases as _pjt_bases
    from . import pjt_housing as _pjt_housing


# Fixed block. Points: the housing, the housing's seal (the seal row's own point) and the housing's
# seal position (the housing's own column). Angles: the housing and its seal.
FIXED_HOUSING = 0
FIXED_SEAL = 1
FIXED_SEAL_POSITION = 2
FIXED_POINTS = 3
FIXED_ANGLES = 2

# Points of one cavity.
POINT_CAVITY = 0
POINT_CAVITY_WIRE = 1
POINT_TERMINAL = 2
POINT_TERMINAL_WIRE = 3
POINT_TERMINAL_ATTACH = 4
POINT_SEAL = 5
POINT_TERMINAL_SEAL = 6
POINT_CAVITY_TERMINAL = 7
POINTS_PER_CAVITY = 8

# Angles of one cavity.
ANGLE_CAVITY = 0
ANGLE_TERMINAL = 1
ANGLE_SEAL = 2
ANGLES_PER_CAVITY = 3

# A chunk holds 10 housings of 100 cavities each (a larger housing still fits in one chunk; one larger
# than a whole chunk gets a chunk of its own).
CHUNK_HOUSINGS = 10
CHUNK_CAVITIES = 100
POINT_CHUNK_SLOTS = CHUNK_HOUSINGS * (FIXED_POINTS + POINTS_PER_CAVITY * CHUNK_CAVITIES)
ANGLE_CHUNK_SLOTS = CHUNK_HOUSINGS * (FIXED_ANGLES + ANGLES_PER_CAVITY * CHUNK_CAVITIES)

# How many parent ids one clone query carries (SQLite's older limit is 999 variables).
_QUERY_CHUNK = 400

# Point-id columns that rebind a slot when they change, by table.
_HOUSING_POINT_COLUMNS = (
    ('point_pegboard_id', FIXED_HOUSING),
    ('seal_point_pegboard_id', FIXED_SEAL_POSITION))

_CAVITY_POINT_COLUMNS = (
    ('point_pegboard_id', POINT_CAVITY),
    ('terminal_point_pegboard_id', POINT_CAVITY_TERMINAL),
    ('wire_point_pegboard_id', POINT_CAVITY_WIRE))

_TERMINAL_POINT_COLUMNS = (
    ('point_pegboard_id', POINT_TERMINAL),
    ('wire_point_pegboard_id', POINT_TERMINAL_WIRE),
    ('attach_point_pegboard_id', POINT_TERMINAL_ATTACH),
    ('seal_point_pegboard_id', POINT_TERMINAL_SEAL))

# The point-id column names of each table, for the tables' ``update`` hooks.
HOUSING_POINT_COLUMNS = frozenset(name for name, _ in _HOUSING_POINT_COLUMNS)
CAVITY_POINT_COLUMNS = frozenset(name for name, _ in _CAVITY_POINT_COLUMNS)
TERMINAL_POINT_COLUMNS = frozenset(name for name, _ in _TERMINAL_POINT_COLUMNS)

# The seal columns that bind a seal's point (or say which housing / terminal / cavity it belongs to).
SEAL_COLUMNS = frozenset(('point_pegboard_id', 'terminal_id', 'cavity_id', 'housing_id'))

_ZERO = np.zeros(3)
_IDENTITY_QUAT = np.array([1.0, 0.0, 0.0, 0.0])


class _Plan:
    """Everything a gesture works out once: who owns each angle slot, and the clone points."""

    def __init__(self):
        self.child_ids: list[bytes] = []
        self.children: list[_point.Point] = []


class HousingSlotsPegboard(_base.SlotsBase):
    """The peg board slots of one housing: its blocks, which row is bound to which slot, and the vector move / rotate."""

    FIXED_POINTS = FIXED_POINTS
    POINTS_PER_CAVITY = POINTS_PER_CAVITY
    POINT_SUFFIX = b'pg'
    TERMINAL_COLUMNS = _TERMINAL_POINT_COLUMNS

    # ------------------------------------------------------------------ blocks

    @_check_types.do
    def _allocate_more(self) -> None:
        """Allocate the fixed block of the angles."""

        self._fixed_angles = self._pools.angles.allocate(FIXED_ANGLES)
        self._cavity_angles: _slot_pool.SlotBlock | None = None

        # What is bound to each angle slot: the (table name, row id) of the owner.
        self._angle_owners: list[tuple[str, bytes] | None] = [None] * FIXED_ANGLES

    @_check_types.do
    def _allocate_cavities_more(self, count: int) -> None:
        """Allocate the cavity block of the angles."""

        self._cavity_angles = self._pools.angles.allocate(ANGLES_PER_CAVITY * count)
        self._angle_owners.extend([None] * (ANGLES_PER_CAVITY * count))

    @_check_types.do
    def _release_more(self) -> None:
        """Give the angle blocks back."""

        self._pools.angles.release(self._fixed_angles)

        if self._cavity_angles is not None:
            self._pools.angles.release(self._cavity_angles)

    @_check_types.do
    def _angle_location(self, slot: int) -> tuple[_slot_pool.SlotBlock, int]:
        """The block and the offset inside it of an angle slot (global numbering)."""

        if slot < FIXED_ANGLES:
            return self._fixed_angles, slot

        return self._cavity_angles, slot - FIXED_ANGLES

    @_check_types.do
    def cavity_angle_slot(self, cavity_id: bytes, role: int) -> int:
        """
        The global angle slot number of one role of one cavity.

        :param cavity_id: The cavity's row id.
        :type cavity_id: bytes
        :param role: ``ANGLE_*``.
        :type role: int
        :returns: The slot number.
        :rtype: int
        """

        return FIXED_ANGLES + self._cavity_index[cavity_id] * ANGLES_PER_CAVITY + role

    # ----------------------------------------------------------------- binding

    @_check_types.do
    def bind_angle(self, slot: int, table_name: str | None, row_id: bytes | None) -> None:
        """
        Bind the row of an object (a cavity, terminal, seal or the housing) to an angle slot, or clear
        it with ``None``. When the owner changed, the slot is seeded from the row and the old angle
        leaves the pool.

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
        quat_text, euler_text = table.select('quat_pegboard', 'angle_pegboard', id=row_id)[0]
        quat[:] = ast.literal_eval(quat_text)
        euler[:] = ast.literal_eval(euler_text)
        matrix[:] = _batch.to_matrices(quat.astype(np.float64)[None, :])[0]

    @_check_types.do
    def _bind_fixed(self) -> None:
        """Bind the housing's own rows and its seal."""

        db = self._db
        row = db.pjt_housings_table.select('point_pegboard_id', 'seal_point_pegboard_id', id=self._id)[0]

        self.bind_point(FIXED_HOUSING, row[0])
        self.bind_point(FIXED_SEAL_POSITION, row[1])
        self.bind_angle(FIXED_HOUSING, 'pjt_housings', self._id)

        seal_rows = db.pjt_seals_table.select('id', 'point_pegboard_id', housing_id=self._id)
        if seal_rows:
            self.bind_housing_seal(seal_rows[0][0], seal_rows[0][1])

    @_check_types.do
    def _bind_cavities(self) -> None:
        """Bind every cavity row, its terminal and its seal."""

        db = self._db
        rows = db.pjt_cavities_table.select(
            'id', 'point_pegboard_id', 'terminal_point_pegboard_id', 'wire_point_pegboard_id',
            housing_id=self._id)

        for cavity_id, point_id, terminal_point_id, wire_point_id in rows:
            self.bind_point(self.cavity_point_slot(cavity_id, POINT_CAVITY), point_id)
            self.bind_point(self.cavity_point_slot(cavity_id, POINT_CAVITY_TERMINAL), terminal_point_id)
            self.bind_point(self.cavity_point_slot(cavity_id, POINT_CAVITY_WIRE), wire_point_id)
            self.bind_angle(self.cavity_angle_slot(cavity_id, ANGLE_CAVITY), 'pjt_cavities', cavity_id)

            terminal_rows = db.pjt_terminals_table.select(
                'id', 'point_pegboard_id', 'wire_point_pegboard_id', 'attach_point_pegboard_id',
                'seal_point_pegboard_id', cavity_id=cavity_id)

            seal_rows = []

            if terminal_rows:
                terminal_id, point_id, wire_id, attach_id, seal_position_id = terminal_rows[0]

                self.bind_point(self.cavity_point_slot(cavity_id, POINT_TERMINAL), point_id)
                self.bind_point(self.cavity_point_slot(cavity_id, POINT_TERMINAL_WIRE), wire_id)
                self.bind_point(self.cavity_point_slot(cavity_id, POINT_TERMINAL_ATTACH), attach_id)
                self.bind_point(self.cavity_point_slot(cavity_id, POINT_TERMINAL_SEAL), seal_position_id)
                self.bind_angle(self.cavity_angle_slot(cavity_id, ANGLE_TERMINAL), 'pjt_terminals', terminal_id)

                seal_rows = db.pjt_seals_table.select('id', 'point_pegboard_id', terminal_id=terminal_id)

            if not seal_rows:
                seal_rows = db.pjt_seals_table.select('id', 'point_pegboard_id', cavity_id=cavity_id)

            if seal_rows:
                self.bind_point(self.cavity_point_slot(cavity_id, POINT_SEAL), seal_rows[0][1])
                self.bind_angle(self.cavity_angle_slot(cavity_id, ANGLE_SEAL), 'pjt_seals', seal_rows[0][0])

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

    @_check_types.do
    def bind_seal_point(self, cavity_id: bytes, point_id: bytes | None) -> None:
        """
        Bind the point of a cavity's seal (on its terminal, or a plug / dummy pin on the cavity).

        :param cavity_id: The cavity the seal belongs to.
        :type cavity_id: bytes
        :param point_id: The seal's point row, or ``None``.
        :type point_id: bytes | None
        """

        self.bind_point(self.cavity_point_slot(cavity_id, POINT_SEAL), point_id)

    @_check_types.do
    def bind_housing_seal(self, seal_id: bytes, point_id: bytes | None) -> None:
        """
        Bind the housing's own seal: its point and its angle.

        :param seal_id: The seal's row id.
        :type seal_id: bytes
        :param point_id: The seal's point row, or ``None``.
        :type point_id: bytes | None
        """

        self.bind_point(FIXED_SEAL, point_id)
        self.bind_angle(FIXED_SEAL, 'pjt_seals', seal_id)

    # ----------------------------------------------------------------- the plan

    @_check_types.do
    def _get_plan(self, housing: "_pjt_housing.PJTHousing") -> _Plan:
        """
        The plan for this gesture: built on the first frame, reused until the gesture ends. Outside a
        gesture a plan is built for the one call.

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
        """Walk the structure once: re-check who owns each angle slot and find the clone points."""

        plan = _Plan()

        for cavity in housing.cavities:
            if cavity is None:
                continue

            terminal = cavity.terminal
            seal = cavity.seal

            terminal_id = None
            if terminal is not None:
                terminal_id = terminal.db_id
                seal = terminal.seal

            seal_id = None
            if seal is not None:
                seal_id = seal.db_id

            self.bind_angle(self.cavity_angle_slot(cavity.db_id, ANGLE_TERMINAL), 'pjt_terminals', terminal_id)
            self.bind_angle(self.cavity_angle_slot(cavity.db_id, ANGLE_SEAL), 'pjt_seals', seal_id)

        housing_seal = housing.seal

        if housing_seal is None:
            self.bind_angle(FIXED_SEAL, None, None)
        else:
            self.bind_angle(FIXED_SEAL, 'pjt_seals', housing_seal.db_id)

        parents = [row_id for slot, row_id in enumerate(self._point_rows)
                   if row_id is not None and slot != FIXED_HOUSING]

        plan.child_ids = self._find_child_ids(parents)

        return plan

    @_check_types.do
    def _find_child_ids(self, parent_ids: list[bytes]) -> list[bytes]:
        """
        The row id of every clone of any point in *parent_ids* (a second-or-later wire attached to the
        same terminal or cavity gets its own clone, ``parent_point_id``) that is not itself pooled.

        :param parent_ids: The housing's bound point rows.
        :type parent_ids: list[bytes]
        :returns: The clone rows.
        :rtype: list[bytes]
        """

        table = self._pools.points_table()
        found: list[bytes] = []

        for start in range(0, len(parent_ids), _QUERY_CHUNK):
            chunk = parent_ids[start:start + _QUERY_CHUNK]
            placeholders = ','.join('?' * len(chunk))

            table.execute(
                f'SELECT id FROM pjt_points_pegboard WHERE parent_point_id IN ({placeholders});', chunk)

            found.extend(row[0] for row in table.fetchall())

        # a clone that is itself in a slot moves with its slot
        return [row_id for row_id in found if self._pools.point_slot(row_id) is None]

    @_check_types.do
    def _children(self, plan: _Plan) -> list[_point.Point]:
        """The clone points of this housing's points (built once per plan)."""

        if len(plan.children) != len(plan.child_ids):
            table = self._pools.points_table()
            plan.children = [table[child_id].point for child_id in plan.child_ids]

        return plan.children

    # ------------------------------------------------------------ the cascades

    @_check_types.do
    def move(self, housing: "_pjt_housing.PJTHousing", delta: np.ndarray) -> None:
        """
        Move every point of the housing except its own by ``delta``, bring the database cache up to
        date and fire the callbacks.

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

        chains = self._suspend_chains(plan)

        try:
            self._move_children(plan, delta)
            self._fire_point_callbacks()
        finally:
            for chain in chains:
                chain.resume_updates()

    @_check_types.do
    def rotate(self, housing: "_pjt_housing.PJTHousing", delta: np.ndarray, center: np.ndarray) -> None:
        """
        Rotate every point of the housing about ``center`` and every angle by ``delta`` (a unit
        quaternion ``(w, x, y, z)``), bring the database cache up to date and fire the point callbacks.

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

        chains = self._suspend_chains(plan)

        try:
            self._rotate_children(plan, delta, center)
            self._rotate_angles(delta)
            self._fire_point_callbacks()
        finally:
            for chain in chains:
                chain.resume_updates()

    @_check_types.do
    def _suspend_chains(self, plan: _Plan) -> list:
        """
        Every wire / bundle chain bound to a point that is about to move gets its own geometry rebuild
        suspended until the whole move is done, instead of once per point (a seated terminal's attach
        point, its stub and its cavity's stub are the SAME wire's three points). Found through each
        point's own already-bound callbacks (``rope_pull_handler.chains_bound_to_point``), including
        the points that follow a pooled root by ``Point.attach``. Returns the chains, for
        ``resume_updates``.
        """

        # Lazy import: rope_pull_handler transitively imports this whole package.
        from ...handlers import rope_pull_handler as _rope_pull_handler  # NOQA

        fixed, cavity = self._members()

        points = [member for member in fixed[1:] if member is not None]
        points.extend(member for member in cavity if member is not None)
        points.extend(self._children(plan))

        followers = []
        for point in points:
            for ref in point._delegators:  # NOQA
                follower = ref()
                if follower is not None:
                    followers.append(follower)

        points.extend(followers)

        suspended: dict[int, object] = {}
        for point in points:
            for chain in _rope_pull_handler.chains_bound_to_point(point):
                suspended[id(chain)] = chain

        chains = list(suspended.values())
        for chain in chains:
            chain.suspend_updates()

        return chains

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
    def _fire_point_callbacks(self) -> None:
        """
        Fire the callbacks of every pooled point that has an object, in the order the old cascade did:
        the cavity points, the terminal points, the seals (the housing's, then each cavity's), then the
        wire-side points. The housing's own point is the one that moved, its callbacks are already
        running.
        """

        fixed, cavity = self._members()

        def fire(member: _slot_pool.PoolMember | None) -> None:
            if member is not None:
                member._process_callbacks()  # NOQA

        count = len(self._cavity_ids)

        for index in range(count):
            fire(cavity[index * POINTS_PER_CAVITY + POINT_CAVITY])

        for role in (POINT_TERMINAL, POINT_CAVITY_TERMINAL):
            for index in range(count):
                fire(cavity[index * POINTS_PER_CAVITY + role])

        fire(fixed[FIXED_SEAL])
        fire(fixed[FIXED_SEAL_POSITION])

        for role in (POINT_SEAL, POINT_TERMINAL_SEAL):
            for index in range(count):
                fire(cavity[index * POINTS_PER_CAVITY + role])

        for role in (POINT_TERMINAL_WIRE, POINT_TERMINAL_ATTACH, POINT_CAVITY_WIRE):
            for index in range(count):
                fire(cavity[index * POINTS_PER_CAVITY + role])

    @_check_types.do
    def _rotate_angles(self, delta: np.ndarray) -> None:
        """Turn every angle of the cavities, terminals and seals by ``delta`` and write the cache."""

        rows: dict[str, list[tuple[str, str, bytes]]] = {}

        count = len(self._cavity_ids)
        if count:
            quat = self._pools.angles.array(self._cavity_angles, 'quat').reshape(count, ANGLES_PER_CAVITY, 4)
            euler = self._pools.angles.array(self._cavity_angles, 'euler').reshape(count, ANGLES_PER_CAVITY, 3)
            matrix = self._pools.angles.array(self._cavity_angles, 'matrix').reshape(count, ANGLES_PER_CAVITY, 3, 3)

            q_acc = _batch.compose(quat[:, ANGLE_CAVITY].astype(np.float64), delta)
            m_acc = _batch.to_matrices(q_acc)
            new_euler = _batch.euler_from_matrices(m_acc, euler[:, ANGLE_CAVITY].astype(np.float64))

            q32 = q_acc.astype(np.float32)
            e32 = new_euler.astype(np.float32)
            m32 = m_acc.astype(np.float32)

            # a terminal and a seal take their cavity's orientation
            for role in (ANGLE_CAVITY, ANGLE_TERMINAL, ANGLE_SEAL):
                quat[:, role] = q32
                euler[:, role] = e32
                matrix[:, role] = m32

            for index in range(count):
                for role in (ANGLE_CAVITY, ANGLE_TERMINAL, ANGLE_SEAL):
                    owner = self._angle_owners[FIXED_ANGLES + index * ANGLES_PER_CAVITY + role]
                    if owner is not None:
                        rows.setdefault(owner[0], []).append(
                            (str(q32[index].tolist()), str(e32[index].tolist()), owner[1]))

        owner = self._angle_owners[FIXED_SEAL]

        if owner is not None:
            fixed_quat = self._pools.angles.array(self._fixed_angles, 'quat')
            fixed_euler = self._pools.angles.array(self._fixed_angles, 'euler')
            fixed_matrix = self._pools.angles.array(self._fixed_angles, 'matrix')

            q_acc = _batch.compose(fixed_quat[FIXED_SEAL:FIXED_SEAL + 1].astype(np.float64), delta)
            m_acc = _batch.to_matrices(q_acc)
            new_euler = _batch.euler_from_matrices(
                m_acc, fixed_euler[FIXED_SEAL:FIXED_SEAL + 1].astype(np.float64))

            q32 = q_acc.astype(np.float32)
            e32 = new_euler.astype(np.float32)

            fixed_quat[FIXED_SEAL] = q32[0]
            fixed_euler[FIXED_SEAL] = e32[0]
            fixed_matrix[FIXED_SEAL] = m_acc[0].astype(np.float32)

            rows.setdefault(owner[0], []).append((str(q32[0].tolist()), str(e32[0].tolist()), owner[1]))

        for table_name, table_rows in rows.items():
            self._pools.table(table_name).batch_update(['quat_pegboard', 'angle_pegboard'], table_rows)


class SlotPoolsPegboard(_base.PoolsBase):
    """The peg board point and angle pools of one project, and every housing's slots."""

    POINT_CHUNK_SLOTS = POINT_CHUNK_SLOTS

    @_check_types.do
    def __init__(self, db: "_pjt_bases.PJTTables"):
        """
        :param db: The project's tables.
        :type db: :class:`_pjt_bases.PJTTables`
        """

        super().__init__(db)

        self.angles = _slot_pool.SlotPool(
            ANGLE_CHUNK_SLOTS, (_slot_pool.SlotField('quat', (4,), _IDENTITY_QUAT),
                                _slot_pool.SlotField('euler', (3,), _ZERO),
                                _slot_pool.SlotField('matrix', (3, 3), np.eye(3))))

    @_check_types.do
    def points_table(self) -> "_pjt_bases.PJTTableBase":
        """The ``pjt_points_pegboard`` table."""

        return self.db.pjt_points_pegboard_table

    @_check_types.do
    def new_slots(self, housing_id: bytes) -> HousingSlotsPegboard:
        """Build the slots of a housing."""

        return HousingSlotsPegboard(housing_id, self)

    @_check_types.do
    def reset(self) -> None:
        """Forget everything: a different project is being loaded."""

        super().reset()
        self.angles.reset()

    @_check_types.do
    def table(self, table_name: str) -> "_pjt_bases.PJTTableBase":
        """The project table with this name (the pooled owners' tables)."""

        db = self.db

        tables = {
            'pjt_housings': db.pjt_housings_table,
            'pjt_cavities': db.pjt_cavities_table,
            'pjt_terminals': db.pjt_terminals_table,
            'pjt_seals': db.pjt_seals_table}

        return tables[table_name]

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

    @_check_types.do
    def seal_changed(self, seal_id: bytes) -> None:
        """
        A seal row was inserted, or its point or its owner was set. The housing's seal and a seal on a
        terminal or plugging a cavity each have a point of their own in the housing's slots.

        :param seal_id: The seal's row id.
        :type seal_id: bytes
        """

        db = self.db

        point_id, housing_id, terminal_id, cavity_id = db.pjt_seals_table.select(
            'point_pegboard_id', 'housing_id', 'terminal_id', 'cavity_id', id=seal_id)[0]

        if housing_id is not None:
            self.housing(housing_id).bind_housing_seal(seal_id, point_id)
            return

        if terminal_id is not None:
            cavity_id = db.pjt_terminals_table.select('cavity_id', id=terminal_id)[0][0]

        if cavity_id is None:
            return

        housing_id = db.pjt_cavities_table.select('housing_id', id=cavity_id)[0][0]
        self.housing(housing_id).bind_seal_point(cavity_id, point_id)

    @_check_types.do
    def build_angle(self, table_name: str, row_id: bytes, db_id: bytes) -> _angle.Angle | None:
        """
        The ``Angle`` of a group member (the housing, a cavity, terminal or seal) over its slot's
        views, or ``None`` when the table is not part of a housing's group (or the row belongs to no
        housing yet).

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
    def _resolve_angle(self, table_name: str, row_id: bytes) -> tuple[HousingSlotsPegboard, int] | None:
        """Find the housing and the global angle slot an owner row belongs to."""

        db = self.db

        if table_name == 'pjt_housings':
            return self.housing(row_id), FIXED_HOUSING

        if table_name == 'pjt_cavities':
            housing_id = db.pjt_cavities_table.select('housing_id', id=row_id)[0][0]
            slots = self.housing(housing_id)
            return slots, slots.cavity_angle_slot(row_id, ANGLE_CAVITY)

        if table_name == 'pjt_terminals':
            cavity_id = db.pjt_terminals_table.select('cavity_id', id=row_id)[0][0]

            if cavity_id is None:
                return None

            housing_id = db.pjt_cavities_table.select('housing_id', id=cavity_id)[0][0]
            slots = self.housing(housing_id)
            return slots, slots.cavity_angle_slot(cavity_id, ANGLE_TERMINAL)

        if table_name == 'pjt_seals':
            housing_id, terminal_id, cavity_id = db.pjt_seals_table.select(
                'housing_id', 'terminal_id', 'cavity_id', id=row_id)[0]

            if housing_id is not None:
                return self.housing(housing_id), FIXED_SEAL

            if terminal_id is not None:
                cavity_id = db.pjt_terminals_table.select('cavity_id', id=terminal_id)[0][0]

            if cavity_id is None:
                return None

            housing_id = db.pjt_cavities_table.select('housing_id', id=cavity_id)[0][0]
            slots = self.housing(housing_id)
            return slots, slots.cavity_angle_slot(cavity_id, ANGLE_SEAL)

        return None
