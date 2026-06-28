# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import numpy as np


def _process_verts_for_normals(
    vertices: np.ndarray,
    faces: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:

    triangles = vertices[faces]  # (F, 3, 3) for triangles, (F, 4, 3) for quads

    v0 = triangles[:, 0, :]
    v1 = triangles[:, 1, :]
    v2 = triangles[:, 2, :]

    if faces.shape[1] == 4:
        # For quads, cross the two diagonals — more accurate for non-planar faces
        v3 = triangles[:, 3, :]
        e1 = v2 - v0  # diagonal 1
        e2 = v3 - v1  # diagonal 2
    else:
        e1 = v1 - v0
        e2 = v2 - v0

    # raw face normal (not normalized): proportional to area * 2
    face_normals_raw = np.cross(e1, e2)  # (F, 3)  # NOQA

    # normalize face normals to unit vectors,
    # but keep zeros for degenerate faces
    norms = np.linalg.norm(face_normals_raw, axis=1, keepdims=True)

    # avoid dividing by zero
    safe = np.maximum(norms, 1e-6)
    face_normals = face_normals_raw / safe

    # set exact-degenerate faces to zero if extremely small
    degenerate = (norms.squeeze() < 1e-6)
    if np.any(degenerate):
        face_normals[degenerate] = 0.0

    return triangles, face_normals


def compute_smooth_normals(
    vertices: np.ndarray,
    faces: np.ndarray
) -> list[np.ndarray, np.ndarray, int]:
    """
    Compute smoothed vertex normals by averaging face normals at each vertex.

    Args:
        vertices: numpy array of shape (V, 3) - unique vertex positions
        faces: numpy array of shape (F, 3) - triangle indices into vertices array

    Returns:
        tuple: (vertices_array, normals_array, length_of_arrays)
            - vertices_array: flattened array of vertex positions (F*9,)
            - normals_array: flattened array of vertex normals (F*9,)
            - length_of_arrays: length of the arrays as an integer
    """
    triangles, face_normals = _process_verts_for_normals(vertices, faces)

    verts_per_face = faces.shape[1]  # 3 for triangles, 4 for quads

    # accumulate face normals into per-vertex sum
    V = len(vertices)
    vertex_normal_sum = np.zeros((V, 3), dtype=float)

    # Repeat each face normal once per vertex of that face, then scatter-add
    repeated_face_normals = np.repeat(face_normals, verts_per_face, axis=0)
    vertex_indices = faces.ravel()  # shape (F*N,)
    np.add.at(vertex_normal_sum, vertex_indices, repeated_face_normals)

    # normalize per-vertex summed normals
    vn_norm = np.linalg.norm(vertex_normal_sum, axis=1, keepdims=True)
    safe_vn_norm = np.maximum(vn_norm, 1e-6)
    vertex_normals = vertex_normal_sum / safe_vn_norm

    # set zero normals where there was no contribution (degenerate isolated vertices)
    isolated = (vn_norm.squeeze() < 1e-6)
    if np.any(isolated):
        vertex_normals[isolated] = 0.0

    # (F*N*3,) - all face vertices expanded (no sharing)
    vertices_array = triangles.astype(np.float32).ravel()

    # Look up the smoothed normal for each vertex of each face, then flatten
    normals_array = vertex_normals[faces].astype(np.float32).ravel()  # (F*N*3,)

    return [vertices_array, normals_array, len(vertices_array) // 3]


def compute_face_normals(
    vertices: np.ndarray, faces: np.ndarray
) -> list[np.ndarray, np.ndarray, int]:
    """
    Compute flat-shaded vertex normals (face normals replicated per vertex).
    For flat shading, each triangle gets its own vertices (no sharing).

    Args:
        vertices: numpy array of shape (V, 3) - original vertex positions
        faces: numpy array of shape (F, 3) - triangle indices into vertices array

    Returns:
        tuple: (vertices_array, normals_array, length_of_arrays)
            - vertices_array: flattened array of vertex positions (F*9,)
            - normals_array: flattened array of face normals (F*9,)
            - length_of_arrays: length of the arrays as an integer
    """

    triangles, face_normals = _process_verts_for_normals(vertices, faces)

    verts_per_face = faces.shape[1]  # 3 for triangles, 4 for quads

    # Replicate each face normal to all vertices of that face
    normals = np.repeat(face_normals[:, np.newaxis, :], verts_per_face, axis=1)  # (F, N, 3)

    # (F*N*3,) - all face vertices
    vertices_array = triangles.astype(np.float32).ravel()

    # (F*N*3,) - replicated face normals
    normals_array = normals.astype(np.float32).ravel()

    return [vertices_array, normals_array, len(vertices_array) // 3]


def compute_normals(
    vertices: np.ndarray,
    faces: np.ndarray
) -> tuple[np.ndarray, int]:

    """
    Compute both smooth and face normals.

    Args:
        vertices: numpy array of shape (V, 3) - original vertex positions
        faces: numpy array of shape (F, 3) - triangle indices into vertices array

    Returns:
        tuple: (packed_array, vertex_count)
            - packed_array: single flat float32 array holding the expanded
              vertex positions, smooth normals and face normals packed end
              to end; every block is vertex_count*3 floats:
                  [0   : n*3)  positions
                  [n*3 : n*6)  smooth normals
                  [n*6 : n*9)  face normals
            - vertex_count: number of triangle-soup vertices (F*3), pass
              to glDrawArrays
    """

    triangles, face_normals = _process_verts_for_normals(vertices, faces)

    # accumulate face normals into per-vertex sum
    V = len(vertices)
    vertex_normal_sum = np.zeros((V, 3), dtype=float)

    # Add each face's normal to its three vertices (np.add.at handles repeated indices)
    # Repeat face normals 3 times so they match faces.ravel()
    repeated_face_normals = np.repeat(face_normals, 3, axis=0)
    vertex_indices = faces.ravel()  # shape (F*3,)
    np.add.at(vertex_normal_sum, vertex_indices, repeated_face_normals)

    # normalize per-vertex summed normals
    vn_norm = np.linalg.norm(vertex_normal_sum, axis=1, keepdims=True)
    safe_vn_norm = np.maximum(vn_norm, 1e-6)
    smooth_normals = vertex_normal_sum / safe_vn_norm

    # set zero normals where there was no contribution (degenerate isolated vertices)
    isolated = (vn_norm.squeeze() < 1e-6)
    if np.any(isolated):
        smooth_normals[isolated] = 0.0

    # Look up the smoothed normal for each vertex of each triangle, then flatten
    # vertex_normals[faces] has shape (F, 3, 3)
    smooth_normals_array = smooth_normals[faces].astype(np.float32).ravel()  # (F*9,)

    # Replicate each face normal to the 3 vertices of the triangle
    normals = np.repeat(face_normals[:, np.newaxis, :], 3, axis=1)

    # (F*9,) - replicated face normals
    normals_array = normals.astype(np.float32).ravel()

    # (F*9,) - all triangle vertices
    vertices_array = triangles.astype(np.float32).ravel()

    packed = np.concatenate((vertices_array, smooth_normals_array, normals_array))

    return packed, len(vertices_array) // 3


def compute_face_indexes(vertices):
    indices_array = np.arange(len(vertices), dtype=np.uint32)

    return indices_array
