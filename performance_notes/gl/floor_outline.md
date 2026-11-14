# harness_designer/gl/floor_outline.py

The outline a selected wire, bundle or cable casts on the floor, seen from above. `TubeMixin._render_floor_outline` (`objects/mixins/tube.py` line 307) rebuilds it every frame while the object is selected and visible.

## Line 39-102 (`silhouette_loops`) — Python loops with a small NumPy call per chord, every frame
For each chord it does `np.asarray(...)` and `np.linalg.norm(...)` (about 5 us each in the interpreter), joins chords into runs, thins the run in a second loop (`np.linalg.norm` per point) and computes mitre offsets in a third loop. For a selected path of 200 chords that is on the order of 2-4 ms per frame, only while the object is selected. `outline_vertices` (line 106-151) is already vectorised and cheap.
Fixes: (1) cache the resulting vertex array on the object and rebuild it only when the path or radius changes (the tube already knows when its path changes). Memory: `chords x 12 vertices x 8 floats x 4 bytes` is about 80 KB for 200 chords, kept only for selected objects, which is a good trade. (2) Vectorise the chord join and thinning with NumPy (`np.diff`, `np.hypot`, a cumulative distance) so the per-chord Python loops go away.

## Line 191-215 (`FloorOutline.draw`) — a new `glBufferData` per frame
`GL_STREAM_DRAW` with a fresh data store each draw (orphaning), which is the correct way to stream data that changes every frame. With the cache above the upload could be skipped on unchanged frames by keeping the buffer.
