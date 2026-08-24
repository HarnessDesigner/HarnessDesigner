# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import program as _program

from ... import check_types as _check_types

_faces_program: _program.FacesProgram = None
_edges_program: _program.EdgesProgram = None
_vertices_program: _program.VerticesProgram = None
_floor_program: _program.FloorProgram = None
_grid2d_program: _program.GridProgram = None


@_check_types.do
def _compile_grid2d_program() -> _program.GridProgram:
    """Compile and link the grid2d program."""

    global _grid2d_program

    if _grid2d_program is None:
        _grid2d_program = _program.GridProgram()

    return _grid2d_program


@_check_types.do
def _compile_faces_program() -> _program.FacesProgram:
    """Compile and link the triangles shader program (faces with lighting and reflections)."""

    global _faces_program

    if _faces_program is None:
        _faces_program = _program.FacesProgram()

    return _faces_program


@_check_types.do
def _compile_edges_program() -> _program.EdgesProgram:
    """Compile and link the lines shader program (edges and normals)."""

    global _edges_program

    if _edges_program is None:
        _edges_program = _program.EdgesProgram()

    return _edges_program


@_check_types.do
def _compile_vertices_program() -> _program.VerticesProgram:
    """Compile and link the points shader program (vertices)."""

    global _vertices_program

    if _vertices_program is None:
        _vertices_program = _program.VerticesProgram()

    return _vertices_program


@_check_types.do
def _compile_floor_program() -> _program.FloorProgram:
    """Compile and link the floor shader program (per-vertex color, no lighting)."""

    global _floor_program

    if _floor_program is None:
        _floor_program = _program.FloorProgram()

    return _floor_program


class _ShaderProgramMeta(type):
    _instance = None

    def __call__(cls):
        if cls._instance is None:
            cls._instance = super().__call__()

        return cls._instance


class ShaderProgram(metaclass=_ShaderProgramMeta):

    def __init__(self):
        self.grid = _compile_grid2d_program()
        self.faces = _compile_faces_program()
        self.edges = _compile_edges_program()
        self.vertices = _compile_vertices_program()
        self.floor = _compile_floor_program()
