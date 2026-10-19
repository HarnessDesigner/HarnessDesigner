## FILES

#### __init__.py

No imports found -- a plain empty package marker, no re-exports.

#### column_defs.py

Append-only `COLUMN_DEFS` catalog (no imports -- a pure data module) plus the default-visible-column sets for each table context. `COLUMN_DEFS[33]`, `'Branch'`, is `transition_only`: it lists the `branch_id`s of a transition's own branches that a wire is routed through, sourced from `pjt_wire_paths`. Transition tables default to `DEFAULT_VISIBLE_COLUMNS_TRANSITION`; a table whose column choice was already saved keeps it (the Branch column can be added back via the header's right-click column picker). As of 2026-09-29, the code that writes the `bundle_id`/`transition_branch_id` tags onto `pjt_wire_paths` does not exist yet, so the Branch column (and the transition table's rows generally, and the wire-highlight's bundle/branch part) is empty until that write path is built -- don't "fix" this by falling back to the old concentric-tables design; there is no fallback path, by design.

#### mdi_host.py

`PegboardTableHost(QtWidgets.QMdiArea)` and `_CursorAndCloseFilter(QtCore.QObject)` -- hosts a `wire_table.WireTable` inside an off-screen `QMdiSubWindow` purely so its rendered appearance can be grabbed as a texture (the same `WA_DontShowOnScreen` + `.grab()`-to-GL-texture technique explored for the Peg Board Editor's floating spreadsheet-style overlay tables; see MEMORY.md's Peg Board Editor entries for the fuller story of why a real Qt widget grabbed to a texture was chosen over a from-scratch GL-drawn table). `_CursorAndCloseFilter.eventFilter` intercepts cursor/close-button events on the hosted sub-window so they still behave sensibly despite the host never actually being shown on a real screen.

#### wire_table.py

`WireTable(_base.EditorList)` -- the peg-board wire table widget: columns driven by `column_defs.COLUMN_DEFS`, cross-table wire-selection sync (`wire_selected`/`wire_deselected` signals, part of the "selecting a wire row in any wire table lights everything it touches blue" highlight feature -- see `objects_pegboard/wire_highlight.py` and MEMORY.md's Peg Board entries), and the transition-only Branch column described under `column_defs.py` above. One table exists per transition (none per branch) -- `PJTTransition.wires` is de-duplicated so a wire entering one branch and leaving another, which appears on two branches' lists, is still exactly one row in the single table.
