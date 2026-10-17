# harness_designer/objects/objects_pegboard/bundle.py

## Line 447-... (`Bundle.render`) — full `BaseVar` pipeline per sub-segment
Same structure as the 3D bundle: one full render pass per segment, so the per-object pipeline overhead multiplies with the segment count. See `performance_notes/objects/objects_3d/bundle.md`.

## Line 303-... (`_recalculate_geometry`) and 327-... (`_update_position`) — recalculation per move
Same recalculation shape as the 3D bundle: one call per endpoint or waypoint move. See `objects_3d/bundle.md`.

**Fixed for the rope-pull drag path specifically (2026-10-16).** Mirrors `objects_pegboard.wire.Wire`'s identical fix exactly -- see that file's own note. Added `unregister_geometry_updates()`/`reregister_geometry_updates()` so `handlers.rope_pull_handler._apply_mid_drag` recalculates once per call instead of once per waypoint moved during its per-point `_place_active` loop, and skips even that one recalculation cheaply (no re-derivation) on a true no-op.

**Fourth fix (2026-10-17): `_recalculate_geometry` was calling `_compute_obb()`/`_compute_aabb()` twice per call**, same bug and same fix as `objects_pegboard.wire.Wire._recalculate_geometry` -- see that file's own note (found via a raw call-stack dump, not the `debug.logfunc` call tree, since the duplicate path runs through `Point`'s own undecorated callback dispatch). `self._scale.z = total_length` already triggers both via `BaseVar._update_scale`; the explicit trailing calls were removed.

**Fifth and final fix (2026-10-17): `unregister_geometry_updates`/`reregister_geometry_updates` renamed to `suspend_updates`/`resume_updates`, simplified to a plain `_update_suspended` bool, and the gate moved into `_recalculate_geometry` itself** -- mirrors `objects_pegboard.wire.Wire`'s identical changes exactly; see that file's own note, including the real remaining bug (an id-based lookup in `handlers.rope_pull_handler` that silently missed some points) and its fix (`chains_bound_to_point`), which lived upstream of this class entirely. **User-confirmed live: fixed.**
