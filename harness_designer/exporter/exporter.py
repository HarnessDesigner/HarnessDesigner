'''
supported export formats

pyassimp: OBJ OPENGEX PLY 3DS ASSBIN ASSXML COLLADA FBX STL X X3D GLTF 3MF PBRT ASSJSON STEP

cadquery: IGES BREP VRML

'''

import ctypes

import numpy as np


# Packed array layout produced by compute_normals() in utils.py:
#   [0   : n*3)  triangle-soup vertex positions  (n verts × 3 floats)
#   [n*3 : n*6)  smooth normals per vertex
#   [n*6 : n*9)  face normals per vertex
# where n = vertex_count = F*3  (F triangles × 3 verts)


def _unpack(packed: np.ndarray, vertex_count: int):
    n = vertex_count
    verts = packed[:n * 3].reshape(-1, 3)
    smooth = packed[n * 3:n * 6].reshape(-1, 3)
    face_n = packed[n * 6:n * 9].reshape(-1, 3)
    return verts, smooth, face_n


# ---------------------------------------------------------------------------
# OCP path — BREP / IGES / VRML
# ---------------------------------------------------------------------------

def _safe_dir(nx, ny, nz):
    """Return a gp_Dir; falls back to (0,0,1) for zero-length normals."""
    from OCP.gp import gp_Dir
    if nx * nx + ny * ny + nz * nz < 1e-12:
        return gp_Dir(0.0, 0.0, 1.0)
    return gp_Dir(float(nx), float(ny), float(nz))


def _build_ocp_face(verts: np.ndarray, normals: np.ndarray):
    from OCP.gp import gp_Pnt
    from OCP.Poly import Poly_Triangulation, Poly_Triangle
    from OCP.TopLoc import TopLoc_Location
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Face

    n_verts = len(verts)
    n_tris  = n_verts // 3

    tri = Poly_Triangulation(n_verts, n_tris, False, True)  # hasUV=False, hasNormals=True

    for i in range(n_verts):
        tri.SetNode(i + 1, gp_Pnt(float(verts[i, 0]), float(verts[i, 1]), float(verts[i, 2])))
        tri.SetNormal(i + 1, _safe_dir(normals[i, 0], normals[i, 1], normals[i, 2]))

    for i in range(n_tris):
        tri.SetTriangle(i + 1, Poly_Triangle(i * 3 + 1, i * 3 + 2, i * 3 + 3))

    builder = BRep_Builder()
    face = TopoDS_Face()
    builder.MakeFace(face)
    builder.UpdateFace(face, tri, TopLoc_Location(), 1e-7)

    return face


def export_ocp(
    packed: np.ndarray,
    vertex_count: int,
    path: str,
    fmt: str,
    use_smooth_normals: bool = True,
):
    """
    Export model data via OCP (cadquery-ocp / OCCT).

    Parameters
    ----------
    packed : np.ndarray
        Flat float32 array from compute_normals().
    vertex_count : int
        Second return value of compute_normals().
    path : str
        Output file path.
    fmt : str
        One of 'brep', 'iges', 'vrml'.
    use_smooth_normals : bool
        True → use smooth normals; False → use flat/face normals.
    """
    verts, smooth_n, face_n = _unpack(packed, vertex_count)
    normals = smooth_n if use_smooth_normals else face_n
    shape = _build_ocp_face(verts, normals)

    fmt = fmt.lower()

    if fmt == 'brep':
        from OCP.BRepTools import BRepTools
        BRepTools.Write_s(shape, path)

    elif fmt == 'iges':
        from OCP.IGESControl import IGESControl_Writer
        writer = IGESControl_Writer()
        writer.AddShape(shape)
        writer.ComputeModel()
        writer.Write(path)

    elif fmt == 'vrml':
        from OCP.VrmlAPI import VrmlAPI_Writer
        writer = VrmlAPI_Writer()
        writer.Write(shape, path)

    else:
        raise ValueError(f'Unknown OCP export format: {fmt!r}  (expected brep/iges/vrml)')


# ---------------------------------------------------------------------------
# pyassimp path — OBJ, PLY, STL, COLLADA, FBX, GLTF, etc.
# ---------------------------------------------------------------------------

