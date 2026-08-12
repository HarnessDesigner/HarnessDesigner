# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import collections
import gc
import sys
import threading
import traceback

import numpy as np
from PySide6 import QtWidgets

from OCP.TopAbs import TopAbs_REVERSED
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location
from .. import check_types as _check_types


@_check_types.do
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


@_check_types.do
def convert_model_to_mesh(model, lin_deflection=0.001, ang_deflection=0.5, is_relative=True):
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

    # Working around a confirmed native heap-corruption bug in OCCT/OCP's
    # meshing code (PDB-symbolized ProcDump analysis, 2026-08-11): a
    # fixed-size out-of-bounds write during triangulation of large meshes
    # occasionally lands on an unrelated, live dict's ob_type/ma_used
    # fields. It's silent until CPython's cyclic GC later walks that dict
    # and dereferences the corrupted type pointer -- crashing here, inside
    # this function, purely because this is where a big enough allocation
    # happens to cross a GC threshold first. Disabling GC for the
    # extraction below does not fix the corruption, it only keeps the
    # collector from touching the bad object *during this window*. If the
    # corrupted object isn't part of a reference cycle, ordinary
    # refcounting frees it once it goes out of scope and that's the end of
    # it; if it's kept alive by a cycle, the same crash can still resurface
    # later, elsewhere, once GC is back on and eventually walks it.
    gc_was_enabled = gc.isenabled()
    gc.disable()

    try:
        loc = TopLoc_Location()
        BRepMesh_IncrementalMesh(theShape=model.wrapped, theLinDeflection=lin_deflection,
                                 isRelative=is_relative, theAngDeflection=ang_deflection, isInParallel=False)

        vertices = []
        faces = []
        offset = 0
        for face_idx, facet in enumerate(model.faces()):

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
                # Expanded out of the list comprehension that used to be here
                # (a single line in every crash traceback so far, regardless of
                # which of these three sub-steps was actually executing) --
                # each is now its own statement, so the next crash pinpoints
                # exactly one of: tri.Value(order[0]), tri.Value(order[1]), or
                # tri.Value(order[2]).
                idx0 = tri.Value(order[0]) + offset - 1
                idx1 = tri.Value(order[1]) + offset - 1
                idx2 = tri.Value(order[2]) + offset - 1
                face_row = [idx0, idx1, idx2]

                faces.append(face_row)

            offset += node_count

        vertices = np.array(vertices, dtype=np.float32)
        faces = np.array(faces, dtype=np.int32)
    finally:
        if gc_was_enabled:
            gc.enable()

    return vertices, faces
