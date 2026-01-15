import build123d
import numpy as np

from OCP.TopAbs import TopAbs_REVERSED
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location

from . import quadratic_mesh_reduction


try:
    from .. import debug as _debug
except ImportError:
    import debug as _debug  # NOQA


@_debug.timeit
def load_from_stl(file):
    shape = build123d.import_stl(file)

    loc = TopLoc_Location()
    BRepMesh_IncrementalMesh(theShape=shape.wrapped, theLinDeflection=0.001,
                             isRelative=True, theAngDeflection=0.1, isInParallel=True)

    vertices = []
    faces = []
    offset = 0
    for facet in shape.faces():
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

    vertices = np.array(vertices, dtype=np.float64)
    faces = np.array(faces, dtype=np.int32)

    if len(faces) * 3 > 50000:
        vertices, faces = quadratic_mesh_reduction.reduce(vertices, faces, len(faces) * 3 // 30)

    return vertices, faces
