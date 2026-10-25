## FILES

#### __init__.py

Package init for `project_db/mixins`; no real logic of its own. Column mixins for the `pjt_*` row classes in `project_db/` — most row classes compose several of these rather than defining position/angle/scale/visibility/name columns directly (this codebase leans heavily on mixins, so a method actually used by a class may not be defined on that class at all; check here before concluding otherwise or before adding an override).

#### angle2d.py

`Angle2DMixin` — schematic-view angle column/property, plus its paired `*Control` editor widget (`AngleProperty(axes='y')` for the schematic case).

#### angle3d.py

`Angle3DMixin` — 3D-view angle column/property (`AngleProperty(axes='y')`), plus its paired `*Control` editor widget. Binds `self._update_angle3d` by default for subclasses that cascade (e.g. `PJTHousing`). Euler angles are stored in the database alongside the derived quaternion (`geometry/angle/angle.py`'s `Angle` holds both forms) — any change to an angle MUST be made via the Euler angles, never the quaternion, since quaternion → Euler conversion suffers gimbal lock while Euler → quaternion does not; reload passes the stored Euler into `Angle.from_quat` rather than deriving it fresh.

#### angle3d_lock.py

`Angle3DLockMixin` — a boolean `angle3d_lock` getter/setter gating whether a row's `angle3d` participates in whatever would otherwise update it. The only `project_db` class using this is `PJTNote`.

#### angle_pegboard.py

`AnglePegboardMixin` — mirrors `angle3d.py` exactly, including the editor control, but for the peg-board view (`AngleProperty(axes='y')`). Important asymmetry vs. `position_pegboard.py`: this mixin's `angle_pegboard` property binds `self._update_angle_pegboard` by *default* — a subclass wanting a cascade only needs to override that *method* (not the property itself).

#### base.py

Shared base plumbing for this package's mixins (parallel to `global_db/mixins/base.py`, but for the project-row mixins rather than the catalog mixins).

#### color.py

`ColorMixin` — color column/property for a project row (e.g. `PJTNote`).

#### housing.py

`HousingMixin` — FK-to-owning-housing column/property, used by every housing-accessory row class (`pjt_cover.py`, `pjt_cpa_lock.py`, `pjt_tpa_lock.py`, `pjt_boot.py`, `pjt_seal.py`).

#### name.py

`NameMixin` — name column/property for a project row.

#### notes.py

`NotesMixin` — free-text notes column/property; also used by the concentric-cable row classes (`pjt_concentric.py`/`pjt_concentric_layer.py`/`pjt_concentric_wire.py`).

#### operating_temp.py

`OperatingTempMixin` / `WireOperatingTempMixin` -- for the four rows that carry heat (wire, wire service loop, splice, terminal). `operating_temp` is the user-settable column (NULL = not set); `ambient_c` is that or the default 20 C; `max_temp_c` parses the rated maximum out of the catalog part's `max_temp` name ("+105 °C"; "Unknown" is None, and an unrated part is never flagged); `temperature_c` and `over_temperature` ask the part's circuit (just the ambient when it is in none). `part_data()` is THE function the circuit solver calls to learn about a part: it builds a `circuit_solver.PartData` from `resistance`, a copper coefficient, the thermal resistance (`_thermal_resistance`: a wire's comes from its outside diameter and routed length, a terminal's or splice's is an assumed constant), the ambient and the rating. This is where the manufacturer's derating table is used: `_part_data` asks `_derating_limits()` (the part's `deratings` ambient rows as `(ambient, amps)` pairs; a factor row is scaled by `_rated_amps()`, which only `PJTTerminal` has) and, when `circuit_solver.calibrate_theta` can say, the part's thermal resistance comes from the table instead of the calculation. Bundling rows (`conductor_count`) are not used yet. The row classes need `part`, `resistance`, `circuit_id` (and, for the wire flavour, `length_mm` and `_resistance_over(length_mm)`). The wire flavour's `part_data()` reads `length_mm` ONCE (it walks the wire's whole route) and hands it to `_resistance_over` and to `_thermal_resistance(length_mm)`; `_part_data(resistance, thermal_resistance)` in the base builds the `PartData` around whatever a flavour worked out.

#### part.py

`PartMixin` — `part_id` FK column/property pointing at the matching `global_db` catalog part; the placed-instance side of the "same-name modules" pipeline's FK link (see `project_db/MAP.md`).

#### position2d.py

`Position2DMixin` — schematic-view position column/property (`PositionProperty(axes='xz')`), plus its paired `*Control` editor widget.

#### position3d.py

`Position3DMixin` — 3D-view position column/property (`PositionProperty(axes='xyz')`), plus its paired `*Control` editor widget. Its `position3d` property does **not** bind a cascade by default — a subclass needing one (e.g. `PJTHousing`) must override the *property itself* to add `.bind()`, unlike `angle3d.py`'s default-bound behavior.

#### position_pegboard.py

`PositionPegboardMixin` — mirrors `position3d.py` (3D position = `axes='xyz'`, peg-board position is likewise full 3-axis), including no default `.bind()` — a subclass needing a cascade overrides the property itself (see `PJTHousing.position_pegboard`). Y is always honored/stored at this DB layer; locking Y to 0.0 for a given object type is deliberately an object-layer decision, not a DB-layer one (see `project_db/MAP.md`'s `pjt_housing.py` entry).

#### scale2d.py

`Scale2DMixin` — schematic-view scale column/property. Defined but, as of this writing, not actually mixed into any `project_db` row class (no schematic-view scaling is in use yet) — don't assume it's wired up anywhere without checking first.

#### scale3d.py

`Scale3DMixin` — 3D-view scale column/property. Widely used: `pjt_housing.py`, `pjt_cover.py`, `pjt_cpa_lock.py`, `pjt_tpa_lock.py`, `pjt_boot.py`, `pjt_seal.py`, `pjt_splice.py`, `pjt_terminal.py`, `pjt_note.py`.

#### scale_pegboard.py

`ScalePegboardMixin` — peg-board-view scale column/property, mirroring `scale3d.py`. Used by `pjt_housing.py`, `pjt_seal.py`, `pjt_splice.py`, `pjt_terminal.py`.

#### smooth.py

`SmoothMixin` — a boolean "smooth" rendering-style flag column/property, mixed into most placeable row classes.

#### start_stop_position2d.py

`StartStopPosition2DMixin` — schematic-view start/stop position pair, for a row with two ends rather than one anchor point (e.g. a splice's two ends).

#### start_stop_position3d.py

`StartStopPosition3DMixin` — 3D-view start/stop position pair, same shape as `start_stop_position2d.py`.

#### start_stop_position_pegboard.py

`StartStopPositionPegboardMixin` — mirrors `start_stop_position3d.py` for the peg-board view. Used by `pjt_wire.py`, `pjt_bundle.py`, `pjt_wire_service_loop.py`.

#### table_hidden.py

`TableHiddenMixin` — a boolean `is_table_hidden` getter/setter for an anchor's own floating peg-board data-table overlay (collapsed/hidden state of the table itself, not the anchor's own visibility). Paired with `table_position_peg.py`'s `TablePositionPegMixin`; mixed into `pjt_housing.py`/`pjt_bundle.py` but deliberately NOT `pjt_transition.py` (which keeps `TablePositionPegMixin` without this) or `pjt_transition_branch.py` (lost both in the 2026-09-29 "one table per transition, not per branch" change — its `table_hidden` schema column is left unused).

#### table_position_peg.py

`TablePositionPegMixin` — the data-table-overlay position mixin (`table_point_peg_id`), deliberately NOT renamed to "pegboard" despite living alongside `position_pegboard.py` — a distinct feature from an anchor's own `position_pegboard`, since it positions the anchor's floating spreadsheet-style table (see `project_db/pjt_pegboard_table.py`), not the anchor itself. Mixed into `pjt_housing.py`, `pjt_bundle.py`, `pjt_transition.py`, and (formerly, now removed) `pjt_transition_branch.py`.

#### visible2d.py

`Visible2DMixin` — `is_visible2d` column/property for the schematic view.

#### visible3d.py

`Visible3DMixin` — `is_visible3d` column/property for the 3D view.

#### visible_pegboard.py

`VisiblePegboardMixin` — `is_visible_pegboard` column/property, mirroring `visible3d.py`'s/`visible2d.py`'s `is_visible3d`/`is_visible2d` naming. Originally read/wrote a `visible_pegboard` column (a naming bug) — fixed to `is_visible_pegboard`, matching the already-correct `create_database` schema. Controls peg-board rendering, notably for a wire/wire-layout when the wire is inside a bundle (a known "wire fully hidden" rendering bug is tracked in `TODO.md`, not fixed as part of adding this mixin).
