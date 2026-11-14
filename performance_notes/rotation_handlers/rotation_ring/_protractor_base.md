# harness_designer/rotation_handlers/rotation_ring/_protractor_base.py

How it works: the module docstring of `_protractor_base.py` (the ring is built once in its own frame and moved by one rotation); this note is the cost and what is left.

## Done 2026-11-14: a protractor ring is one washer VBO, one tick VBO, array-placed labels and array pick boxes
Measured with the real classes, interpreted Python 3.11, offscreen GL, one inner ring (360 ticks, 36 labels, washer), before -> after. The inner and the outer ring are both drawn while an axis is active, so a frame with the gizmo open pays the draw figure twice.

| What | Before | After |
|---|---|---|
| draw one ring, 3D view (CPU submit; the GPU is idle either way) | 11.99 ms | 0.70 ms |
| draw one ring, 2D views (no camera, `TOP_DOWN_TILT`) | 25.27 ms | 0.58 ms |
| the object turns (`reposition_all`), 3D | 91.4 ms | 1.9 ms |
| the object turns, 2D views | 84.2 ms | 1.8 ms |
| camera moves (3 coordinate writes, so 3 label updates), 3D | 22.2 ms | 0.94 ms |
| build a ring | 269 ms | 35 ms |
| pick the tick under the mouse (outer ring) | 16 ms (the per-box ray loop alone) | 0.15 ms |

The old reposition was 95% `Angle.from_direction` (360 calls at 0.34 ms: the `Decimal` quaternion normalise and `as_matrix`), the old draw 397 `VBOHandlerBase.render` calls at about 30 us (three uniform writes through `Point.as_float` / `float(str(v))`, two `Decimal` constructions per `Point`), the old camera move 36 `Angle.from_matrix` per update (0.2 ms each), and the 2D draw also composed `local_tilt + angle` in `Decimal` for every label on every frame. All of that is gone: there is no `Point` or `Angle` per tick, the ticks are one mesh drawn with the ring's rotation, the labels are placed by `geometry.batch` array calls, and the draws take plain floats (`VBOHandlerBase.render_raw`).

Pixels: five rendered frames (3D with the object turned, the centre moved and the camera moved; the 2D top-down view with the tilt) compared with the old code's: no pixel differs by more than 32 levels, although the ticks are now 8-sided prisms (about 0.6 MB of vertices per ring) rather than the shared 360-sided cylinder (about 28 MB if 360 of them had been merged). Picks: the array slab test agrees with `gl.object_picker._ray_intersect_obb` on every box tried (60 random rays), a ray through a tick's centre picks that tick (237 of 240; the other 3 pick a neighbour whose box the ray crosses first at a grazing view angle), the pick box centres match the tick meshes to 3e-6 mm. The batch helpers agree with `Angle.from_matrix`, `Angle.from_direction` and `Point @ Angle` to better than 1e-6. Scripts: `D:\harness_designer_tmp\scripts\gizmo_compare.py`, `check_ring_new.py`.

## What a ring still costs
- **A frame: 38 draws** (washer, tick mesh, 36 labels, plus two more draws while a tick is hovered), about 18 us of Python each. The 36 labels are almost all of the 0.70 ms.
- **An angle change: 1.9 ms**, mostly `_disc_rotation()` (a `Decimal` quaternion built from the object's Euler angles, 0.7 ms; it is called once per change, not per frame) and the matrix and quaternion read off it (`Angle.as_matrix_numpy`, `as_quat_numpy`). A NumPy version of `_disc_rotation` (the matrices it multiplies are already NumPy) would take it to a few tens of microseconds; the ring's matrix could then also skip the `Angle` round trip.
- **Labels in the vertex shader (not done):** a throwaway prototype (`proto_gizmo_shader.py`, a patched scratch copy of `faces/vertex.vert`) billboarded the 36 labels in the shader from the label anchor and the camera position, pixel-identical to the CPU billboard (max channel difference 0 over 15,681 drawn pixels). It would take the camera-move cost to nothing and, if the 36 label meshes were merged with a per-vertex label index, remove the 36 draws too (a shared-shader change, so the ordinary mesh path would have to be compared with the committed shaders afterwards). The CPU array version costs 0.31 ms per camera update, so this is only worth it if the label draws show up in the compiled build's profile.

## Line 106-200 (`__init__`, `set_radii`, `delete`) -- set-up and teardown
Builds the washer VBO, the tick VBO, the 36 `Text` labels (their word meshes are pooled VBOs) and the arrays; releases both buffers on delete. Runs when the rings open and close, and `set_radii` (rebuild both meshes and the derived arrays) when the object is resized.

## Line 750-759 (`_get_label_color`, `_set_solid_color`) -- colour set-up
Chooses the label and solid colours. Cheap; `_set_solid_color` writes two uniforms and runs two or three times per frame.
