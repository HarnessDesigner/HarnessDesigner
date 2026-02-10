from OCP.STEPControl import STEPControl_Reader
from . import ocp_read_shape as _ocp_read_shape
from .. import debug as _debug


@_debug.timeit
def load(file):
    step_reader = STEPControl_Reader()
    step_reader.ReadFile(file)
    step_reader.TransferRoots()  # NOQA
    shape = step_reader.Shape()

    vertices, faces = _ocp_read_shape(shape)

    return [[vertices, faces]]
