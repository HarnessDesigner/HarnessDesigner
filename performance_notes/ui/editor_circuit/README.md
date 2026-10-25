# performance_notes/ui/editor_circuit

Covers `harness_designer/ui/editor_circuit/`.

- [editor_widget.md](editor_widget.md) - row building, project lookups, the table model and delegates, and reload
- [design_rules.md](design_rules.md) - bundle lookup helpers and suggestion generation
- [bitmaps.md](bitmaps.md) - connector pixmap rendering
- [editor_circuit.md](editor_circuit.md) - the dock wrapper and its `Refresh`

## Functional bugs found (not fixed; behaviour kept)
1. **Bundle routing never matched.** FIXED 2026-10-24. The dock now reads a circuit's bundles through `PJTWire.bundles` (the route rows' `bundle_id` tag, or the concentric layers for an untagged bundle), keeps the bundle ids as well as the names, and `bundle_wire_ods` reads each wire's real outside diameter, so the split suggestions can appear.
2. **Connector images never load.** `PJTHousing` has no `image`, `icon` or `pixmap` attribute, so `_load_housing_pixmap` always returns None and every connector takes the placeholder path. It now returns None directly.
3. **Dead attribute names dropped.** `conductor_material`, `conductor`, `hex_code`, `thumbnail`, `photo` and `picture` are not defined anywhere in the package. The wire colour reads the catalog colour's name and RGB (`color`, `stripe_color`), and the conductor is `core_material` (a `Plating`: `description`, `symbol`, `color`), NOT `material` (the insulation). Reading `part.material` as the conductor was the cause of the 2026-10-24 crash below.

## Review status
All files in the folder have now been reviewed for performance. The hot paths are the per-cell `data()` path and the pixmap caches (see `editor_widget.md` and `bitmaps.md`).

## Review 2026-10-24 (fixed)
- `show_row` crashed on a circuit with no wires (`od_mm` is `None`).
- The "N errors" count counted every circuit (operator precedence in `_update_count`).
- The build worker hid any circuit that failed to read (`except: pass`), and an error in the rules pass ended the worker without `finished`, leaving the dock stuck (`refresh` refuses while a build "is running"). Now a failed circuit gets an error row, failures are logged, and `finished` is always emitted.
- A refresh asked for while a build was running was dropped, so changing project could show the old project's rows. Now it is remembered and the stale result is ignored.
- The dock reported a terminal's `voltage_drop` (the drop the user ALLOWS at that load) as the measured drop, summed rated loads, and checked only the first wire's gauge. It now uses the solver: real drop to each load, real current in each wire (parallel wires share it), and it flags over-temperature parts and drops over what the user allows.
- Drag and drop wrote ids as the `repr` of bytes and split on commas (a comma byte in an id broke the drop), and popped several rows by stale indices. Numeric columns sorted as text.
- Connector pictures are built as `QImage` on the worker thread (a `QPixmap` may only be made on the GUI thread).
- Not changed: the design rules still use the fixed NEC/ISO ampacity table, not the part's own derating table; the "Resistance" column is still the plain sum of the wires' and wire service loops' resistances; dragging rows only reorders the view.
- The panel was itself a `QDockWidget`, so `DockBase`'s dock held a second dock (two title bars, two float and close buttons: a window inside a window). It is a plain `QWidget` now. Checked with the real `EditorCircuit` in a real `QMainWindow`: one dock widget in the window before there were two.

## Crash 2026-10-24 (fixed; found from `%APPDATA%\HarnessDesigner\log`)
- The app was ended by one exception raised while a circuit was selected: `AttributeError: 'Material' object has no attribute 'lower'`. Chain: `_on_row_selected` -> `CircuitDetailPanel.show_row` -> `cached_wire_pixmap` -> `make_wire_pixmap` -> `conductor_color`. `_build_row` had stored `Wire.material` (the INSULATION, a `Material` row) as the conductor material, and `conductor_color` called `.lower()` on it. `run.py`'s own comment records that this PySide6 build aborts the whole process once an exception escapes a Qt slot or override, so a plain `AttributeError` became a dead app.
- Fixed at the source: `_build_row` reads the wire colour from the catalog `Color` (`.name`, `.rgb`), treats the nil id (`NIL_UUID.bytes`) as "not set" (no stripe, no conductor), and takes the conductor text from `core_material.description` and its swatch from `core_material.color`. `conductor_color` coerces whatever it is given with `str()` and falls back to the default; `make_wire_pixmap`/`cached_wire_pixmap` take the conductor swatch colour (`conductor_hex`) and it is part of the cache key.
- Second fault in the same area: `QPainter` was left active when a draw call raised, and Qt aborts the process (`Cannot destroy paint device that is being painted`, then `Fatal Python error: Aborted`). Every painter in `bitmaps.py` now runs inside the `painting(device)` context manager, which always calls `end()`. A colour string Qt cannot read draws the fallback grey (`_valid_color`) instead of black.
- Third fault: `CircuitTableModel.cell_edited` was `Signal(int, int, object)` but is emitted with the circuit's bytes id first, so an edit never reached `_on_cell_edited`. It is `Signal(object, int, object)` now.
- Guard: every Qt-facing method of the dock (model `data`/`setData`/`mimeData`/`dropMimeData`, proxy `lessThan`/`filterAcceptsRow`, the delegates' `paint`/`sizeHint`/`displayText`, the panel's slots) is wrapped by `_guarded`: an exception is logged once per (method, error) with its traceback and a harmless fallback is returned, so a display bug in the dock cannot end the process. The price: a bug there now shows up as a log entry (and a blank cell), not a crash dump.
- Checked against the user's real database (a copy): the wires' colour ids are real `Color` rows (`Blue`, `Green`), the conductors are `Plating` rows whose symbol maps to a colour that exists (`Ag/Cu`, `Ni/Cu`, `Sn/Cu/Cu`, ...). Not checked: the dock running in the real app (it has never been opened with real circuits there).
- Not audited: other `QPainter` uses elsewhere in the repo may also lack a `try/finally`.

## Wire pictures, To Pin and Delete Circuit (2026-10-25)
- The wire column and the right panel used one swatch from the FIRST wire. A circuit changes wire where it branches off a splice or another terminal, so the row now holds one `WireInfo` per distinct wire part (wire service loops included), each with its own data and a picture from `images.build_wire`: 100x25 in the table (stacked, the row grows) and 200x50 in a card of the new Wires tab, centred above that wire's data. The old swatch painter is gone (see `bitmaps.md`).
- The Gauge column lists every distinct gauge; the Totals tab keeps the circuit-wide totals and the From/To pins.
- A To Pin column follows To, as From Pin follows From.
- Right-click a row: Delete Circuit, after a Yes/No that says it cannot be undone. Every member's circuit becomes NULL; nothing else is deleted.
- Wire service loops count as wire in the totals (length, resistance, weight) and in the per-wire overcurrent rule (`_add_wire_totals`), as the circuit's own `resistance`, `wire_length_mm` and `wire_weight_g` already did; a loop is taken to be bundled when any wire of its circuit is.
