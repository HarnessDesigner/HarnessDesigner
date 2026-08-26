# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import program as _program

from ... import check_types as _check_types


@_check_types.do
def _compile_grid2d_program() -> _program.GridProgram:
    """Compile and link the grid2d program."""

    return _program.GridProgram()


@_check_types.do
def _compile_faces_program() -> _program.FacesProgram:
    """Compile and link the triangles shader program (faces with lighting and reflections)."""

    return _program.FacesProgram()


@_check_types.do
def _compile_edges_program() -> _program.EdgesProgram:
    """Compile and link the lines shader program (edges and normals)."""

    return _program.EdgesProgram()


@_check_types.do
def _compile_vertices_program() -> _program.VerticesProgram:
    """Compile and link the points shader program (vertices)."""

    return _program.VerticesProgram()


@_check_types.do
def _compile_floor_program() -> _program.FloorProgram:
    """Compile and link the floor shader program (per-vertex color, no lighting)."""

    return _program.FloorProgram()


class ShaderProgram:
    """One set of compiled/linked GL programs, owned by a single canvas.

    Each of the 3 canvases (3D/schematic/pegboard) is a separate
    QOpenGLWidget with its own, non-shared GL context, and constructs its
    own ``ShaderProgram`` from ``initializeGL`` (with that context current).
    A process-wide cache here would hand later canvases program ids that
    are only valid in whichever canvas's context compiled them first --
    exactly the cross-context GL_INVALID_OPERATION bug this replaced.
    """

    def __init__(self):
        self.grid = _compile_grid2d_program()
        self.faces = _compile_faces_program()
        self.edges = _compile_edges_program()
        self.vertices = _compile_vertices_program()
        self.floor = _compile_floor_program()
