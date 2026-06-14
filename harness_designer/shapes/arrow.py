# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Arrow mesh generation helpers.

The mesh built here is converted into a cached
:class:`harness_designer.gl.vbo.PooledVBOHandler` for reuse by the OpenGL layer.
"""

import build123d
import numpy as np

from .. import utils as _utils
from ..gl import vbo as _vbo_handler


_vbo: _vbo_handler.PooledVBOHandler = None


def create_vbo() -> _vbo_handler.PooledVBOHandler:
    """Create or return the cached arrow VBO.

    The geometry is assembled with :mod:`build123d`, converted to a mesh with
    :func:`harness_designer.utils.convert_model_to_mesh`, and then wrapped in a
    :class:`harness_designer.gl.vbo.PooledVBOHandler`.

    :returns: Cached vertex-buffer object data for the move arrow mesh.
    :rtype: :class:`harness_designer.gl.vbo.PooledVBOHandler`
    """
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
    packed, count = _utils.compute_normals(vertices, faces)

    unpacked_verts = packed[:count * 3].reshape(-1, 3)
    aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
    aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
    obb = _utils.compute_obb(aabb1, aabb2)

    _vbo = _vbo_handler.PooledVBOHandler(
        'move_arrow', packed, count, aabb=aabb, obb=obb,
        arena_kind=_vbo_handler.VBO_TYPE_PRIMITIVE)

    return _vbo
