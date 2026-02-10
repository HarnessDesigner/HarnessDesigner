
from OCP.IGESControl import IGESControl_Reader
from . import ocp_read_shape as _ocp_read_shape
from .. import debug as _debug


@_debug.timeit
def load(file):
    reader = IGESControl_Reader()
    reader.ReadFile(file)
    reader.TransferRoots()  # NOQA
    shape = reader.Shape()

    vertices, faces = _ocp_read_shape(shape)

    return [[vertices, faces]]