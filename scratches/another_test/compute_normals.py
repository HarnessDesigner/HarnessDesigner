import numpy as np
import debug as _debug  # NOQA


'''
26,060 triangles
compute_vertex_normals: 4.0ms
compute_smoothed_vertex_normals: 9.0ms
'''

# Performance between calculating smoothed normals and face normals can be
# significant with smooth normals taking ~2x mopr time to calculate.
# this only gets done when an item is added and the normals are cached. The only
# impact would be seen when loading a project that has many objects defined
# in it.

# TODO: Locate a normal calculation that produces a nice smooth representation
#       of a part like a housing without distorting it. Some of this is also
#       going to be controlled by using any reduction in the number of triangles.

@_debug.timeit
def compute_smoothed_vertex_normals(vertices, faces):
    # triangle coordinates (F, 3, 3)
    triangles = vertices[faces]

    # compute two edges per triangle
    v0 = triangles[:, 0, :]
    v1 = triangles[:, 1, :]
    v2 = triangles[:, 2, :]

    e1 = v1 - v0
    e2 = v2 - v0

    # raw face normal (not normalized): proportional to area * 2
    face_normals_raw = np.cross(e1, e2)  # shape (F, 3)  # NOQA

    # normalize face normals to unit vectors, but keep zeros for degenerate faces
    norm = np.linalg.norm(face_normals_raw, axis=1, keepdims=True)
    # avoid dividing by zero
    safe_norm = np.maximum(norm, 1e-6)
    face_normals = face_normals_raw / safe_norm
    # optionally set truly tiny normals to zero to avoid adding noise
    tiny = (norm.squeeze() < 1e-6)

    if np.any(tiny):
        face_normals[tiny] = 0.0

    # accumulate face normals into per-vertex sum
    V = len(vertices)
    vertex_normal_sum = np.zeros((V, 3), dtype=float)

    # Add each face's normal to its three vertices (np.add.at handles repeated indices)
    # Repeat face normals 3 times so they match faces.ravel()
    repeated_face_normals = np.repeat(face_normals, 3, axis=0)  # shape (F*3, 3)
    vertex_indices = faces.ravel()  # shape (F*3,)
    np.add.at(vertex_normal_sum, vertex_indices, repeated_face_normals)

    # normalize per-vertex summed normals
    vn_norm = np.linalg.norm(vertex_normal_sum, axis=1, keepdims=True)
    safe_vn_norm = np.maximum(vn_norm, 1e-6)
    vertex_normals = vertex_normal_sum / safe_vn_norm
    # set zero normals where there was no contribution (degenerate isolated vertices)
    isolated = (vn_norm.squeeze() < 1e-6)
    if np.any(isolated):
        vertex_normals[isolated] = 0.0

    # produce per-triangle per-vertex normals
    normals = vertex_normals[faces].reshape(-1, 3)  # shape (F, 3, 3)

    return triangles, normals


@_debug.timeit
def compute_vertex_normals(vertices, faces):
    triangles = vertices[faces]  # (F, 3, 3)
    v0 = triangles[:, 0, :]
    v1 = triangles[:, 1, :]
    v2 = triangles[:, 2, :]

    e1 = v1 - v0
    e2 = v2 - v0
    face_normals_raw = np.cross(e1, e2)  # (F, 3)  # NOQA

    norms = np.linalg.norm(face_normals_raw, axis=1, keepdims=True)
    safe = np.maximum(norms, 1e-6)
    face_normals = face_normals_raw / safe

    # set exact-degenerate faces to zero if extremely small
    degenerate = (norms.squeeze() < 1e-6)
    if np.any(degenerate):
        face_normals[degenerate] = 0.0

    # (F, 3, 3)ach face normal to the 3 vertices of the triangle
    normals = np.repeat(face_normals[:, np.newaxis, :], 3, axis=1)

    return triangles, normals.reshape(-1, 3)
