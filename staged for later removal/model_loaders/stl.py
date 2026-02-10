
from OCP.RWStl import RWStl_Reader
from . import ocp_read_shape as _ocp_read_shape
from .. import debug as _debug


@_debug.timeit
def load(file):
    reader = RWStl_Reader()
    reader.ReadFile(file)
    reader.TransferRoots()
    shape = reader.Shape()

    vertices, faces = _ocp_read_shape(shape)

    return [[vertices, faces]]

