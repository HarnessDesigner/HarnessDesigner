# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Pooled wire-path storage for one view (currently the Schematic
editor's wire-to-wire lane checks in ``wire_routing/routing.py``).

Modelled on a mesh's vertex array + face-index array, not on
:class:`~.array_pool.ArrayPool`'s one-row-per-object layout, because a
wire's path is a variable-length chain of points rather than a fixed-size
box:

- **Vertices** -- every distinct point any registered wire passes
  through, each stored ONCE no matter how many wires share it (two wires
  meeting at the same terminal point use the same vertex). A vertex is
  not a copy of a position: it is the live ``Point.as_numpy`` buffer
  itself (a direct reference to the ``Point``'s own ``_data``, which is
  only ever mutated in place, never rebound). A ``Point`` can't live
  inside a shared array, but its buffer can be *referenced* from one --
  so a waypoint moving is already visible here with no callback, no
  copy and no invalidation. Vertices are reference-counted so a point
  used by several wires is only dropped once the last of them lets go.
- **Segment index pairs** -- per wire, an ``(n_segments, 2)`` integer
  array of vertex indices, ``[[v0, v1], [v1, v2], ...]``, kept in a dict
  keyed by a weak reference to the wire (an entry disappears, and its
  vertex references are released, when the wire is garbage collected --
  :meth:`release` does the same eagerly on deletion).

A bulk query (:meth:`segments`) concatenates every wanted wire's index
pairs, gathers the vertices those indices name once, and returns the
whole set of ``((x1, z1), (x2, z2))`` segments as one ``(S, 2, 2)``
array. Every wire has the same diameter, so a segment's two endpoints
are all a lane test needs.

A wire's point list has to be handed to :meth:`register` again whenever
its path changes shape (a waypoint added/removed/reordered, or an
endpoint repointed to a different ``Point``); a plain waypoint *move*
needs nothing.
"""

import weakref

import numpy as np

from .. import check_types as _check_types


class SegmentPool:

    def __init__(self):
        self._zero = np.zeros(3, dtype=np.float32)

        # Slot i's vertex buffer (a Point's live ``_data``), or the shared
        # ``_zero`` placeholder for a free slot.
        self._buffers: list[np.ndarray] = []
        self._counts: list[int] = []
        self._free: list[int] = []

        # id(buffer) -> slot. Safe as a key because the pool holds a strong
        # reference to every buffer it has a slot for, so an id can't be
        # recycled to a different array while it's in here.
        self._by_id: dict[int, int] = {}

        self._entries: dict[weakref.ref, np.ndarray] = {}

    @_check_types.do
    def _acquire(self, buffer: np.ndarray) -> int:
        key = id(buffer)
        index = self._by_id.get(key)

        if index is not None:
            self._counts[index] += 1
            return index

        if self._free:
            index = self._free.pop()
            self._buffers[index] = buffer
            self._counts[index] = 1
        else:
            index = len(self._buffers)
            self._buffers.append(buffer)
            self._counts.append(1)

        self._by_id[key] = index
        return index

    @_check_types.do
    def _drop(self, indices: np.ndarray) -> None:
        # set(), not np.unique: this also runs from a weakref callback at
        # interpreter shutdown, when the module-level ``np`` may already be gone.
        for index in set(indices.ravel().tolist()):
            # A vertex shared by two segments of one wire (every interior
            # point) was acquired once per register() call, not once per
            # segment, so it's dropped exactly once here as well.
            self._counts[index] -= 1

            if self._counts[index] == 0:
                del self._by_id[id(self._buffers[index])]
                self._buffers[index] = self._zero
                self._free.append(index)

    def _on_dead(self, ref: weakref.ref) -> None:
        pairs = self._entries.pop(ref, None)
        if pairs is not None:
            self._drop(pairs)

    @_check_types.do
    def register(self, obj: object, buffers: list[np.ndarray]) -> None:
        """Set *obj*'s path to the chain of *buffers* (each a ``Point``'s
        ``as_numpy``, in path order, start to stop), replacing whatever
        it registered before. Acquires the new vertex references before
        dropping the old ones so a point that's in both stays alive."""
        ref = weakref.ref(obj, self._on_dead)

        # One reference per DISTINCT buffer, matching _drop (which drops
        # each distinct vertex once) even if a buffer repeats in the chain.
        acquired: dict[int, int] = {}
        chain = []
        for buffer in buffers:
            index = acquired.get(id(buffer))
            if index is None:
                index = self._acquire(buffer)
                acquired[id(buffer)] = index

            chain.append(index)

        indices = np.array(chain, dtype=np.int32)

        old = self._entries.get(ref)
        if old is not None:
            self._drop(old)

        if indices.size < 2:
            self._entries.pop(ref, None)
            self._drop(indices)
            return

        self._entries[ref] = np.stack((indices[:-1], indices[1:]), axis=1)

    @_check_types.do
    def release(self, obj: object) -> None:
        """Drop *obj*'s path -- call once when it's deleted. Harmless if
        it was never registered or is already released."""
        pairs = self._entries.pop(weakref.ref(obj), None)
        if pairs is not None:
            self._drop(pairs)

    @_check_types.do
    def segments(self, exclude: list | None = None,
                 window: tuple[float, float, float, float] | None = None) -> np.ndarray:
        """Every registered wire's segments as one ``(S, 2, 2)`` float
        array: ``[s, 0]`` is a segment's ``(x, z)`` start, ``[s, 1]`` its
        end.

        :param exclude: Wires to leave out.
        :param window: ``(lo_x, lo_z, hi_x, hi_z)`` -- keep only segments
            whose bounding box overlaps it.
        """
        skip = set()
        if exclude:
            skip = {weakref.ref(obj) for obj in exclude}

        wanted = [pairs for ref, pairs in self._entries.items() if ref not in skip]
        if not wanted:
            return np.empty((0, 2, 2), dtype=np.float32)

        vertices = np.stack(self._buffers)[:, [0, 2]]
        segments = vertices[np.concatenate(wanted)]

        if window is not None:
            lo_x, lo_z, hi_x, hi_z = window

            keep = ~((segments[:, :, 0].max(axis=1) < lo_x)
                     | (segments[:, :, 0].min(axis=1) > hi_x)
                     | (segments[:, :, 1].max(axis=1) < lo_z)
                     | (segments[:, :, 1].min(axis=1) > hi_z))

            segments = segments[keep]

        return segments
