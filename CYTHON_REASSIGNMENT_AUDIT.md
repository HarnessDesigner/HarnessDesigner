# Cython variable-reassignment audit (2026-10-19)

Ran mypy over `harness_designer/` (803 files), filtered to `[assignment]`-class errors (483
candidates across 182 files), and triaged all of them via 5 parallel agents against the specific
known bug: a type-annotated local/parameter reused for an incompatible type within the same
function crashes only once Cython-compiled (see MEMORY.md's "Cython variable type reuse" entry).

## The real rule (reconciled across all 5 triage passes + your live QSize crash)

Three categories, not two:

1. **Builtin primitives/containers** (`int`, `float`, `str`, `bool`, `complex`, `list[...]`,
   `tuple[...]`, `np.ndarray`) — get a real Cython-native C-level type. Reassigning within the same
   scope to an incompatible type is a **confirmed crash risk**.
2. **harness_designer's own plain Python classes** (`Point`, `Angle`, `Wire`, `MainFrame`,
   `GLEvent`, dialogs, material classes, etc. — *including* ones that subclass a Qt type, since the
   subclass itself is still an ordinary `class X:` definition) — verified empirically in MEMORY.md:
   **no coercion check at all**, stays a generic `PyObject*` the whole time. Reassigning between two
   of these is safe.
3. **Raw third-party C-extension types used directly** (Qt/Shiboken classes like `QSize`,
   `QColor`, `QPixmap`, `QHBoxLayout`/`QVBoxLayout`, `QPoint` — not subclassed by this project, used
   as-is) — **newly confirmed risky** by your `tuple[int, int] → QSize` crash. Not covered by the
   existing MEMORY.md entry, which only tested category 2.

