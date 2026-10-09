# harness_designer/gl/object_picker.py

## Line 143-255 (`find_object`) — coarse pass is vectorized, the precise pass is per candidate
The bounds pool's `hit_test` gives a vectorized coarse list (lines 183-193), which is the right design. Each surviving candidate then runs `hit_test_step3` (lines 209-210), which transforms the full mesh per call. That is the same per-candidate full-mesh cost described for the 3D views in `performance_notes/objects/objects_3d/base_3d.md`. Fixing that in `BaseVar.hit_test_step3` fixes this path too.

## Line 419-458 (`_pick_candidates_at_mouse`) — linear over every scene object per click
Walks every scene object, resolves its view, and projects its OBB to the screen per object. This is O(N) per click with a projection per object. It is used by `find_object_in_list` (line 463), which is O(N) per click as well. If that path is ever hot, the projected screen boxes could be cached per camera state and invalidated on camera move.

## Line 419-458 (`_pick_candidates_at_mouse`) — docstring mismatch
The docstring says it returns `(depth, object, bbox2d)`, but line 454 appends `(depth, obj)`. The docstring is out of date; no performance impact.
