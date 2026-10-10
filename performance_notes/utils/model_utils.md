# harness_designer/utils/model_utils.py

## Line 25-64 (`compute_edges`) — NumPy concatenation of edge pairs
Builds the edge list from face indices with `np.concatenate`. Linear and vectorised. Fine.

## Line 65-end (`convert_model_to_mesh`) — tessellates a build123d solid, then copies it into Python lists
Runs `BRepMesh_IncrementalMesh` on the solid, then walks every face (line 115) and copies each node (line 128) and each triangle (line 137) into Python lists before converting to NumPy. This is the same pattern as `process/model_process.md` (`_ocp_read_shape`): per-vertex and per-triangle Python work dominates for large solids. A NumPy-backed copy would be faster.

Lines 96-98 disable the garbage collector around the tessellation (comment: a GC pass could run inside the OCP call). The collector is re-enabled afterwards. Disabling it is a deliberate workaround; the cost is that cyclic garbage accumulates during the call.