Category 1 and 3 hits below are the real action items. Category 2 hits that agents initially
flagged (object-vs-object, both harness_designer's own classes) are listed separately as **not
actually at risk**, per the verified rule — included for completeness, not as a to-do list.

## Confirmed true positives — fix these (grouped by file)

**SQL/field-join helpers (`list[str] | None` → `str` via `', '.join(...)`, identical shape
throughout)** — give the joined value its own name (`..._str`/`..._sql`):
- `database/create_database/boots.py:155`, `bundle_covers.py:209`, `covers.py:226`,
  `cpa_locks.py:142`, `housings.py:272-278` (7 fields), `seals.py:158-159`, `terminals.py:177-178`,
  `tpa_locks.py:119`, `transition_branches.py:96`
- `database/global_db/bases.py:625` (`*args: str` → joined)
- `database/project_db/pjt_bases.py:757,758,782,879`, `pjt_circuit.py:202`,
  `database/utils.py:45,50`, `debug.py:172`

**`np.ndarray`-typed setter param reused as `list`:**
- `objects/objects_3d/cavity.py:483,518`, `database/project_db/pjt_cavity.py:408,432`

**`list[str]` compat-field setters → `str`:**
- `objects/objects_3d/housing.py:503,574,646,715`

**Primitive `str`/`int`/`bytes` mixed with `None` on a non-Optional annotation:**
- `database/global_db/bases.py:247` (`__table_name__: str = None`)
- `objects/objects_3d/housing.py:866` (`bytes | None` into non-Optional `bytes`-typed slot)
- `ui/mainframe.py:195,3091` (`self._selection_source_editor: str = None`)
- `database/create_database/temperatures.py:128,130` (`name: str` reused for `int`)
- `database/create_database/transition_branches.py:124` (`branch_id: bytes | None = 0`) —
  **FIXED 2026-10-20**: not a bad default, a bad annotation. `pjt_transition_branches.branch_id`
  is `_con.IntField(no_null=True)`, so `int` is correct and `0` was always the right default;
  changed the annotation to `int`. This was the live crash: Cython type-checks a typed
  parameter's default against its annotation when building the function object, so importing
  this module (via `TransitionBranchesTable._table_needs_update`, on every `open_database`) raised
  `TypeError: Expected bytes, got int` at import time in the compiled build.

**numpy `ndarray` mixed with a harness_designer class (category 1 × category 2, still risky
since the ndarray side is real):**
- `geometry/angle/angle.py:129,156,203,460,465,472,709`
- `geometry/angle/quaternion.py:65,92,113`
- `geometry/point.py:308,334,360,386,786` (`p` ndarray → `Point`, closest match to the original
  documented `delta`→`Point` bug)
- `gl/canvas_base/camera_base.py:1301` (`best_idx` int → `None` across branches)

**Raw Qt/Shiboken extension types (category 3 — the newly-confirmed risk, same shape as your
`QSize` crash):**
- `ui/prop_ctrls/prop_base.py:63` (`sizer`: `QHBoxLayout` → `QVBoxLayout`)
- `ui/widgets/triple_float_ctrl.py:51` (`group`: `self` → `QtWidgets.QGroupBox`)
- `ui/widgets/cad_datasheet_ctrl.py:326` (`delta`: `QPoint` → `int`)
- `ui/dialogs/error.py:94` (`icon`: `StandardPixmap` enum → `QPixmap`)
- `ui/prop_ctrls/color_prop.py:78,119,124` (`color`: `QColor`/`QtGui.QColor` → harness_designer's
  own `Color` class)

**Other same-scope reuse (primitive/container, no extension types):**
- `ui/scraper_inspector/source_viewer.py:441` (`candidate`: `str` → `list[str]`)
- `ui/widgets/float_ctrl.py:163` (`value`: project's `Decimal` → `float`)
- `resources.py:251,259,370` (`ext`: `str` → `list`)
- `objects/objects_3d/splice.py:124-125`, `objects/objects_pegboard/splice.py:104-105`
  (`area1`/`area2`: `list[float]` → `float` via `sum()`)
- `database/project_db/table_data.py:157` (`rows`: `list` vs `dict_values` across branches)

## Flagged but NOT actually at risk (category 2 — plain class vs. plain class, verified safe)

Initially flagged by individual triage passes before the full picture was reconciled; included so
nothing looks silently dropped, not as something to fix:
- `gl/canvas_base/mouse_handler_base.py` — `event`: `GLEvent` → `GLObjectEvent` (10 occurrences
  across 6 methods). Both are plain classes in `gl/events.py`, siblings of `_GLEventBase`.
- `objects/objectsvar/base_var.py:1154` — `material`: `Metallic` → `Glowing` (both this project's
  own material classes).
- `objects/project.py:760` — `dlg`: `OpenProjectDialog` → `AddProjectDialog` (both this project's
  own dialog subclasses).
- `objects/terminal.py:394` — `view_obj`: `objects_3d.Wire` → `objects_pegboard.Wire` (both plain
  classes).
- `ui/datasheet_viewer/viewer.py:286` — `ctrl`: `PDFViewer` → `ImageViewer` (both this project's
  own viewer widgets).
- `gl/object_picker.py:199` — `pool`: `OBB` → `AABB` (both this project's own bounds classes).

## Everything else (≈400 candidates)

The large majority were false positives from a handful of recurring, now-identified shapes:
- PySide6's `Signal()`/`SignalInstance` class-body declaration idiom (a mypy/stub quirk, not a
  reassignment) — by far the single biggest false-positive cluster.
- `LazyTabMixin`/`PartMixin` base-class attribute declarations narrowed by subclasses (class-level,
  not a same-function reassignment).
- `__dump_schema__` tuple-shape overrides (subclass narrowing a base's generic tuple annotation).
- `self.size`/`self.context`/`self.x`/`self.y`/`self.window` shadowing inherited Qt methods
  (`QOpenGLWidget.size()`, `.context()`, `QWidget.x()`/`.y()`/`.window()`) — a naming collision
  with an inherited method's declared type, not a same-scope reassignment. Worth a separate look as
  a design smell, but not this bug.
- Bare, unannotated locals (Cython only fixes the type of an **explicitly annotated** name in this
  build — `language_level='3'`, no `infer_types`).
- `None` assigned to a plain-object-typed attribute (safe per category 2) — only risky when the
  annotation is actually a primitive (`str`, `int`, etc.), listed above where that applies.
