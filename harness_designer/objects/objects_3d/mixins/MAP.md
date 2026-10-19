## FILES

#### __init__.py

Package init for the per-view (3D) wire-type mixin. CODEBASE_MAP.md also lists `angle`/`move` mixins in this directory — neither exists on disk; see the drift note in `objects/MAP.md`.

#### wire_type.py

`WireTypeMixin(objects.mixins.wire.WireTypeMixin)` — 3D-specific overrides: `_waypoints` (project-db row lookup), `_closest_point_on_segment_to_ray` (ray-vs-segment, for 3D mouse picking), `_point_on_wire`. Mixed into `objects_3d/wire.py`'s `Wire` and related wire-family 3D views. Shares its bare class name `WireTypeMixin` with the base in `objects/mixins/wire.py` and the peg-board version in `objects_pegboard/mixins.py` — a plain-text search for `WireTypeMixin` returns three unrelated-looking definitions; use `dep_trace.py --overrides --name WireTypeMixin` to see the real inheritance chain instead.
