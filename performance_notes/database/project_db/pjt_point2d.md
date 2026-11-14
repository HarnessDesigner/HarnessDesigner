# harness_designer/database/project_db/pjt_point2d.py

## Line 259-353 (`is_referenced`, `delete`)
Same pattern as `pjt_point3d.py`: four `OR` selects (lines 290, 301, 315, 321), each a full scan of its table, on every point delete. See [pjt_point3d.md](pjt_point3d.md) for the cost and the fix (answer `OR` from the per-column indexes).
