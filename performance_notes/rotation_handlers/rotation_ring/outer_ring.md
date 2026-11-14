# harness_designer/rotation_handlers/rotation_ring/outer_ring.py

## `pick_tick_index` -- tick hit test per mouse move (measured 2026-11-14)
One ray against all 360 tick boxes at once: the boxes are three ring-frame arrays (34 KB, `_protractor_base.py`), carried to the world with the ring's matrix (about 60 us) and tested with the vectorised slab test (0.15 ms in all), against 16 ms for the old per-box `_ray_intersect_obb` loop alone, which ran after a screen-bounds pass that projected 8 corners per tick in Python (not timed) and was gated by a ring-level washer test that is no longer needed. Agrees with `gl.object_picker._ray_intersect_obb` on every box tried; no `TickPickObject` / `BaseVar` instances (360 of each per ring before), nothing to resync on a reposition. Differences from the old path: no per-triangle `hit_test_step3` on the surviving box (it refined a 0.66 mm box to the cylinder inside it) and the nearest hit decides (all ticks shared one `_pick_priority`).

## Line 72-130 (`OuterRing.__init__`) -- builds the outer ring
Builds the base ring (washer, tick mesh, labels) and positions it; no per-tick pick objects any more. Runs when the gizmo opens.

## `_get_label_color` -- a constant
Returns a fixed grey. Cheap.

## `delete` -- teardown
Releases the buffers. Runs once per session.
