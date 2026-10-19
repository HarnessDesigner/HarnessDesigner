## FILES

#### __init__.py

Package docstring only; no code. Notes this mirrors `add_handlers.editor_3d`'s own package shape (one module per object type), but the pegboard view only ever supports placing a Housing, a Wire, and waypoints on each — see `ui.toolbar.toolbar.VIEW_MODE_IDS`.

#### bundle_layout.py

`BundleLayout` — bundle's waypoint-placement counterpart, mirrors `wire_layout.py`; started from a bundle's own "Add Waypoint" action. Also holds `create_bundle_layout_on_bundle_pegboard`. Bundles have no dedicated `add_handlers.editor_pegboard` module of their own beyond this waypoint case — a bundle itself is placed only via the 3D editor (`add_handlers.editor_3d.bundle`) and seeded into peg-board afterward; see that module's `_seed_pegboard`.

#### housing.py

`Housing` — single-click placement, mirrors `add_handlers.editor_3d.housing.Housing`/`editor_schematic.housing.Housing` — floats freely, following the cursor across the pegboard's own permanently top-down X/Z plane until the first non-drag click locks it in.

#### wire.py

`Wire` — two-click placement, deliberately simpler than `editor_3d.wire`: no snap-probe spheres or ambient highlighting, no merging onto an existing wire's open end or mid-span — a click only ever resolves to a terminal, a splice, or empty board space. Extension mode and waypoint continuation ("Add to Wire") ARE supported (2026-10-12), both only ever operating on a genuinely free end. The real 3D connection is made the moment each end resolves to a terminal/splice (not deferred), because the 3D view is the one source of truth for real length — `handlers.wire_slack.reconcile` then bows whichever view's straight-line path came up short once both ends exist. The free/unconnected end never needs special-case Y handling to stay flat — the locked top-down camera's own mouse-to-world conversion always returns `y=0.0`, and nothing else in the peg-board view ever sets Y to anything else. Terminals/splices have no dedicated module of their own here beyond this file's click-resolution logic.

#### wire_layout.py

`WireLayout` — interactive waypoint placement, mirrors `editor_3d.wire_layout`, started from a wire's "Add Waypoint" context-menu action (plain click-drag on a wire's own strand already does segment-dragging, so this is reached only through the menu, never a bare click). Also holds `closest_point_on_chain`, `segment_insertion_index`, `create_wire_layout_on_wire_pegboard`.
