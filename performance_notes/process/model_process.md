# harness_designer/process/model_process.py

## Line 53-94 (`_ocp_read_shape`) — tessellates every face of a BREP shape
Runs `BRepMesh_IncrementalMesh` on the whole shape, then walks every face and copies every node and triangle into Python lists before converting to NumPy. Python-level appends per vertex and per triangle make this the slowest part of a model load for large parts. A NumPy-backed copy or chunked extraction would be faster. The tessellation itself is the dominant cost for most files.

## Line 97-130 (`_load_with_assimp`) — concatenates per-mesh arrays
Linear in the total vertex count, with `np.concatenate`. Fine.

## Line 191-244 (`_load_step`) — may tessellate the file twice
Tessellates at the default settings. If the triangle count is above `max_triangle_count`, it re-reads the file and tessellates again at coarse settings (`_read_loose`). The file is parsed twice in that case. The docstring explains why re-tessellating is preferred to decimating, so the second pass is intentional.

## Line 294-306 (`_center_model`) — in-place centering
Subtracts the centroid in place. Linear. Fine.

## Line 315-380 (`_reduce_triangles`) — mesh decimation
Runs the `pyfqmr` simplifier. This is the one step where the target triangle count is enforced. Cost depends on the input size.

**Argument mismatch (flagged, not changed):** `ThreadWorker.run` calls `_reduce_triangles(vertices, faces, target_count, aggressiveness, iterations)` (line 554-556). The fifth positional argument is `update_rate`, not `max_iterations` (the signature is `..., aggressiveness, update_rate, max_iterations, ...`). The database column is called `iterations`, so the value probably belongs in `max_iterations`. The simplifier therefore runs with `update_rate=iterations` and the default `max_iterations=150`.

## Line 383-607 (`ThreadWorker.run`) — one model conversion per message
Reads the row, resolves the file, loads and centres the model, optionally decimates it, computes normals and the bounding volumes, writes a `.npy` file, and updates the database. Each step sends a progress message. The work is in the loaders above.

**Bug (flagged, not changed):** line 422 is `message['allow_retry'] = False,` with a trailing comma. That stores the tuple `(False,)`, which is truthy, so the "no retry" flag is always set. Remove the comma.

**Duplicate messages (flagged, not changed):** the generic exception branch (lines 474-476) and the "file_path is None" branch (lines 485-486) each call `self.out_queue.put(message)` twice. The parent receives the same error message two times.

## Line 610-747 (`_process_worker`) — three busy-wait loops at start-up
Lines 630-631, 633-634 and 638-639 spin on `exit_event` and `in_queue` before the main loop starts. Same problem as `image_process.md`: the process burns a CPU core while it waits for the parent.

The main loop uses `exit_event.wait(0.1)` while a conversion thread is alive (line 719). If `exit_event` is set, that call returns at once, so the poll becomes a tight loop until the thread finishes. Only relevant during shutdown.

## Line 750-829 (`ProcessWorker`) — one child process per model worker
Start-up cost is a full Python process, plus the OCP and pyassimp imports in the child. The manager caps the number of children at the core count (see `manager.md`).

**Typing (fixed in this pass):** loader functions take `file: str` or `path: str` and return `tuple[np.ndarray, np.ndarray]`; `_ocp_read_shape` takes `"TopoDS_Shape"`; `ProcessWorker.recv` returns `dict[str, Any] | None`.
