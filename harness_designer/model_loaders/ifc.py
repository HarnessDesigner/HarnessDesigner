import numpy as np
import ifcopenshell
import ifcopenshell.geom
from .. import debug as _debug


@_debug.timeit
def load(file):
    ifc = ifcopenshell.open(file)

    settings = ifcopenshell.geom.settings()
    # Common options; tweak as needed:
    settings.set(settings.USE_WORLD_COORDS, True)   # bake placements into verts
    settings.set(settings.APPLY_DEFAULT_MATERIALS, False)

    all_vertices = []
    all_faces = []
    offset = 0

    # Iterate products that can have geometry.
    # You can broaden/narrow this list; IfcProduct is typical.
    for product in ifc.by_type("IfcProduct"):
        if not product.Representation:
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, product)
        except Exception:  # NOQA
            continue

        verts = np.asarray(shape.geometry.verts, dtype=np.float64).reshape(-1, 3)
        faces = np.asarray(shape.geometry.faces, dtype=np.int32).reshape(-1, 3)

        if len(verts) == 0 or len(faces) == 0:
            continue

        all_vertices.append(verts)
        all_faces.append(faces + offset)
        offset += verts.shape[0]

    if all_vertices:
        vertices = np.vstack(all_vertices).astype(np.float64, copy=False)
        faces = np.vstack(all_faces).astype(np.int32, copy=False)
    else:
        vertices = np.empty((0, 3), dtype=np.float64)
        faces = np.empty((0, 3), dtype=np.int32)

    return [[vertices, faces]]
