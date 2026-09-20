# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared block/slot storage engine behind both
:class:`~.aabb.AABB`/:class:`~.obb.OBB`.

One instance of a manager holds every object's box for a single view
(the Schematic editor, the Peg Board editor, or the 3D view each get
their own -- see the two subclasses for which view uses which). Storage
is a list of fixed-size (``block_size`` rows, default 50) numpy blocks
rather than one array that grows -- a numpy array can only grow by
allocating a new buffer and copying the old data into it, which would
silently strand any previously-taken reference to the old buffer (numpy
itself refuses to grow an array *in place* while anything still
references it, precisely because of this hazard). A fixed-size block,
once allocated, never moves or resizes again for the rest of the
program -- growing just means appending another block, so an object's
own row is at a permanent address for its entire lifetime, and this
never needs to guard against or even detect a resize.

Three more lists are kept in lockstep with the block list, one entry
added per block:

- ``_refs`` -- a plain Python list of ``block_size`` weak references
  (or ``None``), addressed the same way as the bounds block itself, so
  a hit test's matching row can be resolved back to the real object
  that owns it (see :meth:`resolve`). A plain list, not a ``dict``
  keyed by slot -- the address space is already dense (every slot is
  exactly ``(block, index)``), so there's nothing a hash table buys
  over direct indexing here.
