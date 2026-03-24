
import build123d

from .. import utils as _utils
from ..gl import vbo as _vbo_handler


_vbo: _vbo_handler.VBOHandler = None

SHAFT_RADIUS = 0.05
SHAFT_LENGTH = 0.7
CONE_LENGTH = 0.3
CONE_RADIUS = 0.15


def create_vbo() -> _vbo_handler.VBOHandler:
    global _vbo

    if _vbo is not None:
        return _vbo

    # Create shaft cylinder along +Z axis starting at origin
    shaft = build123d.Cylinder(SHAFT_RADIUS, SHAFT_LENGTH, align=build123d.Align.NONE)

    # Create cone for arrowhead (base_radius, top_radius, height)
    cone = build123d.Cone(CONE_RADIUS, 0.0, CONE_LENGTH, align=build123d.Align.NONE)

    # Position cone at the top of the shaft
    cone = cone.move(build123d.Location((0.0, 0.0, SHAFT_LENGTH)))

    # Combine shaft and cone into a single arrow shape
    arrow = shaft + cone

    vertices, faces = _utils.convert_model_to_mesh(arrow)
    vertices, normals, faces, count = _utils.compute_vbo_smoothed_vertex_normals(vertices, faces)

    _vbo = _vbo_handler.VBOHandler('move_arrows', vertices, normals, faces, count)

    return _vbo
