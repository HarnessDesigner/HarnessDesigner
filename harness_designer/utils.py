# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""General utility helpers for unit conversion, geometry, and UI glue."""

from typing import TYPE_CHECKING

import numpy as np
import sys
import os
import math
from PySide6 import QtWidgets
from OCP.TopAbs import TopAbs_REVERSED
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location

from .geometry.decimal import Decimal as _d
from .geometry import point as _point
from .geometry import angle as _angle


if TYPE_CHECKING:
    from .gl.canvas3d import camera as _camera
    from .objects import wire as _wire


# ---------------------------------------------------------------------------
# Unit conversion constant
# ---------------------------------------------------------------------------
MM2_PER_IN2 = 645.16


# ---------------------------------------------------------------------------
# Stranding tables
# ---------------------------------------------------------------------------

# Generic strand counts by AWG used when strands=0 (stranded but count unknown)
_AWG_STRAND_COUNT = {
    -4: 2109,
    -3: 1665,
    -2: 1330,
    0: 1045,
    1: 817,
    2: 665,
    4: 133,
    6: 133,
    8: 133,
    10: 37,
    12: 19,
    14: 19,
    16: 19,
    18: 19,
    20: 19,
    22: 19,
    24: 19,
    26: 19,
    28: 7,
    30: 7,
}

