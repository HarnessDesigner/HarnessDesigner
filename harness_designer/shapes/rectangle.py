# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Flat rectangle mesh generation helpers.

The functions in this module build a flat (Y=0), axis-aligned quad for use by
:class:`harness_designer.gl.vbo.PooledVBOHandler` instances -- the 2D-editor
counterpart to :mod:`harness_designer.shapes.box`. The generated quad lies in
the XZ plane, matching every other flat/ground-plane mesh in this codebase
(floor, grid, Peg Board strands).
"""

import numpy as np

from .. import utils as _utils
from ..gl import vbo as _vbo_handler
from .. import check_types as _check_types


_vbo: _vbo_handler.PooledVBOHandler = None
_vbo_based: _vbo_handler.PooledVBOHandler = None


@_check_types.do
def create_vbo() -> _vbo_handler.PooledVBOHandler:
    """Create or return the cached unit rectangle VBO.

    The cached mesh is built from :func:`create` using unit dimensions.

    :returns: Cached VBO data for a rectangle with dimensions ``1 x 0 x 1``.
    :rtype: :class:`harness_designer.gl.vbo.PooledVBOHandler`
    """
    global _vbo

    if _vbo is None:
        vertices, faces = create(1.0, 1.0)

        packed, count = _utils.compute_normals(vertices, faces)

        unpacked_verts = packed[:count * 3].reshape(-1, 3)
        aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
        aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
        obb = _utils.compute_obb(aabb1, aabb2)

        _vbo = _vbo_handler.PooledVBOHandler(
            'rectangle', packed, count, aabb=aabb, obb=obb,
            arena_kind=_vbo_handler.VBO_TYPE_PRIMITIVE)

    return _vbo


@_check_types.do
def create_vbo_based() -> _vbo_handler.PooledVBOHandler:
    """Create or return the cached unit "based" rectangle VBO -- same
    shape as :func:`create_vbo`, but X spans ``[0, 1]`` instead of
    ``[-0.5, 0.5]`` (see :func:`create_based`). For objects like a wire,
    whose ``position`` is one endpoint (not a center) and whose length
    is applied via ``scale.x`` -- mirrors ``shapes/cylinder.py``'s own
    based-at-origin convention (a unit cylinder spans local Z ``[0,
    length]``, not centered either), so ``objects_schematic/wire.py``'s ``Wire``
    can use ``position = start point`` exactly like
    ``objects3d/wire.py``'s ``Wire`` does.

    :returns: Cached VBO data for a rectangle with dimensions ``1 x 0 x 1``.
    :rtype: :class:`harness_designer.gl.vbo.PooledVBOHandler`
    """
    global _vbo_based

    if _vbo_based is None:
        vertices, faces = create_based(1.0, 1.0)

        packed, count = _utils.compute_normals(vertices, faces)

        unpacked_verts = packed[:count * 3].reshape(-1, 3)
        aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
        aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
        obb = _utils.compute_obb(aabb1, aabb2)

        _vbo_based = _vbo_handler.PooledVBOHandler(
            'rectangle_based', packed, count, aabb=aabb, obb=obb,
            arena_kind=_vbo_handler.VBO_TYPE_PRIMITIVE)

    return _vbo_based


@_check_types.do
def create_based(width, height):
    """Create vertex and face arrays for a flat rectangle based at the
    origin along X (``[0, width]``) instead of centered (see
    :func:`create`) -- otherwise identical (Y=0 plane, ``height`` along
    Z, centered on Z).

    :param width: Overall size along the X axis, spanning ``[0, width]``.
    :type width: float
    :param height: Overall size along the Z axis, centered on Z.
    :type height: float
    :returns: Vertex and triangle index arrays for the rectangle mesh.
    :rtype: tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`]
    """
    half_h = height / 2.0

    vertices = np.array([
        [0.0, 0, -half_h],
        [width, 0, -half_h],
        [width, 0, half_h],
        [0.0, 0, half_h],
    ], dtype=np.float32)

    # Same winding as create() -- face normal points +Y.
    faces = np.array([[0, 2, 1], [0, 3, 2]], dtype=np.int32)

    return vertices, faces


@_check_types.do
def create(width, height):
    """Create vertex and face arrays for a flat, axis-aligned rectangle.

    The generated rectangle is centered on the origin, lies flat on the
    Y=0 plane (``height`` controls how far the two Y=±height/2 faces are
    apart -- 0 collapses them onto the same plane) and uses triangle faces.

    :param width: Overall size along the X axis.
    :type width: float
    :param height: Overall size along the Y axis.
    :type height: float
    :returns: Vertex and triangle index arrays for the rectangle mesh.
    :rtype: tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`]
    """

    half_w = width / 2.0
    half_h = height / 2.0

    vertices = np.array([
        [-half_w, 0, -half_h],
        [half_w, 0, -half_h],
        [half_w, 0, half_h],
        [-half_w, 0, half_h],
    ], dtype=np.float32)

    # Wound so the face normal points +Y (matches _process_verts_for_normals'
    # cross(v1-v0, v2-v0) convention -- see shapes/circle.py and
    # shapes/triangle.py for the same winding rule applied to a fan/apex).
    faces = np.array([[0, 2, 1], [0, 3, 2]], dtype=np.int32)

    return vertices, faces
