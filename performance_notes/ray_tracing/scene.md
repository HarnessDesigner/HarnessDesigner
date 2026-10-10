# harness_designer/ray_tracing/scene.py

## Line 50-58 (`Scene.add_object`) — list append
Adds the object to a list. Cheap.

## Line 59-88 (`load_environment_map`, `generate_environment`) — image work on demand
Loads or generates the environment image for the sky. Runs when a render is set up, not per frame.

## Line 89-end (`Scene.build`) — flattens every object into arrays
Loops over every object (line 104) and copies its vertices, faces, normals, position, rotation and material into per-object arrays before building the BVH and light arrays. Cost is linear in the total mesh size, once per render. The `astype` calls copy each array; for a large scene, building the arrays once in the target dtype would avoid the copies.

**Typing (fixed in this pass):** `Scene.add_object` takes a `SceneObject` protocol, which describes the attributes `build` reads (vertices, faces, normals, position, angle, material). `build` returns an eight-tuple of arrays.

**Import path (fixed in this pass):** the `TYPE_CHECKING` import referred to `..gl.canvas3d`, which does not exist; it is now `..gl.canvas_3d`.