# Packing factors by strand count
_PACKING_FACTOR = {
    1: 1.000,
    7: 0.750,
    19: 0.780,
    37: 0.800,
    133: 0.830,
    665: 0.850,
    817: 0.850,
    1045: 0.850,
    1330: 0.850,
    1665: 0.850,
    2109: 0.850,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# The functions below have a "strand" parameter. This parameter is
# defaulted to 1 which means a single strcand or a solid wire.
# If this parameter is set to zero that means the wire is a stranded wire
# but the strand count is not known. When that occurs a default value for the
# number of strands is used based on the size of the wire. This is not going
# to produce an exact size for the wire but it will produce a closer estimate
# than calculating it as a solid wire. The calculations are doing using a
# concentric twist for the strands and once again depending on the twist there
# could be a deviation from what the actual diameter of the wire is.
# These functions are a calculated best and not perfect.


def _get_strand_count(awg: int | _d, strands: int | _d) -> int:
    """
    Resolve the strand count used for diameter calculations.

    :param awg: Wire gauge used when ``strands`` is ``0``.
    :type awg: int | _d
    :param strands: Requested strand count.
    :type strands: int | _d
    :returns: Effective strand count.
    :rtype: int
    """

    strands = int(strands)
    if strands == 1:
        return 1

    if strands == 0:
        return _AWG_STRAND_COUNT.get(int(awg), 19)

    return strands


def _get_packing_factor(strand_count: int | _d) -> float:
    """
    Return or interpolate the bundle packing factor for a strand count.

    :param strand_count: Number of strands in the conductor bundle.
    :type strand_count: int | _d
    :returns: Packing factor used to approximate bundle diameter.
    :rtype: float
    """

    if strand_count in _PACKING_FACTOR:
        return _PACKING_FACTOR[strand_count]

    known = sorted(_PACKING_FACTOR.keys())
    for i, k in enumerate(known):
        if strand_count < k:
            if i == 0:
                return _PACKING_FACTOR[k]

            lo, hi = known[i - 1], k
            t = (strand_count - lo) / (hi - lo)
            return _PACKING_FACTOR[lo] + t * (
                _PACKING_FACTOR[hi] - _PACKING_FACTOR[lo])

    return _PACKING_FACTOR[known[-1]]


def _solid_to_bundle(solid_d_mm: float | _d, strand_count: int | _d) -> float:
    """
    Convert a solid-conductor diameter to an approximate bundle diameter.

    :param solid_d_mm: Equivalent solid diameter in millimetres.
    :type solid_d_mm: float | _d
    :param strand_count: Number of strands in the bundle.
    :type strand_count: int | _d
    :returns: Approximate stranded bundle diameter in millimetres.
    :rtype: float
    """

    if strand_count == 1:
        return solid_d_mm

    return solid_d_mm / math.sqrt(_get_packing_factor(strand_count))


def _bundle_to_solid(bundle_d_mm: float | _d, strand_count: int | _d) -> float:
    """
    Convert a bundle diameter back to an equivalent solid diameter.

    :param bundle_d_mm: Stranded bundle diameter in millimetres.
    :type bundle_d_mm: float | _d
    :param strand_count: Number of strands in the bundle.
    :type strand_count: int | _d
    :returns: Equivalent solid diameter in millimetres.
    :rtype: float
    """

    if strand_count == 1:
        return bundle_d_mm

    return bundle_d_mm * math.sqrt(_get_packing_factor(strand_count))


# ---------------------------------------------------------------------------
# Public conversion functions
# ---------------------------------------------------------------------------

def mm2_to_awg(mm2: float | _d, strands: int | _d = 1) -> int:
    """
    Convert cross-sectional area in mm² to AWG.

    :param mm2: Conductor area in square millimetres.
    :type mm2: float | _d
    :param strands: Strand count hint used for diameter estimation.
    :type strands: int | _d
    :returns: Rounded AWG value.
    :rtype: int
    """

    d_in = mm2_to_d_in(mm2, strands)
    awg = 36 - 39 * math.log(float(d_in / 0.005), 92)

    return int(round(awg))


def awg_to_mm2(awg: int | _d, strands: int | _d = 1) -> float:  # NOQA
    """
    Convert AWG to electrical cross-sectional area in mm².

    :param awg: Wire gauge.
    :type awg: int | _d
    :param strands: Unused for area conversion; retained for API compatibility.
    :type strands: int | _d
    :returns: Conductor area in square millimetres.
    :rtype: float
    """

    # mm² is always the electrical equivalent cross-section — stranding doesn't change it
    d_in = float(round(0.005 * 92 ** ((36 - int(awg)) / 39), 6))
    d_mm = d_in * 25.4

    return float(round(math.pi / 4 * d_mm ** 2, 4))


def awg_to_d_in(awg: int | _d, strands: int | _d = 1) -> float:
    """
    Convert AWG to approximate conductor diameter in inches.

    :param awg: Wire gauge.
    :type awg: int | _d
    :param strands: Strand count hint used for bundle estimation.
    :type strands: int | _d
    :returns: Diameter in inches.
    :rtype: float
    """

    d_in = float(round(0.005 * 92 ** ((36 - int(awg)) / 39), 6))
    strand_count = _get_strand_count(awg, strands)
    d_mm = _solid_to_bundle(d_in * 25.4, strand_count)

    return float(round(d_mm / 25.4, 4))


def awg_to_d_mm(awg: int | _d, strands: int | _d = 1) -> float:
    """
    Convert AWG to approximate conductor diameter in millimetres.

    :param awg: Wire gauge.
    :type awg: int | _d
    :param strands: Strand count hint used for bundle estimation.
    :type strands: int | _d
    :returns: Diameter in millimetres.
    :rtype: float
    """

    d_in = float(round(0.005 * 92 ** ((36 - int(awg)) / 39), 6))
    strand_count = _get_strand_count(awg, strands)

    return float(round(_solid_to_bundle(d_in * 25.4, strand_count), 4))


def d_in_to_d_mm(d_in: float | _d, strands: int | _d = 1) -> float:  # NOQA
    """
    Convert diameter in inches to millimetres.

    :param d_in: Diameter in inches.
    :type d_in: float | _d
    :param strands: Unused; retained for API compatibility.
    :type strands: int | _d
    :returns: Diameter in millimetres.
    :rtype: float
    """

    return float(round(float(d_in) * 25.4, 4))


def d_mm_to_mm2(d_mm: float | _d, strands: int | _d = 1) -> float:  # NOQA
    """
    Convert diameter in millimetres to area in mm².

    :param d_mm: Diameter in millimetres.
    :type d_mm: float | _d
    :param strands: Unused; retained for API compatibility.
    :type strands: int | _d
    :returns: Cross-sectional area in mm².
    :rtype: float
    """

    return float(round(math.pi / 4 * float(d_mm) ** 2, 4))


def mm2_to_d_mm(mm2: float | _d, strands: int | _d = 1) -> float:
    """
    Convert area in mm² to approximate conductor diameter in millimetres.

    :param mm2: Conductor area in square millimetres.
    :type mm2: float | _d
    :param strands: Strand count hint used for bundle estimation.
    :type strands: int | _d
    :returns: Approximate diameter in millimetres.
    :rtype: float
    """

    solid_d_mm = 2 * math.sqrt(float(mm2 / math.pi))
    strand_count = _get_strand_count(mm2_to_awg(mm2, strands=1), strands)

    return float(round(_solid_to_bundle(solid_d_mm, strand_count), 4))


def mm2_to_d_in(mm2: float | _d, strands: int | _d = 1) -> float:
    """
    Convert area in mm² to approximate conductor diameter in inches.

    :param mm2: Conductor area in square millimetres.
    :type mm2: float | _d
    :param strands: Strand count hint used for bundle estimation.
    :type strands: int | _d
    :returns: Approximate diameter in inches.
    :rtype: float
    """

    return float(round(mm2_to_d_mm(mm2, strands) / 25.4, 4))


def d_mm_to_awg(d_mm: float | _d, strands: int | _d = 1) -> int:
    """
    Convert diameter in millimetres to AWG.

    :param d_mm: Diameter in millimetres.
    :type d_mm: float | _d
    :param strands: Strand count hint used for bundle estimation.
    :type strands: int | _d
    :returns: Rounded AWG value.
    :rtype: int
    """

    # Convert bundle diameter back to solid equivalent, then derive AWG
    approx_awg = mm2_to_awg(d_mm_to_mm2(float(d_mm), strands), strands=1)
    strand_count = _get_strand_count(approx_awg, strands)
    solid_d_mm = _bundle_to_solid(float(d_mm), strand_count)

    return mm2_to_awg(d_mm_to_mm2(solid_d_mm, strands), strands=1)


def mm2_to_in2(mm2: float | _d, strands: int | _d = 1) -> float:  # NOQA
    """
    Convert area in mm² to square inches.

    :param mm2: Area in square millimetres.
    :type mm2: float | _d
    :param strands: Unused; retained for API compatibility.
    :type strands: int | _d
    :returns: Area in square inches.
    :rtype: float
    """

    return float(round(mm2 / MM2_PER_IN2, 4))


def in2_to_mm2(in2: float | _d, strands: int | _d = 1) -> float:  # NOQA
    """
    Convert area in square inches to mm².

    :param in2: Area in square inches.
    :type in2: float | _d
    :param strands: Unused; retained for API compatibility.
    :type strands: int | _d
    :returns: Area in square millimetres.
    :rtype: float
    """

    return float(round(in2 * MM2_PER_IN2, 4))


def get_appdata():
    """
    Return the ``harness_designer`` application-data directory, creating it if needed.

    :returns: Absolute path to the per-user application-data directory.
    :rtype: str
    """

    user_profile = os.path.expanduser('~')

    if sys.platform.startswith('win'):
        app_data = os.path.join('appdata', 'roaming', 'HarnessDesigner')
    else:
        app_data = '.HarnessDesigner'

    app_data = os.path.join(user_profile, app_data)
    if not os.path.exists(app_data):
        os.mkdir(app_data)

    return app_data


def get_documents():
    """
    Return the user's default documents directory.

    :returns: Absolute path to the documents directory.
    :rtype: str
    """

    documents = os.path.expanduser('~')

    if sys.platform.startswith('win'):
        documents = os.path.join(documents, 'documents')

    return documents


def HSizer(parent, label, ctrl) -> QtWidgets.QHBoxLayout:
    """
    Create a horizontal layout containing a label and control.

    :param parent: Parent widget for the label.
    :type parent: PySide6.QtWidgets.QWidget
    :param label: Label text.
    :type label: str
    :param ctrl: Control widget added beside the label.
    :type ctrl: PySide6.QtWidgets.QWidget
    :returns: Populated horizontal layout.
    :rtype: QHBoxLayout
    """

    layout = QtWidgets.QHBoxLayout()
    lbl = QtWidgets.QLabel(label, parent)
    layout.addWidget(lbl)
    layout.addWidget(ctrl)

    return layout


def remap(
    value: int | float | _d,
    old_min: int | float | _d, old_max: int | float | _d,
    new_min: int | float | _d, new_max: int | float | _d,
    type_=_d
) -> int | float | _d:

    """
    Remaps/Reranges a value from one range to another range.

    Lets say you have a value of 25 and that value fits into a range of 1-100.
    You need that value to fit into the 1-250 range but still be 25% of the range
    like it is in the 0-100 range. This is the function to use to do that.

    :param value: input value

    :param old_min: input value's minimum

    :param old_max: input values maximum
    :param new_min: new minimum
    :param new_max: new maximum
    :param type_: what type to return the value as; `int`, `float` or `Decimal`
    :return: The new value mapped to the new range
    """

    value = _d(value)
    old_min = _d(old_min)
    old_max = _d(old_max)
    new_min = _d(new_min)
    new_max = _d(new_max)

    old_range = old_max - old_min
    new_range = new_max - new_min
    new_value = (((value - old_min) * new_range) / old_range) + new_min

    return type_(new_value)


def compute_edges(faces: np.ndarray) -> np.ndarray:
    """
    Create a numpy array of edges from vertices and triangle faces.

    Parameters:
    -----------
    verts : numpy.ndarray
        Array of vertices with shape (N, 3) where N is the number of vertices
    faces : numpy.ndarray
        Array of triangle faces with shape (M, 3) where M is the number of faces.
        Each face contains indices into the verts array.

    Returns:
    --------
    edges : numpy.ndarray
        Array of unique edges with shape (E, 2) where E is the number of edges.
        Each edge contains two vertex indices.
    """

    # Extract all edges from faces
    # Each triangle has 3 edges: (v0,v1), (v1,v2), (v2,v0)
    edges = np.concatenate(
        [
            faces[:, [0, 1]],  # edge between vertex 0 and 1
            faces[:, [1, 2]],  # edge between vertex 1 and 2
            faces[:, [2, 0]]  # edge between vertex 2 and 0
        ], axis=0
    )

    # Sort each edge so that smaller index comes first
    # This ensures (i,j) and (j,i) are treated as the same edge
    edges = np.sort(edges, axis=1)

    # Remove duplicate edges
    edges = np.unique(edges, axis=0)

    return edges


def compute_aabb(verts):
    """
    Compute an axis-aligned bounding box from vertex positions.

    :param verts: Vertex positions.
    :type verts: numpy.ndarray
    :returns: Minimum and maximum corner points.
    :rtype: tuple[_point.Point, _point.Point]
    """

    p1 = _point.Point(*verts.min(axis=0))
    p2 = _point.Point(*verts.max(axis=0))
    return p1, p2


def compute_obb(p1, p2):
    """
    Construct bounding-box corner coordinates from two opposite points.

    :param p1: Minimum corner.
    :type p1: _point.Point
    :param p2: Maximum corner.
    :type p2: _point.Point
    :returns: Eight corner coordinates.
    :rtype: numpy.ndarray
    """

    x1, y1, z1 = p1.as_float
    x2, y2, z2 = p2.as_float

    corners = np.array([
                [x1, y1, z1],  # 0: bottom-left-front
                [x2, y1, z1],  # 1: bottom-right-front
                [x2, y2, z1],  # 2: top-right-front
                [x1, y2, z1],  # 3: top-left-front
                [x1, y1, z2],  # 4: bottom-left-back
                [x2, y1, z2],  # 5: bottom-right-back
                [x2, y2, z2],  # 6: top-right-back
                [x1, y2, z2],  # 7: top-left-back
            ], dtype=np.float32)
    return corners


def convert_model_to_mesh(model):
    """
    Triangulate a CAD model into vertex and face arrays.

    :param model: Build123d/OCP model wrapper exposing ``wrapped`` and ``faces``.
    :type model: UNKNOWN
    :returns: Vertex and face arrays suitable for mesh processing.
    :rtype: tuple[numpy.ndarray, numpy.ndarray]
    """

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

    vertices = np.array(vertices, dtype=np.float32)
    faces = np.array(faces, dtype=np.int32)

    return vertices, faces


def adjust_aabb(aabb: np.ndarray) -> np.ndarray:
    """
    Normalise an AABB array to explicit min/max rows.

    :param aabb: Bounding-box coordinates.
    :type aabb: numpy.ndarray
    :returns: Two-row array containing min and max coordinates.
    :rtype: numpy.ndarray
    """

    return np.array([aabb.min(axis=0), aabb.max(axis=0)], dtype=np.float32)


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


def unproject_from_ndc(ndc, inv_mvp):
    """
    ndc: (x,y,z) in [-1,1]
    inv_mvp: inverse of P*MV (row-major)
    """

    clip = np.array([ndc[0], ndc[1], ndc[2], 1.0], dtype=np.float32)

    world = inv_mvp.dot(clip)
    if np.isclose(world[3], 0.0):
        return None

    world /= world[3]
    return world[:3]


def get_position_on_focal_plane(
    mouse_pos: "_point.Point",
    camera: "_camera.Camera"
) -> "_point.Point":

    vx, vy, vw, vh = camera.viewport

    ndc_x = (2.0 * (mouse_pos.x - vx) / vw) - 1.0
    ndc_y = (2.0 * (vh - mouse_pos.y - vy) / vh) - 1.0

    # One unproject — ray origin is the camera position itself
    far_world = unproject_from_ndc((ndc_x, ndc_y, 1.0), camera.inv_clip)
    if far_world is None:
        return camera.focal_position.copy()

    origin = camera.position.as_numpy.astype(np.float32)
    direction = np.asarray(far_world, dtype=np.float32) - origin
    direction /= np.linalg.norm(direction)

    # camera.forward  == plane normal (already normalised)
    # camera.focal_distance == dot(focal_pos - origin, plane_normal)
    #                          because forward is the unit vec between them
    denom = np.dot(direction, camera.forward)
    if abs(denom) < 1e-6:
        return camera.focal_position.copy()

    t = camera.focal_distance / denom
    if t < 0:
        return camera.focal_position.copy()

    return _point.Point(*(origin + t * direction))


def closest_point_on_segment_to_ray(seg_p1, seg_p2, ray_origin, ray_dir):
    """
    Find the closest point on line segment (seg_p1, seg_p2) to a ray.

    Uses the parametric formula for closest points between two 3D lines,
    then clamps the result to the line segment.
    """

    # Wire segment direction
    w = seg_p2 - seg_p1
    w_len = np.linalg.norm(w)

    if w_len < 1e-6:
        return seg_p1

    w = w / w_len

    # Vector from ray origin to segment start
    u = seg_p1 - ray_origin

    # Calculate parameters for closest points
    a = np.dot(w, w)  # Should be 1 (normalized)
    b = np.dot(w, ray_dir)
    c = np.dot(ray_dir, ray_dir)  # Should be 1 (normalized)
    d = np.dot(w, u)
    e = np.dot(ray_dir, u)

    denom = a * c - b * b

    if abs(denom) < 1e-6:
        # Lines are parallel, use perpendicular projection
        t = np.dot(u, w)
    else:
        t = (b * e - c * d) / denom

    # Clamp t to [0, wire_length]
    t = np.clip(t, 0.0, w_len)

    # Calculate closest point on segment
    closest = seg_p1 + t * w

    return closest


def _point_on_wire(mouse_pos: "_point.Point", p1, p2, camera):
    """
    Project a mouse ray onto the closest point along a wire segment.

    :param mouse_pos: Mouse position in viewport coordinates.
    :type mouse_pos: _point.Point
    :param p1: Start point of the wire segment.
    :type p1: numpy.ndarray
    :param p2: End point of the wire segment.
    :type p2: numpy.ndarray
    :param camera: Active 3D camera.
    :type camera: _camera.Camera
    :returns: Closest point on the segment, or ``(None, None)`` when the ray
        cannot be constructed.
    :rtype: numpy.ndarray | tuple[None, None]
    """

    # Build ray from mouse position
    pj = camera.projection
    mv = camera.modelview
    viewport = camera.viewport

    mvp = pj.dot(mv)
    inv_mvp = np.linalg.inv(mvp)
    vx, vy, vw, vh = viewport

    x = mouse_pos.x
    y = (vh - mouse_pos.y)

    ndc_x = (2.0 * (x - vx) / vw) - 1.0
    ndc_y = (2.0 * (y - vy) / vh) - 1.0

    # Unproject to get ray
    near_world = unproject_from_ndc((ndc_x, ndc_y, -1.0), inv_mvp)
    far_world = unproject_from_ndc((ndc_x, ndc_y, 1.0), inv_mvp)

    if near_world is None or far_world is None:
        return None, None

    ray_origin = np.array(near_world, dtype=np.float32)
    ray_direction = np.array(far_world, dtype=np.float32) - ray_origin
    ray_direction /= np.linalg.norm(ray_direction)

    # Find closest point on wire line segment to the ray
    # This uses the formula for closest point between two 3D line segments
    closest_point = closest_point_on_segment_to_ray(
        p1, p2, ray_origin, ray_direction)

    if closest_point is None:
        # Fallback to wire midpoint
        closest_point = (p1 + p2) / 2.0

    return closest_point


def get_closest_point_on_wire(
    mouse_pos: "_point.Point",
    camera: "_camera.Camera",
    wire: "_wire.Wire"
):
    """
    Find the closest point on a wire to where the user clicked.

    This computes:
    1. Ray from mouse position
    2. Closest point on wire line segment to that ray
    3. Wire direction at that point

    Returns:
        tuple: (closest_point, wire_angle) or (None, None)
    """

    # Get wire endpoints
    p1 = wire.obj3d.start_position.as_numpy
    p2 = wire.obj3d.stop_position.as_numpy

    closest_point = _point_on_wire(mouse_pos, p1, p2, camera)

    # Calculate wire direction (from p1 to p2)
    wire_direction = p2 - p1
    wire_length = np.linalg.norm(wire_direction)

    if wire_length < 0.001:
        return None, None

    wire_direction /= wire_length

    # Convert to angle
    wire_angle = _angle.Angle.from_direction(wire_direction)

    return _point.Point(*closest_point), wire_angle


def get_closest_point_on_wire_endpoint(
    mouse_pos: "_point.Point",
    camera: "_camera.Camera",
    wire: "_wire.Wire",
    endpoint_tolerance=5.0
):
    """
    Find whether a picked wire location lands on an existing endpoint.

    :param mouse_pos: Mouse position in viewport coordinates.
    :type mouse_pos: _point.Point
    :param camera: Active 3D camera.
    :type camera: _camera.Camera
    :param wire: Wire being evaluated.
    :type wire: _wire.Wire
    :param endpoint_tolerance: Minimum tolerance used for endpoint snapping.
    :type endpoint_tolerance: float
    :returns: Picked position, whether it matches an endpoint, and the endpoint
        name when applicable.
    :rtype: tuple[object, bool, str | None]
    """

    # Get wire endpoints
    p1 = wire.obj3d.start_position.as_numpy
    p2 = wire.obj3d.stop_position.as_numpy

    closest_point = _point_on_wire(mouse_pos, p1, p2, camera)

    # Check if closest point is near an existing endpoint
    dist_to_p1 = np.linalg.norm(closest_point - p1)
    dist_to_p2 = np.linalg.norm(closest_point - p2)

    # Use wire diameter as tolerance for endpoint detection
    wire_diameter = wire.db_obj.part.od_mm
    tolerance = max(wire_diameter, endpoint_tolerance)

    if dist_to_p1 < tolerance:
        # Placing at start endpoint - return the ACTUAL Point instance
        # This ensures the layout will bind to the same Point callbacks
        return p1, True, 'start'
    elif dist_to_p2 < tolerance:
        # Placing at end endpoint - return the ACTUAL Point instance
        return p2, True, 'stop'
    else:
        # Placing in middle - return coordinates for NEW Point creation
        # The project will create a new Point and share it between layout and wires
        position = _point.Point(*closest_point)

        return position, False, None


IMAGE_FILE_WILDCARDS = (
    'All Supported Images |*.png;*.bmp;*.jpg;*.jpeg;*.gif;*.tif;*.tiff|'
    "PNG (png)|*.png|"
    "Bitmap (bmp)|*.bmp|"
    "JPEG (jpg, jpeg)|*.jpg;*.jpeg|"
    "GIF (gif)|*.gif|"
    "Tiff (tif, tiff)|*.tif;*.tiff|"
)


MODEL_FILE_WILDCARDS = (
    "All Supported Models |*.3mf;*.glTF;*.igs;*.iges;*.dae;*.obj;*.stp;*.step;"
    "*.stl;*.vrml;*.wrl;*.mdl;*.hmp;*.3ds;*.ase;*.ac;*.ac3d;*.dxf;*.bvh;*.blend;"
    "*.csm;*.x;*.md5mesh;*.md5anim;*.md5camera;*.fbx;*.ifc;*.irr;*.irrmesh;*.lwo;"
    "*.lws;*.ms3d;*.lxo;*.nff;*.off;*.mesh.xml;*.skeleton.xml;*.ogex;*.mdl;*.md2;"
    "*.md3;*.pk3;*.q3o;*.q3s;*.raw;*.mdc;*.ply;*.ter;*.cob;*.scn;*.smd;*.vta;*.xgl;"
    "*.amf;*.assbin;*.b3d;*.iqm;*.ndo;*.q3d;*.sib;*.x3d;*.x3db;*.x3dz;*.x3dbz;"
    "*.pmd;*.pmx|"
    "All Files |*.*|"
    "3MF (3mf)|*.3mf|"
    "glTF (glTF)|*.glTF|"
    "IGES (igs; iges)|*.igs;*.iges|"
    "Collada (dae)|*.dae|"
    "Wavefront Object (obj)|*.obj|"
    "STEP (stp; step)|*.stp;*.step|"
    "STL (stl)|*.stl|"
    "VRML (vrml; wrl)|*.vrml;*.wrl|"
    "3D GameStudio (mdl; hmp)|*.mdl;*.hmp|"
    "3D Studio Max (3ds; ase)|*.3ds;*.ase|"
    "AC3D (ac; ac3d)|*.ac;*.ac3d|"
    "Autodesk/AutoCAD DXF (dxf)|*.dxf|"
    "Biovision BVH (bvh)|*.bvh|"
    "Blender BVH (blend)|*.blend|"
    "CharacterStudio Motion (csm)|*.csm|"
    "DirectX X (x)|*.x|"
    "Doom 3 (md5mesh; md5anim; md5camera)|*.md5mesh;*.md5anim;*.md5camera|"
    "FBX-Format (fbx)|*.fbx|"
    "IFC-STEP (ifc)|*.ifc|"
    "Irrlicht Mesh/Scene (irr; irrmesh)|*.irr;*.irrmesh|"
    "LightWave Model/Scene (lwo; lws)|*.lwo;*.lws|"
    "Milkshape 3D (ms3d)|*.ms3d|"
    "Modo Model (lxo)|*.lxo|"
    "Neutral File Format (nff)|*.nff|"
    "Object File Format (off)|*.off|"
    "Ogre (mesh.xml; skeleton.xml)|*.mesh.xml;*.skeleton.xml|"
    "OpenGEX-Fomat (ogex)|*.ogex|"
    "Quake I/II/III/3BSP (mdl; md2; md3; pk3)|*.mdl;*.md2;*.md3;*.pk3|"
    "Quick3D (q3o; q3s)|*.q3o;*.q3s|"
    "Raw Triangles (raw)|*.raw|"
    "RtCW (mdc)|*.mdc|"
    "Sense8 WorldToolkit (nff)|*.nff|"
    "Polygon File Format (ply)|*.ply|"
    "Stanford Triangle Format (ply)|*.ply|"
    "Terragen Terrain (ter)|*.ter|"
    "TrueSpace (cob; scn)|*.cob;*.scn|"
    "Valve Model (smd; vta)|*.smd;*.vta|"
    "XGL-3D-Format (xgl)|*.xgl|"
    "Additive Manufacturing (amf)|*.amf|"
    "ASSBIN (assbin)|*.assbin|"
    "OpenBVE 3D (b3d)|*.b3d|"
    "Inter-Quake Model (iqm)|*.iqm|"
    "3D Low-polygon Modeler (ndo)|*.ndo|"
    "Quest3D (q3d)|*.q3d|"
    "Silo Model Format (sib)|*.sib|"
    "Extensible 3D (x3d; x3db; x3dz; x3dbz)|*.x3d;*.x3db;*.x3dz;*.x3dbz|"
    "MikuMikuDance Format (pmd; pmx)|*.pmd;*.pmx"
)


class SnapPool:

    def __init__(self, objects: list, snap_points: list["_point.Point"],
                 threshold: float = 5.00):

        self.objects = objects
        self.numpy_points = np.array([point.as_float for point in snap_points], dtype=np.float32)
        self.threshold_sq = threshold ** 2

    def query(self, pos: "_point.Point"):
        world_pos = pos.as_numpy

        diff = self.numpy_points - world_pos
        dist_sq = (diff * diff).sum(axis=1)
        idx = int(dist_sq.argmin())

        if dist_sq[idx] <= self.threshold_sq:
            return self.objects[idx]
