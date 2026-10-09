# harness_designer/objects/objects_3d/project_model.py

## Line 56-58 (`ProjectModel.render`) — pass-through override, one full render per frame
`render` only calls `super().render(shaders)`, so it adds nothing beyond the
base `BaseVar.render` cost described in `base_3d.md`. The object is a single
10 x 10 x 10 mesh, so the base cost is one object's worth per frame. No change
recommended. The override can be removed if it is not needed for a reason
other than the base call (it is not, as written).
