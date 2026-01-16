import numpy as np

import build123d

from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_REVERSED
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location


from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.TopoDS import TopoDS


from . import quadratic_mesh_reduction

try:
    from .. import debug as _debug
except ImportError:
    import debug as _debug  # NOQA

from . import MODEL_CACHE


@_debug.timeit
def load_from_stp(file):
    if file in MODEL_CACHE:
        return MODEL_CACHE[file]

    step_reader = STEPControl_Reader()
    step_reader.ReadFile(file)
    step_reader.TransferRoots()
    shape = step_reader.Shape()

    loc = TopLoc_Location()
    BRepMesh_IncrementalMesh(theShape=shape, theLinDeflection=0.001,
                             isRelative=True, theAngDeflection=0.1, isInParallel=True)

    vertices = []
    faces = []
    offset = 0

    anExpSF = TopExp_Explorer(shape, TopAbs_FACE)
    while anExpSF.More():

        anExpSF.Next()
        aLoc = TopLoc_Location()

        if anExpSF.Current().ShapeType() != TopAbs_FACE:
            continue

        poly_triangulation = BRep_Tool.Triangulation_s(TopoDS.Face_s(anExpSF.Current()), aLoc)

        if not poly_triangulation:
            continue

        trsf = loc.Transformation()

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

    vertices = np.array(vertices, dtype=np.float64)
    faces = np.array(faces, dtype=np.int32)

    if len(faces) * 3 > 50000:
        vertices, faces = quadratic_mesh_reduction.reduce(vertices, faces, len(faces) * 3 // 30)

    MODEL_CACHE[file] = (vertices, faces)

    return vertices, faces

