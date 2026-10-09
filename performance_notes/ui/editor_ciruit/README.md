# performance_notes/ui/editor_ciruit

Covers `harness_designer/ui/editor_ciruit/`.

- [editor_widget.md](editor_widget.md) - row building, project lookups, the table model and delegates, and reload
- [design_rules.md](design_rules.md) - bundle lookup helpers and suggestion generation
- [bitmaps.md](bitmaps.md) - wire and connector pixmap rendering and caching
- [editor_circuit.md](editor_circuit.md) - the dock wrapper and its `Refresh`

## Functional bugs found (not fixed; behaviour kept)
1. **Bundle routing never matches.** `PJTBundle.wires` returns `PJTWire` objects, and `PJTWire` has no `wire` attribute, so the `bw.wire` lookup in `_bundles_for_circuit` (editor_widget.py) and `bundle_wire_ods` (design_rules.py) never succeeds. Both now return `[]`.
2. **Connector images never load.** `PJTHousing` has no `image`, `icon` or `pixmap` attribute, so `_load_housing_pixmap` always returns None and every connector takes the placeholder path. It now returns None directly.
3. **Dead attribute names dropped.** `conductor_material`, `conductor`, `hex_code`, `thumbnail`, `photo` and `picture` are not defined anywhere in the package. The wire colour reads `color.name`, and conductor material reads `part.material`.

## Review status
All files in the folder have now been reviewed for performance. The hot paths are the per-cell `data()` path and the pixmap caches (see `editor_widget.md` and `bitmaps.md`).
