# harness_designer/bounds/array_pool.py

The pool behind every pick: `hit_test` runs on each `find_object` call (`gl/object_picker.py` lines 195-204), so it is on the mouse-move path of every add handler and every hover.

## Line 247-261 (`__contains__`, `__getitem__`) — O(n) reverse lookup, twice
`ref in self._refs` is a linear scan over a Python list of weakrefs (equality on a live weakref compares the referents), and `self._refs.index(ref)` is a second scan to get the position. `__getitem__` is the "get or allocate" entry the module docstring says guarantees no object gets two slots, so every call pays up to 2n comparisons, and building a pool of N objects costs O(N^2). `_refs` as a list is right for slot -> object (dense index); the missing piece is object -> slot.
Fix: a `dict` keyed by the object (or `id(obj)`) to the slot index, filled in `allocate` and cleared in `release`, makes both O(1). Memory price: one dict entry (about 100 bytes) per live object, a few hundred KB for a very large project. Worth it once a project has a few thousand bounded objects; below a few hundred it is not measurable.

## Line 208-234 (`release`) — another linear scan when the slot was visible
`self._visible_refs.pop(self._visible_refs.index(self._refs[index]))` scans the list of this frame's visible refs. It only runs when the released object was marked visible this frame, so it hits the delete-while-drawn path (a deleted object, a wire rebuild). Deleting many visible objects at once is O(visible x deleted). If `_visible_refs` held slot indices in a `set`, this would be O(1) and `mark_visible` would append an int instead of a weakref.

## Line 375-389 (`snapshot`) — full `np.concatenate` of every block on each call
`hit_test`, `snapshot_live` (and therefore `AABB.extent`) and `rows_tagged` all call it, each time copying every row of every block. In `hit_test` the next step is `rows[candidate_indices]` (line ~523), another copy that keeps only the visible rows, so most of the concatenation is thrown away when few objects are on screen.
Caching the concatenation does not help during a drag, because every `update()` of a moving object would invalidate it. Two options that would: (1) gather only the visible rows (keep the visible slot indices as ints as `mark_visible` is called, then `np.concatenate` just those rows' blocks) - less copying, a little more bookkeeping; (2) allocate one large array with spare capacity and have blocks be slices of it, so `snapshot` becomes a view. (2) costs memory (up to 2x the pool when growing by doubling, and views are invalidated on growth) and changes the module's "addresses never move" rule, so it is a trade only worth making if a measurement with a realistic project shows the concat is significant. A pool row is small (an AABB is 6 floats, an OBB 24), so even 10,000 objects is under 1 MB per pool, and the copy takes well under a millisecond at that size.

## Line 433-443 (`snapshot_visible`) and 476-542 (`hit_test`) — one more flag copy and a Python result list
`snapshot_visible` copies the `_visible` flags each call; `hit_test` then builds `candidate_indices`, runs the vectorised ray test and builds a Python list of `(index, t)` tuples that it sorts. The list is only as long as the number of rays hit, so that part is cheap.

## Line 334-341 (`reset_visible`) and 320-331 (`mark_visible`) — per frame
`reset_visible` zeroes the flag array and clears the list once per frame; `mark_visible` sets a flag and appends a weakref per drawn object. O(visible) per frame with tiny constants. Fine.

## Line 418-430 (`visible_objects`)
Builds a new list per call by dereferencing every weakref. Callers: `CanvasWindowBase.objects_in_window` (`gl/canvas_base/canvas_window_base.py`:413), `WireServiceLoop._viewport_candidates`, `BasePegboard.show_table` / `show_concentric_section` and the ray-trace dialog. Only the wire service loop one could be per-frame; check it before caching.

## Memory
Fixed-size blocks mean a pool never shrinks; a deleted object leaves a sentinel row on the free list. That is intentional (rows are reused at the same address) and the waste is bounded by the peak object count.
