## FILES

#### __init__.py

Package init for the view-agnostic wrapper-level mixins, shared across `objects/<type>.py` modules (not the per-view `objects_3d`/`objects_schematic`/`objects_pegboard` renderables — see those packages' own mixins for the per-view wire mixins).

#### wire.py

`WireTypeMixin` — the view-agnostic base of the wire-type mixin hierarchy: `_waypoints`, `_point_on_wire`, `_endpoint_diameter`, `_segments`, `get_closest_point`, `get_closest_endpoint`. `objects_3d/mixins/wire_type.py`'s `WireTypeMixin` and `objects_pegboard/mixins.py`'s `WireTypeMixin` both subclass this one and override `_waypoints`/`_point_on_wire`/`_segments` with view-specific geometry (ray-vs-segment for 3D, 2D xz-plane closest-point for peg-board); there is no schematic counterpart (`objects_schematic/mixins/` is empty). Two unrelated classes in this codebase share the bare name `WireTypeMixin` (this one, plus the 3D and peg-board subclasses) — not a bug, just worth knowing before grepping by name; `dep_trace.py --calls`/`--overrides` resolves them correctly since it builds a real class hierarchy, but a plain-text search returns three unrelated-looking hits.
