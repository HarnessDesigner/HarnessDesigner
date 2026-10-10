# harness_designer/rotation_handlers/rotation_ring/__init__.py

## Line 1-464 (`RotationRing`) — one ring: inner, outer and torus parts
Builds the ring's inner (drag) and outer (protractor) parts and its torus. `render` draws the parts each frame; `pick` and the hover paths run a ray test per mouse move. Creating the ring builds its geometry once; the per-frame cost is the draw calls.

**Typing (fixed in this pass):** `parent`, `context`, `camera` and `material` are typed; `delete` returns `None`; the rings take the GL context and camera.
