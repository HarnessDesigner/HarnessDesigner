import meshio
from . import meshio_read_mesh as _meshio_read_mesh
from .. import debug as _debug


@_debug.timeit
def load(file):
    m = meshio.read(file)
    vertices, faces = _meshio_read_mesh(m)
    return [[vertices, faces]]
