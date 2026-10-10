# harness_designer/utils/mesh_normals.py

## Line 9-48 (`_process_verts_for_normals`) — vectorised per-face normals
Builds the triangle array and computes face normals with NumPy cross products. Quads use the two diagonals. Linear and vectorised.

## Line 49-134 (`compute_smooth_normals`, `compute_face_normals`) — per-vertex accumulation
Accumulates each face normal into its vertices with `np.zeros` and an indexed add, then normalises. Vectorised. Runs once per model load.

## Line 134-198 (`compute_normals`) — packs positions, smooth normals and face normals
Concatenates the three blocks into one packed array. One allocation per model load. Fine.

## Line 199-201 (`compute_face_indexes`) — index array
`np.arange` over the vertex count. Trivial.
