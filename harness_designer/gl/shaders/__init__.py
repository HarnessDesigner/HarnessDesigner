from . import triangles as _triangles
from . import lines as _lines
from . import points as _points
from . import floor as _floor


def compile_triangles_program():
    """Compile and link the triangles shader program (faces with lighting and reflections)."""
    return _triangles.compile_program()


def compile_lines_program():
    """Compile and link the lines shader program (edges and normals)."""
    return _lines.compile_program()


def compile_points_program():
    """Compile and link the points shader program (vertices)."""
    return _points.compile_program()


def compile_floor_program():
    """Compile and link the floor shader program (per-vertex color, no lighting)."""
    return _floor.compile_program()


def create_program():
    """Create shader program (backwards-compatible alias for compile_triangles_program)."""
    return compile_triangles_program()
