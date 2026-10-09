# harness_designer/objects/objects_3d/terminal.py

## Line 317-361 (`render_cavity_overlay`) and 247-296 (`_refresh_overlay_state`) — re-resolves the overlay state every frame, per terminal
`render_cavity_overlay` calls `_refresh_overlay_state()` on every frame for
every seated terminal. Inside, the cavity identity is cached by `cavity_id`
(good), but these run unconditionally every frame:
- `self.db_obj.cavity` and `pjt_cavity.db_id` (line 264-265),
- the three `_overlay_*` reset assignments (lines 282-284),
- reads of `cavity_3d.wire_surf_idx`, `_wire_marker`, `surf_idx` (lines 289-296),
- `_pin_overlay_needed` (line 295), which reads `self._part.gender.name` and
  does a string `.strip().lower()` on every call (line 304-305).

The uncached reads are deliberate (see the docstring at line 254-262: the
surface match is async and can finish after the first render). So the design
is correct, but the gender string work in `_pin_overlay_needed` does not depend
on that async state and could be computed once per part and cached.

## Line 317-361 (`render_cavity_overlay`) — three housing-level draw calls per terminal, per frame
Up to three draws per terminal per frame (wire surface or wire marker, plus the
pin surface), each going through `housing_3d.render_surface_overlay` or
`render_marker_overlay`. With many seated terminals in one housing, those draws
are the main cost. They are the same batching question as the housing overlays:
the decals share a program, so batching them per housing would reduce state
churn.

## Line 183-196 (`_update_position`, `_update_angle`) — `super()` call per drag event
Calls `super()` and then whatever terminal-specific work follows. Same per-event
GL-context cost as the rest of `Base3D`; see `base_3d.md`.

## Line 483-... (`_pick_free_part`) — not in the per-frame path
Called from add/pick flows. Not a performance concern.

## Previously noted (see `performance_notes/objects/terminal.md` at the objects/ level)
The `wires` property prune-on-read and the `_junction_push_length` O(cavities)
scan are in the objects-level note, not repeated here.
