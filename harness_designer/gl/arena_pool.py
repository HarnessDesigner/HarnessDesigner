# (c) 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""GL-free bookkeeping and planning for the pooled model arenas of ``gl/vbo.py``.

An arena is one big GPU buffer that models are sub-allocated from. This module knows nothing about OpenGL: :class:`ArenaMap`
is the free list of one arena, and :func:`plan` works out, from a snapshot of every arena, the list of steps (:class:`ArenaOp`)
that repacks the models into the fewest arenas. ``vbo.py`` replays those steps with real buffers.

Two tiers of arena (user design, 2026-11-08):

* ``TIER_SHORT``: holds models with fewer than two users. Compacts, is never trimmed, and is half the size of a long arena.
* ``TIER_LONG``: holds models with two or more users. There is one open (unlocked) long arena at a time. When a model that
  is moving to the long tier does not fit in it, the arena is locked: it accepts no new models from then on, only gives them
  up, and it is trimmed to the space actually used.

Draining: an arena whose models all fit in the free space of the other arenas of its tier is emptied into them and deleted,
which is the whole point (each arena is a large block of VRAM). Models are placed best-fit, into the arena that is left with the
least free space.
"""

from dataclasses import dataclass

import itertools

from .. import check_types as _check_types


TIER_SHORT = 0
TIER_LONG = 1

# every arena gets one; a planned (not yet built) arena gets one too, so the step that creates it and the steps that use it
# name the same arena
_UIDS = itertools.count(1)


@dataclass
class ArenaAllocation:
    start: int
    count: int


@dataclass
class ArenaOp:
    """One step of a plan.

    ``kind`` is one of:

    * ``'create'``: build an arena (``uid``, ``tier``, ``capacity``).
    * ``'slide'``: compact the arena ``uid`` in place (its models move down so the free space is one block).
    * ``'move'``: move model ``key`` from the arena ``src`` into the arena ``uid``.
    * ``'lock'``: lock the arena ``uid`` (it takes no more models).
    * ``'trim'``: compact the arena ``uid`` and cut its capacity down to what is used.
    * ``'delete'``: destroy the (empty) arena ``uid``.
    """

    kind: str
    uid: int
    key: str = ''
    src: int = 0
    tier: int = TIER_SHORT
    capacity: int = 0


class ArenaMap:
    """The free list of one arena: where each model sits and which ranges are free. No GL."""

    @_check_types.do
    def __init__(self, capacity_vertices: int, tier: int = TIER_SHORT, uid: int = 0):
        self.capacity_vertices = int(capacity_vertices)
        self.tier = tier

        if uid == 0:
            uid = next(_UIDS)

        self.uid = uid

        # a locked arena accepts no new models (see the module docstring)
        self.locked = False

        self.allocations: dict[str, ArenaAllocation] = {}
        self.free_ranges: list[tuple[int, int]] = [(0, self.capacity_vertices)]

    @_check_types.do
    def get_allocation(self, key: str) -> ArenaAllocation | None:
        return self.allocations.get(key)

    @_check_types.do
    def can_fit(self, vertex_count: int) -> bool:
        needed = int(vertex_count)
        if needed <= 0:
            return False

        return any(count >= needed for _, count in self.free_ranges)

    @_check_types.do
    def allocate(self, key: str, vertex_count: int) -> ArenaAllocation:
        if key in self.allocations:
            return self.allocations[key]

        needed = int(vertex_count)
        if needed <= 0:
            raise ValueError('vertex_count must be > 0')

        for index, (start, count) in enumerate(self.free_ranges):
            if count < needed:
                continue

            alloc = ArenaAllocation(start=start, count=needed)
            self.allocations[key] = alloc

            if count == needed:
                del self.free_ranges[index]
            else:
                self.free_ranges[index] = (start + needed, count - needed)

            return alloc

        raise RuntimeError('model mesh arena has no contiguous free range large enough: '
                           f'requested {needed} vertices, '
                           f'largest hole {self.largest_free_range}, '
                           f'total free {self.free_vertices}, '
                           f'capacity {self.capacity_vertices}')

    @_check_types.do
    def free(self, key: str) -> None:
        alloc = self.allocations.pop(key, None)
        if alloc is None:
            return

        self.free_ranges.append((alloc.start, alloc.count))
        self.free_ranges.sort(key=lambda item: item[0])

        merged: list[tuple[int, int]] = []
        for start, count in self.free_ranges:
            if not merged:
                merged.append((start, count))
                continue

            prev_start, prev_count = merged[-1]
            if prev_start + prev_count == start:
                merged[-1] = (prev_start, prev_count + count)
            else:
                merged.append((start, count))

        self.free_ranges = merged

    @property
    @_check_types.do
    def fragmentation(self) -> float:
        free_total = self.free_vertices
        if free_total <= 0:
            return 0.0

        return 1.0 - (self.largest_free_range / float(free_total))

    @property
    @_check_types.do
    def free_vertices(self) -> int:
        return sum(count for _, count in self.free_ranges)

    @property
    @_check_types.do
    def used_vertices(self) -> int:
        return sum(alloc.count for alloc in self.allocations.values())

    @property
    @_check_types.do
    def largest_free_range(self) -> int:
        if not self.free_ranges:
            return 0

        return max(count for _, count in self.free_ranges)

    @_check_types.do
    def should_compact(self, threshold: float, min_free_vertices: int, needed_vertices: int = 0) -> bool:
        needed = int(needed_vertices)

        if 0 < needed <= self.largest_free_range:
            return False

        return (self.free_vertices >= int(min_free_vertices) and
                self.fragmentation >= float(threshold))

    @_check_types.do
    def slide(self) -> list[tuple[str, int, int, int]]:
        """Pack every model down to the start of the arena, in the order they sit now.

        :returns: ``(key, old start, new start, count)`` for every model, in old-start order. The free space becomes one
            block at the end.
        """
        moves: list[tuple[str, int, int, int]] = []
        cursor = 0

        for key, alloc in sorted(self.allocations.items(), key=lambda item: item[1].start):
            moves.append((key, alloc.start, cursor, alloc.count))
            alloc.start = cursor
            cursor += alloc.count

        if cursor < self.capacity_vertices:
            self.free_ranges = [(cursor, self.capacity_vertices - cursor)]
        else:
            self.free_ranges = []

        return moves

    @_check_types.do
    def clone(self) -> "ArenaMap":
        """A copy of the bookkeeping (same ``uid``) for the planner to try things on."""
        copy = ArenaMap(self.capacity_vertices, self.tier, self.uid)
        copy.locked = self.locked
        copy.allocations = {key: ArenaAllocation(alloc.start, alloc.count) for key, alloc in self.allocations.items()}
        copy.free_ranges = list(self.free_ranges)
        return copy


class _Planner:
    """Works on copies of the arenas and writes down every step it takes."""

    @_check_types.do
    def __init__(self, arenas: list[ArenaMap], desired: dict[str, int], long_capacity: int, short_capacity: int,
                 threshold: float, min_free_vertices: int):
        self.sim: list[ArenaMap] = [arena.clone() for arena in arenas]
        self.ops: list[ArenaOp] = []
        self.desired = desired
        self.long_capacity = long_capacity
        self.short_capacity = short_capacity
        self.threshold = threshold
        self.min_free_vertices = min_free_vertices

    @_check_types.do
    def _open_long(self) -> ArenaMap | None:
        found = None

        for arena in self.sim:
            if arena.tier != TIER_LONG or arena.locked:
                continue

            if found is None or arena.uid > found.uid:
                found = arena

        return found

    @_check_types.do
    def _create(self, tier: int, capacity: int) -> ArenaMap:
        arena = ArenaMap(capacity, tier)
        self.sim.append(arena)
        self.ops.append(ArenaOp('create', arena.uid, tier=tier, capacity=capacity))
        return arena

    @_check_types.do
    def _delete(self, arena: ArenaMap) -> None:
        self.ops.append(ArenaOp('delete', arena.uid))
        self.sim.remove(arena)

    @_check_types.do
    def _make_room(self, arena: ArenaMap, count: int) -> None:
        # there is enough free space in total, but not in one block: slide the arena down so there is
        if arena.largest_free_range < count:
            self.ops.append(ArenaOp('slide', arena.uid))
            arena.slide()

    @_check_types.do
    def _move(self, key: str, source: ArenaMap, target: ArenaMap) -> None:
        count = source.allocations[key].count

        self._make_room(target, count)
        target.allocate(key, count)
        source.free(key)

        self.ops.append(ArenaOp('move', target.uid, key=key, src=source.uid))

    @_check_types.do
    def _pick(self, tier: int, count: int, exclude_uid: int) -> ArenaMap | None:
        """The arena of ``tier`` that takes ``count`` vertices and is left with the least free space."""
        best = None
        best_left = 0

        for arena in self.sim:
            if arena.tier != tier or arena.locked or arena.uid == exclude_uid:
                continue

            left = arena.free_vertices - count
            if left < 0:
                continue

            if best is None or left < best_left or (left == best_left and arena.uid < best.uid):
                best = arena
                best_left = left

        return best

    @_check_types.do
    def _place(self, key: str, source: ArenaMap, tier: int) -> None:
        count = source.allocations[key].count
        target = self._pick(tier, count, source.uid)

        if target is None:
            if tier == TIER_LONG:
                # The open long arena is full to the point that this model does not fit: it is locked, and trimmed once
                # the plan is done. The model starts a new open arena.
                full = self._open_long()
                if full is not None:
                    full.locked = True
                    self.ops.append(ArenaOp('lock', full.uid))

                capacity = max(self.long_capacity, count)
            else:
                capacity = max(self.short_capacity, count)

            target = self._create(tier, capacity)

        self._move(key, source, target)

    @_check_types.do
    def _drain_one(self, source: ArenaMap, arenas: list[ArenaMap]) -> bool:
        if not source.allocations:
            self._delete(source)
            return True

        targets = [arena for arena in arenas if arena is not source and not arena.locked]
        free = {arena.uid: arena.free_vertices for arena in targets}

        if sum(free.values()) < source.used_vertices:
            return False

        placed: list[tuple[str, ArenaMap]] = []

        for key, alloc in sorted(source.allocations.items(), key=lambda item: (-item[1].count, item[0])):
            best = None
            best_left = 0

            for target in targets:
                left = free[target.uid] - alloc.count
                if left < 0:
                    continue

                if best is None or left < best_left or (left == best_left and target.uid < best.uid):
                    best = target
                    best_left = left

            if best is None:
                return False

            free[best.uid] = best_left
            placed.append((key, best))

        for key, target in placed:
            self._move(key, source, target)

        self._delete(source)
        return True

    @_check_types.do
    def _drain(self, tier: int) -> None:
        while True:
            arenas = [arena for arena in self.sim if arena.tier == tier]
            arenas.sort(key=lambda arena: (arena.used_vertices, arena.uid))

            drained = False
            for source in arenas:
                if self._drain_one(source, arenas):
                    drained = True
                    break

            if not drained:
                return

    @_check_types.do
    def _finish(self) -> None:
        for arena in list(self.sim):
            if arena.tier == TIER_LONG and arena.locked:
                used = arena.used_vertices

                if arena.capacity_vertices > used:
                    self.ops.append(ArenaOp('trim', arena.uid))
                    arena.slide()
                    arena.capacity_vertices = used
                    arena.free_ranges = []

            elif arena.should_compact(self.threshold, self.min_free_vertices):
                self.ops.append(ArenaOp('slide', arena.uid))
                arena.slide()

    @_check_types.do
    def run(self) -> list[ArenaOp]:
        moves: list[tuple[int, str, int, int]] = []

        for arena in self.sim:
            for key, alloc in arena.allocations.items():
                wanted = self.desired.get(key, arena.tier)
                if wanted != arena.tier:
                    moves.append((alloc.count, key, arena.uid, wanted))

        moves.sort(key=lambda move: (-move[0], move[1]))
        by_uid = {arena.uid: arena for arena in self.sim}

        for _count, key, uid, wanted in moves:
            self._place(key, by_uid[uid], wanted)

        self._drain(TIER_LONG)
        self._drain(TIER_SHORT)
        self._finish()

        return self.ops


@_check_types.do
def plan(arenas: list[ArenaMap], desired: dict[str, int], long_capacity: int, short_capacity: int, threshold: float,
         min_free_vertices: int) -> list[ArenaOp]:
    """The steps that repack the models into the fewest arenas, and trim the long arenas that are full.

    :param arenas: Every arena as it is now. Not changed.
    :param desired: The tier each model should be in (``TIER_SHORT`` / ``TIER_LONG``), by key.
    :param long_capacity: Capacity of a new long arena, in vertices (more if one model needs more).
    :param short_capacity: Capacity of a new short arena, in vertices.
    :param threshold: Fragmentation at which an arena is slid.
    :param min_free_vertices: Free vertices an arena needs before it is slid.
    :returns: The steps, in the order to run them. Empty when there is nothing to do.
    """
    return _Planner(arenas, desired, long_capacity, short_capacity, threshold, min_free_vertices).run()
