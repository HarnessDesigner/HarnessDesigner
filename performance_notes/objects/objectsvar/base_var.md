# harness_designer/objects/objectsvar/base_var.py

## Line 322-354 (`hit_test_step3`) — full mesh transformed on every call, per candidate
Line 344 builds `(self._vbo.vertices.reshape(-1, 3) * self._scale) @ self._angle` for
the whole mesh, then tests every triangle in world space. That is O(V) matrix work
per candidate object on every click that reaches stage 3. `hit_test_step2` (line 309-310)
already does the right thing by transforming the *ray* into local space once. Doing the
same here (`local_origin`/`local_direction` as in step 2, then testing the untransformed
local triangles) turns the per-candidate cost from O(V) into O(1) plus the triangle test.
Every 3D object inherits this, so the saving applies to housings, terminals, and every
other mesh object. Callers: `gl/object_picker.py:210` and `:572`/`:578`.

## Line 1021-1092 (`render`) — per-object material allocation and state churn, every frame
- Line 1063 and 1080 build a new `_materials.Metallic` / `_materials.Glowing` (and
  `_color.Color`) for each object in the edges and normals passes, every frame, whenever
  those debug toggles are on. These could be created once per distinct debug color.
- Line 1058 and 1060 and 1079 do `_debug_config.*[:] + [1.0]` list copies per frame.
- Line 1044, 1062, and 1089 each enter a `with shaders.*:` context per object per pass.
  Combined with the draw order this is a program bind/unbind pair per object per pass,
  so the cost scales with object count. Grouping objects by program in the canvas draw
  loop would remove most of it; that is a `canvas_base` change, not a change here.
- Lines 1040-1041 call `mark_visible` on both bounds managers every frame for every
  visible object. These are cheap numpy writes, but they happen even when nothing changed.

## Line 476-507 (`_update_position`) — GL context acquire per drag event, numpy-only body
Takes `with self.editor.context:` (line 496) and then only does
`self._obb += delta` and `self._aabb += delta` plus a copy. `harness_designer/bounds/`
imports only numpy, weakref, and its own modules (checked with `dep_trace.py`), so
`_obb`/`_aabb` are CPU-side pool arrays and this block does not touch GL. The context
acquire can be dropped from this path. This is the cheapest drag-path fix in the
folder and is confirmed, not just likely.

## Line 510-544 (`_update_angle`, `_update_scale`) — full OBB/AABB rebuild under the same acquire
Each event recomputes both bounds (`_compute_obb`/`_compute_aabb`) inside the context
acquire. The rebuild itself is numpy-only for the same reason as above, so the acquire
is unnecessary here too.

## Line 271-283 (`_compute_aabb`) and 225-246 (`_compute_obb`) — fresh temporaries per call
`_compute_aabb` allocates an `(8, 3)` corner array (line 271) on every call, then
multiplies in place. `_compute_obb` allocates `local_obb * scale`, `@ angle`, and
`+ position` temporaries. Both run on every angle or scale event. A preallocated scratch
buffer per object would avoid the allocations, but these are small arrays, so the gain is
modest; the context-acquire removal above matters more.

## Line 1054-1076 (`hit_test_step1`/`_step2`) — per-call ray setup
Step 1 (line 292) and step 2 (line 312) compute `1.0 / (direction + 1e-8)` per candidate.
The inverse direction is the same for every candidate in one pick, so it could be computed
once per click by the picker and passed in. Small win; noted for the object picker review.
