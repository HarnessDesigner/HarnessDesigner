# performance_notes/ui/editor_obj

Covers `harness_designer/ui/editor_obj/`.

- [editorobj.md](editorobj.md) - object selection and the per-table property control swap
- `prop_grid.py` - no notes. `PropertyGrid` is not used anywhere in the package (see the functional issue below).

## Functional issue (flagged, not fixed)
- `prop_grid.py` `PropertyGrid.Append` calls `item.Realize()` and `item.GetLabel()`, but neither method is defined anywhere in the package, and `PropertyGrid` has no callers. The class is dead code, so this has never run.
