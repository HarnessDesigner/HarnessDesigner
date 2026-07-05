
### `CODEBASE_MAP.md` Formatting
This file is read both by people (in a rendered markdown viewer) and by AI agents.
When adding or modifying entries, retain the general structure of the file:

- keep the bulleted-list style: 
  - one item per line
  - nested to mirror the directory hierarchy
- do not compress lists into comma-separated prose, even to save tokens — human readability comes first
- keep section ordering: 
  - package directories
  - dependencies
  - layer relationships/patterns

### `CODEBASE_MAP.md` Maintenance
**This file must be updated whenever the file structure changes.**
That includes:
- adding, removing, or renaming any `.py` file or directory
- converting a single-file module into a package (or vice versa)
- moving code between modules
- adding or removing third-party dependencies
- any change to layer relationships or architectural patterns

Keeping this file accurate is as important as keeping the code correct —
AI agents that work on this project depend on it to avoid re-exploring
the entire codebase from scratch every session.

# harness_designer codebase map

PySide6 (Qt) desktop app for designing wire harnesses. ~508 .py files. GUI toolkit is **PySide6**, with a wx-style `CallAfter` shim in `app.py`. OpenGL rendering for 2D/3D editors. Multi-process architecture for DB/model/image work. For release builds the project's Python code is converted to C extension modules and compiled, so hot numeric loops run much faster than the interpreted dev environment suggests.

Contents/structure of the `harness_designer/` package.

## `.`
- `app.py`: Qt application bootstrap
  - `App` class
  - splash + background loading + shutdown
  - `CallAfter()` (run callable on main thread)
- `config.py`: `Config` object 
  - app settings
  - database config under `Config.database`
  - `ConfigDB` metaclass persists settings to sqlite, but **only values changed 
    via a UI element get written** — untouched settings always follow the 
    class defaults in code, so editing a default in `config.py` propagates 
    to users who haven't customized it
- `resources.py`
- `color.py`
- `utils/`: utility helpers (layered package)
  - `paths.py`: `get_appdata()`, `get_documents()`
  - `remap.py`: `remap()` value range conversion
  - `wire_conversions.py`: AWG/mm²/diameter conversions
  - `snap_pool.py`: `SnapPool` (numpy-backed nearest-point lookup)
  - `ui_utils.py`: `HSizer()`, `IMAGE_FILE_WILDCARDS`, `MODEL_FILE_WILDCARDS`
  - `bounding_boxes.py`: `compute_aabb()`, `compute_obb()`, `adjust_aabb()`
  - `mesh_normals.py`: `compute_normals()`, `compute_smooth_normals()`, `compute_face_normals()`, `compute_face_indexes()`
  - `model_utils.py`: `compute_edges()`, `convert_model_to_mesh()`
- `app_mixins/`: application-level mixins
  - `callback_mixin.py`
- `debug.py`
- `monkey_patch.py`
- `splash.py`
- `critical_error_dialog.py`
- `__version__.py`

## database
- `config_db.py`
- `utils.py`
- `db_connectors/`:
  - `base.py`: (`BaseConnector` wrapping con+cursor)
  - `db_data.py`
  - `mysql_connector/`
    - `connector.py`
    - `settings_dialog.py`
    - `sql_table.py`
  - `sqlite_connector/`: same as `mysql_connector/`
- `global_db/`: shared parts-catalog tables, one file per entity
  - part entities:
    - housing
    - terminal
    - seal
    - seal_type
    - boot
    - cover
    - cpa_lock
    - cpa_lock_type
    - tpa_lock
    - splice
    - splice_types
    - wire
    - wire_marker
    - transition (+_branch)
    - cavity
    - cavity_lock
    - accessory
    - adhesive
    - bundle_cover
  - file/resource entities:
    - image
    - datasheet
    - cad
    - file_types
  - lookup tables:
    - color
    - material
    - manufacturer
    - gender
    - plating
    - series
    - family
    - shape
    - temperature
    - direction
    - protection
    - setting
  - `bases.py` (~1300 lines): table base class
  - `resource_state.py`: tracks resource sync state
  - `mixins/`: column mixins
    - part_number
    - manufacturer
    - color
    - dimension
    - image
    - model3d
    - compat_housings/seals/terminals
    - wire_size
  - `model3d.py`: 3D model storage (`Models3DTable`, `Model3D`)
  - `ip/`: IP rating tables
    - fluid
    - solid
    - supp
