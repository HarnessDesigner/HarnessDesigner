import numpy as np

from OCP.gp import gp_Vec, gp
from OCP.TopAbs import TopAbs_REVERSED
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location

import debug as _debug

import compute_normals as _compute_normals


def _convert_shape_to_mesh(ocp_mesh):
    loc = TopLoc_Location()
    BRepMesh_IncrementalMesh(theShape=ocp_mesh.wrapped, theLinDeflection=0.001,
                             isRelative=True, theAngDeflection=0.1, isInParallel=True)

    vertices = []
    faces = []
    offset = 0
    for facet in ocp_mesh.faces():
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


@_debug.timeit
def get_triangles(ocp_mesh):
    vertices, faces = _convert_shape_to_mesh(ocp_mesh)
    triangles, normals = _compute_normals.compute_vertex_normals(vertices, faces)

    return normals, triangles, len(triangles) * 3


@_debug.timeit
def get_smooth_triangles(ocp_mesh):
    vertices, faces = _convert_shape_to_mesh(ocp_mesh)
    triangles, normals = _compute_normals.compute_smoothed_vertex_normals(vertices, faces)

    return normals, triangles, len(triangles) * 3


'''
<bound method Camera._update_camera of <canvas.camera.Camera object at 0x000002C1034D5650>>
<bound method Camera._update_camera of <canvas.camera.Camera object at 0x000002C1034D5650>>
compute_smoothed_vertex_normals: 0.0ms
get_smooth_triangles: 20.0ms
compute_smoothed_vertex_normals: 1.0ms
get_smooth_triangles: 18.0ms
compute_smoothed_vertex_normals: 0.0ms
get_smooth_triangles: 18.0ms
compute_smoothed_vertex_normals: 4.0ms
get_smooth_triangles: 130.03ms
load_from_stl: 445.06ms
compute_vertex_normals: 1.0ms
<bound method timeit.<locals>._wrapper of <objects.housing.Housing object at 0x000002C1049AD090>>
compute_smoothed_vertex_normals: 1.0ms
get_smooth_triangles: 18.0ms
compute_smoothed_vertex_normals: 1.0ms
get_smooth_triangles: 16.95ms
compute_smoothed_vertex_normals: 0.0ms
get_smooth_triangles: 16.52ms

'''