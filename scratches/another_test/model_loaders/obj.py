from . import quadratic_mesh_reduction


try:
    from .. import debug as _debug
except ImportError:
    import debug as _debug  # NOQA


@_debug.timeit
def load_from_obj(file):

    vertices = []
    faces = []
    with open(file) as f:
        for line in f:
            if line[0] == "v":
                vertex = list(map(float, line[2:].strip().split()))
                vertices.append(vertex)
            elif line[0] == "f":
                face = list(map(int, line[2:].strip().split()))
                faces.append(face)

    if len(faces) > 10000:
        vertices, faces = quadratic_mesh_reduction.reduce(vertices, faces, faces // 10)

    return vertices, faces


