import os
import numpy as np

import pyfqmr

from OCP.TopAbs import TopAbs_REVERSED
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location
from OCP.Vrml import Vrml_Provider
from OCP.STEPControl import STEPControl_Reader
from OCP.IGESControl import IGESControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.TopoDS import TopoDS

from .... import debug as _debug


os.environ['PATH'] = os.path.dirname(__file__) + ';' + os.environ['PATH']

import pyassimp  # NOQA


class ModelException(Exception):
    pass


class ModelLoadError(ModelException):
    pass


@_debug.logfunc
def _ocp_read_shape(shape):

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


@_debug.logfunc
def _load_with_assimp(path):
    flags = (pyassimp.postprocess.aiProcess_Triangulate |
             pyassimp.postprocess.aiProcess_JoinIdenticalVertices)

    vertices = []
    faces = []
    offset = 0

    with pyassimp.load(path, processing=flags) as scene:
        for mesh in scene.meshes:
            v = mesh.vertices.copy()
            vertices.append(v)
            faces.append(mesh.faces.copy() + offset)
            offset += len(v)

    vertices = np.array(vertices, dtype=np.float64).reshape(-1, 3)
    faces = np.array(faces, dtype=np.int32).reshape(-1, 3)

    return vertices, faces


@_debug.logfunc
def _load_vrml(file):
    reader = Vrml_Provider()
    reader.ReadFile(file)
    reader.TransferRoots()
    shape = reader.Shape()

    vertices, faces = _ocp_read_shape(shape)

    return vertices, faces


@_debug.logfunc
def _load_step(file):
    step_reader = STEPControl_Reader()
    step_reader.ReadFile(file)
    step_reader.TransferRoots()  # NOQA
    shape = step_reader.Shape()

    vertices, faces = _ocp_read_shape(shape)

    return vertices, faces


@_debug.logfunc
def _load_iges(file):
    reader = IGESControl_Reader()
    reader.ReadFile(file)
    reader.TransferRoots()  # NOQA
    shape = reader.Shape()

    vertices, faces = _ocp_read_shape(shape)

    return vertices, faces


@_debug.logfunc
def load(file: str) -> tuple[np.ndarray, np.ndarray]:
    if file.endswith('.vrml'):
        return _load_vrml(file)
    elif file.endswith('.iges'):
        return _load_iges(file)
    elif file.endswith('.step') or file.endswith('stp'):
        return _load_step(file)
    else:
        try:
            return _load_with_assimp(file)
        except Exception as err:
            raise ModelLoadError from err


@_debug.logfunc
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
