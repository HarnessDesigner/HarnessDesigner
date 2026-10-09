# harness_designer/ui/dialogs/export_dialog.py

## `ExportDialog._collect_mesh_data` - whole-scene gather on the UI thread
When the export runs, `_collect_mesh_data` loops over the seven object collections of the project (boots, covers, housings, seals, splices, terminals, transitions) and, for each visible object, transforms its vertices and normals into world space. The export blocks the UI while it runs, and each object adds a line to the log through `_log_line` as it goes.

What is already right:
- Transforms are vectorised per object, over all of that object's vertices in one call. That is the right granularity, since the number of objects is small and the vertex arrays are large.
- The vertices are read from the VBO's in-memory arrays (`obj3d.vbo.vertices`), not re-read from the source model. This matches the project's "use the VBO, not the file" rule.

What to consider:
- Gathering runs on the UI thread. The export is modal, so this is a usability cost rather than a correctness one. Moving the gather plus the format write to a worker thread would keep the progress log live, but it means the VBO arrays must not be released or rebuilt while the worker reads them. That needs a check of when a VBO can be evicted before doing it.
- `_log_line` appends a line per object. For a project with many objects, the log widget repaints for each line. Batching the lines into one `appendPlainText` call at the end of each collection would avoid that, at no cost to the output.
- The concatenation at the end (`np.concatenate` over per-object lists) copies every vertex once more. For large projects it doubles peak memory for the mesh data. This is probably acceptable, but it is worth knowing about if exports get large.

The `getattr` lookups that used to select the collections by name were replaced with direct attribute access in this pass, and the `getattr(obj3d, 'smooth', ...)` lookup became `obj3d.smooth` (every 3D class in these collections defines `smooth`).
