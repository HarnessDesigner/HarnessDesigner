// ASCII characters only -- this file is read with encoding='ascii' (see
// floor.py's own compile_program()); a non-ASCII byte here raises
// UnicodeDecodeError instead of compiling.
#version 330 core

in  vec3 vWorld;

// -- Grid dimensions -----------------------------------------------------------

// world units per major tile
uniform float uTileSize;

// world units per minor cell (tileSize / linesPerTile)
uniform float uMinorSpacing;

// -- Colours -------------------------------------------------------------------

// primary tile colour
uniform vec4  uColorA;

 // secondary tile colour
uniform vec4  uColorB;

// major line colour
uniform vec4  uMajorColor;

// minor (dashed) line colour
uniform vec4  uMinorColor;

// -- Line widths (world units) -------------------------------------------------
uniform float uMajorWidth;
uniform float uMinorWidth;

// -- Dash parameters -----------------------------------------------------------

// bit 0 (LSB) = first 1/32 of segment, bit 31 = last
uniform uint uStipplePattern;

// 1 = phase shift on, 0 = off
uniform uint uStipplePhase;

// -- Feature flags -------------------------------------------------------------

// 1 = draw minor dashed lines, 0 = skip
uniform uint uHasMinorGrid;

// 1 = opaque pre-pass (discard alpha<threshold), 0 = transparent pass
uniform int  uOpaquePass;

out vec4 oColor;

// -----------------------------------------------------------------------------
// Anti-aliased coverage for a family of parallel lines spaced 'spacing' apart.
//
//   coord   - world coordinate perpendicular to the line direction
//   spacing - distance between adjacent line centres  (world units)
//   halfW   - half the desired line width             (world units)
//   fw      - fwidth(coord): world units per screen pixel at this fragment
//
// Returns 1.0 on a line centre, 0.0 well between lines, smoothly blended
// at the edges.  The max(halfW, fw) guarantee ensures lines are never rendered
// thinner than one pixel regardless of distance or camera angle.
// -----------------------------------------------------------------------------
float lineCoverage(float coord, float spacing, float halfW, float fw) {
    float f        = fract(coord / spacing);
    float dist     = min(f, 1.0 - f) * spacing;
    float hw       = max(halfW, fw);

    // sub-pixel attenuation
    float coverage = min(halfW / fw, 1.0);

    return (1.0 - smoothstep(hw - fw, hw + fw, dist)) * coverage;
}

void main() {
    float wx  = vWorld.x;
    float wz  = vWorld.z;

    // Screen-space derivatives: how many world units change per pixel here.
    // These are the foundation of all anti-aliasing below.
    float fwx = fwidth(wx);
    float fwz = fwidth(wz);

    // -- Checkerboard tiles ----------------------------------------------------
    vec2 tidx = floor(vec2(wx, wz) / uTileSize);
    vec4 checker4 = (mod(tidx.x + tidx.y, 2.0) < 0.5) ? uColorA : uColorB;
    vec3 checker = checker4.rgb;
    float tileAlpha = checker4.a;

    // As tiles shrink below ~1 pixel the two colours create moire by competing
    // for the same pixels.  Blend toward their average to prevent this.
    float tileFade  = smoothstep(0.25, 1.0, max(fwx, fwz) / uTileSize);
    vec3  tileColor = mix(checker, (uColorA.rgb + uColorB.rgb) * 0.5, tileFade);

    // -- Major grid lines ------------------------------------------------------
    float majHW = uMajorWidth * 0.5;
    float majA  = max(lineCoverage(wx, uTileSize, majHW, fwx),
                      lineCoverage(wz, uTileSize, majHW, fwz));

    // -- Minor dashed lines ----------------------------------------------------
    float minA = 0.0;

    if (bool(uHasMinorGrid)) {
        float minHW = uMinorWidth * 0.5;
        float minFade = 1.0 - smoothstep(0.25, 1.0, max(fwx, fwz) / uMinorSpacing);

        // X-parallel lines (at z = n*minorSpacing, stipple runs along x)
        float nearXP = lineCoverage(wz, uMinorSpacing, minHW, fwz);

        // X-parallel lines - replace the shiftXP line:
        float shiftXP = float(uStipplePhase) * mod(round(wz / uMinorSpacing), 2.0) * uTileSize * 0.5;

        // 0..1 within tile
        float segXP = mod(wx + shiftXP, uTileSize) / uTileSize;

        uint  bitXP = min(uint(segXP * 32.0), 31u);
        float dashXP = float((uStipplePattern >> bitXP) & 1u);

        // Z-parallel lines (at x = n*minorSpacing, stipple runs along z)
        float nearZP = lineCoverage(wx, uMinorSpacing, minHW, fwx);

        // Z-parallel lines - replace the shiftZP line:
        float shiftZP = float(uStipplePhase) * mod(round(wx / uMinorSpacing), 2.0) * uTileSize * 0.5;

        float segZP = mod(wz + shiftZP, uTileSize) / uTileSize;
        uint  bitZP = min(uint(segZP * 32.0), 31u);
        float dashZP = float((uStipplePattern >> bitZP) & 1u);

        minA = max(nearXP * dashXP, nearZP * dashZP) * minFade;
    }

    // -- Composite: tiles -> minor lines -> major lines --------------------------
    vec3  color = tileColor;
    color = mix(color, uMinorColor.rgb, minA);
    color = mix(color, uMajorColor.rgb, majA);

    float alpha = tileAlpha;
    alpha = mix(alpha, uMinorColor.a, minA);
    alpha = mix(alpha, uMajorColor.a, majA);

    // Depth-correct compositing: opaque fragments write depth; transparent do not.
    // This must be handled per-fragment in the shader because glDepthMask cannot
    // toggle within a single draw call.  We split the draw into two passes via the
    // uOpaquePass uniform and discard the unwanted tier in each pass.
    if (uOpaquePass == 1 && alpha < 0.999) discard;
    if (uOpaquePass == 0 && alpha >= 0.999) discard;

    oColor = vec4(color, alpha);
}