def _build_assimp_scene(verts: np.ndarray, normals: np.ndarray):
    """
    Construct a minimal aiScene ctypes structure pointing at the mesh data.

    Returns (scene, refs).  ``refs`` must be kept alive until after
    pyassimp.export() returns — it holds every ctypes allocation that
    the scene's internal pointers reference.
    """
    from pyassimp import structs

    n_verts = len(verts)
    n_tris  = n_verts // 3
    _AI_PRIMITIVE_TRIANGLES = 4

    # -- vertex positions -------------------------------------------------
    VArr  = structs.Vector3D * n_verts
    v_arr = VArr()
    for i in range(n_verts):
        v_arr[i].x = float(verts[i, 0])
        v_arr[i].y = float(verts[i, 1])
        v_arr[i].z = float(verts[i, 2])

    # -- normals ----------------------------------------------------------
    n_arr = VArr()
    for i in range(n_verts):
        n_arr[i].x = float(normals[i, 0])
        n_arr[i].y = float(normals[i, 1])
        n_arr[i].z = float(normals[i, 2])

    # -- faces (each face owns a small 3-element index array) -------------
    FArr    = structs.Face * n_tris
    f_arr   = FArr()
    idx_bufs = []                          # must outlive the scene
    for i in range(n_tris):
        IdxArr = ctypes.c_uint * 3
        idx = IdxArr(i * 3, i * 3 + 1, i * 3 + 2)
        idx_bufs.append(idx)
        f_arr[i].mNumIndices = 3
        f_arr[i].mIndices    = idx

    # -- mesh -------------------------------------------------------------
    mesh = structs.Mesh()
    mesh.mPrimitiveTypes    = _AI_PRIMITIVE_TRIANGLES
    mesh.mNumVertices       = n_verts
    mesh.mNumFaces          = n_tris
    mesh.mVertices          = ctypes.cast(v_arr, ctypes.POINTER(structs.Vector3D))
    mesh.mNormals           = ctypes.cast(n_arr, ctypes.POINTER(structs.Vector3D))
    mesh.mFaces             = ctypes.cast(f_arr, ctypes.POINTER(structs.Face))
    mesh.mMaterialIndex     = 0

    # -- material (minimal: zero properties) ------------------------------
    mat = structs.Material()
    mat.mNumProperties = 0
    mat.mNumAllocated  = 0

    # -- root node --------------------------------------------------------
    mesh_idx_buf = (ctypes.c_uint * 1)(0)
    node = structs.Node()
    node.mNumMeshes   = 1
    node.mMeshes      = mesh_idx_buf
    node.mNumChildren = 0
    # identity transform
    node.mTransformation.a1 = 1.0
    node.mTransformation.b2 = 1.0
    node.mTransformation.c3 = 1.0
    node.mTransformation.d4 = 1.0

    # -- pointer arrays ---------------------------------------------------
    mesh_ptr  = ctypes.pointer(mesh)
    MeshPArr  = ctypes.POINTER(structs.Mesh) * 1
    mesh_p_arr = MeshPArr(mesh_ptr)

    mat_ptr   = ctypes.pointer(mat)
    MatPArr   = ctypes.POINTER(structs.Material) * 1
    mat_p_arr = MatPArr(mat_ptr)

    node_ptr  = ctypes.pointer(node)

    # -- scene ------------------------------------------------------------
    scene = structs.Scene()
    scene.mFlags        = 0
    scene.mRootNode     = node_ptr
    scene.mNumMeshes    = 1
    scene.mMeshes       = ctypes.cast(mesh_p_arr, ctypes.POINTER(ctypes.POINTER(structs.Mesh)))
    scene.mNumMaterials = 1
    scene.mMaterials    = ctypes.cast(mat_p_arr, ctypes.POINTER(ctypes.POINTER(structs.Material)))

    refs = [
        v_arr, n_arr, f_arr, idx_bufs,
        mesh, mat, node,
        mesh_ptr, mat_ptr, node_ptr,
        mesh_idx_buf, mesh_p_arr, mat_p_arr,
    ]

    return scene, refs


def export_assimp(
    packed: np.ndarray,
    vertex_count: int,
    path: str,
    file_type: str,
    use_smooth_normals: bool = True,
):
    """
    Export model data via pyassimp / libassimp.

    Parameters
    ----------
    packed : np.ndarray
        Flat float32 array from compute_normals().
    vertex_count : int
        Second return value of compute_normals().
    path : str
        Output file path.
    file_type : str
        Assimp exporter id, e.g. 'obj', 'stl', 'collada', 'fbx', 'gltf2',
        'ply', '3ds', 'x3d', 'assxml', 'step'.
    use_smooth_normals : bool
        True → use smooth normals; False → use flat/face normals.
    """
    import pyassimp.core as _assimp

    verts, smooth_n, face_n = _unpack(packed, vertex_count)
    normals = smooth_n if use_smooth_normals else face_n

    scene, refs = _build_assimp_scene(verts, normals)
    try:
        _assimp.export(scene, path, file_type)
    finally:
        del refs
