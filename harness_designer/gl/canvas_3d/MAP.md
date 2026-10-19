## FILES

#### __init__.py

`from . import canvas_window as _canvas_window` — the package's construction entry point, same
pattern `canvas_schematic/`/`canvas_pegboard/` use.

#### axis_overlay.py

`Overlay(QtWidgets.QWidget)` — a screen-space compass/axis-orientation gizmo drawn over the 3D
canvas (cylinder/sphere `shapes` primitives, raw `GLU`, driven by the camera's current angle),
configured via `Config.editor_3d.axis_overlay`. Optional: `CanvasWindow` only constructs one when
built with `axis_overlay=True`.

#### camera.py

`Camera(CameraBase)` — the free-orbit 3D camera. `Reset()` extends `CameraBase.Reset()` via
`super()` to also pin the eye's Z back to 75.0. `MoveRigTo(eye_position)` rigidly translates the
eye and focal point together (the same paired-write mechanics `CenterOn`/`Dolly` use — a single
`_updating_rig` guard suppresses the duplicate `_update_camera` recompute on the first of the two
writes) and, like every other camera-movement method, ends by calling `_send_event` — the
deliberate universal extension point (`CameraBase._send_event`, confirmed by the user 2026-08-05)
every movement method (`Reset`/`Rotate`/`PanTilt`/`Zoom`/`Walk`/`Dolly`/`TruckPedestal`/`CenterOn`)
funnels through, so any future "react to the camera moving, however it moved" need should hook
`_send_event`/`_refresh_active_hover` there instead of adding a call to every individual movement
method. This module also defines `build_lookat_matrix()`, a pure-numpy `gluLookAt` equivalent kept
here (not in `canvas.py`, which calls it as part of its own `_set_view()`) specifically so
`Camera.set()` can reuse the same function.

#### canvas.py

`Canvas(CanvasBase)` — the 3D GL surface itself. `FOV_DEGREES = 65.0` is a deliberate module-level
constant (not buried in a method) so anything that has to reason about what the camera can see
(e.g. `CanvasWindowBase.request_fit_all`'s fit-to-project math) uses the exact same value the
renderer's own `_build_perspective_matrix()` does. Owns construction of `Floor`/`Camera`/
`Headlight`/`MouseHandler`/`AxisOverlay` and extends `CanvasBase.__init__` via `super()`.

#### canvas_window.py

`CanvasWindow(CanvasWindowBase)` — thin outer wrapper; builds the inner fixed-size `Canvas` before
calling `super().__init__()`, and optionally attaches the `axis_overlay.Overlay` widget when
constructed with `axis_overlay=True`.

#### floor.py

`Floor(FloorBase)` — fully shadows `FloorBase.render()` (does not call `super()`) with the 3D
procedural floor: checkerboard tiles plus major solid/minor dashed lines, computed entirely inside
one fragment shader via screen-space derivatives (`fwidth`) rather than relying on thin rasterized
line geometry — avoids the orientation-dependent moiré that approach produces.

#### focal_target.py

`FocalTarget(ObjectBase)` — the camera's look-at point, rendered as a real scene object.
Deliberately subclasses `ObjectBase` directly rather than `objects.generic.Generic`, since that
class's `__init__` unconditionally builds a placeholder `objects_3d.generic.Generic` with no
vbo/angle/position/scale/material and can never actually succeed as written — instead it builds
its own real `objschematic`/`obj3d`/`objpegboard` children directly, the same shape
`objects.housing.Housing` uses. Because it owns slots in all three bounds pools, `Canvas`'s
`delete_focal_target()`/`create_focal_target()` must bracket any `bounds_manager.reset()` call —
resetting while it still exists leaves it with dead slot indices and raises `IndexError` in
`mark_visible` (see MEMORY.md "Stored project bounds + fit-to-project camera").

#### headlight.py

`Headlight` — always targets `shaders.faces` (`FacesProgram` is the one program that owns the
headlight spotlight uniforms: `headlight_position`/`direction`/`diffuse`/`diameter`/`enabled`).
Binds to the camera's `position`/`focal_position` points so `light_direction` is recomputed on
every camera move to keep pointing from eye to focal target; `set()` pushes the uniforms under
`with self.canvas.context: with program: ...`.

#### mouse_handler.py

`MouseHandler(MouseHandlerBase)` — the entire 3D-specific override is one static method,
`_get_view_object`, returning `obj.obj3d`. Every other mouse behavior (dispatch to
`CanvasBase.active_handler_obj`, selection, camera drag, wheel easing) is inherited unchanged from
the shared `canvas_base.mouse_handler_base.MouseHandlerBase`.
