# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Pre-allocated, chunked slot storage for ``Point`` / ``Quaternion`` / ``Angle`` data.

A :class:`SlotPool` owns several float32 arrays that share one slot index, split into
fixed-size chunks that are allocated once and never grow, move or compact. A :class:`SlotBlock`
is a contiguous run of slots handed out by best fit (``allocate``) and given back with
``release``, which first gives every live object built over the block a private copy of its data
and then resets the rows to their neutral values and merges the free run with its neighbours.
``Point`` and ``Angle`` derive from :class:`PoolMember` so they can leave the pool. An object built
over a slot holds a view of its row and never learns a slot number.

THE WHOLE DESIGN -- why it exists, the layout of a housing's slots, when blocks are allocated and
released, how rows are bound to slots, the rules that keep it correct and its limits -- is
documented in the module docstring of ``database/project_db/pjt_housing.py`` ("POOLED 3D
STORAGE"; sections 3 and 4 describe this pool). Read that first: this module is only the pool,
and the text there is the one to keep up to date.
"""

import bisect
import threading
import weakref

import numpy as np

from .. import check_types as _check_types


class PoolMember:
    """
    Base class of every object whose data can live in a pool row.

    A member built over a pool view must be able to leave the pool: take a
    private copy of its data so it no longer aliases the shared rows.
    """

    @_check_types.do
    def _leave_pool(self) -> None:
        """
        Replace every view this object holds with a private copy.

        :raises NotImplementedError: A subclass did not implement it.
        """

        raise NotImplementedError


class SlotField:
    """One array of a pool: its name, the shape of one slot and the slot's neutral value."""

    __slots__ = ('name', 'shape', 'neutral')

    @_check_types.do
    def __init__(self, name: str, shape: tuple[int, ...], neutral: np.ndarray):
        """
        :param name: Name the array is asked for by.
        :type name: str
        :param shape: Shape of a single slot, ``()`` for a scalar.
        :type shape: tuple[int, ...]
        :param neutral: Value of an unused slot (broadcast to ``shape``).
        :type neutral: :class:`numpy.ndarray`
        """

        self.name = name
        self.shape = shape
        self.neutral = np.asarray(neutral, dtype=np.float32)


class SlotBlock:
    """A contiguous run of slots in one chunk. Handed out by :meth:`SlotPool.allocate`."""

    __slots__ = ('chunk', 'start', 'count', 'released')

    @_check_types.do
    def __init__(self, chunk: int, start: int, count: int):
        """
        :param chunk: Index of the chunk the block is in.
        :type chunk: int
        :param start: First slot of the block, counted from the start of the chunk.
        :type start: int
        :param count: Number of slots.
        :type count: int
        """

        self.chunk = chunk
        self.start = start
        self.count = count
        self.released = False


class _Chunk:
    """One fixed-size set of arrays, its free list and the weak references of its members."""

    __slots__ = ('capacity', 'arrays', 'free', 'refs')

    def __init__(self, capacity: int, fields: tuple[SlotField, ...]):
        self.capacity = capacity
        self.arrays: dict[str, np.ndarray] = {}

        for field in fields:
            array = np.empty((capacity,) + field.shape, dtype=np.float32)
            array[:] = field.neutral
            self.arrays[field.name] = array

        # Sorted, non-adjacent (start, length) runs.
        self.free: list[tuple[int, int]] = [(0, capacity)]
        self.refs: list[weakref.ReferenceType | None] = [None] * capacity


class SlotPool:
    """
    Chunked slot storage with contiguous blocks, best-fit allocation and
    merging of freed blocks. See the module docstring for the design.
    """

    @_check_types.do
    def __init__(self, chunk_slots: int, fields: tuple[SlotField, ...]):
        """
        :param chunk_slots: Slots in a normal chunk.
        :type chunk_slots: int
        :param fields: The arrays of this pool; they share one slot index.
        :type fields: tuple[:class:`SlotField`, ...]
        """

        self._chunk_slots = chunk_slots
        self._fields = fields
        self._chunks: list[_Chunk] = []

        # Allocation, release and registration can be asked for from the UI
        # thread and from a worker thread (the circuit dock reads rows from
        # one), and a weakref callback can run on any thread.
        self._lock = threading.RLock()

    @property
    @_check_types.do
    def chunk_count(self) -> int:
        """Return the number of chunks."""

        return len(self._chunks)

    @property
    @_check_types.do
    def chunk_slots(self) -> int:
        """Return the slot count of a normal chunk."""

        return self._chunk_slots

    @_check_types.do
    def free_slots(self) -> int:
        """Return how many slots are free across every chunk."""

        with self._lock:
            total = 0
            for chunk in self._chunks:
                for _, length in chunk.free:
                    total += length

        return total

    @_check_types.do
    def reset(self) -> None:
        """
        Drop every chunk, back to the empty state.

        Storage is dropped, not wiped: a member that still holds a view keeps
        its own (now unowned) array alive, so it can never write into a row a
        new block owns. Every block handed out before is meaningless after this.
        """

        with self._lock:
            self._chunks = []

    @_check_types.do
    def allocate(self, count: int) -> SlotBlock:
        """
        Claim ``count`` contiguous slots: the smallest free block that fits,
        searched over every chunk (a chunk's unused tail counts as a free
        block); a new chunk when none does.

        :param count: Number of slots, at least 1.
        :type count: int
        :returns: The block.
        :rtype: :class:`SlotBlock`
        :raises ValueError: ``count`` is less than 1.
        """

        if count < 1:
            raise ValueError('a block needs at least one slot')

        with self._lock:
            best_length = 0
            best_chunk = -1
            best_index = -1

            for chunk_index, chunk in enumerate(self._chunks):
                for free_index, (_, length) in enumerate(chunk.free):
                    if length < count:
                        continue

                    if best_chunk == -1 or length < best_length:
                        best_length = length
                        best_chunk = chunk_index
                        best_index = free_index

            if best_chunk == -1:
                capacity = max(self._chunk_slots, count)
                self._chunks.append(_Chunk(capacity, self._fields))
                best_chunk = len(self._chunks) - 1
                best_index = 0

            chunk = self._chunks[best_chunk]
            start, length = chunk.free[best_index]

            if length == count:
                del chunk.free[best_index]
            else:
                chunk.free[best_index] = (start + count, length - count)

            return SlotBlock(best_chunk, start, count)

    @_check_types.do
    def release(self, block: SlotBlock) -> None:
        """
        Give a block back. Every live member in it first takes a private copy of
        its data, the rows are reset to their neutral values and the block
        is merged with any free neighbour.

        :param block: A block from :meth:`allocate`.
        :type block: :class:`SlotBlock`
        :raises ValueError: The block was already released.
        """

        with self._lock:
            if block.released:
                raise ValueError('block already released')

            chunk = self._chunks[block.chunk]
            end = block.start + block.count

            for slot in range(block.start, end):
                ref = chunk.refs[slot]
                chunk.refs[slot] = None

                if ref is None:
                    continue

                member = ref()
                if member is not None:
                    member._leave_pool()

            for field in self._fields:
                chunk.arrays[field.name][block.start:end] = field.neutral

            index = bisect.bisect_left(chunk.free, (block.start, 0))
            start = block.start
            length = block.count

            if index > 0:
                prev_start, prev_length = chunk.free[index - 1]
                if prev_start + prev_length == start:
                    start = prev_start
                    length += prev_length
                    index -= 1
                    del chunk.free[index]

            if index < len(chunk.free):
                next_start, next_length = chunk.free[index]
                if start + length == next_start:
                    length += next_length
                    del chunk.free[index]

            chunk.free.insert(index, (start, length))
            block.released = True

    @_check_types.do
    def array(self, block: SlotBlock, name: str) -> np.ndarray:
        """
        The slice of one array that covers a block: a view, not a copy.

        :param block: A live block.
        :type block: :class:`SlotBlock`
        :param name: A field name.
        :type name: str
        :returns: ``(block.count,) + slot shape`` view.
        :rtype: :class:`numpy.ndarray`
        """

        return self._chunks[block.chunk].arrays[name][block.start:block.start + block.count]

    @_check_types.do
    def row(self, block: SlotBlock, name: str, offset: int) -> np.ndarray:
        """
        One slot's row of one array: a view of ``block.start + offset``.

        :param block: A live block.
        :type block: :class:`SlotBlock`
        :param name: A field name.
        :type name: str
        :param offset: Slot number inside the block.
        :type offset: int
        :returns: The row, contiguous.
        :rtype: :class:`numpy.ndarray`
        """

        return self._chunks[block.chunk].arrays[name][block.start + offset]

    @_check_types.do
    def register(self, block: SlotBlock, offset: int, member: PoolMember) -> None:
        """
        Remember (weakly) the object built over a slot, so :meth:`release` can
        take it out of the pool and :meth:`members` can reach it.

        :param block: A live block.
        :type block: :class:`SlotBlock`
        :param offset: Slot number inside the block.
        :type offset: int
        :param member: The object built over the slot's rows.
        :type member: :class:`PoolMember`
        :raises ValueError: A different live object is already registered on the slot.
        """

        with self._lock:
            chunk = self._chunks[block.chunk]
            slot = block.start + offset
            ref = chunk.refs[slot]

            if ref is not None:
                current = ref()
                if current is not None and current is not member:
                    raise ValueError('slot already has a live member')

            chunk.refs[slot] = weakref.ref(member)

    @_check_types.do
    def evict(self, block: SlotBlock, offset: int) -> None:
        """
        Take the object built over one slot out of the pool (it gets a private
        copy of its data) and forget it. Used when the row that owned the slot
        is replaced, so the old object can never write into the new owner's data.

        :param block: A live block.
        :type block: :class:`SlotBlock`
        :param offset: Slot number inside the block.
        :type offset: int
        """

        with self._lock:
            chunk = self._chunks[block.chunk]
            slot = block.start + offset
            ref = chunk.refs[slot]
            chunk.refs[slot] = None

            if ref is None:
                return

            member = ref()
            if member is not None:
                member._leave_pool()

    @_check_types.do
    def members(self, block: SlotBlock) -> list[PoolMember | None]:
        """
        The live object of every slot of a block, in slot order (``None`` where
        nothing was built or the object is gone).

        :param block: A live block.
        :type block: :class:`SlotBlock`
        :returns: One entry per slot.
        :rtype: list[:class:`PoolMember` | None]
        """

        chunk = self._chunks[block.chunk]
        result: list[PoolMember | None] = []

        for ref in chunk.refs[block.start:block.start + block.count]:
            if ref is None:
                result.append(None)
            else:
                result.append(ref())

        return result
