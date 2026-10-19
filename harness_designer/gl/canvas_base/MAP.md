## FILES

#### __init__.py

Empty of local imports — marks the package only. `canvas_3d`/`canvas_schematic`/`canvas_pegboard`
each import the modules below directly (e.g. `from ..canvas_base import camera_base as ...`);
there is no `canvas_window`-style re-export here since this package has no "CanvasWindow" concept
of its own, only the `*Base` classes each editor's own window class extends.

#### camera_base.py

`CameraBase` — the shared camera engine for all three editors. Splits behavior into genuinely
per-view-type pieces left abstract (`zoom_at_point` here; `_calculate_camera`/`Rotate`/`PanTilt`/
`Walk` are also abstract, implemented separately by each editor's locked-orthographic-vs-free-orbit
`Camera`) versus behavior that's truly view-agnostic and kept concrete (`Zoom`, `TruckPedestal`,
`CenterOn`, `Dolly`, `ProjectPoint`/`UnprojectPoint`). Owns `_send_event`/`_refresh_active_hover` —
called at the end of every movement method so any future "the camera just moved, no matter what
caused it" behavior has one hook instead of a matching call scattered across every input path;
built to fix a real gap where an active wire-placement preview or snapped drag kept reflecting a
stale camera framing after a mouse-wheel zoom or a held-key camera move that never touched
`on_mouse_motion`. A "move the whole rig" pair (`_position`+`_focal_position`, both bound to
`_update_camera`) uses an explicit `_updating_rig` flag to suppress the redundant recompute on the
first of the two writes — deliberately NOT done by wrapping the first write in
`with self._position:`, since `CallbackMixin`'s own batching guard would then silently drop every
*other* callback bound to `_position` too, not just this class's internal one (a real regression
once something else, `shapes.text`'s camera-tracking update, started depending on that write
firing). A stray comment in this file still says "new_canvas2d is dedicated to the flat
schematic/pegboard views" — leftover wording from before the `new_canvas2d`→`canvas_schematic`
rename; harmless, but a sign the rename was mechanical rather than a full re-read of every comment.

#### canvas_base.py

`CanvasBase(QOpenGLWidget)` — the shared canvas lifecycle/render pipeline all three editors
subclass (ported from a prior wx `GLCanvas`; the class docstring still carries the full wx→Qt
mapping table). Declares the per-subclass construction contract as class-level `None` placeholders
each concrete `Canvas` is expected to fill (`_mouse_handler`, `camera`, `_editor_name`, `_floor`,
`bounds_manager`) and builds every genuinely shared piece directly in `__init__`
(`shaders.ShaderProgram`, the shared `culling.cull(...)` singleton, `camera_base`, `floor_base`,
`key_handler`, `scene_light`, `mouse_handler_base`). Drag/rotation dispatch is NOT wired up here
via a `_drag_handler: DragHandlerBase`/`_rotation_handler: RotationHandlerBase` attribute pair the
way an earlier (2026-08-17) design note describes — current source instead tracks one
`active_handler_obj` and routes mouse events to it through `MouseHandlerBase.
_dispatch_to_active_handler`; the real per-object-type interaction behavior now lives directly on
the view objects (`obj.obj3d`/`.objschematic`/`.objpegboard`, see
`objectsvar.base_var.BaseVar.handle_interaction`) and in the top-level `drag_handlers/` package,
not as a `CanvasBase`-declared handler-class hierarchy — MEMORY.md's note describing those two
specific attributes at this file's old line 342-343 no longer matches current source and should be
treated as superseded by this entry, not re-verified line-for-line.

#### canvas_window_base.py