- `project_db/`: per-project tables, all prefixed `pjt_`
  - pjt_housing
  - pjt_wire
  - pjt_wire_marker
  - pjt_wire_service_loop
  - pjt_wire_layout
  - pjt_bundle
  - pjt_bundle_layout
  - pjt_concentric*
  - pjt_point2d
  - pjt_point3d
  - pjt_circuit
  - pjt_note
  - pjt_tpa_lock
  - pjt_bases.py (~1100 lines): base class
  - `project.py`: project table
  - `cleanup.py`
  - `mixins/`:
    - position2d/3d
    - angle2d/3d
    - scale3d
    - visible2d/3d
    - color
    - name
    - notes
    - part
    - smooth
    - start_stop_position2d
    - start_stop_position3d
- `create_database/`: one file per table containing seed/creation 
                      logic (mirrors global_db naming)
- `common_db/`
  - `callback.py`: DB callback plumbing
- `update_monitor/` — currently empty

## `process/` (multiprocessing)
- `manager.py`: keyring-backed credential management for DB monitor processes (HMAC handshake)
- `db_broker.py`: handles the database connections for the processes.
- `db_process.py`: database worker process
- `model_process.py`: 3D model processing worker
- `image_process.py`: image worker
- `clean_creds/win.py`: Windows credential cleanup

## `objects/` (scene objects rendered in editors)
- wrapper classes (`ObjectBase` in `object_base.py`): one wrapper per scene part
  holding `obj2d` + `obj3d` plus child wrappers (e.g. `objects/housing.py` `Housing`
  owns cavities, tpa/cpa locks, seal, cover, boot) and fanning select/delete/identify
  out to both views.
  - housing
  - terminal
  - wire
  - wire_layout
  - bundle
  - circuit
  - note
  - splice
  - transition
  - project_model
  - generic
- `objects3d/`: the actual renderable 3D views (constructed with `(parent=wrapper, db_obj=pjt entry)`)
  - one file per harness part (housing, terminal, wire, wire_layout, bundle, splice, transition, seal, boot, cover, tpa_lock, cpa_lock, note, wire_marker, project_model, generic)
  - `base3d.py` (~960 lines): base 3D object
  - `housing_cavity_picker.py`: cavity selection overlay
  - `menu_ops.py`: context-menu operations
  - `mixins/`:
    - angle
    - move
- `objects2d/`: same structure as `objects3d` except for 2D rendering
  - wire
  - wire_layout
  - project_model
  - generic
  - `base2d.py`: base 2D object

  

## `handlers/` (selection/interaction handlers, one per part type)
- `handler_base.py` (small, ~80 lines): base class
- `*_handler.py`:
  - bundle
  - bundle_layout
  - cover
  - cpa_lock
  - housing
  - note
  - seal
  - splice
  - terminal
  - tpa_lock
  - transition
  - wire
  - wire_layout
  - wire_service_loop

## `gl/` (OpenGL)
- `context.py`
- `vbo.py` (~750 lines, VBO pipeline) 
- `events.py` 
- `info.py`
- `canvas2d/`: 
  - camera 
  - canvas 
  - grid
  - dragging
  - key/mouse handlers 
  - object_picker
- `canvas3d/`: same as `canvas2d` plus
  - arcball (dormant — replaced by rotation_rings; pending decision to expose as option or remove)
  - axis_overlay
  - floor
  - focal_target
  - headlight
  - scene_light
  - move_arrows
  - rotation_rings (rotation gizmo + DragRotate; see Patterns section)
