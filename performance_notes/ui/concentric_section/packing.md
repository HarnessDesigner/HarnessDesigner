# harness_designer/ui/concentric_section/packing.py

Circle packing for the conductors of a multi-conductor cable (`pack_circles(radii)`).

## `pack_circles` — cached by the radii tuple
Results are cached with `functools.lru_cache`. One cache is `maxsize=None` (unbounded) and one is bounded at 512. Each entry is a small list of centres, a few hundred bytes, and the number of distinct radii tuples is the number of distinct cable constructions in the project, so the unbounded one is a negligible leak in practice; bounding it at a few thousand costs nothing and removes the question.

## Line 124-153 (`_enclosing_center`) — nested loops, O(n^2) per candidate
A search for the enclosing circle over the packed circles with two nested loops; n is the conductor count (a few to a few dozen), so the cost is microseconds, and the result is cached.
