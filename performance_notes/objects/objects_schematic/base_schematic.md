# harness_designer/objects/objects_schematic/base_schematic.py

## Line 35-46 (`box_hit_test`) — function-level import executed on every hit test
`from ...gl import object_picker as _object_picker` (line 43) runs on every call. It is a cycle-avoidance import, so it has to stay somewhere, but Python still performs the import lookup on each call. `box_hit_test` is called per label per mouse-hit test, so on a canvas with many labels this adds up. The cleanest fix is a module-level lazy holder (set once on first call) instead of a per-call import statement.

## Line 161-... (`BaseSchematic.handle_interaction`) — per mouse event, default path
Returns False by default. The subclasses that override it (Housing, Splice, Terminal, Wire, WireMarker) either call `super()` or fully shadow it (see the `--overrides` output: Wire and WireMarker shadow it entirely). No hot cost in the base itself; the cost is whatever each override does per mouse move.

## Inherited render path
`BaseSchematic` inherits `BaseVar.render`, so every schematic object pays the per-object `with shaders.*:` churn and material upload described in `performance_notes/objects/objectsvar/base_var.md`.
