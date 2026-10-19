## FILES

#### __init__.py

Package docstring only; no code. Notes this mirrors `add_handlers.editor_3d`'s own package shape (one module per object type), but only supports a subset: `housing`, `splice`, `terminal`, and `wire`. No `bundle`/`transition`/`bundle_layout`/`wire_layout`/`wire_service_loop` module exists here — those object types have no 2D schematic representation at all (see MEMORY.md "2D schematic scope": mechanical accessories and routing/grouping types are deliberately excluded from the wiring schematic).

#### housing.py

`Housing` — single-click placement, mirrors `add_handlers.editor_3d.housing.Housing` — floats freely across the schematic's own flat (Y=0) plane instead of the 3D camera's focal plane.

#### splice.py

`Splice` — wire-snapping placement. The actual wire-fork cut still goes through the wire's real 3D geometry (`handlers.wire_topology.split_wire_at_point`, same as the 3D editor's version) — the schematic click is mapped onto the wire's 3D chord by fractional arc-length along the wire's full 2D polyline. Also holds `closest_point_on_wire_2d`.

#### terminal.py

`Terminal` — cavity-pick placement. Unlike the 3D editor, a schematic terminal has no free position of its own to preview — its `position2d` is only computed once actually seated in a cavity — so nothing meaningfully follows the cursor before a cavity is picked; a click on any eligible empty cavity seats it immediately using the same male/female attach math 3D's Mode 1/2/3 already compute (reused directly).

#### wire.py

`Wire` — interactive placement, ported from `handlers.wire_handler_2d.AddWireHandler2D`. Every session starts pinned to a Terminal or Splice; the user draws the wire PCB-editor style — each left click places an orthogonal (H/V-only) waypoint, hovering a terminal/splice previews the full auto-routed path to it, and a left click on one ends the wire there with the auto-router laying out the rest. A terminal's mandatory exit stub is placed automatically as the first waypoint. Waypoint placement enforces strict orthogonality and blocks a segment that would cut through a housing/splice/note or run parallel too close to another wire — shown as a message at the cursor with the click ignored, rather than a hard error.
