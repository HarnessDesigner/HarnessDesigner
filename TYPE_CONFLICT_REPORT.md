# Type-conflict / type-reassignment scan (2026-10-20)

Full-codebase scan requested by the user: look for (1) conflicts in the types being used and
(2) locals/attributes that change type within the same scope. Builds directly on the existing
`CYTHON_REASSIGNMENT_AUDIT.md` (2026-10-19) and the "Cython variable type reuse" / "Concrete
return types" / "Cython variable-reassignment audit" entries in `MEMORY.md` — read those first for
the background rule this report applies: **plain harness_designer classes are safe to reassign
(no C-level coercion); builtins/containers and raw third-party extension types (Qt/Shiboken) are
not.**

## Methodology

- `mypy 2.1.0` run against `harness_designer/` only (799 `.py` files; matches the Cython-compiled
  surface — `builder/` and `diagnostics/` are build tooling, not compiled, and were not scanned).
  Interpreter: `C:\Python3.11.14\python.exe` (the one with the project's real dependencies —
  PySide6, numpy, OCP, etc. — installed; the default `python`/3.10 on `PATH` has none of them and
  mypy would fail to resolve almost everything under it).
  ```
  C:\Python3.11.14\python.exe -m mypy harness_designer/ --no-error-summary
  ```
- 4833 raw error lines came back. Filtering to `[assignment]`/`[arg-type]`-shaped messages,
  bucketing both sides of each "expression has type X / variable has type Y" pair into
  {builtin/container/ndarray, Qt-extension-type, plain class, None, other}, and then — critically —
  **checking the actual source line for an explicit type annotation** (bare `x = value` with no
  `:` anywhere for that name vs. an explicit `x: T = value`) turned out to be the single most
  decisive filter: Cython only gives a C-level storage type to an **explicitly annotated** name
  (`language_level='3'`, no `infer_types`); an unannotated local/attribute stays a generic
  `PyObject*` regardless of how many different types mypy infers for it across branches. That one
  check alone reclassified ~450 of the ~1300 `[assignment]` candidates from "looks risky" to
  "bare, not a Cython risk."
- Everything below that survived both filters was then read in context (not just the one flagged
  line) to confirm the pattern and rule out the specific known false-positive shapes already
  catalogued in `CYTHON_REASSIGNMENT_AUDIT.md` (PySide6 `Signal()` idiom, `self.size`/`.context`
  shadowing an inherited Qt method, branch-dependent-but-unannotated locals, `None` into a
  plain-class slot).
- A separate plain-AST pass (no mypy) found every class defined more than once by simple name
  under `harness_designer/`, to catch annotation ambiguity that doesn't depend on assignment at
  all.

Scripts used are throwaway (session scratchpad, not committed) — rerun the mypy command above to
regenerate the raw data if this report goes stale.

---

## Part 1 — Locals/attributes that change type (the Cython reassignment bug)

### 1a. New confirmed bug: wrong sentinel type in `DefaultStoredValue` annotations (pjt_housing.py / pjt_cpa_lock.py)

The project's own documented convention (comment right above the two classes,
`database/project_db/pjt_bases.py:125-138`) is:
```python
# _stored_value: DefaultStoredValueType | float = DefaultStoredValue
```
i.e. the **annotation** names `DefaultStoredValueType` (the metaclass — "this slot's type can be
the sentinel"), while the **value** assigned is the bare class `DefaultStoredValue` (an instance of
that metaclass). 423 other declarations across the codebase do this correctly. These 9 don't — they
put the instance-class `DefaultStoredValue` directly in the annotation instead of
`DefaultStoredValueType`, which is a real type statement (mypy reads bare `DefaultStoredValue` in an
annotation as "an *instance* of DefaultStoredValue", not "the class object"), and it doesn't match
what's actually stored:

