# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Square outline (picture-frame) mesh generation.

Built with :mod:`build123d` as one box minus a second, taller box
punched through its middle -- the frame equivalent of
:mod:`harness_designer.shapes.box`. Meant to be scaled non-uniformly at
render time (X = length, Y = thickness, Z = width) to trace an outline
around an arbitrary rectangle, e.g. an object's OBB footprint projected
onto the floor.
"""

import build123d
import numpy as np

from .. import utils as _utils
from ..gl import vbo as _vbo_handler
from . import mesh_cache as _mesh_cache
from .. import check_types as _check_types


_vbo: _vbo_handler.PooledVBOHandler = None

# Bump if this module's own build123d geometry ever changes -- see
# shapes/mesh_cache.py's own docstring for why.
_MESH_CACHE_VERSION = 1

# Inner box's width/depth as a fraction of the outer box's -- controls
# how thick the frame's border reads relative to its own footprint.
_INNER_FRACTION = 0.9


@_check_types.do
def create_vbo() -> _vbo_handler.PooledVBOHandler:
    """Create or return the cached unit square-outline VBO.

    The geometry is one ``1 x 1 x 1`` box with a second, taller
    (``0.9 x 1.2 x 0.9``) box subtracted from its middle -- since the
    inner box is taller than the outer one, the subtraction punches
    straight through along Y, leaving a hollow picture-frame. Built with
    :mod:`build123d`, converted to a mesh with
    :func:`harness_designer.utils.convert_model_to_mesh`, and cached to
    disk the same way :func:`harness_designer.shapes.arrow.create_vbo`
    caches its own build123d mesh.

    :returns: Cached VBO data for a ``1 x 1 x 1`` square outline frame.
    :rtype: :class:`harness_designer.gl.vbo.PooledVBOHandler`
    """
    global _vbo

    if _vbo is not None:
        return _vbo

    cached = _mesh_cache.load('square_outline', _MESH_CACHE_VERSION)
    if cached is not None:
        packed, count, aabb, obb, _extra = cached
        _vbo = _vbo_handler.PooledVBOHandler(
            'square_outline', packed, count, aabb=aabb, obb=obb,
            arena_kind=_vbo_handler.VBO_TYPE_PRIMITIVE)
        return _vbo

    outer = build123d.Box(1.0, 1.0, 1.0)
    inner = build123d.Box(_INNER_FRACTION, 1.2, _INNER_FRACTION)
    frame = outer - inner

    vertices, faces = _utils.convert_model_to_mesh(frame)
    packed, count = _utils.compute_normals(vertices, faces)

    unpacked_verts = packed[:count * 3].reshape(-1, 3)
    aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
    aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
    obb = _utils.compute_obb(aabb1, aabb2)

    _vbo = _vbo_handler.PooledVBOHandler(
        'square_outline', packed, count, aabb=aabb, obb=obb,
        arena_kind=_vbo_handler.VBO_TYPE_PRIMITIVE)

    _mesh_cache.save('square_outline', _MESH_CACHE_VERSION, packed, count, aabb, obb)

    return _vbo
