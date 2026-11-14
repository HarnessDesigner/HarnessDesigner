# harness_designer/ui/pegboard_table/wire_table.py

The peg-board wire table (63 KB: columns from `column_defs`, a row per conductor or cable, cross-table selection sync). The costs are in building rows, not in painting (Qt paints the cells).

## Table calls inside loops (lines 515-523, 716, 966) — in-memory, not round trips
The calls the AST pass finds inside loops here are on project tables, which are answered from the in-memory store (`database/README.md`); each is a dict lookup, so a table rebuild is O(rows x columns) of cheap lookups. The lines to watch are the ones that touch global catalog wrappers (a wire's `part`), which cost one `SELECT` the first time a wrapper is created.

## Line 934-980 (`_cavity_names_for_wire`) — three nested loops
Walks the wire's chain of pieces, junctions and cavities to build the cavity names for the Cavity columns, called per row. For a table with hundreds of rows and long chains (a lead cut by service loops) it is O(rows x chain length x cavities). Cache the names per wire for the life of one rebuild.

## Line 1271-1325 (`live_drag_step`) — header drag
A loop over the header sections for each drag event, with a few header calls per iteration. Cheap.

## Memory
Row widgets and cell pixmaps (the wire pictures) belong to Qt; the pictures come from `image/wire_images.py`, whose cache is unbounded (see `image/wire_images.md`), so a table that shows many distinct colours holds many 160 KB images.