| File | Line | Current type (in annotation) | Should be |
|---|---|---|---|
| `database/project_db/pjt_housing.py` | 1136 | `DefaultStoredValue` | `DefaultStoredValueType` |
| `database/project_db/pjt_housing.py` | 1199 | `DefaultStoredValue` | `DefaultStoredValueType` |
| `database/project_db/pjt_housing.py` | 1262 | `DefaultStoredValue` | `DefaultStoredValueType` |
| `database/project_db/pjt_housing.py` | 1322 | `DefaultStoredValue` | `DefaultStoredValueType` |
| `database/project_db/pjt_housing.py` | 1385 | `DefaultStoredValue` | `DefaultStoredValueType` |
| `database/project_db/pjt_housing.py` | 1448 | `DefaultStoredValue` | `DefaultStoredValueType` |
| `database/project_db/pjt_housing.py` | 1511 | `DefaultStoredValue` | `DefaultStoredValueType` |
| `database/project_db/pjt_housing.py` | 1758 | `DefaultStoredValue` | `DefaultStoredValueType` |
| `database/project_db/pjt_cpa_lock.py` | 221 | `DefaultStoredValue` | `DefaultStoredValueType` |

(Only the one word in each annotation needs to change — the rest of the union, e.g.
`"_pjt_point3d.PJTPoint3D" | None`, stays as-is. Example, pjt_housing.py:1136:
`_stored_cover_position3d: _Union["_pjt_point3d.PJTPoint3D", None, DefaultStoredValue] = DefaultStoredValue`
→ swap the annotation's `DefaultStoredValue` for `DefaultStoredValueType`; the assigned value on the
right of `=` is correct as-is and doesn't change.)

### 1b. "Cannot override writeable attribute with read-only property" — real, currently latent

`objects_pegboard/wire.py:348,354`, `objects_3d/wire.py:253,259`, `objects_3d/bundle.py:886,892`:
each of these overrides a base/mixin attribute that's a plain **writable** instance attribute
(e.g. `WireMixin`'s `start_position`/`stop_position`, assignable per the mixin's own declaration)
with a **read-only `@property`** (getter only, no setter). Any code that does
`some_wire.start_position = point` on one of these concrete classes will raise
`AttributeError: can't set attribute` — not a Cython-only issue, a plain-Python runtime break.
Checked whether anything currently exercises this: a grep for `.start_position =` / `.stop_position
=` across the codebase found **no call sites today**, so this is latent, not an active crash — but
it's a real contract violation that will bite the next person who tries to set these through the
base-typed interface.

### 1c. Missing `| None` on a primitive/container-typed parameter or attribute — confirmed crash shape, 53 new/un-fixed sites

This is exactly the bug class `MEMORY.md`'s "Cython variable type reuse" entry and the Oct-19 audit
already fixed ~75 instances of (`__table_name__: str = None` et al.) — these are **additional**
sites, either new since that pass or missed because the fix only landed in one half of a
parallel-file pair. Two are literally the parallel-file-miss case: `pjt_bases.py:445`'s
`__table_name__: str = None` is the exact bug already fixed in `global_db/bases.py` but not in its
`project_db` twin, and `ui/mainframe.py:555`'s `label: str = None` is a second, different parameter
in the very file whose `_selection_source_editor` was already fixed.

Fix shape is the same as the Oct-19 audit used: add `| None` to the annotation — these are real
parameter/attribute values defaulting to `None`, not typos. Full list, current declared type vs.
what it should be:

| File | Line | Current type | Should be |
|---|---|---|---|
| `plugins/register.py` | 24 | `str` | `str \| None` |
| `database/db_connectors/sqlite_connector/connector.py` | 407 | `list[Any]` | `list[Any] \| None` |
| `objects/objects_pegboard/wire.py` | 880 | `bytes` (`preset_part_id`) | `bytes \| None` |
| `objects/objects_pegboard/wire.py` | 880 | `tuple[Any, ...]` (`extend_wire`, `add_to_wire`) | `tuple[Any, ...] \| None` |
| `database/create_database/accessories.py` | 79 | `str` | `str \| None` |
| `database/create_database/splices.py` | 225 | `bytes` | `bytes \| None` |
| `database/create_database/terminals.py` | 208 | `bytes` | `bytes \| None` |
| `database/global_db/used_part.py` | 59 | `bytes` | `bytes \| None` |
| `database/global_db/used_part.py` | 60 | `bytes` | `bytes \| None` |
| `database/global_db/tpa_lock.py` | 131 | `str` | `str \| None` |
| `database/global_db/terminal.py` | 159 | `str` | `str \| None` |
| `database/global_db/seal.py` | 135 | `str` | `str \| None` |
| `database/global_db/housing.py` | 147 | `str` | `str \| None` |
| `database/global_db/housing.py` | 148 | `str` | `str \| None` |
| `database/global_db/housing.py` | 149 | `str` | `str \| None` |
| `database/global_db/cpa_lock.py` | 131 | `str` | `str \| None` |
| `database/global_db/cover.py` | 131 | `str` | `str \| None` |
| `database/global_db/boot.py` | 130 | `str` | `str \| None` |
| `database/create_database/wire_service_loops.py` | 24 | `bytes` | `bytes \| None` |
| `database/project_db/pjt_wire_layout.py` | 139 | `bytes` | `bytes \| None` |
| `database/project_db/pjt_wire_layout.py` | 140 | `bytes` | `bytes \| None` |
| `database/project_db/pjt_tpa_lock.py` | 137 | `bytes` | `bytes \| None` |
| `database/project_db/pjt_seal.py` | 144 | `bytes` | `bytes \| None` |
| `database/project_db/pjt_housing.py` | 212 | `bytes` | `bytes \| None` |
| `database/project_db/pjt_housing.py` | 213 | `bytes` | `bytes \| None` |
| `database/project_db/pjt_bundle_layout.py` | 153 | `bytes` | `bytes \| None` |
| `database/project_db/pjt_bundle_layout.py` | 154 | `bytes` | `bytes \| None` |
| `ui/mainframe.py` | 555 | `str` (`label`) | `str \| None` |
| `utils/mesh_surface_picker.py` | 161 | `int` | `int \| None` |
| `utils/mesh_surface_picker.py` | 728 | `int` | `int \| None` |
| `process/image_process.py` | 222 | `dict[Any, Any]` | `dict[Any, Any] \| None` |
| `process/image_process.py` | 376 | `dict[Any, Any]` | `dict[Any, Any] \| None` |
| `process/image_process.py` | 386 | `dict[Any, Any]` | `dict[Any, Any] \| None` |
| `objects/objectsvar/base_var.py` | 145 | `ndarray[Any, Any]` | `ndarray[Any, Any] \| None` |
| `objects/objects_3d/wire_service_loop.py` | 310 | `list[Any]` (`attached`) | `list[Any] \| None` |
| `objects/objects_3d/wire_service_loop.py` | 311 | `list[Any]` (`markers`) | `list[Any] \| None` |
| `objects/objects_3d/wire_service_loop.py` | 312 | `list[Any]` (`candidates`) | `list[Any] \| None` |
| `gl/canvas_base/canvas_base.py` | 350 | `str` (`_editor_name`) | `str \| None` |
| `database/global_db/mixins/resource.py` | 276 | `dict[Any, Any]` | `dict[Any, Any] \| None` |
| `database/global_db/mixins/color.py` | 99 | `list[list[Any]]` | `list[list[Any]] \| None` |
| `database/project_db/mixins/color.py` | 87 | `list[list[Any]]` | `list[list[Any]] \| None` |
| `database/project_db/pjt_transition.py` | 501 | `list[Any]` (`_o_quat3d`) | `list[Any] \| None` |
| `database/project_db/pjt_transition.py` | 502 | `list[Any]` (`_o_euler3d`) | `list[Any] \| None` |
| `database/project_db/pjt_transition.py` | 570 | `list[Any]` (`_o_quat_pegboard`) | `list[Any] \| None` |
| `database/project_db/pjt_transition.py` | 571 | `list[Any]` (`_o_euler_pegboard`) | `list[Any] \| None` |
| `database/project_db/pjt_housing.py` | 867 | `list[Any]` (`_stored_cavities`) | `list[Any] \| None` |
| `database/project_db/pjt_housing.py` | 942 | `dict[Any, Any]` (`_stored_cavity_geometry`) | `dict[Any, Any] \| None` |
| `database/project_db/pjt_housing.py` | 1029 | `list[Any]` (`_stored_terminals`) | `list[Any] \| None` |
| `database/project_db/pjt_housing.py` | 2307 | `list[Any]` (`_o_quat3d`) | `list[Any] \| None` |
| `database/project_db/pjt_housing.py` | 2308 | `list[Any]` (`_o_euler3d`) | `list[Any] \| None` |
| `database/project_db/pjt_housing.py` | 2608 | `list[Any]` (`_o_quat_pegboard`) | `list[Any] \| None` |
| `database/project_db/pjt_housing.py` | 2609 | `list[Any]` (`_o_euler_pegboard`) | `list[Any] \| None` |
| `database/project_db/pjt_housing.py` | 2840 | `list[Any]` (`_o_quat2d`) | `list[Any] \| None` |
| `database/project_db/pjt_housing.py` | 2841 | `list[Any]` (`_o_euler2d`) | `list[Any] \| None` |
| `database/project_db/pjt_bases.py` | 445 | `str` (`__table_name__`) | `str \| None` |
| `handlers/wire_routing_drag.py` | 322 | `str` (`_view`) | `str \| None` |

### 1d. Missing `| None` on a raw Qt-type attribute/parameter — same shape, lower confidence

The empirically-confirmed Cython risk for raw Qt/Shiboken types (category 3 in
`CYTHON_REASSIGNMENT_AUDIT.md`) was tested for *value-to-value* reassignment (the `QSize` crash),
not specifically for `None`. Cython's own `None`-handling for extension types is usually more
forgiving than for unboxed primitives, so these are **worth checking, not confirmed crashes**:

| File | Line | Current type | Should be |
|---|---|---|---|
| `ui/object_browser/objectbrowser.py` | 590 | `QTreeWidgetItem` (`_boots`) | `QTreeWidgetItem \| None` |
| `ui/object_browser/objectbrowser.py` | 591 | `QTreeWidgetItem` (`_bundles`) | `QTreeWidgetItem \| None` |
| `ui/object_browser/objectbrowser.py` | 592 | `QTreeWidgetItem` (`_cavities`) | `QTreeWidgetItem \| None` |
| `ui/object_browser/objectbrowser.py` | 593 | `QTreeWidgetItem` (`_circuits`) | `QTreeWidgetItem \| None` |
| `ui/object_browser/objectbrowser.py` | 594 | `QTreeWidgetItem` (`_covers`) | `QTreeWidgetItem \| None` |
| `ui/object_browser/objectbrowser.py` | 595 | `QTreeWidgetItem` (`_cpa_locks`) | `QTreeWidgetItem \| None` |
| `ui/object_browser/objectbrowser.py` | 596 | `QTreeWidgetItem` (`_housings`) | `QTreeWidgetItem \| None` |
| `ui/object_browser/objectbrowser.py` | 597 | `QTreeWidgetItem` (`_notes`) | `QTreeWidgetItem \| None` |
| `ui/object_browser/objectbrowser.py` | 598 | `QTreeWidgetItem` (`_seals`) | `QTreeWidgetItem \| None` |
| `ui/object_browser/objectbrowser.py` | 599 | `QTreeWidgetItem` (`_splices`) | `QTreeWidgetItem \| None` |
| `ui/object_browser/objectbrowser.py` | 600 | `QTreeWidgetItem` (`_terminals`) | `QTreeWidgetItem \| None` |
| `ui/object_browser/objectbrowser.py` | 601 | `QTreeWidgetItem` (`_tpa_locks`) | `QTreeWidgetItem \| None` |
| `ui/object_browser/objectbrowser.py` | 602 | `QTreeWidgetItem` (`_transitions`) | `QTreeWidgetItem \| None` |
| `ui/object_browser/objectbrowser.py` | 603 | `QTreeWidgetItem` (`_wires`) | `QTreeWidgetItem \| None` |
| `ui/object_browser/objectbrowser.py` | 604 | `QTreeWidgetItem` (`_wire_markers`) | `QTreeWidgetItem \| None` |
| `ray_tracing/dialog.py` | 56 | `QImage` (`current_image`) | `QImage \| None` |
| `gl/canvas_base/canvas_base.py` | 368 | `QSize` (`size` param) | `QSize \| None` |
| `ui/widgets/stipple_ctrl.py` | 42 | `QWidget` (`parent` param) | `QWidget \| None` |
| `ui/widgets/foldpanelbar.py` | 1186 | `QColor` (`colour` param) | `QColor \| None` |

### 1e. Other confirmed/likely risky reassignments

| File | Line | Declared/first type | Reassigned to | Note |
|---|---|---|---|---|
| `utils/model_utils.py` | 154 | `list[list[Any]]` (param `faces`) | `ndarray[tuple[int,...], dtype[int32]]` | same shape as the documented `cavity.py`/`pjt_cavity.py` ndarray-setter bugs, a new site |
| `gl/canvas_base/camera_base.py` | 952 | `target_distance` is `numpy.float64` (from `current_distance - float(delta)` at line 949, where `current_distance = np.linalg.norm(offset)`) | reassigned at line 952 to `min_distance` (a plain Python `float` literal, `0.1`) | wrap line 949 as `target_distance = float(current_distance - float(delta))` so `target_distance` stays a plain `float` through every branch |
| `gl/canvas_base/camera_base.py` | 954 | same `numpy.float64` as above | reassigned at line 954 to `max_distance` (plain Python `float`, `500.0`) | same fix as line 952 |
| `gl/canvas_base/camera_base.py` | 1009 | `move_dir` is a `numpy.ndarray` (built from `self._right`/`self._forward`), divided by `mdn` (`numpy.float64` from `np.linalg.norm()`) | mypy's reported "variable has type `float`" here is unreliable, not a real concrete type | root cause: `self._right`/`self._forward` are declared bare (`self._right = None`) in `__init__` with no annotation (`gl/canvas_base/camera_base.py:256-257`), then reassigned real `np.ndarray` values elsewhere (`:732-733`) — same attribute-declared-twice pattern as §2a. Annotate `self._right`/`self._forward` as `np.ndarray \| None` in `__init__` first, then re-run mypy to get a trustworthy answer for this line |
| `gl/canvas_base/camera_base.py` | 1085 | `move_dir` (`numpy.ndarray`, from `self._right`/`self._up`) divided by `mdn` (`numpy.float64`) | same unreliable "float" report | same root cause as line 1009, via `self._up` instead of `self._forward` |
| `database/create_database/colors.py` | 100 | `bytes` | `int \| None` | cross-file cluster, same shape as Oct-19 audit's SQL-helper findings |
| `database/create_database/manufacturers.py` | 175 | `bytes` | `int \| None` | same cluster |
| `database/create_database/platings.py` | 98 | `bytes` | `int \| None` | same cluster |
| `database/create_database/seal_types.py` | 115 | `bytes` | `int \| None` | same cluster |
| `database/create_database/splice_types.py` | 96 | `bytes` | `int \| None` | same cluster |
| `database/create_database/temperatures.py` | 96 | `bytes` | `int \| None` | same cluster |
| `database/project_db/mixins/smooth.py` | 50 | `int` | `bool \| None` | one-off |

### 1f. Known false-positive patterns, still present (not re-fixed, not new bugs — logged for completeness)

- **`self.size`/`.context` shadowing an inherited Qt method** — already flagged in
  `CYTHON_REASSIGNMENT_AUDIT.md` as "a design smell, not this bug," and it's still there:
  `gl/canvas_3d/axis_overlay.py:620`, `gl/canvas_base/canvas_base.py:910,941,972`,
  `gl/canvas_pegboard/canvas.py:105` all do `self.size = (w, h)` on a `QOpenGLWidget` subclass,
  permanently replacing the inherited `size()` method with a tuple attribute. No annotation exists
  at these lines (that's why Cython doesn't care), but **any Python call to
  `widget.size()` after this assignment runs would raise `'tuple' object is not callable`** — a
  real runtime landmine independent of Cython. A grep for `.size()` calls on these specific widgets
  turned up none today, same latent-not-active situation as 1b.
- **Branch-dependent but unannotated locals** (CAD/datasheet file-type dispatch): `database/global_db/cad.py:180,184,211,215`
  and `datasheet.py:176,203` assign one of `QPdfDocument`/`QSvgRenderer`/`QPixmap`/`ezdxf.Drawing`
  to the same bare local depending on file extension — mypy flags every branch after the first, but
  since the name is never annotated, Cython leaves it fully dynamic. Not a bug, just noisy to a
  naive mypy scan.
- Same shape (bare local assigned one of several widget types per branch), same non-issue:
  `ui/widgets/text_ctrl.py:84` (`self.ctrl`), `ui/prop_ctrls/prop_base.py:59` (`self._sizer`),
  `database/db_connectors/mysql_connector/settings_dialog.py:310` (loop variable `w`).
- PySide6 `Signal()`/`SignalInstance` class-body idiom: 75 hits, all the same long-documented mypy/
  stub quirk, not a real reassignment.
- `None` assigned to a non-`Optional`-annotated **plain harness_designer class** attribute:
  ~420 sites (e.g. `start_position: _point.Point = None`, `editor3d: "_canvas3d.Canvas3D" = None`).
  Confirmed safe under category 2 (no C-level coercion for a plain Python class) — these are a
  static-typing nicety (the annotation *should* say `| None`) but not a crash risk. Not itemized
  individually; there are too many and none of them are dangerous.

---

## Part 2 — Other type conflicts

### 2a. Attribute declared twice per class (bare assignment + later explicit annotation) — causes a large mypy blind spot, not a runtime bug

`[no-redef]` (17 hits) traces back to one repeating shape: an attribute like `db_obj`,
`name_choices`, `circuit_choices`, `seal_type_choices`, `shrink_temp_choices`, `error_blob`, or
`_where_params` gets set once via a bare `self.x = value` in a helper method, and set *again* later
(usually in `__init__`) with an explicit `self.x: T = value`. Python doesn't care (same object,
two assignments), but mypy can't decide which declaration is authoritative, and that confusion
cascades into "Cannot determine type of X" (`[has-type]`, 257 hits) for **every other reference**
to that name in the same file — which is why `pjt_circuit.py` (65), `ui/editor_db/base.py` (40),
`global_db/splice.py` (37), `global_db/transition.py` (31) and `global_db/housing.py` (27) alone
account for the bulk of the 257. Confirmed by reading `database/global_db/mixins/name.py:68` vs
`:98` — both declare `self.db_obj` as `NameMixin | None`, identical type, just declared twice.
**Not a type conflict in the sense asked for (nothing actually changes type) — it's a style
inconsistency that happens to blind mypy to real problems for the rest of each affected file.**
Worth a pass to declare each of these once (in `__init__`, before any other method touches it) if
you want mypy to actually see the rest of those five files.

