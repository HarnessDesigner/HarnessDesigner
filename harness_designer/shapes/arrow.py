
import build123d

from .. import utils as _utils
from ..gl import vbo as _vbo_handler


_vbo: _vbo_handler.VBOHandler = None

ARROW_LENGTH = 1.0
SHAFT_RADIUS = 0.05
SHAFT_LENGTH = 0.7
CONE_LENGTH = 0.3
CONE_RADIUS = 0.15


def create_vbo() -> _vbo_handler.VBOHandler:
    global _vbo

    if _vbo is not None:
        return _vbo

    shaft = build123d.Cylinder(
        SHAFT_RADIUS, SHAFT_LENGTH,
        align=(build123d.Align.CENTER, build123d.Align.CENTER, build123d.Align.MIN))

    cone = build123d.Cone(
        bottom_radius=CONE_RADIUS, top_radius=0.0, height=CONE_LENGTH,
        align=(build123d.Align.CENTER, build123d.Align.CENTER, build123d.Align.MIN))

    cone = cone.move(build123d.Location((0.0, 0.0, SHAFT_LENGTH)))

    arrow = shaft + cone

    vertices, faces = _utils.convert_model_to_mesh(arrow)
    verts, nrmls, faces, count = _utils.compute_vbo_smoothed_vertex_normals(vertices, faces)

    _vbo = _vbo_handler.VBOHandler('move_arrows', verts, nrmls, faces, count)

    return _vbo
