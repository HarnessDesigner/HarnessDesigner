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

(2026-11-08) `_draw_scene` starts a frame of `gl/wire_batch.py` (`BATCH.begin()`), flushes it after the main object loop (`_flush_wire_batch`: every wire that is not the selected object, in one draw) and again at the end (a selected wire), then `BATCH.end()`; every wire, cable and bundle of the view hands itself in (`objects/mixins/tube.py`).

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
treated as superseded by this entry, not re-verified line-for-line. `_draw_scene` and `_render_selected_overlay` skip a selected object that has no view in that canvas, and `_report_view_less_selection` reports it once per canvas and object class, instead of dereferencing `None` (an exception escaping `paintGL` aborts the whole process in this PySide6 build; a selected circuit used to do exactly that, fixed 2026-10-25 by giving circuits placeholder views, with this guard as the safety net). Every selectable object needs a view in every canvas: `MouseHandlerBase.on_left_up` deselects through `canvas.get_selected()`, so a canvas that ignored a view-less selection would never deselect it (and a circuit's highlight would stay on).

#### canvas_window_base.py

`CanvasWindowBase` — the shared outer-window wrapper each editor's `CanvasWindow` extends via
`super().__init__()`. Owns the fixed "virtual size" behavior that makes a plain `resizeEvent` only
`move()` the already-rendered, fixed-size inner canvas to recenter it, never touching the
camera/viewport/projection — a deliberate fix (see this file's DESIGN NOTES "Canvas render surface is a fixed
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

## DESIGN NOTES

Lasting rules and design notes moved here from the repo-root `MEMORY.md` on 2026-11-01 and trimmed the
same day: bug-fix narratives were dropped (git history has them), keeping only what still constrains
the code. Point-in-time -- verify claims against the current code before relying on them.



#### Canvas design decisions (2026-08-12; the old `canvas2d`/`new_canvas2d`/`new_canvas_base` names are gone, now `canvas_base/`, `canvas_3d/`, `canvas_schematic/`, `canvas_pegboard/`)
- **Shared base, with abstract hooks where views differ.** The schematic and peg-board canvases render through the real 3D pipeline with a locked orthographic camera looking down world Y; the 2D shader survives only for the grid. Methods that must differ between locked-2D and free-orbit 3D are abstract in the base (`CameraBase._calculate_camera/Rotate/PanTilt/Walk`, `CanvasBase._get_view_object`, which tells `_draw_scene`/`add_object` whether to use `.obj3d` or `.objschematic`/`.objpegboard`); genuinely identical ones (`Zoom`, `TruckPedestal`, `CenterOn`, `ProjectPoint/UnprojectPoint`, `closest_point`) stay concrete. Sort new shared behaviour into one of those two buckets rather than defaulting to concrete. The faces/edges/vertices shader programs are shared by all views (they consume only generic camera uniforms); the floor/grid shader is the exception (`FloorBase` is an abstract shell). The goal is for all canvases' public APIs to be almost identical.
- **Config-null gating (user's pattern):** `Config` has the three editors as separate top-level classes, each with an `input` section with identical attribute names (`rotate`, `pan_tilt`, `truck_pedestal`, `walk`, `zoom`, `reset`, ...). A feature an editor does not support is a plain class WITHOUT the `ConfigDB` metaclass with every value `None`, and handlers check `if rot is not None:`. Use this for capability gating in key/mouse handlers instead of per-editor subclassing. Where mechanics genuinely differ (drag/rotation), each view subclasses a drag/rotation base with an overridable `__call__` that returns True if it handled the interaction and False otherwise; the mouse handler just calls it and falls back on False.
- **One shared culling pool.** Always go through `gl.culling.cull(...)`/`shutdown()` (a `sys.modules` replacement backing one `CullingThreadPool()` built at import); never instantiate a pool per canvas (canvas updates are serial on the main thread, so extra pools only add worker threads). `gl/object_picker.py`'s `find_object()` is the one shared, camera-agnostic picker (duck-typed on `camera.modelview/.projection/.viewport` with a required `get_view` callable); keep it that way. The peg-board mouse handler's own `_find_anchor_at_point` AABB hit test was the one remaining gap and may be stale.
- **Fixed virtual canvas size; a window resize never touches the camera.** Every canvas has a fixed virtual render size (`self.size`, `_virtual_w/_virtual_h`, changed only by an explicit `set_virtual_size()` such as `Canvas3D.set_virtual_size`), deliberately larger than any window (`part_orientation.py` uses 1600x900). The outer container's `resizeEvent` only `move()`s the inner GL widget to re-centre it and lets Qt clip; it never calls `notify_virtual_size_changed`, touches the viewport, or marks the camera dirty. Rejected earlier: adjusting FOV to the window (empty bars, and a visible left/right shake while dragging the window edge) and stretching the viewport to fill (aspect distortion). Side benefit: Qt recomposites the existing framebuffer, so resizing needs no GL redraw. Do not treat "the camera ignores a plain window resize" as a bug, and do not add a dirty flag there; for a real resolution change use `set_virtual_size()` (-> `notify_virtual_size_changed()` -> `glViewport` -> `update()`; not verified whether it marks the camera dirty). Anything that frames the view must fit the VISIBLE window crop, not the virtual canvas.

#### Stored project bounds + fit-to-project camera (built 2026-09-23)
The `projects` table has nullable TEXT columns `bounds_3d`, `bounds_schematic`, `bounds_pegboard` holding `[[min x,y,z],[max x,y,z]]` (exposed as `Project.bounds_*`; `None` = never saved); read at load, written at unload.
- **Lifecycle (user-specified order):** `MainFrame.unload()` tears objects down, deletes the 3D focal target, then `_save_project_bounds()` (each view's `bounds_manager.<view>.aabb.extent()`) LAST, then `bounds_manager.reset()`, then `gc.collect()`. App close runs `closeEvent` -> `if self._project is not None: self.unload()` first (check `_project`, never the `project` property, which opens the load dialog). `Project.__init__` recreates the focal target and calls `request_fit_all(stored_bounds)` on each editor BEFORE objects load; a view with no stored bounds is fitted from the loaded objects at the end of load.
- **Why reset and recreate the focal target:** unload never calls `ObjectBase.delete()`, so pool slots are never released and must be reset. `FocalTarget` owns slots in all three pools; a reset while it exists leaves dead slot indices (`IndexError` in `mark_visible`), hence `Canvas.delete_focal_target()`/`create_focal_target()` around it. `ArrayPool.reset()` drops storage in place (the pool and View objects stay the same because canvases hold references).
- **Fit (`CanvasWindowBase.request_fit_all`):** waits until the tab is visible with a real size (a hidden tab has a placeholder size and `required_zoom_scale` returns 1.0 hidden: the "zoomed way out at startup" bug), pads 15% of the extent per side, re-fits on resize until the user touches the camera (`_camera_state()` comparison). 2D: `distance = 1000 * extent/pixels`, recentre. 3D (perspective, `FOV_DEGREES` = 65 in `canvas_3d/canvas.py`): keeps viewing direction and eye-to-focal distance and moves the whole rig (`Camera.MoveRigTo`), centred on the box and backed off until all 8 corners fit, so the focal point can end up far from the project. `center_on_object` no-ops while `is_fit_active`.
- **User input during load:** a load pumps the event loop, so the user can orbit/zoom. `CanvasEventFilter` sets `CanvasBase._user_input_seen` on any mouse press/double-click or wheel turn; `Project.__init__` calls `editor.clear_user_input()` right after `create_focal_target()`, and `_try_fit_all` drops the request if the flag is set. `Project.__init__` ends with `Refresh()` on all three editors.
- **Schematic repaint gotcha:** `CanvasBase.add_object` calls `Refresh()` inside `with self:`, which treats it as batching (a no-op). 3D/pegboard repaint during load via their `_set_model()` refreshes; schematic has no model step, so `canvas_schematic.Canvas.add_object` calls `self.Refresh()` itself after registering.
