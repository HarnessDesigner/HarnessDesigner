# performance_notes/ui/editor_circuit

Covers `harness_designer/ui/editor_circuit/`.

- [editor_widget.md](editor_widget.md) - row building, project lookups, the table model and delegates, and reload
- [design_rules.md](design_rules.md) - bundle lookup helpers and suggestion generation
- [bitmaps.md](bitmaps.md) - connector pixmap rendering
- [editor_circuit.md](editor_circuit.md) - the dock wrapper and its `Refresh`

## Functional issues still open (not performance; behaviour kept)
2. **Connector images never load.** `PJTHousing` has no `image`, `icon` or `pixmap` attribute, so `_load_housing_pixmap` always returns None and every connector takes the placeholder path. It now returns None directly.
3. **Dead attribute names dropped.** `conductor_material`, `conductor`, `hex_code`, `thumbnail`, `photo` and `picture` are not defined anywhere in the package. The wire colour reads the catalog colour's name and RGB (`color`, `stripe_color`), and the conductor is `core_material` (a `Plating`: `description`, `symbol`, `color`), NOT `material` (the insulation). Reading `part.material` as the conductor was the cause of the 2026-10-24 crash below.

## Review status
All files in the folder have now been reviewed for performance. The hot paths are the per-cell `data()` path and the pixmap caches (see `editor_widget.md` and `bitmaps.md`).

## Wire pictures, To Pin and Delete Circuit (2026-10-25)
- The wire column and the right panel used one swatch from the FIRST wire. A circuit changes wire where it branches off a splice or another terminal, so the row now holds one `WireInfo` per distinct wire part (wire service loops included), each with its own data and a picture from `images.build_wire`: 100x25 in the table (stacked, the row grows) and 200x50 in a card of the new Wires tab, centred above that wire's data. The old swatch painter is gone (see `bitmaps.md`).
- The Gauge column lists every distinct gauge; the Totals tab keeps the circuit-wide totals and the From/To pins.
- A To Pin column follows To, as From Pin follows From.
- Right-click a row: Delete Circuit, after a Yes/No that says it cannot be undone. Every member's circuit becomes NULL; nothing else is deleted.
- Wire service loops count as wire in the totals (length, resistance, weight) and in the per-wire overcurrent rule (`_add_wire_totals`), as the circuit's own `resistance`, `wire_length_mm` and `wire_weight_g` already did; a loop is taken to be bundled when any wire of its circuit is.
