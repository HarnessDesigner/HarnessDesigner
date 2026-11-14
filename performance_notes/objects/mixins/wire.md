# harness_designer/objects/mixins/wire.py

`WireTypeMixin` (the shared wire-path helpers: closest point, end anchors). Six methods, no loops or allocations flagged by the AST pass; each is called per hover during wire placement through the picker, and the cost is the NumPy segment projection already described in `add_handlers/editor_pegboard/wire_layout.md` (`closest_point_on_chain` is the Python-loop version of the same idea). Nothing specific to change here.
