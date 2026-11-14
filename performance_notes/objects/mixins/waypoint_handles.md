# harness_designer/objects/mixins/waypoint_handles.py

Invisible drag handles at a selected wire, bundle or cable's waypoints. Runs only while the owner is selected, and the picking functions run on mouse moves.

## Line 87-110 (`_handle_centers`), 113-136 (`waypoint_under_ray`), 204-226 (`closest_waypoint`) — handle centers recomputed on every call
`_handle_centers` calls `_curve_chords()` (which needs the twist plan, see `mixins/tube.md`) and then, for every waypoint, computes the nearest point on every chord with NumPy (`O(waypoints x chords)` array operations, about 6 small NumPy calls per waypoint). `waypoint_under_ray` calls it on each hover or pick while selected, so a mouse move over a selected wire with 10 waypoints and 200 chords runs about 60 NumPy calls to throw the centers away again. The centers depend only on the path, not on the ray.
Fix: cache the centers on the owner and rebuild them when the path changes (the same stamp that invalidates the twist plan). Memory: one `(waypoints, 3)` float64 array, a few hundred bytes. A larger gain is available by vectorising over waypoints too, but the cache removes the repeated work entirely.
