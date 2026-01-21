
from OCP.Vrml import Vrml_Provider
from . import ocp_read_shape as _ocp_read_shape
from .. import debug as _debug


@_debug.timeit
def load(file):
    reader = Vrml_Provider()
    reader.ReadFile(file)
    reader.TransferRoots()
    shape = reader.Shape()

    vertices, faces = _ocp_read_shape(shape)

    return [[vertices, faces]]
