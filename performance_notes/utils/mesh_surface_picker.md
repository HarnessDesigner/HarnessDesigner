# harness_designer/utils/mesh_surface_picker.py

## Line 58-91 (`_points_in_triangles`) — vectorised over every triangle
The function docstring says it is evaluated for every triangle in one shot instead of a Python loop. Good: the test runs as NumPy arrays over all triangles at once.

## Line 92-194 (`MeshSurfacePicker.__init__`) — copies the mesh and the transform caches
Copies the vertex and normal arrays to float64 (lines 184-186), and builds the transform caches. Runs when a picker is created for an object. Cost is linear in the mesh size, once per picker.

## Line 195-227 (`_refresh_transform_cache`, `_on_position`, `_on_angle`, `_on_scale`) — rebuilt on every transform change
The three `_on_*` handlers are bound to the object's position, angle and scale. A drag fires them many times per second, and each one calls the cache refresh. The refresh rebuilds the rotation and inverse-rotation matrices and the position and scale arrays. This is per-move work proportional to the small transform, not the mesh, so it is cheap. It is still avoidable: the matrices could be built lazily when a pick happens.

## Line 228-288 (`update_vbo`) — re-copies the mesh when the VBO changes
Copies the vertex and normal arrays again (lines 273-274). Runs when the underlying VBO changes, not on every move. Fine.

## Line 289-end (`_weld_vertices`) — vertex welding
Merges duplicate vertices so surfaces can be found across face seams. Runs once when the surfaces are built. Its cost depends on the mesh size; not verified in detail here.
