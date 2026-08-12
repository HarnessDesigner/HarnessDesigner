# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""A positionable/rotatable string of cached character glyphs (see
shapes/glyph.py) for the routing/collision benchmark harness.

Move/rotate it the same way the rest of this codebase moves/rotates a
Point/Angle -- ``text += position_delta`` translates (Point.__iadd__),
``text @= angle_delta`` rotates (Angle composition) -- rather than a
set_position()/set_angle() method pair. Every character's own world
position is recomputed eagerly, once, whenever either dunder mutates
this text's position/angle -- not on every render() call -- since a
Text is expected to move rarely (or never) relative to how often it's
drawn.
"""

import build123d
import numpy as np
from OpenGL import GL
from PySide6 import QtWidgets
import fontTools.ttLib
import OCP.Font
import OCP.TCollection

from .. import utils as _utils
from ..geometry import angle as _angle
from ..geometry import point as _point
from ..gl import vbo as _vbo_handler


# Neither of these comes from a font metric this harness has access to
# (build123d doesn't expose per-character advance width or kerning
# pairs through its public API) -- both are a flat approximation
# calibrated by comparing a handful of whole strings' own build123d-
# measured width against the sum of their individual characters' widths
# (typically landed in the 0.07-0.13 range per gap; a bare space glyph
# measures 0 width, since there's no ink to bound). Good enough for a
# legible schematic label, not typographically exact -- retune directly
# if particular letter pairs look visibly off once rendered.
INTER_CHAR_GAP = 0.09
SPACE_ADVANCE = 0.3

# char -> [None, entry_for_REGULAR(1), entry_for_BOLD(2),
#          entry_for_ITALIC(3), entry_for_BOLDITALIC(4)] -- indexed
# directly by FontStyle.value (1-4; index 0 is never used) so a caller
# never needs to translate the enum to a 0-based slot. Each populated
# entry is ``(vbo | None, Point(width, height, depth))`` -- vbo is None
# for a space (nothing to draw, just an advance). Point (not a plain
# tuple) so objects/text.py's Text can use its own dunder arithmetic
# directly against a glyph's own measured size.
_CHARS: dict[str, list] = {}

# --- Real, kerning-aware character advances -- read directly from the
# same font FILE build123d/OCCT itself resolves "Arial"+style to (see
# _font_metrics's own docstring), via fontTools -- a mature, pure-Python
# library built specifically for reading font tables, not the flat
# INTER_CHAR_GAP/SPACE_ADVANCE approximation above (still used as a
# fallback for a space, which has no glyph/no hmtx entry to read an
# advance from either way).
#
# An earlier attempt used OCP.Font.Font_FTFont.AdvanceX() (OCCT's own
# FreeType wrapper) directly -- fast, but its results didn't hold up:
# 'l' and 'i' are the same width in real Arial (confirmed independently
# via fontTools' own hmtx table below, both 0.2222), but AdvanceX gave
# 'l' the same *wide* value as 'e'/'n'/'a' (0.5562) while correctly
# giving 'i' the narrow one -- an internal inconsistency, not just
# imprecision, that pointed at a binding issue rather than a real font-
# metric result. fontTools' hmtx/kern values were checked against known
# real Arial metrics directly and are unambiguously correct.

_FontMetrics = tuple  # (advance: dict[str, float], kern: dict[tuple[str, str], float])
_FONT_METRICS: dict = {}


def _font_metrics(style: int):
    """
    Return (building it first if needed) *style*'s own
    ``(advance, kern)`` pair -- ``advance[char]`` is that character's
    unkerned advance width, ``kern[(char, next_char)]`` a kerning
    delta (added to ``advance[char]``) present only for the -- sparse,
    909 pairs for the whole font -- pairs the font actually defines a
    correction for. Both normalized to the font_size=1.0 baseline
    (divided by the font's own ``unitsPerEm``).

    Loaded from the exact same font file build123d/OCCT's own
    ``Font_FontMgr`` resolves that style to (build123d resolves "Arial"
    to ``C:\\WINDOWS\\Fonts\\arial.ttf``/``arialbd.ttf``/etc -- reading
    that same path here, rather than a font found by some other lookup,
    is what keeps this in sync with whatever build123d actually
    rendered).
    """

    aspect_by_value = {
        build123d.FontStyle.REGULAR.value: OCP.Font.Font_FontAspect.Font_FA_Regular,
        build123d.FontStyle.BOLD.value: OCP.Font.Font_FontAspect.Font_FA_Bold,
        build123d.FontStyle.ITALIC.value: OCP.Font.Font_FontAspect.Font_FA_Italic,
        build123d.FontStyle.BOLDITALIC.value: OCP.Font.Font_FontAspect.Font_FA_BoldItalic,
    }

    aspect = aspect_by_value[style]

    system_font = OCP.Font.Font_FontMgr.GetInstance_s().FindFont(  # NOQA
        OCP.TCollection.TCollection_AsciiString('Arial'), aspect)

    path = system_font.FontPath(aspect).ToCString()

    font = fontTools.ttLib.TTFont(path)
    units_per_em = float(font['head'].unitsPerEm)  # NOQA
    hmtx = font['hmtx']
    cmap = font.getBestCmap()

    def _glyph_name(char_: str) -> str | None:
        return cmap.get(ord(char_))

    advance_widths: dict[str, float] = {}

    chars = (
        ' '
        'abcdefghijklmnopqrstuvwxyz'
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        '0123456789'
        '.,;:!?()[]{}\'"-_=+/\\*&^%$#@~`|<>'
    )

    for char in chars:
        if char == ' ':
            continue

        gname = _glyph_name(char)
        if gname is not None:
            advance_widths[char] = hmtx[gname][0] / units_per_em

    kern: dict[tuple[str, str], float] = {}
    if 'kern' in font:
        name_to_char = {_glyph_name(c): c for c in chars if c != ' '}

        for table in font['kern'].kernTables:
            for (g1, g2), value in table.kernTable.items():
                c1 = name_to_char.get(g1)
                c2 = name_to_char.get(g2)

                if c1 is not None and c2 is not None:
                    kern[(c1, c2)] = value / units_per_em

    result = (advance_widths, kern)
    _FONT_METRICS[style] = result


def _build_char(char: str, depth: float, style: build123d.FontStyle):
    if char == ' ':
        return None, _point.Point(SPACE_ADVANCE, 0.0, depth), 0.0

    model = build123d.Text(
        char, font_size=1.0, font_style=style,
        text_align=[build123d.TextAlign.LEFT, build123d.TextAlign.BOTTOM])

    model = build123d.extrude(model, depth)

    # character-width X stays X, character-height Y -> world Z,
    # extrusion Z -> world Y.
    model = model.rotate(build123d.Axis.X, 90.0)

    vertices, faces = _utils.convert_model_to_mesh(
        model, lin_deflection=0.01, ang_deflection=0.5)

    # Only Y (depth, the extrusion axis) is centered on the mesh's own
    # true vertex centroid, so it sits symmetric about world Y=0 the
    # same as every other piece of the housing. X (character width) and
    # Z (character height) are both deliberately left untouched, at
    # build123d's own LEFT/BOTTOM-alignment reference -- real font-
    # metric references (left side-bearing, baseline), not a bounding
    # box or a vertex centroid. Both of the latter are shape-dependent,
    # so they land somewhere different for every character (measured:
    # the Z mismatch alone ran 0 to ~40% of a glyph's own height) --
    # exactly why characters centered that way, then placed at a shared
    # string-local X/Z, read with their left edges and their bottoms
    # both out of line with each other. A font's own LEFT/BOTTOM
    # reference is the one X/Z pair every character in it actually
    # shares, and leaving it alone also preserves the characters that
    # are *supposed* to sit differently -- a comma hanging below the
    # baseline, an italic lead-in -- which any uniform "align every
    # edge" rule would break just as badly, the other direction.
    centroid = vertices.mean(axis=0)
    centroid[0] = 0.0
    centroid[2] = 0.0
    vertices = vertices - centroid

    # Measured from the actual tessellated mesh's own extent (post-
    # centering), not a separate build123d bounding_box() query -- this
    # *is* the geometry that gets rendered (at the coarsened deflection
    # settings above), so its own vertex bounds are the true size, not
    # an analytic approximation of it.
    min_z = float(vertices[:, 2].min())
    max_z = float(vertices[:, 2].max())
    width = float(vertices[:, 0].max() - vertices[:, 0].min())
    height = max_z - min_z

    # This glyph's own true vertical center, as an offset from the
    # baseline (Z=0 -- see the centering comment above) -- distinct
    # from `height`, which is just the total span and says nothing
    # about how much of it sits above vs. below the baseline. Needed
    # for pieces that visually "come out of the middle of" a glyph
    # (objects/housing.py's wire-stub cylinder, attached to the "("
    # bracket) rather than sitting on its baseline like normal text.
    center_z = (min_z + max_z) / 2.0

    packed, count = _utils.compute_normals(vertices, faces)

    unpacked_verts = packed[:count * 3].reshape(-1, 3)
    aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
    aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
    obb = _utils.compute_obb(aabb1, aabb2)
    vbo = _vbo_handler.NonPooledVBOHandler(packed, count, aabb=aabb, obb=obb)

    return vbo, _point.Point(width, height, depth), center_z


def build_chars(mainframe) -> None:
    """Eagerly build+cache every character in *chars* (the full keyboard
    set by default), in every FontStyle, at *depth* -- so every later
    :func:`get` call (via objects/text.py's Text) hits an already-
    uploaded VBO instead of triggering a fresh build123d/OCCT call.
    Call once, with a current GL context held open, before constructing
    any Text (see run_me.py). Safe to call again later with a different
    *depth* or *chars* -- only fills in entries that aren't already
    cached.

    Yields to the Qt event loop (``QApplication.processEvents()``)
    after each character -- ~95 characters * 4 styles takes several
    seconds of solid OCCT/build123d work (see the module docstring's
    profiling numbers); without yielding, that whole stretch runs
    between two Qt event-loop iterations, so the window can't repaint
    or respond to input and the OS reports it as not responding for the
    duration. One call per *character*, not per (character, style) --
    frequent enough to keep the window responsive without adding
    meaningful overhead against work already measured in milliseconds
    per glyph.
    """

    chars = (
        ' '
        'abcdefghijklmnopqrstuvwxyz'
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        '0123456789'
        '.,;:!?()[]{}\'"-_=+/\\*&^%$#@~`|<>'
    )

    for style in (
        build123d.FontStyle.REGULAR.value,
        build123d.FontStyle.BOLD.value,
        build123d.FontStyle.ITALIC.value,
        build123d.FontStyle.BOLDITALIC.value
    ):
        _font_metrics(style)

    for char in chars:
        entry = _CHARS.setdefault(char, [None, None, None, None, None])
        QtWidgets.QApplication.processEvents()

        with mainframe.editor3d.context:
            for style in (
                build123d.FontStyle.REGULAR,
                build123d.FontStyle.BOLD,
                build123d.FontStyle.ITALIC,
                build123d.FontStyle.BOLDITALIC
            ):
                entry[style.value] = _build_char(char, 1.0, style)


class Text:
    """*text* is composed from shapes/glyph.py's cached per-character
    glyphs at *style* (must already be built -- see
    shapes/glyph.py's build_chars()), scaled to *size*. Starts at
    position ``(0, 0, 0)``/identity angle -- use ``+=``/``@=`` to place
    it (see the module docstring).
    """

    _font_metrics_cache: dict[int, _FontMetrics] = {}

    def __init__(self, text: str, size: float,
                 style: build123d.FontStyle | int):

        if not isinstance(style, int):
            style = style.value

        self._size = size
        self._style = style

        self._position = _point.Point(0.0, 0.0, 0.0)
        self._angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)

        # Per character: its own shared glyph VBO, and its own LOCAL
        # (unrotated, font_size=1.0 basis) offset -- x is the cursor
        # position directly (no half-width shift), z always 0. Neither
        # needs an offset because each cached glyph's own X/Z is left at
        # build123d's own LEFT/BOTTOM-alignment reference (a real font-
        # metric left side-bearing/baseline, shared by every character
        # in the font) rather than centered on that glyph's own
        # bounding box or centroid -- see shapes/glyph.py's own
        # docstring for why a per-glyph center is exactly what made
        # characters read with mismatched left edges/bottoms once placed
        # at a shared string-local X/Z. A glyph's own local x=0 already
        # *is* its left edge, so the string's own left-to-right cursor
        # can be used as each glyph's local_x as-is.
        self._vbos = []
        self._locals = []

        # Recomputed by _recompute() whenever position/angle changes --
        # each entry a world-space Point, same order as self._vbos.
        self._world = []

        # The cursor advances by shapes/glyph.py's own real, kerning-
        # aware advance() (read from the font file itself) rather than
        # this glyph's own tessellated-mesh width -- the two aren't the
        # same thing (a real advance includes side-bearing on both
        # sides of the ink, not just the ink itself), and advance() is
        # what actually reproduces correct inter-character spacing/
        # kerning, not just glyph-to-glyph non-overlap.
        cursor = 0.0
        height = 0.0
        last = len(text) - 1

        for i, char in enumerate(text):
            vbo, dims = self._get(char)

            if vbo is not None:
                self._vbos.append(vbo)
                self._locals.append(_point.Point(cursor, 0.0, 0.0))
                height = max(height, dims.y)

            next_char = text[i + 1] if i != last else ''
            cursor += self._advance(char, next_char)

        self.width = cursor * size
        self.height = height * size

        self._recompute()

    def _advance(self, char: str, next_char: str) -> float:
        if char == ' ':
            return SPACE_ADVANCE

        advance_widths, kern = _FONT_METRICS[self._style]
        base = advance_widths.get(char, SPACE_ADVANCE)

        return base + kern.get((char, next_char), 0.0)

    def _entry(self, char: str):
        entry = _CHARS.get(char)

        if entry is None or entry[self._style] is None:
            raise KeyError(
                f'glyph for {char!r} (style {self._style}) not built -- call build_chars() first'
                )

        return entry[self._style]

    def center_z(self, char: str) -> float:
        """Return *char*'s own true vertical center, as an offset from the
        baseline (font_size=1.0 basis) -- distinct from ``get()``'s own
        ``dimensions.y`` (just the total height span, silent on how much of
        it sits above vs. below the baseline). For a piece that needs to
        visually "come out of the middle of" a glyph rather than sit on its
        baseline like normal text -- currently just the "(" bracket's own
        wire-stub cylinder attachment point (see objects/housing.py).
        """
        _vbo, _dims, cz = self._entry(char)
        return cz

    def _get(self, char: str) -> tuple[_vbo_handler.NonPooledVBOHandler, _point.Point]:
        vbo, dims, _center_z = self._entry(char)
        return vbo, dims

    def _recompute(self) -> None:
        """Rebuild every character's own cached world position from
        this text's current position/angle.

        X is negated (and the whole offset scaled to *size*) before
        rotating -- matches objects/housing.py's Housing._world_offset
        exactly, same reason: the locked camera's gluLookAt basis
        (forward ``(0,-1,0)``, up ``(0,0,1)`` -- see gl/camera.py) has
        ``cross(forward, up) == (-1, 0, 0)``, i.e. world +X renders to
        screen -X, so a plain, un-negated local offset would place
        (and, combined with render()'s own glyph-mirror scale, read)
        every character on the wrong side/backwards.
        """
        world = []

        for local in self._locals:
            scaled = _point.Point(-local.x * self._size, local.y, local.z * self._size)
            rotated = scaled @ self._angle
            world.append(self._position + rotated)

        self._world = world

    def __iadd__(self, delta) -> "Text":
        self._position += delta
        self._recompute()
        return self

    def __imatmul__(self, angle_delta: "_angle.Angle") -> "Text":
        self._angle = self._angle + angle_delta
        self._recompute()
        return self

    def set_transform(self, position: "_point.Point", angle: "_angle.Angle") -> None:
        """Set this text's own position/angle directly to *position*/
        *angle* (not composed with the current values, unlike ``+=``/
        ``@=``) -- for a parent (objects/housing.py's Housing) that owns
        this text's placement relative to its own moving/rotating frame
        and needs to push a freshly-recomputed absolute transform each
        time it moves, rather than accumulate a delta on top of
        whatever this text's own position/angle already were.
        """
        self._position = position
        self._angle = angle
        self._recompute()

    def render(self, program, pos_loc, rot_loc, scale_loc, normal_loc) -> None:  # NOQA
        """Draw every character in this string as its own shared glyph
        VBO. X is negated on the *scale* uniform per character -- see
        :meth:`_recompute`'s own docstring for why that's needed for
        legibility and never affects position.
        """
        GL.glUniform1i(normal_loc, 0)
        GL.glUniform4f(rot_loc, *self._angle.as_quat_float)
        GL.glUniform3f(scale_loc, -self._size, 1.0, self._size)

        for vbo, world_pos in zip(self._vbos, self._world):
            GL.glUniform3f(pos_loc, *world_pos.as_float)
            vbo.render()