- ``_visible`` -- one boolean per slot, reset to ``False`` in a batch
  every time :meth:`reset_visible` is called (once per frame, at the
  start of a view's own render pass) and set back to ``True`` inline by
  whichever objects actually get drawn that frame (see
  :meth:`mark_visible`, called from inside an object's own ``render()``
  override). "Currently in view" falls out of this for free -- nothing
  here ever has to detect an object entering or leaving view itself,
  since that's already exactly what decides whether ``render()`` gets
  called on it at all.
- Slot reuse: :meth:`release` (called once, when the owning object is
  deleted -- and ONLY then) pushes the freed slot index onto a
  free-list, and the row itself gets overwritten with a sentinel value
  (supplied by the subclass) that can never satisfy a real geometric
  query -- so a matching hit test can never resolve to a slot that's
  actually been freed, without a separate "is this slot still alive"
  check anywhere.

A slot's own address never changes for its whole lifetime -- released
slots are only ever reused via the free-list at the SAME address,
nothing is ever renumbered/compacted -- so an object holding onto a
slot index never needs to be told anything moved.

:meth:`hit_test` is the entry point for a bulk ray-vs-everything query
(object picking) -- it filters down to the currently-visible rows via
:meth:`snapshot_visible`, then hands the surviving rows to the
subclass's own :meth:`_vectorized_ray_test` (AABB slab test or OBB
slab-on-local-axes test -- see :mod:`~.aabb`/:mod:`~.obb`), and maps
the result back to real slot indices a caller can :meth:`resolve` into
the objects that actually got hit.
"""

import weakref

import numpy as np

from .. import check_types as _check_types


# Slot categories for :meth:`ArrayPool.set_tag`. Add new ones here.
TAG_NONE = 0
TAG_OBSTACLE = 1  # schematic housing/splice/note -- a hard obstacle for wire routing


class ArrayPool:
    """See the module docstring for the overall design. Not used
    directly -- :class:`~.aabb.AABB`/:class:`~.obb.OBB` supply the row
    width and the sentinel row for their own box shape, plus the actual
    ray-test math via :meth:`_vectorized_ray_test`.
    """

    @_check_types.do
    def __init__(self, sentinel_row: list, block_size: int = 50,
                 dtype: type = np.float32):
        self._block_size = block_size

        # float32 is load-bearing: rows are handed straight to
        # gl/culling/culling.pyx, which declares them ``float[::1]`` --
        # a float64 row raises a buffer dtype mismatch there and every
        # frame's cull fails (nothing but non-culled gizmos draws).
        self._dtype = dtype
        self._sentinel_row = np.asarray(sentinel_row, dtype=dtype)

        self._shape = (self._block_size,) + self._sentinel_row.shape

        self._blocks: list[np.ndarray] = []
        self._refs = []
        self._visible_refs = []
        self._visible = np.empty((0,), dtype=bool)

        # One small integer per slot, in the same row order as
        # ``_visible`` -- see :meth:`set_tag`/:meth:`rows_tagged`.
        # ``TAG_NONE`` (0) for every unissued/released/untagged slot.
        self._tags = np.empty((0,), dtype=np.uint8)
        self._free: list[int] = []
        self._issued_in_last_block = 0

    @property
    @_check_types.do
    def block_size(self) -> int:
        return self._block_size

    @_check_types.do
    def _add_block(self) -> None:
        """A fresh block, pre-filled with the sentinel row throughout --
        every row starts "released" until :meth:`allocate` hands it out,
        so a never-yet-issued row already reads as inert with no extra
        bookkeeping.
        """

        block = np.ascontiguousarray(
            np.array([self._sentinel_row] * self._block_size, dtype=self._dtype))

        self._blocks.append(block)
        self._refs.extend([None] * self._block_size)

        self._visible = np.concatenate(
            (self._visible, np.zeros(self._block_size, dtype=bool)),
            axis=0, dtype=bool)

        self._tags = np.concatenate(
            (self._tags, np.zeros(self._block_size, dtype=np.uint8)),
            axis=0, dtype=np.uint8)

        self._issued_in_last_block = 0

    @_check_types.do
    def allocate(self, obj: object) -> int:
        """Claim a row for *obj* -- a freed slot from an earlier
        release if one's available (reused at its own original
        address), otherwise the next never-issued row in the current
        tail block (appending a brand-new block first if that block is
        already full). *obj* is stored as a weak reference only (see
        :meth:`resolve`) -- this manager never keeps an object alive
        past its own natural lifetime just because it still holds a
        slot.

        The returned index is *obj*'s own handle for every other method
        here, for as long as it lives -- callers hold onto it, they
        never derive one themselves.
        """
        if self._free:
            index = self._free.pop()
        else:
            if not self._blocks or self._issued_in_last_block >= self._block_size:
                self._add_block()

            index = ((len(self._blocks) - 1) * self._block_size) + self._issued_in_last_block
            self._issued_in_last_block += 1

        self._refs[index] = weakref.ref(obj)
        return index

    @_check_types.do
    def release(self, index: int) -> None:
        """Free *slot* -- call exactly once, when the object that
        allocated it is deleted, never on a mere visibility/state
        change. Overwrites the row with the sentinel value so it can
        never satisfy a real query again, clears its weak reference,
        and returns it to the free-list for a future :meth:`allocate`
        to reuse at this same address.
        """

        if self._refs[index] is None:
            # Already released (or never issued) -- a second call would
            # push the same slot onto the free-list twice and hand it to
            # two different objects.
            return

        block, slot = divmod(index, self._block_size)
        self._blocks[block][slot][:] = self._sentinel_row

        if self._visible[index]:
            self._visible_refs.pop(
                self._visible_refs.index(self._refs[index]))

        self._refs[index] = None
        self._visible[index] = False
        self._tags[index] = TAG_NONE
        self._free.append(index)

    @_check_types.do
    def update(self, index: int, values: np.ndarray) -> None:
        """Overwrite *slot*'s own row in place with *values* (already in
        whatever shape/units the concrete subclass's row represents)."""
        block, slot = divmod(index, self._block_size)
        self._blocks[block][slot][:] = values

    def __contains__(self, item) -> bool:
        ref = weakref.ref(item)
        return ref in self._refs

    def __getitem__(self, item) -> int:
        # this next bit of code makes sure we are not double allocating
        # an aabb or obb for any object.
        ref = weakref.ref(item)

        if ref in self._refs:
            return self._refs.index(ref)

        return self.allocate(item)

    def __setitem__(self, key: int, value: bool) -> None:
        if value is True:
            self.mark_visible(key)

    @_check_types.do
    def set_tag(self, index: int, tag: int) -> None:
        """Categorize *index*'s slot (one of the ``TAG_*`` constants) so a
        bulk query can select a whole category at once via
        :meth:`rows_tagged` instead of walking objects in Python."""
        self._tags[index] = tag

    @_check_types.do
    def rows_tagged(self, tag: int, exclude: list[int] | None = None) -> np.ndarray:
        """Every row whose slot is tagged *tag*, as one new array (a copy,
        not a view -- this is a boolean-mask selection). Independent of
        visibility: a routing obstacle scan needs every such object, in
        view or not.

        :param exclude: Slot indices to leave out even if tagged.
        """
        mask = self._tags == tag

        if exclude:
            for index in exclude:
                mask[index] = False

        return self.snapshot()[mask]

    @_check_types.do
    def read(self, index: int) -> np.ndarray:
        """*slot*'s own current row."""
        block, slot = divmod(index, self._block_size)

        return self._blocks[block][slot]

    @_check_types.do
    def mark_visible(self, index: int) -> None:
        """Called from inside the owning object's own ``render()`` --
        see the module docstring's ``_visible`` bullet. A no-op for a
        released slot (a deleted object still mid-render)."""
        if self._refs[index] is None:
            return

        self._visible[index] = True
        self._visible_refs.append(self._refs[index])

    @_check_types.do
    def reset_visible(self) -> None:
        """Called once, at the start of this view's own render pass,
        before any object's ``render()`` runs this frame."""
        self._visible[:] = False
        del self._visible_refs[:]

    @_check_types.do
    def resolve(self, index: int) -> object | None:
        """The real, live object *slot* belongs to, or ``None`` if it's
        already been garbage collected (a defensive guard, same as
        ``objects.wire.Wire.start_sibling``/``objects.terminal.Terminal
        .wires`` already do for their own weak references elsewhere in
        this codebase -- shouldn't normally happen if every object
        properly calls :meth:`release` on its own deletion, but resolving
        a dead weak reference is not itself an error)."""
        ref = self._refs[index]

        return None if ref is None else ref()

    @_check_types.do
    def slot_at_row(self, index: int) -> tuple[int, int]:
        """The ``(block, slot)`` pair a :meth:`snapshot` row index came
        from -- snapshot rows are a straight concatenation of every
        block in order, so a row index maps onto ``(block, index)`` by
        the same arithmetic the blocks are themselves sized by. Only
        needed at this one boundary (translating a bulk vectorized
        query's result back into real slots) -- everywhere else, a slot
        is passed around as the opaque index it already is.
        """
        block, slot = divmod(index, self._block_size)
        return block, slot

    @_check_types.do
    def snapshot(self) -> np.ndarray:
        """Every row across every block, concatenated into one array --
        for a bulk vectorized query (a hit test, a routing obstacle
        scan) against everything currently stored, released or not
        (a released/never-issued row's own sentinel value already
        guarantees it can't affect the result -- see the module
        docstring). Row ``i`` of the result is exactly
        :meth:`slot_at_row`'s own ``i``.
        """
        if not self._blocks:
            return np.empty((0,) + self._shape[1:], dtype=self._dtype)

        return np.concatenate(self._blocks, axis=0)

    def visible_objects(self):
        ret = []
        for ref in self._visible_refs:
            if ref is None:
                continue

            obj = ref()
            if obj is None:
                continue

            ret.append(obj)

        return ret

    @_check_types.do
    def snapshot_visible(self) -> np.ndarray:
        """The ``_visible`` flags in the same row order :meth:`snapshot`
        returns its bounds in -- AND the two together to restrict a
        bulk query to only what's actually in view this frame."""
        if not self._blocks:
            return np.empty((0,), dtype=bool)

        return self._visible.copy()

    def _vectorized_ray_test(self, rows: np.ndarray, origin: np.ndarray,
                              direc: np.ndarray, t0: float, t1: float):
        """Subclass hook -- given *rows* (an ``(N, ...)`` array, this
        pool's own row shape per entry) and a ray (*origin*/*direc*,
        world space, *direc* already normalized), test every row at
        once and return ``(hit_mask, t_vals)``: both shape ``(N,)``,
        *hit_mask* a bool array, *t_vals* the ray-entry distance for
        every row (garbage where *hit_mask* is False -- :meth:`hit_test`
        never reads those entries).

        :class:`~.aabb.AABB` implements this as a vectorized slab test
        against each row's min/max corner pair; :class:`~.obb.OBB`
        implements it as a vectorized slab test against each row's own
        oriented edge axes -- mirroring
        ``gl.object_picker._ray_intersect_aabb``/``_ray_intersect_obb``'s
        scalar, one-object-at-a-time math, just batched over every row
        in one call instead of looping in Python.
        """
        raise NotImplementedError

    @_check_types.do
    def hit_test(self, origin: np.ndarray, direc: np.ndarray,
                 t0: float = 0.0, t1: float = np.inf,
                 visible_only: bool = True) -> list[tuple[int, float]]:
        """Vectorized ray hit test against every stored row -- restricted
        to only the rows currently flagged ``_visible`` when
        *visible_only* is True (the normal case: there is no reason to
        ray-test an object that isn't even being drawn this frame).

        :param origin: Ray origin, world space, shape ``(3,)``.
        :param direc: Ray direction, world space, shape ``(3,)`` --
            expected already normalized (matches
            ``gl.object_picker.find_object``'s own convention).
        :param t0: Minimum accepted hit distance along the ray.
        :param t1: Maximum accepted hit distance along the ray.
        :param visible_only: Restrict the test to rows flagged visible
            this frame (see :meth:`mark_visible`/:meth:`reset_visible`).
            Pass False to test every live row regardless of visibility.

        :returns: ``(index, t_hit)`` pairs, nearest first -- *index* is
            this pool's own slot index, the exact same value
            :meth:`allocate`/``__getitem__`` hand out and
            :meth:`resolve`/:meth:`slot_at_row` accept, so a caller
            pulls the real object straight off it via
            ``pool.resolve(index)``.
        """
        rows = self.snapshot()
        if rows.shape[0] == 0:
            return []

        if visible_only:
            visible = self.snapshot_visible()
        else:
            visible = np.ones(rows.shape[0], dtype=bool)

        candidate_indices = np.nonzero(visible)[0]
        if candidate_indices.size == 0:
            return []

        candidate_rows = rows[candidate_indices]

        hit_mask, t_vals = self._vectorized_ray_test(
            candidate_rows, origin, direc, t0, t1)

        hit_local = np.nonzero(hit_mask)[0]
        if hit_local.size == 0:
            return []

        results = [
            (int(candidate_indices[i]), float(t_vals[i]))
            for i in hit_local
        ]
        results.sort(key=lambda pair: pair[1])
        return results