- `shaders/`
  - compiler
  - faces
  - edges
  - vertices
  - floor
  - grid2d
  - schematic2d
- `materials/`:
  - material 
  - generic 
  - glowing 
  - metallic 
  - plastic 
  - polished 
  - rubber
- `model_preview/canvas.py`: small preview canvas

## `ui/`
- `mainframe.py` (~2000 lines): main window, docking, ties everything together
- `editor_2d/editor2d.py`, `editor_3d/editor3d.py`: schematic & 3D editors
- `editor_assembly/`, `editor_ciruit/` (note typo "ciruit"): assembly & circuit editors (circuit has design_rules.py, editor_widget.py)
- `editor_db/`: parts-database editor
  - `base.py` (~1100 lines) + one file per part type
  - `editordb.py`
  - `edit_dialog.py`
- `editor_obj/`: object property editor
  - `editorobj.py`
  - `prop_grid.py`
- `editor_script/`: empty stub
- `object_browser/objectbrowser.py`: scene tree
- `prop_ctrls/`: property-grid controls 
  - `prop_base.py` + one file per type: 
    - float
    - int
    - string
    - color
    - position2d/3d
    - angle3d
    - scale3d
    - model3d
    - image
    - path
    - enum
    - choice
    - combobox
    - array_*…
- `widgets/`: reusable controls
  - autocomplete combos/textctrls
  - color_ctrl
  - list_ctrl
  - foldpanelbar
  - context_menus
  - search_db
  - *_ctrl wrappers
- `dialogs/`:
  - dialog_base.py
  - about_dialog.py: About box — app info, update check (GitHub releases API),
    package credits (left list, alphabetical) + metadata/license viewer
    (`importlib.metadata` over installed dist-info dirs, incl. Python itself)
  - part_search.py
  - part_orientation.py
  - properties_dialog.py
  - bundle_wires_dialog.py
  - export_dialog.py
  - transition_routing.py
  - add_project
  - add_note
  - project_dialog
  - render_setings (typo)
  - debug_settings
  - error
  - header
  - `housing_editor/`:
    - housing
    - cavity
    - accessory
    - obj+panel pairs
    - housing_editor.py
- `system_menu/`: menubar menus
  - file
  - edit
  - view
  - database
  - settings
  - window
  - help
- `toolbar/`: 
  - toolbar.py
  - float_spin_button.py
  - snap_angle_button.py (rotation-snap toggle: left click = enable/disable with 
    checkbox icon overlay, right click = AutoCompleteComboBox popup of the 71 
    valid snap angles; writes Config.editor3d.rotation_rings)
- `log_viewer/viewer.py`
- `datasheet_viewer/viewer.py`
- `web_viewer/` (empty)

## Other subsystems
- `exporter/`: project export
  - `exporter.py`
- `geometry/`: 
  - point
  - line
  - decimal
- `geometry/angle/`: 
  - angle
  - quaternion
- `shapes/`:procedural geometry generators 
  (ported from a small C 3D library; deliberately NOT build123d — direct mesh 
  generation is far faster for primitives)
  - box
  - sphere
  - cylinder
  - cone
  - torus
  - helix
  - cylinder_helix
  - arrow
  - circle
  - rectangle
  - line
- `gpu_mem/`: GPU memory monitoring per vendor
  - nvidia
  - amd
  - intel
  - apple
  - manager
- `ray_tracing/`: offline renderer
  - renderer
  - scene
  - light
  - bvh_processor
  - dialog
- `logger/`: logging
  - log_handler
  - stdout
  - stderr
- `themes/`: theme manager 
  - Dark
  - Light
- `image/`: image loading
  - icons
  - cursors
  - connector images
  - overlays

