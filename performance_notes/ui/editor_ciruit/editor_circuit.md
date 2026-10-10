# harness_designer/ui/editor_ciruit/editor_circuit.py

## `EditorCircuitPanel.Refresh` - repaint only, no reload
`Refresh` calls `self.update()`, which only schedules a repaint and does not rebuild the rows. The reload path is `refresh()` in `editor_widget.py` (see `editor_widget.md`). An AST search of the package found no `.Refresh(` call whose receiver names the circuit editor; the callers that exist are on the 3D and schematic editors. The method is not on any hot path.

## `EditorCircuit` / `EditorCircuitPanel.__init__` - constructed once per window
Construction creates the panel once. No per-frame or per-row work happens here.
