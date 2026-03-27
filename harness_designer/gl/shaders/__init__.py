from . import vertices as _vertices
from . import faces as _faces
from . import edges as _edges
from . import floor as _floor


def compile_faces_program():
    """Compile and link the triangles shader program (faces with lighting and reflections)."""
    return _faces.compile_program()


def compile_edges_program():
    """Compile and link the lines shader program (edges and normals)."""
    return _edges.compile_program()


def compile_vertices_program():
    """Compile and link the points shader program (vertices)."""
    return _vertices.compile_program()


def compile_floor_program():
    """Compile and link the floor shader program (per-vertex color, no lighting)."""
    return _floor.compile_program()