## Third-party dependencies (non-stdlib imports)
- `PySide6`: PySide6
- `OpenGL`: PyOpenGL
- `numpy`: numpy
- `pandas`: pandas
- `PIL`: Pillow
- `requests`: requests
- `keyring`: keyring
- `win32ctypes`: pywin32-ctypes
- `mysql`: mysql-connector-python
- `build123d`: build123d
- `OCP`: cadquery-ocp
- `pyassimp`: pyassimp
- `pyfqmr`: pyfqmr
- `ezdxf`: ezdxf
- `pyopencl`: pyopencl
- `pynvml`: nvidia-ml-py
- `amdsmi`: amdsmi
- `apple_smi`: apple_smi (Apple-only)

## Same-name modules: layer relationships & loading order
A part type (e.g. "housing") has same-named modules in several packages. They 
are distinct layers of one pipeline, from catalog definition to pixels on screen:

```
database/create_database/housings.py     DDL/seed — creates/updates both tables below
        │
database/global_db/housing.py            catalog part: part_number, dims, materials, model3d ref
        ▲  (part_id foreign key; entry exposed as .part)
database/project_db/pjt_housing.py       PJTHousing — an instance placed in a project:
        │                                position/angle/scale + part_id → global part.
        │                                Holds weakref to its scene object
        │                                (get_object()/set_object()).
        ▼  creates
objects/housing.py                       Housing(ObjectBase) wrapper — owns obj2d + obj3d
        │                                and child wrappers (cavities, locks, seal, cover, boot);
        │                                fans select/delete/identify to both views
        ▼  creates both
objects2d/housing.py + objects3d/housing.py   renderable views; ctor(parent=wrapper,
                                              db_obj=PJTHousing); geometry from
                                              db_obj.part (model3d, dims) via gl/ VBOs
```

- **Creation flow (user adds a part):** `handlers/housing_handler.py` (`Add*Handler`) → 
                                        `ui/dialogs/part_search.py` picks a global_db part → 
                                         inserts a `pjt_*` row → 
                                         builds the `objects/` wrapper → 
                                         wrapper builds the 2d/3d objects → 
                                         editors render them.
- **Project load flow:** project_db tables iterate `pjt_*` entries → 
                         each entry builds its wrapper + 2d/3d objects 
                         (3D models fetched/meshed via `process/model_process.py`).
- **Catalog editing** is a separate path: `ui/editor_db/housing.py` edits the global_db table 
                                          directly and never touches `pjt_*` or scene objects.
- Naming convention per layer: 
  - `create_database`: uses plural (`housings.py`)
  - `global_db`: singular (`housing.py`)
  - `project_db`: prefixed (`pjt_housing.py`)
  - `handlers`: suffixed (`housing_handler.py`) 
  - `objects` all just `housing.py` (wrapper, 2d, 3d).

## 3D rendering pipeline (model file → GPU)
How a part's 3D model gets from disk to the screen:

- **Model save file** (`process/model_process.py` worker):
  - imports the source CAD file (STEP/IGES via OCP, others via pyassimp)
  - simplifies the mesh (pyfqmr), computes smooth + face normals
  - packs vertices + both normal sets into one flat float array
  - saves it as a plain **uncompressed `.npy`** file at `<model_dir>/<uuid[:2]>/<uuid>.npy`
  - only metadata goes to the DB: uuid, vertex_count, aabb, obb
- **Loading** (`global_db/model3d.py`):
  - the parent process opens the `.npy` with `np.load(mmap_mode='r')`
  - the **memmap** is streamed straight into the GPU vertex buffer — model data is never fully loaded into RAM
