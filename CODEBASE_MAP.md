# harness_designer codebase map

A folder-level trail of breadcrumbs for finding things in a new session: every directory under
`harness_designer/`, `builder/` and `diagnostics/` with a brief outline of what lives inside it. It
lists **no file names** and holds **no per-file notes**.

**To find a file or learn what is in a folder, read that folder's own `MAP.md`** (it sits next to the
code): a `## FILES` section with one `####` entry per file, a `## FOLDERS` section with one per
subdirectory, and an optional trailing `## DESIGN NOTES` section. Reading the `MAP.md` of a directory
is mandatory before working in it. For "where is X defined / who calls Y / what imports Z" questions
use `diagnostics/dep_trace.py` (see `CLAUDE.md`). See `MEMORY.md`'s "MANDATORY: per-directory MAP.md
files" section for the full rule.

Update this file in the same change whenever a directory is added, removed or renamed (and the parent
directory's `MAP.md` `## FOLDERS` entry too). Adding or renaming a plain file only touches that
directory's `MAP.md`.

Project in one line: a PySide6 (Qt) desktop app for designing wire harnesses, with OpenGL 2D/3D/peg-board
editors, a multi-process DB/model/image back end, and Cython-compiled release builds.

## Tree

- harness_designer/ — the application package; top-level modules are app bootstrap, config, color, logging-of-crashes and the OCP model pipeline
  - add_handlers/ — "Add X" placement sessions, one per object type per view
    - editor_3d/ — placement sessions in the 3D editor (every object type)
    - editor_pegboard/ — placement sessions on the peg board (housing, wire, waypoints)
    - editor_schematic/ — placement sessions in the schematic (housing, splice, terminal, wire)
  - app_mixins/ — application-level mixins, chiefly the `CallbackMixin` reactive backbone
  - bounds/ — pooled bounding-box and wire-path storage, one set per view
  - crash_dump/ — crash-dump capture and writing
    - extras/ — lazily-imported rendering support for optional stdlib/third-party types
    - writer/ — streaming NDJSON records plus the self-contained HTML dump file
  - database/ — the whole DB layer: parts catalog, per-project tables, seed/creation, connectors
    - common_db/ — plumbing shared by both schemas' row/table classes
    - create_database/ — DDL and seed data, one file per table
    - db_connectors/ — backend-agnostic connector abstraction
      - mysql_connector/ — MySQL backend (shared parts-catalog server)
      - sqlite_connector/ — SQLite backend (local project database)
    - global_db/ — the shared parts catalog, one file per entity (housing, wire, terminal, ...)
      - ip/ — IP-rating tables
      - mixins/ — column mixins shared across the catalog entity classes
    - project_db/ — per-project `pjt_*` tables: the placed-instance layer
      - mixins/ — column mixins for the `pjt_*` row classes
  - drag_handlers/ — per-object-type drag handlers
    - editor_3d/ — 3D drag handlers (free-orbit camera, axis lock)
    - editor_pegboard/ — peg-board drag handlers (length-budget / rope-pull gated)
    - editor_schematic/ — schematic drag handlers (top-down plane, auto-reroute)
  - exporter/ — project export
  - geometry/ — point, line, angle and quaternion primitives
    - angle/ — `Angle` and `Quaternion`
  - gl/ — OpenGL rendering: canvases, shaders, materials, culling, buffer management
    - canvas_3d/ — the free-orbit 3D editor canvas
    - canvas_base/ — shared base classes for all canvases
    - canvas_pegboard/ — the peg-board canvas
    - canvas_schematic/ — the schematic canvas
    - culling/ — process-wide culling thread pool
    - materials/ — weight-based material system
    - model_preview/ — standalone model preview canvas
    - shaders/ — GLSL compiling/linking and the program wrapper classes
      - edges/ — edge-rendering program
      - faces/ — face-rendering program
      - floor/ — 3D procedural floor program
      - grid2d/ — 2D dot-grid program
      - texture/ — textured-quad program
      - vertices/ — vertex-marker program
  - gpu/ — per-vendor GPU memory monitoring
    - amd/ — AMD backend
    - apple/ — Apple Silicon backend
    - intel/ — Intel backend
    - nvidia/ — NVIDIA backend
  - handlers/ — selection/interaction handlers per part type, plus the orthogonal wire-routing engine
  - image/ — image loading and bundled icon/cursor/image assets
    - cursors/ — custom Qt cursors (PNG)
    - electrical/ — schematic symbol icons (PNG)
    - icons/ — toolbar/menu icons (PNG)
    - images/ — banners, placeholders, numbered download icons (PNG)
    - ip/ — IP-rating icon overlays (PNG)
  - licenses/ — bundled third-party license texts
  - logger/ — logging handler and stdout/stderr redirection
  - models/ — bundled 3D model files (STL/STEP)
  - objects/ — scene-object wrapper classes and their per-view renderables
    - mixins/ — wrapper-level mixins shared across object types
    - objects_3d/ — 3D renderables
      - mixins/ — wire-type mixin
    - objects_pegboard/ — peg-board renderables
    - objects_schematic/ — schematic (2D) renderables
      - mixins/ — empty package
    - objectsvar/ — `BaseVar`, common ancestor of the per-view base classes
  - pegboard_print/ — true-scale tiled printing of the peg board with alignment marks
  - plugins/ — plugin registration framework
    - ai/ — provider-agnostic AI plugin contract
    - plugins/ — concrete plugin implementations
      - claude_ai/ — the Claude API plugin
        - qt/ — Qt-facing layer (job runner, API-key dialog)
  - process/ — multiprocessing: DB, model and image worker processes
    - clean_creds/ — Windows credential-store cleanup
  - ray_tracing/ — offline BVH-based ray tracer
  - rope_pull/ — peg-board rope-pull length solver
  - rotation_handlers/ — protractor-style rotation gizmos per view
    - editor_3d/ — 3-axis rings
    - editor_pegboard/ — single-axis rings
    - editor_schematic/ — single-axis rings
    - rotation_ring/ — shared ring assembly and ring implementations
  - scraping/ — point-and-click scraper authoring (non-UI logic)
  - shapes/ — procedural geometry generators (box, sphere, cylinder, ...)
  - themes/ — theme manager
    - Dark/ — dark theme stylesheet
      - icons/ — dark theme UI glyphs (PNG)
    - Light/ — light theme stylesheet
      - icons/ — light theme UI glyphs (PNG)
  - ui/ — every Qt window, dock, dialog and widget
    - concentric_section/ — concentric-twist bundle cross-section widget
    - datasheet_viewer/ — datasheet viewer dock
    - dialogs/ — standalone dialogs (About, part search, project, ...)
      - housing_editor/ — housing cavity/accessory editor
      - transition_editor/ — transition catalog-part editor with live 3D preview
    - editor_3d/ — 3D editor dock
    - editor_assembly/ — assembly editor dock
    - editor_circuit/ — circuit table editor dock
    - editor_db/ — parts-database editor dock
    - editor_obj/ — object property editor dock
    - editor_pegboard/ — peg board editor dock
    - editor_schematic/ — schematic editor dock
    - editor_script/ — scraper Script Editor dock
    - log_viewer/ — log viewer dock
    - object_browser/ — scene-tree dock
    - pegboard_table/ — peg-board wire table widget
    - prop_ctrls/ — property-grid field controls, one per value type
    - scraper_inspector/ — scraper XHR/source inspector docks
    - system_menu/ — menubar menus
    - toolbar/ — toolbar classes and snap/spin buttons
    - web_viewer/ — scraper QtWebEngine browser dock
    - widgets/ — reusable low-level controls
      - resources/ — widget image assets
        - images/ — up/down button images (PNG)
  - utils/ — stateless helpers (paths, conversions, mesh/geometry math)
  - wire_routing/ — orthogonal auto-routing for schematic wires

- builder/ — build system: wheel/Cython/PyInstaller build, installer assets, native deps
  - scripts/ — standalone scripts bundled into the frozen app (not build-time tooling)

- diagnostics/ — developer tooling: `dep_trace.py` (static code queries), memory and snapshot tools, audits and offline checks
