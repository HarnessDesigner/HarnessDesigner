# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Central home for every function that touches OCP directly.

This is the *only* module allowed to ``import OCP`` (or any ``OCP.*``
submodule) at the top level. Every OCP-driven operation the application
needs lives here as one function, wrapped in
:func:`~harness_designer.ocp_threadworker.ocp_thread` so it always runs
on the single dedicated OCP-access thread regardless of which thread
calls it.

Each function's boundary is plain Python/numpy in, plain Python/numpy
out -- none of them hand a live OCP object back to the caller. That's
deliberate: an OCP object handed back to caller code would be a live
invitation for some other thread to touch it directly later, which is
exactly what the single-thread restriction exists to prevent (see the
module docstring on ``ocp_threadworker`` for the "NOTE" about this). If
a caller needs a follow-up operation performed on a shape produced
here, that operation gets its own ``@ocp_thread`` function in this
file, not a raw shape passed back out.

Not yet wired into the application -- see harness_designer's own build
notes for why (waiting on a from-source OCP build targeting Python
3.14t before any existing build123d call site gets switched over to
these).
"""

import enum

import numpy as np

from OCP.BRep import BRep_Tool
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.Font import (
    Font_FontMgr,
    Font_FA_Regular,
    Font_FA_Bold,
    Font_FA_Italic,
    Font_FA_BoldItalic,
)
from OCP.Graphic3d import (
    Graphic3d_HTA_LEFT,
    Graphic3d_HTA_CENTER,
    Graphic3d_HTA_RIGHT,
    Graphic3d_VTA_BOTTOM,
    Graphic3d_VTA_CENTER,
    Graphic3d_VTA_TOP,
    Graphic3d_VTA_TOPFIRSTLINE,
)
from OCP.gp import gp_Ax3, gp_Vec
from OCP.NCollection import NCollection_Utf8String
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.StdPrs import StdPrs_BRepFont, StdPrs_BRepTextBuilder
from OCP.TCollection import TCollection_AsciiString
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_ListOfShape

from .ocp_threadworker import ocp_thread as _ocp_thread


class FontStyle(enum.Enum):
    """Mirrors build123d.FontStyle -- same members, same meaning, no
    dependency on build123d to express it.
    """
    REGULAR = 1
    BOLD = 2
    ITALIC = 3
    BOLDITALIC = 4


class TextAlign(enum.Enum):
    """Mirrors build123d.TextAlign -- same members, same meaning, no
    dependency on build123d to express it.
    """
    BOTTOM = 1
    CENTER = 2
    LEFT = 3
    RIGHT = 4
    TOP = 5
    TOPFIRSTLINE = 6


_FONT_STYLE = {
    FontStyle.REGULAR: Font_FA_Regular,
    FontStyle.BOLD: Font_FA_Bold,
    FontStyle.ITALIC: Font_FA_Italic,
    FontStyle.BOLDITALIC: Font_FA_BoldItalic,
}

_HORIZ_ALIGN = {
    TextAlign.LEFT: Graphic3d_HTA_LEFT,
    TextAlign.CENTER: Graphic3d_HTA_CENTER,
    TextAlign.RIGHT: Graphic3d_HTA_RIGHT,
}

_VERT_ALIGN = {
    TextAlign.BOTTOM: Graphic3d_VTA_BOTTOM,
    TextAlign.CENTER: Graphic3d_VTA_CENTER,
    TextAlign.TOP: Graphic3d_VTA_TOP,
    TextAlign.TOPFIRSTLINE: Graphic3d_VTA_TOPFIRSTLINE,
}

# (font_name, style) -> StdPrs_BRepFont. Only ever touched from the OCP
# access thread (every read/write happens inside an @ocp_thread
# function), so this needs no lock of its own -- the single-thread
# restriction that ocp_threadworker enforces already serializes access
# to it for free. NOT safe to read from anywhere else; if a future
# per-style-parallel path gets built, it needs its own dedicated pool,
# not this cache.
_font_cache: dict[tuple[str, FontStyle], StdPrs_BRepFont] = {}


def _get_font(name: str, style: FontStyle, font_size: float) -> StdPrs_BRepFont:
    key = (name, style)
    font_i = _font_cache.get(key)
    if font_i is not None:
        return font_i

    aspect = _FONT_STYLE[style]
    mgr = Font_FontMgr.GetInstance_s()
    font_t = mgr.FindFont(TCollection_AsciiString(name), aspect)
    font_i = StdPrs_BRepFont(
        NCollection_Utf8String(font_t.FontName().ToCString()),
        aspect, float(font_size))
    _font_cache[key] = font_i

    return font_i


def _extrude_and_fuse(compound, depth: float):
    """Extrude every face of *compound* by *depth* along +Z and fuse the
    results into one shape. Mirrors build123d.extrude()'s own behavior
    for a flat, XY-plane compound of faces (see ocp_ops's own design
    notes -- text is always built in the default gp_Ax3(), so every
    glyph face's normal is (0, 0, 1); no per-face plane inference is
    needed the way build123d's generic extrude() does it).
    """
    direction = gp_Vec(0.0, 0.0, float(depth))

    exp = TopExp_Explorer(compound, TopAbs_FACE)
    solids = []
    while exp.More():
        prism = BRepPrimAPI_MakePrism(exp.Current(), direction)
        solids.append(prism.Shape())
        exp.Next()

    if not solids:
        return None

    if len(solids) == 1:
        result = solids[0]
    else:
        fuse_op = BRepAlgoAPI_Fuse()
        args = TopTools_ListOfShape()
        args.Append(solids[0])
        tools = TopTools_ListOfShape()
        for solid in solids[1:]:
            tools.Append(solid)
        fuse_op.SetArguments(args)
        fuse_op.SetTools(tools)
        fuse_op.Build()
        result = fuse_op.Shape()

    upgrader = ShapeUpgrade_UnifySameDomain(result, True, True, True)
    upgrader.AllowInternalEdges(False)
    try:
        upgrader.Build()
        result = upgrader.Shape()
    except Exception:
        pass

    return result


def _tessellate_shape(
    shape, lin_deflection: float = 0.001, ang_deflection: float = 0.5,
    is_relative: bool = True
) -> tuple[np.ndarray, np.ndarray]:
    """Triangulate a raw TopoDS_Shape into vertex/face arrays.

    Same algorithm as utils.model_utils.convert_model_to_mesh (including
    its GC-disable step, kept here even though this codebase's own
    heap-corruption theory for that step turned out to be wrong -- see
    that function's own comment for the full story; disabling GC around
    a big triangulation extraction is still cheap insurance either way).
    Duplicated rather than called directly because that function expects
    a build123d/OCP wrapper object exposing ``.wrapped``/``.faces()``,
    not a raw TopoDS_Shape -- this module has no build123d dependency to
    produce one.
    """
    import gc

    gc_was_enabled = gc.isenabled()
    gc.disable()

    try:
        loc = TopLoc_Location()
        BRepMesh_IncrementalMesh(
            theShape=shape, theLinDeflection=lin_deflection,
            isRelative=is_relative, theAngDeflection=ang_deflection,
            isInParallel=False)

        vertices = []
        faces = []
        offset = 0

        exp = TopExp_Explorer(shape, TopAbs_FACE)
        while exp.More():
            facet = TopoDS.Face_s(exp.Current())
            exp.Next()

            poly_triangulation = BRep_Tool.Triangulation_s(facet, loc)  # NOQA
            if not poly_triangulation:
                continue

            trsf = loc.Transformation()

            node_count = poly_triangulation.NbNodes()
            for i in range(1, node_count + 1):
                gp_pnt = poly_triangulation.Node(i).Transformed(trsf)
                vertices.append((gp_pnt.X(), gp_pnt.Y(), gp_pnt.Z()))

            facet_reversed = facet.Orientation() == TopAbs_REVERSED
            order = [1, 3, 2] if facet_reversed else [1, 2, 3]

            for tri in poly_triangulation.Triangles():
                idx0 = tri.Value(order[0]) + offset - 1
                idx1 = tri.Value(order[1]) + offset - 1
                idx2 = tri.Value(order[2]) + offset - 1
                faces.append([idx0, idx1, idx2])

            offset += node_count

        vertices = np.array(vertices, dtype=np.float32)
        faces = np.array(faces, dtype=np.int32)
    finally:
        if gc_was_enabled:
            gc.enable()

    return vertices, faces


@_ocp_thread
def build_text_mesh(
    text: str, font_size: float, depth: float, font: str = 'Arial',
    font_style: FontStyle = FontStyle.REGULAR,
    text_align: tuple[TextAlign, TextAlign] = (TextAlign.LEFT, TextAlign.BOTTOM),
    lin_deflection: float = 0.001, ang_deflection: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    """Build extruded text and tessellate it in one call.

    Replacement for the build123d.Text(...) + build123d.extrude(...) +
    utils.convert_model_to_mesh(...) sequence used today by
    shapes/text.py's _tessellate_char() and
    ui/dialogs/part_orientation.py's AxisLabel3D -- both call sites pass
    a single font/depth combination per call and never use build123d's
    ``align`` (bounding-box alignment) or ``path`` (text-on-a-curve)
    parameters, so neither is implemented here; add them if a future
    caller actually needs them.

    :param text: Text to render -- a single character or a short string.
    :param font_size: Font size in model units.
    :param depth: Extrusion depth along +Z.
    :param font: System font family name.
    :param font_style: One of :class:`FontStyle`.
    :param text_align: ``(horizontal, vertical)`` alignment.
    :param lin_deflection: Chordal tessellation tolerance (relative to
        the shape's own bounding box).
    :param ang_deflection: Angular tessellation tolerance, in radians.
    :returns: ``(vertices, faces)`` numpy arrays, same shape/dtype as
        utils.model_utils.convert_model_to_mesh's return value.
    """
    horiz_align = _HORIZ_ALIGN[text_align[0]]
    vert_align = _VERT_ALIGN[text_align[1]]

    font_i = _get_font(font, font_style, font_size)
    builder = StdPrs_BRepTextBuilder()
    text_flat = builder.Perform(
        font_i, NCollection_Utf8String(text), gp_Ax3(), horiz_align, vert_align)

    solid = _extrude_and_fuse(text_flat, depth)
    if solid is None:
        return np.zeros((0, 3), dtype=np.float32), np.zeros((0, 3), dtype=np.int32)

    return _tessellate_shape(solid, lin_deflection, ang_deflection)
