# harness_designer/objects/objects_schematic/wire.py

## Line 715-771 (`Wire.render`) — per-segment full pipeline, plus per-frame VBO and allocation work for the stripe
- The loop at lines 742-744 runs the full `BaseVar.render` once per segment. The segment list is built once (line 740), which is better than the 3D wire, which rebuilt it several times.
- Line 755 calls `_helix.create_vbo(self._length)` every frame. The helix is cached, so this is a lookup, but it runs for every wire on every frame that the stripe is visible.
- Lines 763-766 build a new `_point.Point(seg_position.x, 0.0, seg_position.z)` per segment per frame. The stripe position depends only on the segment transforms, which change only when the wire moves, so these could be cached with the transforms.
- Lines 754-757 enter `with faces_program:` and set the stripe material every frame, per wire. Batching wires that share a material would remove most of that.

## Line 279-327 (`_recalculate_geometry`) — helix lookup on every drag move
Line 302 calls `_helix.create_vbo(self._length)` on every recalculation, which runs on every endpoint or waypoint move during a drag. The 3D wire guards this with a capacity check first (`_ensure_stripe_capacity`), so the lookup only happens when capacity actually grows. The schematic version should use the same guard.

## Line 350-... (`_segment_world_corners`), 391-443 (`_compute_obb`, `_compute_aabb`, `hit_test_step3`) — same structure as the 3D wire
The corners are built separately for the OBB and the AABB, and `hit_test_step3` transforms the whole mesh per segment. See `objects_3d/wire.md` for the detailed write-up and fixes; they apply here unchanged.