- **Shared GL contexts** (`app.py`, `gl/context.py`):
  - `AA_ShareOpenGLContexts` is set at import time in `app.py` (before the QApplication is created)
  - so the uploaded model data (VBOs) is **shared across every GL canvas** 
    (editor3d, model_preview) — one upload serves them all
  - editor2d does **not** use the shared context yet — planned (as of 2026-06-11, 
    expected within days); remove this note once it does
  - VAOs are **not** shareable across contexts, so `vbo.py` tracks/rebuilds VAOs per canvas 
    (`_clear_vaos`, `_clear_model_vaos_for_arena`)
  - `gl/context.py` `GLContext`: thread-safe acquire/release wrapper around each canvas's 
    `makeCurrent()` (re-entrant, skips redundant makeCurrent calls)
- **VBO handling** (`gl/vbo.py`):
  - the shader reads all 3 vertex attributes (position / smooth normal / face normal) 
    from **ONE buffer** at byte offsets baked into a per-context VAO — geometry must be 
    uploaded as a single packed buffer (the `compute_normals` layout); 
    `Base3D._render_geometry`'s separate-client-array fallback path is **legacy** 
    (`rotation_rings.py` `_GizmoBuffer` is the reference for a private single-buffer 
    mesh outside the arena)
  - ⚠ the `vbo=None`/`_data` path assumes **world-space** geometry: `_update_position` 
    shifts `_data[0]` by the position delta AND re-applies the floor lock on every 
    position write — local-space users must override `_update_position` (see `Rings3D`)
  - ⚠ `Base3D.__init__` and `_update_position` apply the **floor lock** to any object 
    whose AABB dips below ground — UI gizmos must opt out via a `_floor_guard` during 
    init + an `_update_position` override (see `Rings3D` and `Arrows3D`)
  - `_MeshArena`: a **managed GPU buffer pool** — one large arena buffer, sub-allocated per model
  - tracks **fragmentation** of freed ranges; when it crosses a threshold 
    (`MODEL_ARENA_FRAGMENTATION_THRESHOLD`) the arena **compacts** via GPU-to-GPU copies 
    (`_gpu_copy`), no CPU round-trip
  - `VBOHandler` is a per-id refcounted singleton (`VBOSingleton` metaclass + 
    `acquire()`/release): objects sharing the same model **reuse the same uploaded data** — 
    the model is uploaded once no matter how many instances exist
- **Shaders** (`gl/shaders/faces.py` etc.):
  - vertex attributes are **local/model space** (vertex, smooth normal, face normal)
  - per-object transform is done **in the shader** via uniforms: 
    - `objectPosition` (vec3)
    - `objectRotation` (quaternion, vec4)
    - `objectScale` (vec3)
  - **quaternion ordering is scalar-first: `(w, x, y, z)`** — used consistently in 
    `geometry/angle/quaternion.py` (`_data = [w, x, y, z]`) and the shader uniform
    - ⚠ in GLSL the vec4 component names do NOT match the quaternion components: 
      `q.x` = w, `q.y` = x, `q.z` = y, `q.w` = z (see `quaternionToMatrix` in 
      `gl/shaders/faces.py`)
    - libraries that are xyzw-ordered (e.g. scipy) need reordering at the boundary
  - **Euler angles are stored in the database alongside the quaternion** 
    (`geometry/angle/angle.py` `Angle` holds both forms; `project_db/mixins/angle3d.py` 
    writes both, and reload passes the stored Euler into `Angle.from_quat` instead of 
    deriving it):
    - **any change to an angle MUST be made via the Euler angles, never the quaternion**
    - reason: Euler → quaternion conversion is safe, but quaternion → Euler 
      (and any rotation-form → Euler conversion) suffers **gimbal lock** — 
      deriving Euler from the quaternion can produce wrong/ambiguous angles
    - the quaternion is the derived form (kept for the shader); the Euler angles 
      are the editable source of truth
  - so position/angle/scale changes never touch the VBO — only uniform updates

## Patterns to remember
- Part-type fan-out: a part (e.g. "seal") usually has files in 
  - global_db
  - project_db (pjt_)
  - create_database
  - objects (wrapper)
  - objects2d
  - objects3d
  - handlers
  - editor_db. 

  Adding/altering a part type typically touches all of those.
  

