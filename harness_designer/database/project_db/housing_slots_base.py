# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
The point plumbing the peg board and the schematic share: one housing's blocks of point slots
(``SlotsBase``) and a project's point pool with the row -> slot registry (``PoolsBase``).

This is the part of ``housing_slots.py`` (3D) that does not depend on which view it is: a housing
gets a FIXED block of point slots and, once it has cavities, a CAVITY block; a point row is bound to
one slot (a row asked for by a second slot is an ALIAS of the first); a ``Point`` is built over its
slot's view; a deleted row unbinds. A view's subclass (``housing_slots_pegboard.py``,
``housing_slots_schematic.py``) adds what is its own: the layout constants (the roles of the fixed
and cavity slots, which columns hold which role), what is bound from the database (``_bind_fixed`` /
``_bind_cavities`` / ``column_changed``), and ``move`` / ``rotate``.

Why a base and not the 3D classes: 3D (``housing_slots.py``) was built and checked first and is left
as it is. The three views differ in layout, in what rotates (the 3D view turns its angles by the
parts' OBB faces; the peg board turns them plainly; the schematic has no angles of its own and a 180
degree correction) and in how seals are linked, so each view has its own subclass.

THE WHOLE DESIGN is in the module docstring of ``database/project_db/pjt_housing.py`` ("POOLED 3D
STORAGE", section 15 for the peg board and the schematic). Change that text in the same edit as any
change here.
"""

from typing import TYPE_CHECKING

import numpy as np

from ...geometry import slot_pool as _slot_pool
from ...geometry import point as _point
from ... import check_types as _check_types
from . import housing_slots as _housing_slots

if TYPE_CHECKING:
    from . import pjt_bases as _pjt_bases
    from . import pjt_housing as _pjt_housing


_ZERO = np.zeros(3)


class SlotsBase:
    """One housing's point slots in one view: its blocks, which row is bound to which slot, and the writes."""

    # Set by the view's subclass.
    FIXED_POINTS: int = 1
    POINTS_PER_CAVITY: int = 1
    POINT_SUFFIX: bytes = b''

    # The terminal's point-id columns and the cavity slot role each one fills: ``((column, role), ...)``.
    TERMINAL_COLUMNS: tuple = ()

    @_check_types.do
    def __init__(self, housing_id: bytes, pools: "PoolsBase"):
        """
        Allocate the fixed block, and the cavity block when the housing already has cavities, then
        bind every row that already exists.

        :param housing_id: The housing's row id.
        :type housing_id: bytes
        :param pools: The project's pools for this view.
        :type pools: :class:`PoolsBase`
        """

        self._id = housing_id
        self._pools = pools
        self._db = pools.db

        self._fixed_points = pools.points.allocate(self.FIXED_POINTS)
        self._cavity_points: _slot_pool.SlotBlock | None = None

        self._cavity_ids: list[bytes] = []
        self._cavity_index: dict[bytes, int] = {}

        # What is bound to each point slot, in "global" slot numbers: the fixed block first, then the
        # cavity block.
        self._point_rows: list[bytes | None] = [None] * self.FIXED_POINTS

        # slot -> the row it was asked to hold but that already lives in ANOTHER slot (a point id that
        # two parts share is allocated once; see ``bind_point``). Such a slot stays empty.
        self._alias_rows: dict[int, bytes] = {}

        self._plan: object | None = None
        self._plan_serial = 0
        self._released = False

        self._allocate_more()
        self._bind_fixed()

        if self._db.pjt_cavities_table.select('id', housing_id=housing_id):
            self.cavities_created()

    # ------------------------------------------------- what a view's subclass fills in

    @_check_types.do
    def _allocate_more(self) -> None:
        """Allocate whatever else the view keeps per housing in its fixed block (the angle block)."""

    @_check_types.do
    def _allocate_cavities_more(self, count: int) -> None:
        """Allocate whatever else the view keeps per cavity (the cavity block of the angles)."""

    @_check_types.do
    def _release_more(self) -> None:
        """Give back whatever ``_allocate_more`` / ``_allocate_cavities_more`` took."""

    @_check_types.do
    def _bind_fixed(self) -> None:
        """Bind the housing's own rows (and its accessories, in a view that has any)."""

        raise NotImplementedError

    @_check_types.do
    def _bind_cavities(self) -> None:
        """Bind every cavity row, its terminal and its seal."""

        raise NotImplementedError

    # ------------------------------------------------------------------ blocks

    @_check_types.do
    def cavities_created(self) -> None:
        """
        Allocate the cavity block for the cavities the housing has now, and bind their rows. Called
        when the housing's cavity rows exist: at allocation for a loaded housing, and by ``insert`` /
        ``update_cavities`` for a new one.

        :raises RuntimeError: The cavity block already exists.
        """

        if self._cavity_points is not None:
            raise RuntimeError('this housing already has its cavity slots')

        rows = self._db.pjt_cavities_table.select('id', housing_id=self._id)
        self._cavity_ids = [row[0] for row in rows]
        self._cavity_index = {cavity_id: index for index, cavity_id in enumerate(self._cavity_ids)}

        count = len(self._cavity_ids)
        self._cavity_points = self._pools.points.allocate(self.POINTS_PER_CAVITY * count)
        self._point_rows.extend([None] * (self.POINTS_PER_CAVITY * count))

        self._allocate_cavities_more(count)
        self._bind_cavities()

    @_check_types.do
    def release(self) -> None:
        """Give every block back and forget every row. Called when the housing is deleted."""

        if self._released:
            return

        for slot, row_id in self._alias_rows.items():
            self._pools.drop_alias(row_id, self, slot)

        self._alias_rows = {}
        owned = [row_id for row_id in self._point_rows if row_id is not None]

        for row_id in owned:
            self._pools.forget_point(row_id)

        self._pools.points.release(self._fixed_points)

        if self._cavity_points is not None:
            self._pools.points.release(self._cavity_points)

        self._release_more()

        self._released = True

        # a slot elsewhere that wanted one of these rows takes it over
        for row_id in owned:
            self._pools.promote_alias(row_id)

    @_check_types.do
    def _point_location(self, slot: int) -> tuple[_slot_pool.SlotBlock, int]:
        """The block and the offset inside it of a point slot (global numbering)."""

        if slot < self.FIXED_POINTS:
            return self._fixed_points, slot

        return self._cavity_points, slot - self.FIXED_POINTS

    @_check_types.do
    def cavity_point_slot(self, cavity_id: bytes, role: int) -> int:
        """
        The global point slot number of one role of one cavity.

        :param cavity_id: The cavity's row id.
        :type cavity_id: bytes
        :param role: The view's ``POINT_*`` role.
        :type role: int
        :returns: The slot number.
        :rtype: int
        """

        return self.FIXED_POINTS + self._cavity_index[cavity_id] * self.POINTS_PER_CAVITY + role

    # ----------------------------------------------------------------- binding

    @_check_types.do
    def bind_point(self, slot: int, row_id: bytes | None) -> None:
        """
        Bind a point row to a point slot (or clear the slot with ``None``). The object built over the
        slot's previous row, if any, leaves the pool.

        A point row is allocated ONCE. Two parts that ask for the same row (the 3D view documents
        which ones, section 4 of the pooled-storage text) ask for the same slot's row; the first to
        ask owns the slot and the others are remembered as aliases and left empty, until the owner
        lets go of the row, when the first alias takes it over.

        A ``Point`` that already exists for the row is NOT rebuilt: its own array is copied into the
        slot and the slot becomes its array (``housing_slots._seat_point``). Only a row with no
        ``Point`` yet is seeded from the cached coordinates.

        :param slot: Global point slot number.
        :type slot: int
        :param row_id: The row id, or ``None``.
        :type row_id: bytes | None
        """

        alias = self._alias_rows.pop(slot, None)
        if alias is not None:
            self._pools.drop_alias(alias, self, slot)

        old = self._point_rows[slot]
        if old == row_id:
            return

        if row_id is not None:
            owner = self._pools.point_slot(row_id)

            if owner is not None and (owner[0] is not self or owner[1] != slot):
                self._pools.add_alias(row_id, self, slot)
                self._alias_rows[slot] = row_id
                row_id = None

                if old is None:
                    return

        block, offset = self._point_location(slot)
        view = self._pools.points.row(block, 'data', offset)

        if old is not None:
            self._pools.forget_point(old)
            self._pools.points.evict(block, offset)

        self._point_rows[slot] = row_id

        if row_id is None:
            view[:] = 0.0
            self._pools.promote_alias(old)
            return

        self._pools.remember_point(row_id, self, slot, block, offset)

        existing = _point.PointMeta._instances.get(row_id + self.POINT_SUFFIX)  # NOQA
        live = None
        if existing is not None:
            live = existing()

        if live is not None and live._root is None:  # NOQA
            _housing_slots._seat_point(live, view, block, offset, self._pools.points)  # NOQA
        else:
            x, y, z = self._pools.points_table().select('x', 'y', 'z', id=row_id)[0]
            view[:] = (x, y, z)

        if old is not None:
            self._pools.promote_alias(old)

    @_check_types.do
    def column_changed(self, table_name: str, row_id: bytes, columns: dict[str, bytes | None]) -> None:
        """
        A point-id column of the housing, a cavity or a terminal was written: rebind the slot that
        column belongs to (the view's subclass says which).
        """

        raise NotImplementedError

    @_check_types.do
    def terminal_left(self, terminal_id: bytes, cavity_id: bytes) -> None:
        """
        A terminal is no longer in this cavity (it was moved to another cavity or taken out of the
        housing): the slots that hold its points let go of them, so a move of this housing no longer
        carries them. A slot that holds something else (another terminal already took the place) is left alone.

        :param terminal_id: The terminal's row id.
        :type terminal_id: bytes
        :param cavity_id: The cavity it left.
        :type cavity_id: bytes
        """

        names = [name for name, _ in self.TERMINAL_COLUMNS]
        row = self._db.pjt_terminals_table.select(*names, id=terminal_id)[0]

        for (name, role), row_id in zip(self.TERMINAL_COLUMNS, row):
            slot = self.cavity_point_slot(cavity_id, role)

            if row_id is not None and self._point_rows[slot] == row_id:
                self.bind_point(slot, None)

    @_check_types.do
    def terminal_arrived(self, terminal_id: bytes, cavity_id: bytes) -> None:
        """
        A terminal is now in this cavity (a free terminal was seated, or it was moved here): its point
        rows are bound to the cavity's slots, so a move of this housing carries them.

        :param terminal_id: The terminal's row id.
        :type terminal_id: bytes
        :param cavity_id: The cavity it is in now.
        :type cavity_id: bytes
        """

        names = [name for name, _ in self.TERMINAL_COLUMNS]
        row = self._db.pjt_terminals_table.select(*names, id=terminal_id)[0]

        self.column_changed('pjt_terminals', terminal_id, dict(zip(names, row)))

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

        self._pools.points_table().batch_update(['x', 'y', 'z'], rows)

    @_check_types.do
    def _members(self) -> tuple[list[_slot_pool.PoolMember | None], list[_slot_pool.PoolMember | None]]:
        """The objects built over the fixed block and over the cavity block (``None`` where a slot has none)."""

        fixed = self._pools.points.members(self._fixed_points)
        cavity = []

        if self._cavity_points is not None:
            cavity = self._pools.points.members(self._cavity_points)

        return fixed, cavity


class PoolsBase:
    """The point pool of one view of one project, every housing's slots, and the row -> slot registry."""

    # Set by the view's subclass.
    POINT_CHUNK_SLOTS: int = 1

    @_check_types.do
    def __init__(self, db: "_pjt_bases.PJTTables"):
        """
        :param db: The project's tables.
        :type db: :class:`_pjt_bases.PJTTables`
        """

        self.db = db

        self.points = _slot_pool.SlotPool(
            self.POINT_CHUNK_SLOTS, (_slot_pool.SlotField('data', (3,), _ZERO),))

        self._housings: dict[bytes, SlotsBase] = {}

        # point row id -> (the housing's slots, global slot number, block, offset)
        self._point_slots: dict[bytes, tuple[SlotsBase, int, _slot_pool.SlotBlock, int]] = {}

        # point row id -> the (housing slots, slot) pairs that asked for a row that lives in another slot
        self._aliases: dict[bytes, list[tuple[SlotsBase, int]]] = {}

    @_check_types.do
    def points_table(self) -> "_pjt_bases.PJTTableBase":
        """The view's points table."""

        raise NotImplementedError

    @_check_types.do
    def new_slots(self, housing_id: bytes) -> SlotsBase:
        """Build the view's slots object for a housing."""

        raise NotImplementedError

    @_check_types.do
    def reset(self) -> None:
        """Forget everything: a different project is being loaded."""

        self.points.reset()
        self._housings = {}
        self._point_slots = {}
        self._aliases = {}

    @_check_types.do
    def allocate_all(self) -> None:
        """Allocate the slots of every housing of the loaded project (rows are read from the cache)."""

        for row in self.db.pjt_housings_table.select('id'):
            self.housing(row[0])

    @_check_types.do
    def housing(self, housing_id: bytes) -> SlotsBase:
        """
        The slots of a housing, allocated the first time they are asked for.

        :param housing_id: The housing's row id.
        :type housing_id: bytes
        :returns: The housing's slots.
        :rtype: :class:`SlotsBase`
        """

        slots = self._housings.get(housing_id)

        if slots is None:
            slots = self.new_slots(housing_id)
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
    def housing_of_terminal(self, terminal_id: bytes) -> bytes | None:
        """
        The housing a terminal sits in, or ``None`` for a terminal that is in no cavity (a free terminal
        has no slots).

        :param terminal_id: The terminal's row id.
        :type terminal_id: bytes
        :returns: The housing's row id, or ``None``.
        :rtype: bytes | None
        """

        db = self.db

        cavity_id = db.pjt_terminals_table.select('cavity_id', id=terminal_id)[0][0]

        if cavity_id is None:
            return None

        return db.pjt_cavities_table.select('housing_id', id=cavity_id)[0][0]

    @_check_types.do
    def terminal_moved(self, terminal_id: bytes, old_cavity_id: bytes | None, new_cavity_id: bytes | None) -> None:
        """
        A terminal's ``cavity_id`` was written (a free terminal was seated, or it moved to another
        cavity, or was taken out): its points leave the old cavity's slots and take the new cavity's.

        :param terminal_id: The terminal's row id.
        :type terminal_id: bytes
        :param old_cavity_id: The cavity it was in, or ``None``.
        :type old_cavity_id: bytes | None
        :param new_cavity_id: The cavity it is in now, or ``None``.
        :type new_cavity_id: bytes | None
        """

        cavities = self.db.pjt_cavities_table

        if old_cavity_id is not None:
            housing_id = cavities.select('housing_id', id=old_cavity_id)[0][0]
            self.housing(housing_id).terminal_left(terminal_id, old_cavity_id)

        if new_cavity_id is not None:
            housing_id = cavities.select('housing_id', id=new_cavity_id)[0][0]
            self.housing(housing_id).terminal_arrived(terminal_id, new_cavity_id)

    @_check_types.do
    def point_deleted(self, row_id: bytes) -> None:
        """
        A point row is being deleted: if it is bound to a slot, clear the slot, so nothing writes to
        the deleted row.

        :param row_id: The point row id.
        :type row_id: bytes
        """

        # slots that only asked for the row stop asking: it is gone, there is nothing to take over
        for slots, slot in self._aliases.pop(row_id, []):
            slots._alias_rows.pop(slot, None)  # NOQA

        entry = self._point_slots.get(row_id)

        if entry is not None:
            entry[0].bind_point(entry[1], None)

    @_check_types.do
    def remember_point(self, row_id: bytes, slots: SlotsBase, slot: int,
                       block: _slot_pool.SlotBlock, offset: int) -> None:
        """
        Note which slot a point row is bound to.

        :param row_id: The point row id.
        :type row_id: bytes
        :param slots: The housing's slots that own the slot.
        :type slots: :class:`SlotsBase`
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
    def point_slot(self, row_id: bytes) -> tuple[SlotsBase, int, _slot_pool.SlotBlock, int] | None:
        """
        The slot a point row lives in, or ``None``.

        :param row_id: The point row id.
        :type row_id: bytes
        :returns: ``(housing slots, slot, block, offset)`` or ``None``.
        :rtype: tuple | None
        """

        return self._point_slots.get(row_id)

    @_check_types.do
    def add_alias(self, row_id: bytes, slots: SlotsBase, slot: int) -> None:
        """
        Note that a slot asked for a row that already lives in another slot.

        :param row_id: The point row id.
        :type row_id: bytes
        :param slots: The housing's slots that own the asking slot.
        :type slots: :class:`SlotsBase`
        :param slot: The asking slot (global number inside the housing).
        :type slot: int
        """

        entries = self._aliases.setdefault(row_id, [])

        if (slots, slot) not in entries:
            entries.append((slots, slot))

    @_check_types.do
    def drop_alias(self, row_id: bytes, slots: SlotsBase, slot: int) -> None:
        """
        Forget that a slot asked for a row (it now asks for something else, or its housing is gone).

        :param row_id: The point row id.
        :type row_id: bytes
        :param slots: The housing's slots that own the slot.
        :type slots: :class:`SlotsBase`
        :param slot: The slot (global number inside the housing).
        :type slot: int
        """

        entries = self._aliases.get(row_id)

        if entries is None:
            return

        if (slots, slot) in entries:
            entries.remove((slots, slot))

        if not entries:
            del self._aliases[row_id]

    @_check_types.do
    def promote_alias(self, row_id: bytes | None) -> None:
        """
        The slot that owned a row let go of it: the first slot that asked for it while it lived
        elsewhere takes it over (its existing ``Point`` joins that slot's row).

        :param row_id: The point row id.
        :type row_id: bytes | None
        """

        if row_id is None or row_id in self._point_slots:
            return

        entries = self._aliases.get(row_id)

        if not entries:
            return

        slots, slot = entries[0]
        slots.bind_point(slot, row_id)

    @_check_types.do
    def forget_point(self, row_id: bytes) -> None:
        """
        Forget a point row's slot.

        :param row_id: The point row id.
        :type row_id: bytes
        """

        self._point_slots.pop(row_id, None)

    @_check_types.do
    def build_point(self, row_id: bytes, db_id: bytes) -> _point.Point | None:
        """
        The ``Point`` of a point row over its slot's view, or ``None`` when the row is not in a
        housing's group.

        :param row_id: The point row id.
        :type row_id: bytes
        :param db_id: The ``Point``'s ``db_id`` (the row id with the view's suffix).
        :type db_id: bytes
        :returns: The point, or ``None``.
        :rtype: :class:`~harness_designer.geometry.point.Point` | None
        """

        entry = self._point_slots.get(row_id)

        if entry is None:
            return None

        block, offset = entry[2], entry[3]
        view = self.points.row(block, 'data', offset)
        point = _point.Point(0.0, 0.0, 0.0, db_id=db_id, data=view)

        # The row's Point may exist already: asked for a second time, or made before the row had its
        # slot. It is moved into the slot, never refused.
        _housing_slots._seat_point(point, view, block, offset, self.points)  # NOQA
        return point
