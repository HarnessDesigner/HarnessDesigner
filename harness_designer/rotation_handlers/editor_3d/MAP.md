## FILES

#### __init__.py

Package docstring only, explaining why there's no per-object-type split yet (kept `generic.py`-first, mirroring `drag_handlers.editor_3d`'s own generic/specific split, so a future object type needing bespoke rotation behavior has a place to live without restructuring this package again) — this is the one implementation every rotatable 3D object type currently shares.

#### generic.py

`Rings3D(Base3D)` — owns three per-axis `rotation_ring.RotationRing` gizmos and their pick/activate/drag/snap interaction: `pick` (which torus ring is under the mouse), `activate`/`deactivate` (show/hide a protractor, dim the other two), `begin_inner_drag`/`update_inner_drag`/`end_inner_drag` (free-rotation drag on the inner ring), `update_outer_hover`/`click_outer_snap` (hover-highlight + click-to-snap on the outer ring's ticks), `apply_drag_angle` (write a drag-driven Euler value without re-triggering itself). This is what `rotation_rings.RotationRings` (the facade) holds as its own `obj3d`. `Rings3D._on_obj_angle`/`_on_obj_scale` are bound callbacks on the tracked object — every ring's orientation/size is re-derived from the object's live state, not cached independently; don't introduce a second source of truth for "where is this gizmo right now." `_update_position` deliberately tracks gizmo position WITHOUT `Base3D`'s own world-space floor-lock logic (same pattern used by `drag_handlers.move_arrows.Arrows3D`/`wire_marker_arrow.ArrowMarker3D`) — a gizmo object following its tracked target is not subject to the same ground-plane constraints a real placed object is.
