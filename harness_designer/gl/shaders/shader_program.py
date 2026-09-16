# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import program as _program


class ShaderProgram:
    """
    One set of compiled/linked GL programs, owned by a single canvas.

    Each of the 3 canvases (3D/schematic/pegboard) is a separate
    QOpenGLWidget with its own, non-shared GL context, and constructs its
    own ``ShaderProgram`` from ``initializeGL`` (with that context current).
    A process-wide cache here would hand later canvases program ids that
    are only valid in whichever canvas's context compiled them first --
    exactly the cross-context GL_INVALID_OPERATION bug this replaced.
    """

    def __init__(self):
        self.grid = _program.GridProgram()
        self.faces = _program.FacesProgram()
        self.edges = _program.EdgesProgram()
        self.vertices = _program.VerticesProgram()
        self.floor = _program.FloorProgram()
        self.texture = _program.TextureProgram()
