# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""A string of cached character glyphs (see shapes/glyph.py), rendered
as one draw call per glyph.

A ``Text`` owns no position/angle/scale of its own -- unlike a real
mesh VBO's *data*, a glyph layout never moves on its own account, only
because whatever object owns it (as its own ``_vbo``, see the
VBOHandlerBase-compatible interface below) moved. So a ``Text`` is
handed its owner's current position/angle/scale fresh on every single
``render()`` call (see that method's own docstring) -- there is
nothing to keep in sync between moves the way an explicit
``set_transform()`` call used to require.
"""

from typing import Callable, TYPE_CHECKING, Union as _Union

import os
import time

import build123d
import numpy as np
from PySide6 import QtWidgets
import fontTools.ttLib
import OCP.Font
import OCP.TCollection

from .. import utils as _utils
from ..geometry import angle as _angle
from ..geometry import point as _point
from ..gl import vbo as _vbo_handler

if TYPE_CHECKING:
    from ..gl.shaders import program as _shader_program


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

# Extra line spacing on top of a line's own raw glyph height (font_size=1.0
# basis, applied to CHARACTER_HEIGHT below) -- same hand-tuned multiple
# objects_schematic/housing.py's corner label used to stack its own
# separate Text-per-line instances before Text supported '\n' natively;
# centralized here now that it does, so every multi-line Text (not just
# that one hand-rolled case) uses the same line-height convention.
_LINE_HEIGHT_SCALE = 1.2

# char -> [None, entry_for_REGULAR(1), entry_for_BOLD(2),
#          entry_for_ITALIC(3), entry_for_BOLDITALIC(4)] -- indexed
# directly by FontStyle.value (1-4; index 0 is never used) so a caller
# never needs to translate the enum to a 0-based slot. Each populated
# entry is ``(vbo | None, Point(width, height, depth))`` -- vbo is None
# for a space (nothing to draw, just an advance). Point (not a plain
# tuple) so objects/text.py's Text can use its own dunder arithmetic
# directly against a glyph's own measured size.
_CHARS: dict[str, list] = {}

# Tallest glyph height across every character/style built by build_chars()
# (font_size=1.0 basis, same dims.y _build_char() measures per-character
# below) -- the one real character-height ratio this module can offer, for
# callers (objects_schematic/housing.py's Housing) that need to compute a
# text-driven layout size (e.g. cavity slot height) before any actual Text
# string exists to measure. Set once, during build_chars()'s preload pass.
CHARACTER_HEIGHT: float = 0.0

# Shared ``local_tilt`` (see Text.__init__) for every Text rendered in the
# schematic or peg-board view. Both views' locked cameras use world Z as
# screen-vertical (see gl/shaders/schematic2d.py's own top-down projection
# comment), while a Text's own raw glyph mesh has its height on Y, matching
# build123d's native sketch axes and this application's own 3D view (world
# X=right, Y=up, Z=forward -- see gl/canvas_base/camera_base.py's
# _WORLD_UP) -- see _tessellate_char's own docstring for why the glyph mesh
# itself is never rotated to compensate. Every schematic/peg-board-view
# Text needs this passed at construction (not the 3D view, whose own
# world-up already matches the glyph's native Y-height with no tilt).
TOP_DOWN_TILT = _angle.Angle.from_euler(-90.0, 0.0, 0.0)

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
        ' \n'
        'abcdefghijklmnopqrstuvwxyz'
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        '0123456789'
        '.,;:!?()[]{}\'"-_=+/\\*&^%$#@~`|<>'
    )

    for char in chars:
        if char in (' ', '\n'):
            continue

        gname = _glyph_name(char)
        if gname is not None:
            advance_widths[char] = hmtx[gname][0] / units_per_em

    kern: dict[tuple[str, str], float] = {}
    if 'kern' in font:
        name_to_char = {_glyph_name(c): c for c in chars if c not in (' ', '\n')}

        for table in font['kern'].kernTables:
            for (g1, g2), value in table.kernTable.items():
                c1 = name_to_char.get(g1)
                c2 = name_to_char.get(g2)

                if c1 is not None and c2 is not None:
                    kern[(c1, c2)] = value / units_per_em

    result = (advance_widths, kern)
    _FONT_METRICS[style] = result


# Bump whenever _tessellate_char's tessellation parameters (deflection
# settings, alignment/centering rule) or the cache file's own layout
# change -- a mismatch means the cache on disk was written by different
# logic than what's running now, so it's discarded and rebuilt rather
# than trusted.
_GLYPH_CACHE_VERSION = 2


def _glyph_cache_path() -> str:
    return os.path.join(_utils.get_appdata(), 'glyph_cache.npz')


def _load_glyph_cache() -> dict | None:
    """Return every previously-tessellated glyph cached on disk by an
    earlier run, as ``{(char, style_value): (packed, count, aabb, obb,
    width, height, center_y)}`` -- or ``None`` if there's no cache file
    yet, it's unreadable, or it was written by an incompatible version
    (see _GLYPH_CACHE_VERSION). A ``None`` return means every glyph
    needs full build123d/OCCT tessellation this run, same as before this
    cache existed at all.
    """
    path = _glyph_cache_path()
    if not os.path.exists(path):
        return None

    try:
        with np.load(path) as data:
            if int(data['version'][0]) != _GLYPH_CACHE_VERSION:
                return None

            result = {}
            for char_code, style in data['keys']:
                char_code = int(char_code)
                style = int(style)
                prefix = f'{style}_{char_code}_'
                meta = data[prefix + 'meta']

                result[(chr(char_code), style)] = (
                    data[prefix + 'packed'], int(meta[0]),
                    data[prefix + 'aabb'], data[prefix + 'obb'],
                    float(meta[1]), float(meta[2]), float(meta[3]))

            return result
    except Exception:  # NOQA -- any read/format problem just means rebuild
        return None


def _save_glyph_cache(entries: dict) -> None:
    """Write every ``(char, style_value): (packed, count, aabb, obb,
    width, height, center_y)`` entry in *entries* to disk as a single
    ``.npz`` archive, so the next app launch can skip build123d/OCCT
    entirely for every glyph gathered this run (see _load_glyph_cache).
    Written to a temp file and moved into place with ``os.replace`` so a
    run interrupted mid-save never leaves a corrupt/partial cache file
    behind for the next launch to trip over.
    """
    if not entries:
        return

    arrays = {'version': np.array([_GLYPH_CACHE_VERSION], dtype=np.int64)}
    keys = []

    for (char, style), (packed, count, aabb, obb, width, height, center_y) in entries.items():
        char_code = ord(char)
        keys.append((char_code, style))
        prefix = f'{style}_{char_code}_'

        arrays[prefix + 'packed'] = packed
        arrays[prefix + 'aabb'] = aabb
        arrays[prefix + 'obb'] = obb
        arrays[prefix + 'meta'] = np.array(
            [count, width, height, center_y], dtype=np.float64)

    arrays['keys'] = np.array(keys, dtype=np.int64)

    path = _glyph_cache_path()
    tmp_path = path + '.tmp'

    # np.savez appends '.npz' to a path with no extension -- pass the
    # already-'.npz'-suffixed tmp path as a file object instead so the
    # actual written filename matches tmp_path exactly for the
    # os.replace below.
    with open(tmp_path, 'wb') as f:
        np.savez(f, **arrays)

    os.replace(tmp_path, path)


def _tessellate_char(char: str, depth: float, style: build123d.FontStyle):
    """Build *char*'s mesh via build123d/OCCT and tessellate it -- the
    slow, OCCT-bound half of building one glyph, split out from
    _build_char() so a disk-cached result (see _load_glyph_cache) can
    skip straight to VBO creation without ever reaching this. Does not
    handle ``' '`` (no geometry to tessellate at all) -- callers check
    for that themselves.

    Returns ``(packed, count, aabb, obb, width, height, center_y)``.
    """
    model = build123d.Text(
        char, font_size=1.0, font_style=style,
        text_align=[build123d.TextAlign.LEFT, build123d.TextAlign.BOTTOM])

    model = build123d.extrude(model, depth)

    # build123d's own native sketch axes are left untouched here --
    # character-width X stays X, character-height stays Y, extrusion
    # stays Z. That already matches this application's own 3D view
    # (world X=right, Y=up, Z=forward -- see gl/canvas_base/camera_base.py's
    # _WORLD_UP), so a Text needs no rotation of its own glyph meshes to
    # stand upright there. A view whose own screen-vertical is a
    # different world axis (schematic/pegboard, whose locked cameras
    # use world Z as screen-vertical -- see gl/shaders/schematic2d.py's
    # own top-down projection comment) compensates for that itself, via
    # Text's own ``local_tilt`` (see Text.__init__) -- not by rotating
    # the glyph mesh in build123d, which would then be wrong for the 3D
    # view instead.
    vertices, faces = _utils.convert_model_to_mesh(
        model, lin_deflection=0.01, ang_deflection=0.5)

    # Only Z (depth, the extrusion axis) is centered on the mesh's own
    # true vertex centroid, so it sits symmetric about local Z=0 the
    # same as every other piece of the housing. X (character width) and
    # Y (character height) are both deliberately left untouched, at
    # build123d's own LEFT/BOTTOM-alignment reference -- real font-
    # metric references (left side-bearing, baseline), not a bounding
    # box or a vertex centroid. Both of the latter are shape-dependent,
    # so they land somewhere different for every character (measured:
    # the Y mismatch alone ran 0 to ~40% of a glyph's own height) --
    # exactly why characters centered that way, then placed at a shared
    # string-local X/Y, read with their left edges and their bottoms
    # both out of line with each other. A font's own LEFT/BOTTOM
    # reference is the one X/Y pair every character in it actually
    # shares, and leaving it alone also preserves the characters that
    # are *supposed* to sit differently -- a comma hanging below the
    # baseline, an italic lead-in -- which any uniform "align every
    # edge" rule would break just as badly, the other direction.
    centroid = vertices.mean(axis=0)
    centroid[0] = 0.0
    centroid[1] = 0.0
    vertices = vertices - centroid

    # Measured from the actual tessellated mesh's own extent (post-
    # centering), not a separate build123d bounding_box() query -- this
    # *is* the geometry that gets rendered (at the coarsened deflection
    # settings above), so its own vertex bounds are the true size, not
    # an analytic approximation of it.
    min_y = float(vertices[:, 1].min())
    max_y = float(vertices[:, 1].max())
    width = float(vertices[:, 0].max() - vertices[:, 0].min())
    height = max_y - min_y

    # This glyph's own true vertical center, as an offset from the
    # baseline (Y=0 -- see the centering comment above) -- distinct
    # from `height`, which is just the total span and says nothing
    # about how much of it sits above vs. below the baseline. Currently
    # unused (see Text.center_y's own docstring).
    center_y = (min_y + max_y) / 2.0

    packed, count = _utils.compute_normals(vertices, faces)

    unpacked_verts = packed[:count * 3].reshape(-1, 3)
    aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
    aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
    obb = _utils.compute_obb(aabb1, aabb2)

    return packed, count, aabb, obb, width, height, center_y


def _build_char(char: str, depth: float, style: build123d.FontStyle,
                tessellated: tuple | None = None):
    """Return this character's ``(vbo, dims, center_y)`` glyph entry.

    *tessellated* -- if given (a disk-cache hit, or already computed by
    the caller this run) -- is used as-is instead of calling
    :func:`_tessellate_char`, skipping the slow build123d/OCCT work
    entirely; VBO creation (needs a live GL context, unlike tessellation
    itself) always still happens here.
    """
    if char == ' ':
        return None, _point.Point(SPACE_ADVANCE, 0.0, depth), 0.0

    if char == '\n':
        # No ink, no horizontal advance of its own -- Text.__init__
        # special-cases '\n' for the actual line-break layout (reset
        # cursor, move to the next line) before it ever reaches here, so
        # this entry only exists for callers that look a glyph up
        # generically (_entry/_get/center_y) rather than through that
        # per-character layout loop.
        return None, _point.Point(0.0, 0.0, depth), 0.0

    if tessellated is None:
        tessellated = _tessellate_char(char, depth, style)

    packed, count, aabb, obb, width, height, center_y = tessellated
    vbo = _vbo_handler.NonPooledVBOHandler(packed, count, aabb=aabb, obb=obb)

    return vbo, _point.Point(width, height, depth), center_y


def build_chars(mainframe, on_progress: Callable[[int, int], None] | None = None) -> None:
    """Eagerly build+cache every character in *chars* (the full keyboard
    set by default), in every FontStyle, at *depth* -- so every later
    :func:`get` call (via objects/text.py's Text) hits an already-
    uploaded VBO instead of triggering a fresh build123d/OCCT call.
    Call once, with a current GL context held open, before constructing
    any Text (see run_me.py). Safe to call again later with a different
    *depth* or *chars* -- only fills in entries that aren't already
    cached.

    Each glyph's tessellated mesh (the actual slow part -- see
    _tessellate_char) is also cached to disk, across app launches, as a
    single ``.npz`` file (see _load_glyph_cache/_save_glyph_cache): the
    first run after a cache miss (first-ever launch, or
    _GLYPH_CACHE_VERSION bumped) still does the full build123d/OCCT
    tessellation for every glyph and writes the result to disk once at
    the end; every later launch loads that file instead and skips
    build123d/OCCT entirely (VBO upload still happens fresh every launch
    -- that needs a live GL context, and was never the slow part).
    Logs a one-line summary of where the time went (total, how much of
    that was spent in build123d/OCCT tessellation specifically, and
    whether the disk cache was used) through *mainframe*'s own logger.

    Yields to the Qt event loop (``QApplication.processEvents()``)
    after each character -- ~95 characters * 4 styles takes several
    seconds of solid OCCT/build123d work on a cache miss (see the module
    docstring's profiling numbers); without yielding, that whole stretch
    runs between two Qt event-loop iterations, so the window can't
    repaint or respond to input and the OS reports it as not responding
    for the duration. One call per *character*, not per (character,
    style) -- frequent enough to keep the window responsive without
    adding meaningful overhead against work already measured in
    milliseconds per glyph.

    :param on_progress: If given, called as ``on_progress(done, total)``
        -- once with ``done=0`` before any glyph is built (so a caller
        can initialize a progress bar against the real total), then once
        more after each individual (character, style) glyph finishes.
    :type on_progress: Callable[[int, int], None] | None
    """

    chars = (
        ' \n'
        'abcdefghijklmnopqrstuvwxyz'
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        '0123456789'
        '.,;:!?()[]{}\'"-_=+/\\*&^%$#@~`|<>'
    )

    styles = (
        build123d.FontStyle.REGULAR,
        build123d.FontStyle.BOLD,
        build123d.FontStyle.ITALIC,
        build123d.FontStyle.BOLDITALIC
    )

    for style in styles:
        _font_metrics(style.value)

    global CHARACTER_HEIGHT

    total = len(chars) * len(styles)
    done = 0

    if on_progress is not None:
        on_progress(done, total)

    cache = _load_glyph_cache()
    to_save = {} if cache is None else None

    tessellate_time = 0.0
    build_start = time.perf_counter()

    for char in chars:
        entry = _CHARS.setdefault(char, [None, None, None, None, None])
        QtWidgets.QApplication.processEvents()

        with mainframe.editor3d.context:
            for style in styles:
                tessellated = None

                if char not in (' ', '\n'):
                    if cache is not None:
                        tessellated = cache.get((char, style.value))

                    if tessellated is None:
                        t0 = time.perf_counter()
                        tessellated = _tessellate_char(char, 1.0, style)
                        tessellate_time += time.perf_counter() - t0

                        if to_save is not None:
                            to_save[(char, style.value)] = tessellated

                built = _build_char(char, 1.0, style, tessellated=tessellated)
                entry[style.value] = built

                _, dims, _center_y = built
                CHARACTER_HEIGHT = max(CHARACTER_HEIGHT, dims.y)

                done += 1
                if on_progress is not None:
                    on_progress(done, total)

    total_time = time.perf_counter() - build_start

    if to_save:
        _save_glyph_cache(to_save)

    if cache is not None:
        status = 'loaded from disk cache'
    elif to_save:
        status = 'no disk cache found -- tessellated fresh, wrote one for next launch'
    else:
        status = 'disk cache write skipped (nothing tessellated)'

    mainframe.logger.info(
        f'glyphs: {total_time:.3f}s total for {total} glyphs '
        f'({tessellate_time:.3f}s in build123d/OCCT tessellation) -- {status}')


class Text:
    """*text* is composed from shapes/glyph.py's cached per-character
    glyphs at *style* (must already be built -- see
    shapes/glyph.py's build_chars()), scaled to *size*.
    """

    _font_metrics_cache: dict[int, _FontMetrics] = {}

    def __init__(self, text: str, size: float,
                 style: build123d.FontStyle | int,
                 h_align: build123d.TextAlign | int = build123d.TextAlign.LEFT,
                 local_tilt: _angle.Angle | None = None,
                 center_anchor: bool = False):
        """
        :param h_align: How each line is positioned relative to the
            others when *text* has more than one line (a single-line
            Text always renders identically regardless of this -- there
            is only ever the one line, nothing for it to align
            *against*). ``LEFT`` (the default) leaves every line's own
            left edge flush against local x=0, matching this class's
            existing single-line behavior exactly. ``RIGHT``/``CENTER``
            shift each line individually so its own right edge/midpoint
            lines up with the widest line's. Purely a per-line
            *justification* concern -- see *center_anchor* below for
            the entirely separate question of where local (0, 0, 0)
            itself sits.
        :type h_align: :class:`build123d.TextAlign` | int
        :param local_tilt: A fixed rotation applied to this Text's own
            local geometry (both ``local_aabb``/``local_obb`` -- see
            :meth:`_compute_local_bounds` -- and every glyph's own
            render-time transform -- see :meth:`render`), composed
            with whatever angle this Text is actually rendered with
            each call, never stored anywhere else. For a caller whose
            own view needs a Text tilted a fixed amount relative to
            that caller's own stored/persisted angle (e.g. a top-down
            2D view -- see objects_schematic/objects_pegboard's own
            Note) without that fixed tilt becoming part of the
            persisted angle itself.
        :type local_tilt: :class:`~harness_designer.geometry.angle.Angle` | None
        :param center_anchor: ``False`` (default) leaves local
            ``(0, 0, 0)`` at this block's own bottom-left-of-widest-line
            baseline corner, matching this class's original single-line
            behavior (and what objects_schematic/cavity.py's Cavity/
            housing.py's Housing/terminal.py's Terminal each still
            expect -- they compute their own corner/edge-relative
            offset against that same reference). ``True`` shifts every
            glyph's own local position by half this block's own
            width/height instead, so local ``(0, 0, 0)`` -- and so
            whatever world position a caller renders/drags this Text
            at -- is the *center* of the whole block regardless of how
            many lines it has, matching the anchor a mouse actually
            expects to be dragging while placing/moving one (see
            objects_3d/objects_schematic/objects_pegboard's own
            Note). Entirely independent of *h_align* -- h_align only
            ever redistributes a *shorter* line relative to the widest
            one, never changes the widest line's own span, so it plays
            no part in where this overall center actually is either.
        :type center_anchor: bool
        """

        if not isinstance(style, int):
            style = style.value

        if not isinstance(h_align, int):
            h_align = h_align.value

        self._size = size
        self._style = style
        self._local_tilt = local_tilt

        # Per character: its own shared glyph VBO, and its own LOCAL
        # (unrotated, font_size=1.0 basis) offset -- x is this line's
        # own alignment offset (see line_x0 below) plus the cursor
        # position within it, y is 0 for the last line and steps up by
        # one line_height per line above it (y, not z -- a glyph's own
        # raw mesh has height on Y now, see _tessellate_char's own
        # docstring for why). Neither the per-character cursor nor a
        # glyph's own local x/y needs any further offset of its own,
        # because each cached glyph's own X/Y is left at build123d's
        # own LEFT/BOTTOM-alignment reference (a real font-metric left
        # side-bearing/baseline, shared by every character in the font)
        # rather than centered on that glyph's own bounding box or
        # centroid -- see shapes/glyph.py's own docstring for why a
        # per-glyph center is exactly what made characters read with
        # mismatched left edges/bottoms once placed at a shared
        # string-local X/Y. A glyph's own local x=0 already *is* its
        # left edge, so a line's own left-to-right cursor can be used
        # as each glyph's local_x as-is (LEFT alignment: line_x0 is
        # always 0, so this reduces to exactly that existing
        # single-line behavior).
        self._vbos = []
        self._locals = []

        # Per-glyph world position cache -- see render()'s own docstring
        # for why. ``None`` means "never rendered yet" (always a miss).
        self._cached_position: "_point.Point | None" = None
        self._cached_angle: "_angle.Angle | None" = None
        self._cached_scale: "_point.Point | None" = None
        self._cached_glyph_scale: "_point.Point | None" = None
        self._cached_world_positions: list = []

        lines = text.split('\n')
        line_count = len(lines)
        line_height = CHARACTER_HEIGHT * _LINE_HEIGHT_SCALE

        # First pass: every line's own width, via the exact same real,
        # kerning-aware advance() the second pass below lays characters
        # out with -- needed up front because RIGHT/CENTER alignment
        # shifts a line relative to the *widest* one, which isn't known
        # until every line has been measured.
        line_widths = []
        for line in lines:
            cursor = 0.0
            last = len(line) - 1

            for i, char in enumerate(line):
                next_char = line[i + 1] if i != last else ''
                cursor += self._advance(char, next_char)

            line_widths.append(cursor)

        max_line_width = max(line_widths, default=0.0)
        height = 0.0

        for line_idx, line in enumerate(lines):
            # Line 0 (the top) gets the largest Y offset, the last line
            # gets 0 -- same top-to-bottom stacking convention
            # objects_schematic/housing.py's own corner label used
            # (built as separate single-line Text instances, back when
            # this class had no '\n'/multi-line support of its own).
            line_y = (line_count - 1 - line_idx) * line_height

            if h_align == build123d.TextAlign.CENTER.value:
                line_x0 = (max_line_width - line_widths[line_idx]) / 2.0
            elif h_align == build123d.TextAlign.RIGHT.value:
                line_x0 = max_line_width - line_widths[line_idx]
            else:
                line_x0 = 0.0

            cursor = 0.0
            last = len(line) - 1

            for i, char in enumerate(line):
                vbo, dims = self._get(char)

                if vbo is not None:
                    self._vbos.append(vbo)
                    self._locals.append(_point.Point(line_x0 + cursor, line_y, 0.0))
                    height = max(height, dims.y)

                next_char = line[i + 1] if i != last else ''
                cursor += self._advance(char, next_char)

        # Total block height: from the last line's own baseline (Y=0)
        # up through every extra line stacked above it, plus the
        # tallest glyph's own span on top of that -- reduces to exactly
        # the single-line case (just `height`) when line_count == 1.
        total_height = (line_count - 1) * line_height + height

        self.width = max_line_width * size
        self.height = total_height * size

        if center_anchor:
            # Shift every glyph's own local position by half this
            # block's own (alignment-independent -- see __init__'s own
            # docstring) width/height, so local (0, 0, 0) becomes this
            # block's own center instead of its bottom-left-of-widest-
            # line baseline corner.
            half_width = max_line_width / 2.0
            half_height = total_height / 2.0

            self._locals = [
                _point.Point(local.x - half_width, local.y - half_height, local.z)
                for local in self._locals
            ]

        self._compute_local_bounds()

    def _compute_local_bounds(self) -> None:
        """Combine every placed glyph's own ``local_aabb`` (each glyph's
        cached VBO is a real VBO handler, so it already carries one --
        see gl/vbo.py's VBOHandlerBase) into this Text's own overall
        ``local_aabb``/``local_obb``, in this Text's own local
        (unrotated -- everything render() itself later rotates by
        whatever angle it's actually called with) frame, using the
        exact same Y-scale/no-Z-scale convention render() lays glyphs
        out with (see that method's own docstring for why).
        Computed once here rather than lazily -- this Text's own glyph
        layout never changes without a whole new Text being constructed
        (see e.g. objects_3d.note.Note._rebuild), so there is nothing
        that would ever make a cached result here stale.

        Deliberately has nothing to do with ``h_align`` -- alignment is
        purely a per-line *justification* concern (how a shorter line
        sits relative to the widest one; see __init__ above), not a
        change in the overall block's own size, so it plays no part in
        this bounding-box math either.

        If this Text has its own ``local_tilt`` (see __init__), both
        ``local_aabb``/``local_obb`` are pre-rotated by it here so they
        match what render() actually draws (render() composes the same
        tilt with whatever angle it's called with, every call).
        """
        if not self._vbos:
            self.local_aabb = np.zeros((2, 3), dtype=np.float32)
            self.local_obb = np.zeros((8, 3), dtype=np.float32)
            return

        mins = []
        maxs = []

        for vbo, local in zip(self._vbos, self._locals):
            glyph_min, glyph_max = vbo.local_aabb

            x0 = (local.x + glyph_min[0]) * self._size
            x1 = (local.x + glyph_max[0]) * self._size

            y0 = (local.y + glyph_min[1]) * self._size
            y1 = (local.y + glyph_max[1]) * self._size

            z0 = float(glyph_min[2])
            z1 = float(glyph_max[2])

            mins.append((min(x0, x1), min(y0, y1), min(z0, z1)))
            maxs.append((max(x0, x1), max(y0, y1), max(z0, z1)))

        local_min = np.array(mins, dtype=np.float32).min(axis=0)
        local_max = np.array(maxs, dtype=np.float32).max(axis=0)

        p1 = _point.Point(*[float(v) for v in local_min.tolist()])
        p2 = _point.Point(*[float(v) for v in local_max.tolist()])
        corners = _utils.compute_obb(p1, p2)

        if self._local_tilt is not None:
            corners @= self._local_tilt

        self.local_obb = corners
        self.local_aabb = _utils.adjust_aabb(corners)

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

    def center_y(self, char: str) -> float:
        """Return *char*'s own true vertical center, as an offset from the
        baseline (font_size=1.0 basis) -- distinct from ``get()``'s own
        ``dimensions.y`` (just the total height span, silent on how much of
        it sits above vs. below the baseline). Currently unused -- no
        caller needs a glyph's own mid-height offset yet.
        """
        _vbo, _dims, cy = self._entry(char)
        return cy

    def _get(self, char: str) -> tuple[_vbo_handler.NonPooledVBOHandler, _point.Point]:
        vbo, dims, _center_y = self._entry(char)
        return vbo, dims

    def render(self, program: _Union["_shader_program.FacesProgram", "_shader_program.EdgesProgram", "_shader_program.VerticesProgram"],
               position: "_point.Point", angle: "_angle.Angle", scale: "_point.Point",
               smooth: bool | None) -> None:
        """Draw every character in this string as its own shared glyph
        VBO, computing each glyph's own world position/rotation/scale
        fresh from *position*/*angle*/*scale* -- this Text's owner's
        own current transform, handed to every VBO's ``render()``
        identically (see gl/vbo.py's ``VBOHandlerBase.render``) -- and
        letting that glyph's own (real mesh) VBO set its own uniforms
        and draw itself. A Text never sets a GL uniform directly, or
        keeps any position/angle of its own between calls -- there is
        nothing to keep in sync, since every render() call is already
        given the truth fresh.

        *local_tilt* (see __init__), if given, is composed with *angle*
        here -- always, every call -- rather than baked into a stored
        angle anywhere, so it can never leak into whatever persisted
        angle the caller's own *angle* came from.

        ``smooth`` is passed straight through to every glyph, same as
        *program* -- purely forwarded to whichever VBO handler actually
        owns setting that uniform, same as every other parameter here.

        Every glyph's own world position is expensive to re-derive (a
        Point addition/rotation per glyph, times however many notes are
        in the scene, every single frame) for something that's actually
        constant almost every frame -- a note's own position/angle only
        changes while it's actively ebing dragged/rotated. So the result
        is cached (see __init__'s own ``_cached_*`` attributes) keyed on
        a value-equality snapshot of *position*/*angle*/*scale* (not
        identity -- *position* in particular is typically the same
        live, mutable ``Point`` object call after call, so an identity
        or reference check would never see it change); recomputed only
        the first call, or the first call after any of the three
        actually changes value.

        No axis is mirrored here -- every glyph's own local X/Y/Z maps
        straight into this Text's local frame (scaled by *size*/*scale*
        and rotated by *angle*, nothing more). A caller whose own view
        needs a different reading direction or orientation gets there
        entirely through *local_tilt* (a real rotation -- see __init__)
        composed with *angle*, never through a separate axis flip.
        """
        if self._local_tilt is not None:
            angle = self._local_tilt + angle

        if (
            self._cached_position is None or
            position != self._cached_position or
            angle != self._cached_angle or
            scale != self._cached_scale
        ):
            self._cached_position = position.copy()
            self._cached_angle = angle.copy()
            self._cached_scale = scale.copy()

            self._cached_glyph_scale = _point.Point(
                self._size * scale.x, self._size * scale.y, scale.z)

            world_positions = []
            for local in self._locals:
                local_pos = _point.Point(
                    local.x * self._size, local.y * self._size, local.z)
                world_positions.append(position + (local_pos @ angle))

            self._cached_world_positions = world_positions

        glyph_scale = self._cached_glyph_scale

        for vbo, world_pos in zip(self._vbos, self._cached_world_positions):
            vbo.render(program, world_pos, angle, glyph_scale, smooth)

    # ------------------------------------------------------------------
    # VBOHandlerBase-compatible interface -- lets a Text stand in
    # directly as a BaseVar._vbo (e.g. objects_3d/objects_schematic/
    # objects_pegboard's own Note) so the generic render()/
    # is_dirty-check/_compute_obb()/_compute_aabb() pipeline in
    # objects/objectsvar/base_var.py never needs a Text-specific
    # branch or override of its own -- ``local_aabb``/``local_obb`` are
    # real, computed once by :meth:`_compute_local_bounds` (called at
    # the end of __init__, see its own docstring), not placeholders.
    # ------------------------------------------------------------------

    @property
    def is_dirty(self) -> bool:
        return False

    @property
    def data(self):
        return np.zeros((0,), dtype=np.float32)

    @property
    def vertices(self):
        return np.zeros((0,), dtype=np.float32)

    @property
    def smooth_normals(self):
        return np.zeros((0,), dtype=np.float32)

    @property
    def face_normals(self):
        return np.zeros((0,), dtype=np.float32)

    @property
    def faces(self):
        return np.zeros((0, 3), dtype=np.int32)

    @property
    def vertex_count(self) -> int:
        return 0

    @staticmethod
    def get_aspect() -> tuple[float, float, float]:
        return 1.0, 1.0, 1.0

    @property
    def ctx(self):
        from PySide6.QtGui import QOpenGLContext

        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            raise RuntimeError('context has not been acquired')

        return ctx

    def acquire(self) -> None:
        """No-op -- each character's own cached glyph VBO (see
        build_chars()) manages its own GL acquisition lazily."""

    def release(self) -> None:
        """No-op -- a Text never owns a VBO of its own to release; its
        character glyphs are globally shared/cached (see build_chars()),
        and releasing them here would break every other Text instance
        using the same letters."""
