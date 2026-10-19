## FILES

#### __init__.py

Package init for the circuit table editor dock; no content beyond the standard package marker. Note: "ciruit" is a genuine pre-existing typo in the real directory name itself (not a doc error) — kept as-is per repo convention, do not "fix"/rename it.

#### bitmaps.py

Pixmap generation for the circuit table's image columns — `make_wire_pixmap` (cylinder-gradient-shaded wire swatch), `scale_housing_pixmap`, `placeholder_connector_pixmap`, and `cached_wire_pixmap` (a cache wrapper over `make_wire_pixmap`).

#### design_rules.py

The DRT (design-rule-check) logic — `Severity` enum, `DRTIssue`/`SplitSuggestion` dataclasses, AWG/mm² conversion helpers (`awg_to_mm2`, `awg_to_od_mm`, `resolve_awg`), `run_drt(row)` (the actual rule evaluation), and `generate_suggestions(row, project_db)` (bundle-split suggestions, using `bundle_wire_ods`/`find_bundle_by_name`).

#### editor_circuit.py

Defines `EditorCircuit(DockBase)` — the dock wrapper, and its own `EditorCircuitPanel(editor_widget.EditorCircuitPanel)` — a thin subclass of the "real" panel class defined in `editor_widget.py`, adding only a mainframe-aware `__init__` and a no-op-safe `Refresh()`. `EditorCircuitPanel` is defined twice in this directory — once here (the thin `DockBase`-adjacent wrapper subclassing the other one) and once in `editor_widget.py` (the real `QtWidgets.QtDockWidget` implementation); when looking for "the" `EditorCircuitPanel`, check which module imported it — the real logic is in `editor_widget.py`'s version.

#### editor_widget.py

The real implementation (~1800 lines, the bulk of this directory) of the circuit table editor dock: a spreadsheet-style view of every circuit in the project (one row per circuit/wire), with per-row design-rule-check (DRT) severity, wire/connector thumbnails, and split suggestions for oversized bundles. `CircuitRow` is one built row's display data (wire/connector pixmaps, DRT issues, bundle membership, etc.), built by `_build_row()`/`_build_worker` off the UI thread (`_BuildWorker(QtCore.QObject)` plus a QThread) so loading a large project's circuit table doesn't block the GUI — row building is explicitly threaded to avoid blocking the GUI on large projects, so don't move DB/row-construction work back onto the UI thread without re-checking why this split exists. `CircuitTableModel(QtCore.QAbstractTableModel)` is the Qt model backing the table, including drag-and-drop support (`mimeTypes`/`mimeData`/`dropMimeData`). `CircuitFilterProxy(QtCore.QSortFilterProxyModel)` does text + severity filtering over the model. `WireDelegate`, `ConnectorImageDelegate`, `NumericDelegate` (`QtWidgets.QStyledItemDelegate` subclasses) handle custom cell painting for wire color/stripe swatches, connector thumbnails, and numeric formatting. `CircuitDetailPanel` is the selected row's detail view (connector strip image, full text fields). `CircuitTableView(QtWidgets.QTableView)` is the table widget itself, wired to `mainframe`. `EditorCircuitPanel(QtWidgets.QDockWidget)` is the actual top-level panel — builds the toolbar (severity filter, etc.), owns the model/proxy/view/detail-panel, and exposes `load_project()`/`refresh()`/`highlight_circuit(circuit_db_id)` — this is the real `EditorCircuitPanel` (see `editor_circuit.py`'s note above).
