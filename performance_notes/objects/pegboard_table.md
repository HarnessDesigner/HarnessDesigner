# harness_designer/objects/pegboard_table.py

PegboardTable(ObjectBase) — the wrapper for a floating wire table, still named for its DB table; the real peg-board-view rendering lives in objects_pegboard/table.py's Table.

Cold path (60 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