### 2b. Override signature conflicts (LSP violations) — real, worth a design pass

- **`drag_handlers/editor_{3d,pegboard}/wire_snap.py` and `wire.py`** (10 sites): each concrete
  drag handler narrows a base method's (`SnapProbeSet`/`WireDragMixin`) parameter type —
  e.g. the base declares `_get_view_object(self, obj: ObjectBase)`, the 3d/pegboard overrides only
  accept their own editor's concrete view-object type. Safe in practice only because nothing calls
  these polymorphically through the base type today; still a real Liskov violation if that ever
  changes (e.g. a future generic dispatcher).
- **Qt model/delegate overrides** (`ui/scraper_inspector/network_panel.py:51,57,70,146`,
  `json_tree.py:45-46`): override narrows `QModelIndex | QPersistentModelIndex` to just
  `QModelIndex`, or returns `QWidget | None` where Qt's base declares non-`None` `QWidget`. Very
  common, usually-harmless PySide6 pattern — flagged for completeness, low priority.
- **`logger/redirect.py`** (`_io._IOBase` override, 5 sites): the stdout/stderr log-redirect shim
  presents itself as a binary stream base class but reads/writes `str`. Intentional duck-typing for
  a logging shim; only a risk if something explicitly type-checks it as a real binary `IOBase`.

