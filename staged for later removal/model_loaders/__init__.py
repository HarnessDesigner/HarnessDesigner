import numpy as np

import meshio
import pyfqmr

from OCP.TopAbs import TopAbs_REVERSED
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location

from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.TopoDS import TopoDS


def ocp_read_shape(shape):

    BRepMesh_IncrementalMesh(theShape=shape, theLinDeflection=0.001,
                             isRelative=True, theAngDeflection=0.1, isInParallel=True)

    vertices = []
    faces = []
    offset = 0

    anExpSF = TopExp_Explorer(shape, TopAbs_FACE)
    while anExpSF.More():
        if anExpSF.Current().ShapeType() != TopAbs_FACE:
            continue

        aLoc = TopLoc_Location()

        poly_triangulation = (
            BRep_Tool.Triangulation_s(TopoDS.Face_s(anExpSF.Current()), aLoc))  # NOQA

        if not poly_triangulation:
            continue

        trsf = aLoc.Transformation()

        node_count = poly_triangulation.NbNodes()
        for i in range(1, node_count + 1):
            gp_pnt = poly_triangulation.Node(i).Transformed(trsf)
            pnt = (gp_pnt.X(), gp_pnt.Y(), gp_pnt.Z())
            vertices.append(pnt)

        facet_reversed = anExpSF.Current().Orientation() == TopAbs_REVERSED

        order = [1, 3, 2] if facet_reversed else [1, 2, 3]
        for tri in poly_triangulation.Triangles():
            faces.append([tri.Value(i) + offset - 1 for i in order])

        offset += node_count
        anExpSF.Next()

    vertices = np.array(vertices, dtype=np.float64)
    faces = np.array(faces, dtype=np.int32)

    return vertices, faces


def meshio_read_mesh(m: meshio.Mesh):
    vertices = np.asarray(m.points, dtype=np.float64)
    if vertices.ndim != 2 or vertices.shape[1] < 3:
        raise ValueError(f"meshio points has unexpected shape {vertices.shape}")

    vertices = vertices[:, :3]

    faces_out = []

    for cell_block in m.cells:
        ctype = cell_block.type
        data = np.asarray(cell_block.data)

        if ctype == "triangle":
            faces_out.append(data.astype(np.int32, copy=False))

        elif ctype == "quad":
            # triangulate quads
            for q in data:
                i0, i1, i2, i3 = map(int, q)
                faces_out.append(np.array([[i0, i1, i2], [i0, i2, i3]],
                                          dtype=np.int32))

        elif ctype == "polygon":
            # may be ragged; fan triangulate each polygon
            for poly in data:
                poly = np.asarray(poly, dtype=np.int64).ravel()
                if len(poly) < 3:
                    continue

                i0 = int(poly[0])
                for j in range(1, len(poly) - 1):
                    faces_out.append(np.array([[i0, int(poly[j]), int(poly[j + 1])]],
                                              dtype=np.int32))

        else:
            # ignore non-surface cells
            continue

    if faces_out:
        faces = np.vstack(faces_out).astype(np.int32, copy=False)
    else:
        faces = np.empty((0, 3), dtype=np.int32)

    vertices = vertices.astype(np.float64, copy=False)
    return vertices, faces


def reduce_triangles(verts: np.ndarray, faces: np.ndarray, target_count: int,
                     aggressiveness: float, update_rate: int = 1,
                     max_iterations: int = 150, lossless: bool = False,
                     threshold_lossless: float = 1e-3, alpha: float = 1e-9,
                     K: int = 3) -> tuple[np.ndarray, np.ndarray]:

    """
    target_count : int
        Target number of triangles, not used if lossless is True
    update_rate : int
        Number of iterations between each update.
        If lossless flag is set to True, rate is 1
    aggressiveness : float
        Parameter controlling the growth rate of the threshold at each
        iteration when lossless is False.
    max_iterations : int
        Maximal number of iterations
    verbose : bool
        control verbosity
    lossless : bool
        Use the lossless simplification method
    threshold_lossless : float
        Maximal error after which a vertex is not deleted, only for
        lossless method.
    alpha : float
        Parameter for controlling the threshold growth
    K : int
        Parameter for controlling the thresold growth
    preserve_border : Bool
        Flag for preserving vertices on open border
    """

    mesh_simplifier = pyfqmr.Simplify()
    mesh_simplifier.setMesh(verts, faces)
    mesh_simplifier.simplify_mesh(
        target_count=target_count,
        update_rate=update_rate,
        max_iterations=max_iterations,
        aggressiveness=aggressiveness,
        lossless=lossless,
        threshold_lossless=threshold_lossless,
        alpha=alpha,
        K=K,
        verbose=False
    )

    vertices, faces, _ = mesh_simplifier.getMesh()

    return vertices, faces

