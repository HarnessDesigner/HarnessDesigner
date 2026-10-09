# performance_notes/ui/pegboard_table

Covers `harness_designer/ui/pegboard_table/`.

## Reviewed
- `wire_table.py` (about 1,080 lines) was read for its cell-text and icon paths, and for its column picker.
- `mdi_host.py` and `column_defs.py` were checked for structure only.

## Notes
- `WireTable._get_cell_text` computes the seven circuit "math" columns (resistance, volts, load, voltage drop, weight, and length) by reading the `PJTCircuit` object for each row. The table asks for these cells on every repaint of the visible rows. Whether that is costly depends on whether `PJTCircuit` caches those values between reads. That has **not** been checked yet. It is the first thing to look at in this folder.
- `_get_icon` builds the colour and material icon for each row. The same composite-icon issue found in `ui/toolbar` may apply here. Not measured.
