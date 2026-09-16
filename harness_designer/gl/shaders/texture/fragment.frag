// ASCII characters only -- this file is read with encoding='ascii' (see
// texture.py's own compile_program()); a non-ASCII byte here raises
// UnicodeDecodeError instead of compiling.
#version 330 core

in vec2 fragUV;
uniform sampler2D imageTexture;
// Pixel size of the quad this shader draws, and the per-corner radius
// (in the same units) to clip it to -- (top-left, top-right,
// bottom-right, bottom-left), each 0 disabling clipping on that one
// corner. All 4 zero draws a plain rectangle. See program.py's own
// TextureProgram.quad_size_px/corner_radius_px docstrings. pixelPos.y
// == 0 is the TOP of the quad (fragUV.y == 0 there -- see vertex.vert),
// matching this vec4's own ordering.
uniform vec2 quadSizePx;
uniform vec4 cornerRadiusPx;
// 0 (default) draws a normal filled rect. >0 additionally discards
// anything MORE than this many units inside the outer rect's boundary,
// leaving only a ring of this width -- used by the peg-board table's
// selection border (see objects_pegboard.pegboard_table.PegboardTable.
// _render_selection_border), drawn as a solid-color quad through this
// same program rather than a plain filled rect.
uniform float ringThicknessPx;
// Size (in the same units as quadSizePx) of a plain SQUARE notch
// discarded at the bottom-left and bottom-right corners only -- 0
// disables it. The peg-board table's own bottom corners are meant to
// be square (no cornerRadiusPx there), but the captured native chrome
// still leaves a faint, partially-transparent curved line right at
// those two corners once WA_TranslucentBackground made real alpha
// visible there (confirmed 2026-09-16, Kevin: "the bottom corners are
// rendered as square but they have a gray rounded line") -- a plain
// discard (not a rounded clip, which would just be a differently-
// shaped version of the same visible artifact) removes it outright.
uniform float bottomCornerTrimPx;
out vec4 fragColor;

// Signed distance from pixelPos to the edge of a size-by-size rectangle
// centered at the origin, independently rounded per corner -- standard
// per-corner rounded-box SDF (Inigo Quilez's formulation). Positive
// outside, negative/zero inside. radius = (top-left, top-right,
// bottom-right, bottom-left); pixelPos.y == 0 is the top of the rect
// (image/texture convention, not math-up-is-positive).
float roundedRectDist(vec2 pixelPos, vec2 size, vec4 radius) {
    vec2 halfSize = size * 0.5;
    vec2 centered = pixelPos - halfSize;

    bool isRight = centered.x > 0.0;
    bool isBottom = centered.y > 0.0;
    float radius2 = isRight ? (isBottom ? radius.z : radius.y)
                             : (isBottom ? radius.w : radius.x);

    vec2 d = abs(centered) - (halfSize - radius2);
    return length(max(d, 0.0)) - radius2;
}

void main() {
    // Runs whenever EITHER any corner radius or a ring is wanted -- an
    // all-zero radius degenerates roundedRectDist into a plain
    // (square-cornered) rect SDF, so a square ring (cornerRadiusPx all
    // 0, ringThicknessPx > 0) is just as valid a combination as a
    // rounded one, including mixed (e.g. rounded top, square bottom).
    vec2 pixelPos = fragUV * quadSizePx;

    if (any(greaterThan(cornerRadiusPx, vec4(0.0))) || ringThicknessPx > 0.0) {
        float dist = roundedRectDist(pixelPos, quadSizePx, cornerRadiusPx);
        if (dist > 0.0 || (ringThicknessPx > 0.0 && dist < -ringThicknessPx)) {
            discard;
        }
    }

    if (bottomCornerTrimPx > 0.0 && pixelPos.y > quadSizePx.y - bottomCornerTrimPx &&
        (pixelPos.x < bottomCornerTrimPx || pixelPos.x > quadSizePx.x - bottomCornerTrimPx)) {
        discard;
    }

    vec4 sampled = texture(imageTexture, fragUV);
    if (sampled.a < 0.01) {
        discard;
    }

    fragColor = sampled;
}
