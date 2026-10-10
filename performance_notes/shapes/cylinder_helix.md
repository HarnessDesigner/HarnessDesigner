# harness_designer/shapes/cylinder_helix.py

## Line 57-143 (`_stripe_profile`, `_straight_stripe`, `_loop_stripe_guide`, `_loop_stripe`) — build123d sweeps per stripe
Builds the stripe geometry with build123d (a face, a sweep along a spline path, and so on). Each call is an OCCT operation, which is comparatively slow. These run once per mesh build.

## Line 164-283 (`create_vbo`, `create_stripe_vbo`) — VBO creation and caching
Build the helix mesh and its stripe mesh and wrap them in VBO handlers. The results are reused through the VBO layer, so the OCCT work is paid once per process.

**Typing (fixed in this pass):** the sweep helpers return the build123d types (`Face`, `Shape`, `Edge`); the VBO builders return `VBOHandlerBase`.
