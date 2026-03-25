import build123d

from .. import utils as _utils
from ..gl import vbo as _vbo_handler


_vbo: _vbo_handler.VBOHandler = None


def create_vbo() -> _vbo_handler.VBOHandler:
    global _vbo

    if _vbo is not None:
        return _vbo

    edge = build123d.Edge.extrude(build123d.Vertex(2.0, 0.0, 0.0), (6.0, 0.0, 0.0))
    wire = build123d.Wire(edge)

    wire_angle = wire.tangent_angle_at(0) - 20.0

    # build123d.HeadType.FILLETED

    # Create the arrow head
    arrow_head = build123d.ArrowHead(size=2.0, rotation=wire_angle,
                                     head_type=build123d.HeadType.CURVED)

    polygon = build123d.Polygon((7.5, 0.20), (6.5, -0.125), (8.50, -0.125), align=None)

    arrow_head = arrow_head.move(build123d.Location((8.50, -0.125, 0.0)))

    # Trim the path so the tip of the arrow isn't lost
    trim_amount = 1.0 / wire.length
    shaft_path = wire.trim(trim_amount, 1.0)

    # Create a perpendicular line to sweep the tail path
    shaft_pen = shaft_path.perpendicular_line(0.25, 0)
    shaft = build123d.sweep(shaft_pen, shaft_path)

    arrow = arrow_head + shaft
    arrow += polygon

    arrow = build123d.extrude(arrow, 0.25, (0, 0, 1))
    arrow = arrow.move(build123d.Location((2.5, 0.0, 0.0)))

    vertices, faces = _utils.convert_model_to_mesh(arrow)
    vertices, normals, faces, count = _utils.compute_vbo_vertex_normals(vertices, faces)
    edges = _utils.compute_edges(faces)

    _vbo = _vbo_handler.VBOHandler('move_arrow', vertices, edges, normals, faces, count)

    return _vbo
