# harness_designer/database/project_db/pjt_point_pegboard.py

## Line 337-530 (`is_referenced`, `delete`)
Same pattern as `pjt_point3d.py`: nine `OR` selects (lines 396-512), each a full scan of its table, on every point delete. See [pjt_point3d.md](pjt_point3d.md). `handlers/rope_pull_handler.py` also uses `OR` selects over the start/stop pegboard point columns of the wires table inside drag frames (`_lead_pieces`, `_is_owned_end`, `_node_for_point`); those are the more important call sites to move to an index union.