- **Change propagation via instance singletons** (`geometry/point.py` `Point`, 
  `geometry/angle/angle.py` `Angle`, also `color.py` `Color`):
  - instances are cached by `db_id` — every lookup for the same id returns the 
    **same object**, so holding a reference IS the subscription
  - `bind(callback)` / `unbind(callback)` notify on any change; this is how state 
    propagates across UI controls, scene objects, and gizmos (no event/signal 
    library involved)
  - writers that are also bound listeners MUST use the **unbind → write → rebind** 
    idiom to avoid feedback loops (see prop_ctrls and `Rings3D.apply_drag_angle` 
    for the reference pattern)
- **Type hints are load-bearing — do not weaken them.**
  The entire codebase is compiled to C extension modules via Cython for release builds.
  Cython uses concrete type annotations to emit statically typed C; if a hint is 
  removed, generalised to a base class, or replaced with a TypeVar/Generic, Cython 
  falls back to Python object boxing for that value and the compiled code loses its 
  performance advantage. This means:
  - every `@property` return type, `__iter__` yield type, and `__getitem__` return 
    type must name the most specific concrete class, not a base or abstract type
  - refactors that appear to reduce boilerplate by moving typed methods into a base 
    class often destroy Cython's ability to specialise those methods — check whether 
    the type information survives before proceeding
  - `TYPE_CHECKING` blocks are fine (Cython ignores them at compile time), but 
    runtime annotations on hot paths must be concrete
- Lazy imports are used in objects3d context menus.
- Dialogs use a custom title bar and close only via bottom buttons — no native window chrome.
- **Mouse-drag interaction: axis locking** (`gl/canvas3d/dragging.py` `DragObject`):
  - on the first movement, the axis with the greatest absolute delta becomes the 
    **locked axis** (`axis_lock` mask + `MoveArrows` indicator created at that moment)
  - all movement is constrained to that axis until the mouse button is released — 
    makes positioning predictable
- **Mouse-drag interaction: rotation rings / angle mode** (`gl/canvas3d/rotation_rings.py`):
  - right-click a **selected** object → rotation ring gizmo appears (angle mode)
  - three rings (x=red, y=green, z=blue), each with a sphere grab handle
  - dragging a handle locks that Euler axis; screen-space cursor angle around the 
    object's projected center is accumulated **directly into that axis's Euler angle** 
    (wrapped to -180…180) — no quaternion → Euler conversion ever happens
  - exits: left-click the object, or click+release (no motion) anywhere that is not 
    a grab handle; drag not on a handle moves the camera; rings survive handle drags
  - ring planes follow the **nested Euler order** (see below); each ring spins with 
    its own slot's angle so the handle tracks the drag
  - drag features: **0.0 detent** (snap-free mode only) and **angle snapping** 
    (`snap_enable`/`snap_angle` config, toolbar `snap_angle_button.py`); valid snap 
    angles = divisors of 36000 in hundredths (71 values ≤ 180°), enforced by 
    `validate_snap_angle()`; settings are read **per mouse event** so changes apply 
    live mid-drag
  - gizmo position is the object's **shared Point instance** (not a copy); culling 
    mirrors the object's AABB/OBB; floor lock is opted out via `_floor_guard`
  - rendering: private single-buffer meshes (`_GizmoBuffer`), config dirty-checked 
    per frame (dimensions/colors apply in real time)
  - **Euler nesting order (verified numerically): effective matrix is `Ry·Rx·Rz` — 
    Z innermost, X middle, Y outermost.** Per-slot world rotation axes: 
    - y slot: world Y (fixed)
    - x slot: `Ry @ X`
    - z slot: `Ry·Rx @ Z` (full rotation applied to Z)
  - the old `arcball.py` is no longer wired into the mouse handler (kept dormant)
- Euler-angle UI controls are clamped to **-180…180** so rotation direction stays 
  intuitive for the user; keep that range when adding angle controls.
