# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import numpy as np

from OCP.TopAbs import TopAbs_REVERSED
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location


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


def convert_model_to_mesh(model, lin_deflection=0.001, ang_deflection=0.1, is_relative=True):
    """
    Triangulate a CAD model into vertex and face arrays.

    :param model: Build123d/OCP model wrapper exposing ``wrapped`` and ``faces``.
    :type model: UNKNOWN
    :param lin_deflection: Chordal tolerance passed to OCCT's incremental
        mesher. When ``is_relative`` is True (the default) this is scaled by
        the model's own bounding box, so it stays coarse relative to large
        parts and fine relative to small ones -- pass ``is_relative=False``
        with an absolute value when the curvature you care about is much
        smaller than the model's overall bounding box (e.g. a thin helix
        swept across a long, shared mesh).
    :type lin_deflection: float
    :param ang_deflection: Maximum angle (radians) between tessellation
        segments on a curved surface -- lower is smoother.
    :type ang_deflection: float
    :param is_relative: Whether ``lin_deflection`` is relative to the
        model's bounding box (OCCT default) or an absolute distance.
    :type is_relative: bool
    :returns: Vertex and face arrays suitable for mesh processing.
    :rtype: tuple[numpy.ndarray, numpy.ndarray]
    """

    loc = TopLoc_Location()
    BRepMesh_IncrementalMesh(theShape=model.wrapped, theLinDeflection=lin_deflection,
                             isRelative=is_relative, theAngDeflection=ang_deflection, isInParallel=True)

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
