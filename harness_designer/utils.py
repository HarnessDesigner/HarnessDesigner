import numpy as np
import wx
import sys
import os

from OCP.TopAbs import TopAbs_REVERSED
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location

from .geometry import point as _point


def get_appdata():
    user_profile = os.path.expanduser('~')

    if sys.platform.startswith('win'):
        app_data = os.path.join('appdata', 'roaming', 'HarnessDesigner')
    else:
        app_data = '.HarnessDesigner'

    app_data = os.path.join(user_profile, app_data)
    if not os.path.exists(app_data):
        os.mkdir(app_data)

    return app_data


def HSizer(parent, label, ctrl) -> wx.BoxSizer:
    sizer = wx.BoxSizer(wx.HORIZONTAL)

    st = wx.StaticText(parent, wx.ID_ANY, label=label)
    sizer.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
    sizer.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
    return sizer


def remap(value, old_min, old_max, new_min, new_max):
    old_range = old_max - old_min
    new_range = new_max - new_min
    new_value = (((value - old_min) * new_range) / old_range) + new_min
    return new_value


def compute_smoothed_vertex_normals(vertices: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
    """
    Compute smoothed vertex normals by averaging face normals at each vertex.
    Works for both triangles and quads.

    Args:
        vertices: numpy array of shape (N, 3) - vertex coordinates
        faces: numpy array of shape (F, K) where K is 3 for triangles or 4 for quads

    Returns:
        tuple of (expanded_vertices, smoothed_normals, total_vertex_count)
    """
    # Get number of vertices per face (3 for triangles, 4 for quads)
    verts_per_face = faces.shape[1]

    # Expand vertices according to face indices (F, K, 3)
    expanded_verts = vertices[faces]

    # Compute two edges per face (using first 3 vertices)
    v0 = expanded_verts[:, 0, :]
    v1 = expanded_verts[:, 1, :]
    v2 = expanded_verts[:, 2, :]

    e1 = v1 - v0
    e2 = v2 - v0

    # Raw face normal (not normalized): proportional to area * 2
    face_normals_raw = np.cross(e1, e2)  # shape (F, 3)  # NOQA

    # Normalize face normals to unit vectors,
    # but keep zeros for degenerate faces
    norm = np.linalg.norm(face_normals_raw, axis=1, keepdims=True)

    # Avoid dividing by zero
    safe_norm = np.maximum(norm, 1e-6)
    face_normals = face_normals_raw / safe_norm

    # Optionally set truly tiny normals to zero to avoid adding noise
    tiny = (norm.squeeze() < 1e-6)

    if np.any(tiny):
        face_normals[tiny] = 0.0

    # Accumulate face normals into per-vertex sum
    V = len(vertices)
    vertex_normal_sum = np.zeros((V, 3), dtype=float)

    # Add each face's normal to all its vertices
    # (np.add.at handles repeated indices)
    # Repeat face normals K times (3 for triangles, 4 for quads)
    repeated_face_normals = np.repeat(
        face_normals, verts_per_face, axis=0)  # shape (F*K, 3)

    vertex_indices = faces.ravel()  # shape (F*K,)
    np.add.at(vertex_normal_sum, vertex_indices, repeated_face_normals)

    # Normalize per-vertex summed normals
    vn_norm = np.linalg.norm(vertex_normal_sum, axis=1, keepdims=True)
    safe_vn_norm = np.maximum(vn_norm, 1e-6)
    vertex_normals = vertex_normal_sum / safe_vn_norm

    # Set zero normals where there was no contribution
    # (degenerate isolated vertices)
    isolated = (vn_norm.squeeze() < 1e-6)
    if np.any(isolated):
        vertex_normals[isolated] = 0.0

    # Produce per-face per-vertex normals by indexing smoothed vertex normals
    normals = vertex_normals[faces].reshape(-1, 3)  # shape (F*K, 3)

    # Reshape expanded_verts to match normals shape
    expanded_verts_reshaped = expanded_verts.reshape(-1, 3)  # shape (F*K, 3)

    return expanded_verts_reshaped, normals, len(expanded_verts) * verts_per_face


def compute_vertex_normals(vertices: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
    """
    Compute face normals duplicated per vertex for triangles or quads.

    Args:
        vertices: numpy array of shape (N, 3) - vertex coordinates
        faces: numpy array of shape (F, K) where K is 3 for triangles or 4 for quads

    Returns:
        tuple of (expanded_vertices, normals, total_vertex_count)
    """
    # Get number of vertices per face (3 for triangles, 4 for quads)
    verts_per_face = faces.shape[1]

    # Expand vertices according to face indices
    expanded_verts = vertices[faces]  # (F, K, 3)
    v0 = expanded_verts[:, 0, :]
    v1 = expanded_verts[:, 1, :]
    v2 = expanded_verts[:, 2, :]

    # Calculate face normals using first 3 vertices
    e1 = v1 - v0
    e2 = v2 - v0
    face_normals_raw = np.cross(e1, e2)  # (F, 3) # NOQA

    # Normalize safely
    norms = np.linalg.norm(face_normals_raw, axis=1, keepdims=True)
    safe = np.maximum(norms, 1e-6)
    face_normals = face_normals_raw / safe

    # Set exact-degenerate faces to zero if extremely small
    degenerate = (norms.squeeze() < 1e-6)
    if np.any(degenerate):
        face_normals[degenerate] = 0.0

    # Duplicate each face normal K times (once per vertex in the face)
    # Changed from hardcoded 3 to verts_per_face
    normals = np.repeat(face_normals[:, np.newaxis, :], verts_per_face, axis=1)

    # Reshape expanded_verts to match normals shape
    expanded_verts_reshaped = expanded_verts.reshape(-1, 3)  # shape (F*K, 3)

    return expanded_verts_reshaped, normals.reshape(-1, 3), len(expanded_verts) * verts_per_face


def compute_aabb(triangles):
    verts = triangles.reshape(-1, 3)
    p1 = _point.Point(*verts.min(axis=0))
    p2 = _point.Point(*verts.max(axis=0))
    return p1, p2


def compute_obb(p1, p2):
    x1, y1, z1 = p1.as_float
    x2, y2, z2 = p2.as_float

    corners = np.array([[x1, y1, z1], [x1, y1, z2],
                       [x1, y2, z1], [x1, y2, z2],
                       [x2, y1, z1], [x2, y1, z2],
                       [x2, y2, z1], [x2, y2, z2]],
                       dtype=np.float64)

    return corners


def convert_model_to_mesh(model):
    loc = TopLoc_Location()
    BRepMesh_IncrementalMesh(theShape=model.wrapped, theLinDeflection=0.001,
                             isRelative=True, theAngDeflection=0.1, isInParallel=True)

    vertices = []
    faces = []
    offset = 0
    for facet in model.faces():
        if not facet:
            continue

        poly_triangulation = BRep_Tool.Triangulation_s(facet.wrapped, loc)  # NOQA

        if not poly_triangulation:
            continue

        trsf = loc.Transformation()

        node_count = poly_triangulation.NbNodes()
        for i in range(1, node_count + 1):
            gp_pnt = poly_triangulation.Node(i).Transformed(trsf)
            pnt = (gp_pnt.X(), gp_pnt.Y(), gp_pnt.Z())
            vertices.append(pnt)

        facet_reversed = facet.wrapped.Orientation() == TopAbs_REVERSED

        order = [1, 3, 2] if facet_reversed else [1, 2, 3]
        for tri in poly_triangulation.Triangles():
            faces.append([tri.Value(i) + offset - 1 for i in order])

        offset += node_count

    vertices = np.array(vertices, dtype=np.dtypes.Float64DType)
    faces = np.array(faces, dtype=np.dtypes.Int32DType)

    return vertices, faces


def adjust_aabb(aabb: np.ndarray) -> np.ndarray:
    return np.array([aabb.min(axis=0), aabb.max(axis=0)], dtype=np.float64)


def compute_vbo_smoothed_vertex_normals(
    vertices: np.ndarray, faces: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:

    """
    Compute smoothed vertex normals by averaging face normals at each vertex.

    Args:
        vertices: numpy array of shape (V, 3) - unique vertex positions
        faces: numpy array of shape (F, 3) - triangle indices into vertices array

    Returns:
        tuple: (vertices_array, normals_array, indices_array)
            - vertices_array: flattened array of vertex positions (V*3,)
            - normals_array: flattened array of vertex normals (V*3,)
            - indices_array: flattened array of triangle indices (F*3,)
    """
    # triangle coordinates (F, 3, 3)
    triangles = vertices[faces]

    # compute two edges per triangle
    v0 = triangles[:, 0, :]
    v1 = triangles[:, 1, :]
    v2 = triangles[:, 2, :]

    e1 = v1 - v0
    e2 = v2 - v0

    # raw face normal (not normalized): proportional to area * 2
    face_normals_raw = np.cross(e1, e2)  # NOQA

    # normalize face normals to unit vectors,
    # but keep zeros for degenerate faces
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
    repeated_face_normals = np.repeat(face_normals, 3, axis=0)
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

    # Return arrays suitable for VBO:
    # - vertices: flattened unique vertex positions
    # - normals: per-vertex normals (one per vertex, smoothed across faces)
    # - indices: triangle indices into the vertices array
    vertices_array = vertices.astype(np.float32).ravel()  # (V*3,)
    normals_array = vertex_normals.astype(np.float32).ravel()  # (V*3,)
    indices_array = faces.astype(np.uint32).ravel()  # (F*3,)

    return vertices_array, normals_array, indices_array, len(indices_array) * 3


def compute_vbo_vertex_normals(
    vertices: np.ndarray, faces: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:

    """
    Compute flat-shaded vertex normals (face normals replicated per vertex).
    For flat shading, each triangle gets its own vertices (no sharing).

    Args:
        vertices: numpy array of shape (V, 3) - original vertex positions
        faces: numpy array of shape (F, 3) - triangle indices into vertices array

    Returns:
        tuple: (vertices_array, normals_array, indices_array)
            - vertices_array: flattened array of vertex positions (F*9,)
            - normals_array: flattened array of face normals (F*9,)
            - indices_array: flattened array of sequential indices (F*3,)
    """
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

    # Replicate each face normal to the 3 vertices of the triangle
    normals = np.repeat(face_normals[:, np.newaxis, :], 3, axis=1)

    # For flat shading, we need unique vertices per triangle (no sharing)
    # So we expand triangles and create sequential indices
    num_triangles = len(triangles)

    # (F*9,) - all triangle vertices
    vertices_array = triangles.astype(np.float32).ravel()

    # (F*9,) - replicated face normals
    normals_array = normals.astype(np.float32).ravel()

    # (F*3,) - sequential 0,1,2,3,4,5...
    indices_array = np.arange(num_triangles * 3, dtype=np.uint32)

    return vertices_array, normals_array, indices_array, len(indices_array) * 3
