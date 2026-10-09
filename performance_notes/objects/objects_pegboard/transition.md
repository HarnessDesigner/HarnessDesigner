# harness_designer/objects/objects_pegboard/transition.py

## Line 274-288 (`_PegBranch.render`) — per-frame VBO lookup and up to four draws per branch
`_cylinder.create_vbo()` and `_sphere.create_vbo()` are cached lookups, so the lookup itself is cheap. The cost is the draw count: one cylinder, plus a bulb cylinder and up to two spheres when the branch has a bulb. `_use_body_model` skips the duplicate draw when a shared body mesh already covers the branch, which is the right optimization.

## Line 638-... (`_PegBody.render`) and 772 (`Transition._render_geometry`) — one shared body draw per transition
Passes the material and branch materials into one VBO render per transition. Same shape as the 3D transition.

## Line 791-830 (`hit_test_branch`, `hit_test_branch_ray`) — per mouse event while a drag is armed
Sphere tests per branch, a few branches per transition. Cheap per call.
