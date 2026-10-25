## FILES

#### __init__.py

Package init for `mixins`; no real logic of its own. Column mixins for the global parts-catalog row classes in `global_db/` — a part entity (e.g. `Cavity`, `Housing`) typically inherits several of these rather than defining every column property itself; check here before concluding a property doesn't exist on a class.

#### adhesive.py

Adhesive reference mixin.

#### base.py

`BaseMixin` and shared plumbing, including `NIL_ID` — the all-zero NIL-id sentinel used by the lookup-reference mixins (see `global_db/MAP.md`'s NIL-id convention note, under `housing.py`).

#### cavity_lock.py

Cavity-lock reference mixin — converted to the NIL-id → `None` convention.

#### color.py

Color reference mixin — NOT yet converted to the NIL-id → `None` convention (the precedent for the conversion is `global_db/wire.py`'s own `stripe_color` column instead, a reference handled outside this mixin).

#### compat_housings.py

Compatibility-list mixin: which housings a given part is compatible with.

#### compat_seals.py

Compatibility-list mixin: which seals a given part is compatible with.

#### compat_terminals.py

Compatibility-list mixin: which terminals a given part is compatible with.

#### derating.py

`DeratingMixin` (terminal, wire, splice) -- the manufacturer's derating table of the part. `load_deratings()` asks the `deratings` table to read this part's whole table now (the part tables' `__getitem__` call it as they load a part; it does nothing while `GLBTables` is still starting up and the table does not exist yet), `reload_deratings()` drops and re-reads it, and `deratings` is the tuple of `Derating` rows from `DeratingsTable`'s cache. The part holds no state of its own.

#### description.py

Basic text-column mixin for a free-text description field.

#### dimension.py

`DimensionMixin` — composite width/height/length setter (`size`), one UPDATE instead of three individual column writes. Don't bypass it with three separate column setters when a caller wants to change all three dimensions at once.

#### direction.py

Lookup-table reference mixin for `directions` — converted to the NIL-id → `None` convention.

#### family.py

Lookup-table reference mixin for `families` — converted to the NIL-id → `None` convention; the matching editor control is disabled when unset since family/series name choices are keyed off the manufacturer.

#### gender.py

Lookup-table reference mixin for `genders` — converted to the NIL-id → `None` convention.

#### image.py

Generic image-reference mixin.

#### manufacturer.py

Lookup-table reference mixin for `manufacturers` — converted to the NIL-id → `None` convention.

#### material.py

Lookup-table reference mixin for `materials` — NOT yet converted to the NIL-id → `None` convention.

#### model3d.py

3D-model reference mixin (points at a `models3d` row).

#### name.py

Basic text-column mixin for a part's name.

#### part_number.py

Basic text-column mixin for a part's catalog part number.

#### plating.py

Lookup-table reference mixin for `platings`.

#### protection.py

Lookup-table reference mixin for `protections` — NOT yet converted to the NIL-id → `None` convention.

#### resource.py

Generic resource-reference mixin (datasheet/cad-style file attachments).

#### series.py

Lookup-table reference mixin for `series` — converted to the NIL-id → `None` convention; same disabled-when-unset control behavior as `family.py`.

#### temperature.py

Lookup-table reference mixin for `temperatures` — converted to the NIL-id → `None` convention (`min_temp`/`max_temp`).

#### weight.py

Weight column mixin.

#### wire_size.py

Wire-size column mixin (dia/cross/awg). Wire-size columns can be NULL even though derivable from a sibling column (conversion helpers exist in `utils/wire_conversions.py`, outside this directory) — NULL backfill is handled by a separate maintenance utility invoked from an app menu, not by inline fallback logic. When writing code that reads a possibly-NULL wire-size column, only add NULL-safety (`IS NULL OR` guards, skip-if-None) — don't derive the value inline with a 3-way fallback chain (dia ← cross ← awg).

#### wire_type.py

`WireTypeMixin`/`WireTypeControl` — used by `global_db/wire.py` to reference the `wire_types` lookup table.
