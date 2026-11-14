# harness_designer/ui/scraper_inspector/network_panel.py

NetworkModel(QtCore.QAbstractTableModel) and NetworkPanel(QtWidgets.QWidget) -- the captured-requests table, backed by a rolling window of 2000 entries (...scraping.capture_model) so a long scraping session doesn't grow this table's memory unbounded. Selecting a row feeds response_panel.py's detail view.

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `NetworkModel.rowCount` (line 52-56): no loops or allocations found.
- `NetworkModel.columnCount` (line 59-63): no loops or allocations found.
- `NetworkModel.headerData` (line 66-71): no loops or allocations found.
- `NetworkModel.data` (line 74-97): no loops or allocations found.
- `_FilterModel.filterAcceptsRow` (line 151-162): no loops or allocations found.
None of them allocates or loops in a way the AST pass flags, so they are cheap per call.

Status: static read of the code only. Nothing here has been profiled.
