# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import vertices as _vertices
from . import faces as _faces
from . import edges as _edges
from . import floor as _floor
from . import grid2d as _grid2d
from . import schematic2d as _schematic2d

_faces_program = None
_edges_program = None
_vertices_program = None
_floor_program = None
_grid2d_program = None
_schematic2d_program = None


def compile_schematic2d_program():
    """Compile and link the schematic2d program."""

    global _schematic2d_program

    if _schematic2d_program is None:
        _schematic2d_program = _schematic2d.compile_program()

    return _schematic2d_program


def compile_grid2d_program():
    """Compile and link the grid2d program."""

    global _grid2d_program

    if _grid2d_program is None:
        _grid2d_program = _grid2d.compile_program()

    return _grid2d_program


def compile_faces_program():
    """Compile and link the triangles shader program (faces with lighting and reflections)."""

    global _faces_program

    if _faces_program is None:
        _faces_program = _faces.compile_program()

    return _faces_program


def compile_edges_program():
    """Compile and link the lines shader program (edges and normals)."""

    global _edges_program

    if _edges_program is None:
        _edges_program = _edges.compile_program()

    return _edges_program


def compile_vertices_program():
    """Compile and link the points shader program (vertices)."""

    global _vertices_program

    if _vertices_program is None:
        _vertices_program = _vertices.compile_program()

    return _vertices_program


def compile_floor_program():
    """Compile and link the floor shader program (per-vertex color, no lighting)."""

    global _floor_program

    if _floor_program is None:
        _floor_program = _floor.compile_program()

    return _floor_program