`CanvasWindowBase` — the shared outer-window wrapper each editor's `CanvasWindow` extends via
`super().__init__()`. Owns the fixed "virtual size" behavior that makes a plain `resizeEvent` only
`move()` the already-rendered, fixed-size inner canvas to recenter it, never touching the
camera/viewport/projection — a deliberate fix (see MEMORY.md "Canvas render surface is a fixed
virtual size") for ugly letterboxing from FOV-recompute and a visible resize "shake" that were both
tried and rejected before landing on this fixed-oversized-canvas-plus-clipping design. Also owns
`request_fit_all`, which waits for a visible tab with a real (non-placeholder) size before
computing the fit, since `required_zoom_scale` returns a meaningless 1.0 while hidden.

#### floor_base.py

`FloorBase` — an almost-empty abstract shell (`_initialize_grid`/`set`/`render` all
`raise NotImplementedError`), deliberately the one piece NOT unified across editors even though
the three main render shaders (faces/edges/vertices) are otherwise identical once driven off the
same camera-base split: floor/grid rendering genuinely differs per editor (3D: checkerboard tiles
+ lines; schematic/pegboard: a procedural dot grid — and even those two turned out byte-identical
to each other, see `canvas_pegboard/floor.py`'s own note). `__init__` takes no program argument;
`render()` takes the per-canvas `ShaderProgram` singleton itself and each concrete subclass picks
out its own fixed program (`.floor` vs `.grid`).

#### interaction.py

`MouseInteraction(enum.Enum)` — a small, dispatch-specific enum (`MOVE`/`LEFT_DOWN`/`LEFT_UP`/
`LEFT_DCLICK`/`RIGHT_DOWN`/`RIGHT_UP`/`MIDDLE_DOWN`/`MIDDLE_UP`/`CANCEL`) passed to
`BaseVar.handle_interaction`. Deliberately distinct from `gl.events`' `EVT_GL_*` string constants,
which also cover camera-movement and plain object-selection events that have nothing to do with an
armed add/drag/rotation handler.

#### key_handler.py

`KeyHandler` — the editor-agnostic held-key repeat engine. Spawns one daemon `threading.Thread`
running `_key_loop` per canvas; `KEY_MULTIPLES` normalizes numpad/shifted/punctuation key variants
to one canonical keycode. `clear_keys()` is called when a canvas loses keyboard focus.
`handle_event()` short-circuits one hardcoded diagnostic shortcut (Ctrl+Shift+D →
`canvas._dump_visible_objects()`) before any held-key tracking runs. Every movement type
(`rotate`/`pan_tilt`/`truck_pedestal`/`walk`/`zoom`/`reset`) is read straight off `self.config` and
simply skipped when `None` — the "config-null-gating" pattern that is *why* this file came out
100% byte-identical between the old `canvas3d`/`new_canvas2d` split before any explicit
unification plan even existed, and the template the user intends to extend to mouse handling next
(`Config` is being restructured so every editor's `input` sub-config shares identical attribute
names, with unsupported features set to a plain non-`ConfigDB` class full of `None`s rather than
omitted).

#### mouse_handler_base.py

`MouseHandlerBase` — the shared, editor-agnostic Qt mouse-event dispatcher; every editor's
`MouseHandler` extends it by overriding only `_get_view_object` (maps an `ObjectBase` to its
editor-specific view child: `.obj3d`/`.objschematic`/`.objpegboard`). Per its own module
docstring, every add/drag/rotation handler now lives directly on the relevant view-object instance
rather than as a separate Qt-signal listener reacting from outside; `CanvasBase.active_handler_obj`
tracks which one (if any) is currently armed, and `_dispatch_to_active_handler` routes every
button/motion event there first — called at the top of each `on_*` handler below, before any of
this class's own default click/drag/selection logic runs — with a `True` return meaning the event
was fully consumed. Also implements physically-motivated mouse-wheel easing
(`_WHEEL_TICK_MS`=16ms/`_WHEEL_EASE_RATIO`=0.35/`_WHEEL_MAX_PENDING`=2.0/`_WHEEL_IDLE_MS`=500): a
hardware wheel notch is one discrete step with nothing to interpolate between notches on its own,
so each notch's contribution is eased in over several ~60Hz ticks instead of applied instantly, with
a capped pending-distance buffer and an idle watchdog so a fast scroll burst can't leave the camera
visibly "coasting" well after the user stopped turning the wheel.

#### scene_light.py

`SceneLight` — always targets `shaders.faces`; pushes `light_position`/`light_ambient`/
`light_diffuse`/`light_specular` from `Config.*.lighting` every frame. Confirmed byte-for-byte
identical across what used to be the separate `canvas3d`/`new_canvas2d` packages (nothing in it is
actually editor-specific) — exactly the kind of fully-duplicated file the base-class effort was
built to absorb, and now lives here once instead of three times.
