# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Text mesh generation helpers.

Unlike every other ``shapes/`` generator, text has no single "unit" shape
to cache -- content is per-instance (a note's/housing's own string), so
there is no ``shapes/text.py``-owned ``create_vbo()`` singleton the way
``shapes/box.create_vbo()``/``shapes/rectangle.create_vbo()`` etc. are.
Instead the calling class (``objects.objects3d.note.Note``,
``objects.objects2d.housing.Housing``) generates and holds its own UUID --
exactly like a catalog part's ``Model3D.uuid`` keys its own
``PooledVBOHandler`` (see
``objects.objects3d.base3d.Base3D._set_model``) -- and passes it to
:func:`create_vbo` below. To update the text/size/style of an existing
VBO in place, build fresh mesh data with :func:`create` and call
``.update(packed, count)`` on the retained handler directly (see
``objects.objects3d.note.Note._rebuild`` for the reference).
"""

import numpy as np
import build123d

from .. import utils as _utils
from ..gl import vbo as _vbo_handler


def create(text: str, font_size: float, depth: float = 0.0,
           font_style: build123d.FontStyle = build123d.FontStyle.REGULAR,
           text_align: list[build123d.TextAlign] | None = None):
    """Create vertex and face arrays for a text mesh, plus its measured
    width.

    :param text: The text string.
    :type text: str
    :param font_size: Font size, world units (mm).
    :type font_size: float
    :param depth: Extrusion depth. ``0`` (the default) keeps the text
        flat, rotated so build123d's natural XY reading plane becomes the
        world XZ plane (Y axis -> Z axis) -- matches every other flat
        primitive in this codebase (``shapes/rectangle.py``,
        ``shapes/circle.py``, ``shapes/triangle.py``). A nonzero depth
        extrudes the text upright instead, unrotated -- real 3D
        thickness, visible from any angle (e.g. the 3D editor's notes).
    :type depth: float
    :param font_style: build123d font style.
    :type font_style: :class:`build123d.FontStyle`
    :param text_align: build123d ``[horizontal, vertical]`` text
        alignment (``LEFT``/``CENTER``/``RIGHT`` and ``TOP``/``CENTER``/
        ``BOTTOM`` respectively -- build123d puts the mesh origin at
        exactly that edge/corner of the text, so callers anchoring a
        specific edge, e.g. ``[RIGHT, BOTTOM]``, should pass that instead
        of doing their own offset math against the CENTER,CENTER default).
        Defaults to ``[CENTER, CENTER]``.
    :type text_align: list[:class:`build123d.TextAlign`] | None
    :returns: ``(vertices, faces, width, height)`` -- build123d's own X/Y
        extent (the character-width/-height axes), unaffected by either
        transform above.
    :rtype: tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`, float, float]
    """
    if text_align is None:
        text_align = [build123d.TextAlign.CENTER, build123d.TextAlign.CENTER]

    model = build123d.Text(text, font_size=font_size, font_style=font_style,
                           text_align=text_align)
    size = model.bounding_box().size
    width, height = float(size.X), float(size.Y)

    if depth:
        model = build123d.extrude(model, depth)
    else:
        # build123d draws text on its natural XY plane (character-width =
        # X, character-height = Y, face normal = Z). Every flat primitive
        # in this codebase instead lies in the world XZ plane (Y=0), so
        # rotate +90 degrees about X (character-height Y -> world Z, face
        # normal Z -> world Y) -- sign verified empirically against a live
        # render (the initial -90 degrees guess read upside-down).
        model = model.rotate(build123d.Axis.X, 90.0)

    vertices, faces = _utils.convert_model_to_mesh(model)

    return vertices, faces, width, height


def create_vbo(uuid_: str, text: str, font_size: float, depth: float = 0.0,
               font_style: build123d.FontStyle = build123d.FontStyle.REGULAR,
               text_align: list[build123d.TextAlign] | None = None
               ) -> tuple[_vbo_handler.PooledVBOHandler, float, float]:
    """Build (or, if *uuid_* is already registered, return the cached)
    ``PooledVBOHandler`` for *text*, plus its measured width/height. See
    the module docstring for the id-ownership convention and how to
    update an existing handler's content in place.

    :returns: ``(vbo, width, height)``.
    :rtype: tuple[:class:`harness_designer.gl.vbo.PooledVBOHandler`, float, float]
    """
    vertices, faces, width, height = create(text, font_size, depth, font_style, text_align)

    packed, count = _utils.compute_normals(vertices, faces)

    unpacked_verts = packed[:count * 3].reshape(-1, 3)
    aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
    aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
    obb = _utils.compute_obb(aabb1, aabb2)

    vbo = _vbo_handler.PooledVBOHandler(uuid_, packed, count, aabb=aabb, obb=obb)

    return vbo, width, height
