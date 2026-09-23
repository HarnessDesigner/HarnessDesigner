# harness_designer/color.py

## Line 25-35 — `_remove_ref` does a linear scan to find the dying entry
`ColorMeta._remove_ref` is the weakref callback fired when a cached `Color`
is garbage collected. All `weakref.ref(instance, cls._remove_ref)` calls
(lines 60-62, 71-74) share the same classmethod callback, so `_remove_ref`
has no way to know the `db_id` key directly and instead scans
`list(cls._instances.items())` doing `value == ref` to find it — O(n) in the
current cache size on every single Color collection.

A per-instance closure or `functools.partial(cls._remove_ref, db_id)` bound
at `weakref.ref(...)` construction time (lines 60-62, 71-74) would let the
callback delete `cls._instances[db_id]` directly in O(1), no scan needed.
Worth it if the color cache grows large (many distinct db-backed colors) and
churns (colors going out of scope during project edits) — investigate actual
cache size in a real project before prioritizing this.
