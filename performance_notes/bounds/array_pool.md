# harness_designer/bounds/array_pool.py

## Line 201-209 (`__getitem__`) — O(n) reverse lookup on every "get-or-allocate" call
`ref in self._refs` is an O(n) linear scan (list membership test comparing
weakrefs), immediately followed by `self._refs.index(ref)`, ANOTHER O(n)
scan to find the same position. This runs every time `pool[obj]` is used to
either fetch an already-allocated slot or allocate a new one -- per the
module docstring's own note that `__getitem__` exists specifically "to make
sure we are not double allocating an aabb or obb for any object." Building
up N objects this way costs O(n^2) overall.

The module docstring's design rationale for `_refs` being a plain list
(lines 23-29) is about forward lookup (slot index -> weak reference), where
a list is genuinely the right structure since the address space is already
dense. That reasoning doesn't cover this specific case: a reverse lookup
(object -> slot index), which is a different access pattern. A
`weakref.WeakKeyDictionary` (or a plain `dict` keyed by `id(obj)`, cleaned
up in `release()`) mapping object identity to slot index would make this
O(1) without changing `_refs`'s own role or shape. Worth doing if any view
regularly allocates/looks-up more than a handful of objects per interaction
(a project with hundreds of housings/cavities/wires would notice).

## Line 291-303 (`snapshot`) and Line 375, 388 (`hit_test`) — full re-concatenation on every call, most of it discarded immediately
`snapshot()` does `np.concatenate(self._blocks, axis=0)` -- a fresh copy of
every row in every block -- on every single call, with no caching. Both
`hit_test` and `rows_tagged` call it unconditionally. In `hit_test`
specifically, the very next thing that happens is narrowing down to just
the visible subset (`candidate_rows = rows[candidate_indices]`, line 388) --
so on a scene where only a fraction of stored rows are visible, most of
what `snapshot()` just copied is thrown away immediately. `hit_test` is
picking/ray-query code, likely triggered per click or per mouse-move during
a drag, not strictly per-frame, but still a plausible hot path during
interactive use.

Needs investigation rather than a direct fix: the per-block storage layout
(fixed-size blocks, addresses that never move -- see the module docstring)
makes "gather only the visible rows directly from blocks, skip the full
concat" less than a one-line change, and it's not yet clear whether the
concat cost is actually significant at realistic scene sizes (worth
benchmarking with the block count a real large project reaches before
changing this).
