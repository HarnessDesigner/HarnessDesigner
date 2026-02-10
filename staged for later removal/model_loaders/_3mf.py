import numpy as np
import lib3mf
from .. import debug as _debug


@_debug.timeit
def load(file):
    wrapper = lib3mf.Wrapper()
    model = wrapper.CreateModel()

    reader = model.QueryReader("3mf")
    reader.ReadFromFile(file)

    res = []

    it = model.GetObjects()
    while it.MoveNext():
        obj = it.GetCurrentObject()
        # We only care about mesh objects; 3MF can contain components, slices, etc.
        if not obj.IsMeshObject():
            continue

        mesh = obj.GetMeshObject()

        vertices = np.array(mesh.GetVertices(), dtype=np.float64).reshape(-1, 3)
        faces = np.array(mesh.GetTriangleIndices(), dtype=np.int32).reshape(-1, 3)

        res.append([vertices, faces])

    return res