### 2c. Duplicate class names — mostly the documented "part-type fan-out" convention, a few worth a second look

A full-codebase scan for classes sharing a simple name found 93 duplicated names, 938 distinct
names total. The great majority are the already-documented, intentional patterns from `MEMORY.md`'s
"part-type fan-out" (`Housing`/`Wire`/`Seal`/`Terminal`/`Cavity`/`Boot`/`Cover`/`CPALock`/`TPALock`/
`Splice`/`Transition`/`WireLayout`/`WireMarker`/`WireServiceLoop`/`Generic`/`BundleLayout`/`Bundle`/
`ProjectModel`/`Note`/`Circuit` each have one unrelated class per layer —
`global_db`/`objects`/`objects_3d`/`objects_pegboard`/`objects_schematic`/`add_handlers`/
`drag_handlers`), the parallel mysql/sqlite connector implementations (`SQLTable`, `SQLField`,
`IntField`, etc.), and the parallel 3d/pegboard/schematic GL implementations (`Camera`, `Canvas`,
`CanvasWindow`, `Floor`, `MouseHandler`). None of those are conflicts — they're never both in scope
at once.

Already known (per `CLAUDE.md`'s `dep_trace.py` section, cited as a real past bug): **`CallbackMixin`**
is defined twice as two genuinely unrelated classes — `app_mixins/callback_mixin.py:11` and
`database/common_db/callback.py:13`. Still true today; nothing to add beyond what's already
documented, but repeating it here since it's exactly the shape this scan was asked to look for.

A handful of others aren't part of a documented fan-out and aren't obviously parallel
implementations either — worth a quick human glance, not flagged as bugs, just naming collisions
that could bite a future `grep`/forward-reference:
- `Config` — `config.py:601` (app-wide config) vs `ui/dialogs/housing_editor/config.py:6`
  (unrelated, dialog-local config)
- `ConfigDB` — `config.py:300` (a metaclass, `bases=['type']`) vs `database/config_db.py:125`
  (an ordinary class) — different roles, same name
- `_Config` — `ui/dialogs/part_orientation.py:65` vs `ui/dialogs/transition_editor/dialog.py:49`
- `Image` — `database/global_db/image.py:114` (DB entry) vs `image/__init__.py:24` (asset loader)
- `Line` — `geometry/line.py:26` (math primitive) vs `shapes/line.py:24` (renderable shape)
- `Splash` — `splash.py:31` (the startup splash screen) vs
  `database/project_db/pjt_bases.py:1370` (unrelated — worth checking what this second one actually
  is; it reads like an accidental name reuse)
- `ProcessWorker` — `process/image_process.py:210` vs `process/model_process.py:751` (likely a
  parallel-worker pattern, same shape as the fan-out, but not documented as such)
- `EditorCircuitPanel` — `ui/editor_circuit/editor_circuit.py:45` (a `class
  EditorCircuitPanel(EditorCircuitPanel)` self-import-and-subclass idiom used elsewhere in this
  codebase, e.g. `SnapProbeSet`) vs `editor_widget.py:1330`, which is a **wholly unrelated**
  `QDockWidget` subclass with the same name — this one pairing isn't the usual idiom, it's a
  coincidental collision.

### 2d. Conditional backend-selection imports — a structural mypy blind spot, not a bug

`database/db_connectors/__init__.py:13-45` imports `SQLTable`/`IntField`/etc. from
*either* `sqlite_connector` or `mysql_connector` depending on `Config.database.connector`, binding
both to the same names. Correct and intentional at runtime (only one branch ever executes), but
mypy statically sees both branches unconditionally, flags the second as "already defined by an
import" (`[no-redef]`, 2 hits: `db_connectors/__init__.py:32`,
`mysql_connector/connector.py:112`), and then can only ever type-check the *last* branch it saw —
meaning a real type error in the sqlite-specific path could be invisible to any future mypy run
over this file. Nothing to fix; just a limit on what a static scan like this one can see here.

### 2e. `"_splash.Splash" is not defined` — mypy resolution gap, not a runtime issue

91 occurrences, almost all in `database/create_database/*.py`'s `add_records(...)` helpers
(the ones `MEMORY.md` already notes are "kept for possible future use," not currently called from
`global_db/*.py`). Each file correctly imports `from ... import splash as _splash` under
`TYPE_CHECKING` — the class really does exist at `splash.py:31` — so this isn't a missing import,
it's mypy failing to resolve that one class through this module's particular import chain
(`splash.py` → `utils`/`config`, both imported in several directions elsewhere). Zero runtime
effect (it's `TYPE_CHECKING`-only); not investigated further here since it doesn't match either
thing this scan was asked to find, but flagged in case it's worth a `mypy --follow-imports=skip`
style investigation later.

---

## What this report does *not* cover

- `builder/` and `diagnostics/` (not Cython-compiled; scope-matched to the Oct-19 audit instead).
- No fixes were applied — this is a report only, per the scope of what was asked.
- The ~420 "`None` into a non-Optional plain-class attribute" sites and the ~450 bare-unannotated
  branch-dependent-type sites are real mypy findings but confirmed safe/non-issues per the rules
  above; they're summarized by count, not listed line-by-line, to keep this readable.
