# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from OpenGL import GL

from . import compiler as _compiler


VERTEX_SHADER = """\
#version 330 core

layout(location = 0) in vec3 aPos;

uniform mat4 uMVP;

out vec3 vWorld;

void main() {
    vWorld      = aPos;
    gl_Position = uMVP * vec4(aPos, 1.0);
}
"""

FRAGMENT_SHADER = """\
#version 330 core

in  vec3 vWorld;

// ── Grid dimensions ───────────────────────────────────────────────────────────
uniform float uTileSize;       // world units per major tile
uniform float uMinorSpacing;   // world units per minor cell (tileSize / linesPerTile)

// ── Colours ───────────────────────────────────────────────────────────────────
uniform vec4  uColorA;         // primary tile colour
uniform vec4  uColorB;         // secondary tile colour
uniform vec4  uMajorColor;     // major line colour
uniform vec4  uMinorColor;     // minor (dashed) line colour

// ── Line widths (world units) ─────────────────────────────────────────────────
uniform float uMajorWidth;
uniform float uMinorWidth;

// ── Dash parameters ───────────────────────────────────────────────────────────
uniform uint uStipplePattern;   // bit 0 (LSB) = first 1/32 of segment, bit 31 = last
uniform uint uStipplePhase;   // 1 = phase shift on, 0 = off

// ── Feature flags ─────────────────────────────────────────────────────────────
uniform uint uHasMinorGrid;   // 1 = draw minor dashed lines, 0 = skip

out vec4 oColor;

// ─────────────────────────────────────────────────────────────────────────────
// Anti-aliased coverage for a family of parallel lines spaced 'spacing' apart.
//
//   coord   – world coordinate perpendicular to the line direction
//   spacing – distance between adjacent line centres  (world units)
//   halfW   – half the desired line width             (world units)
//   fw      – fwidth(coord): world units per screen pixel at this fragment
//
// Returns 1.0 on a line centre, 0.0 well between lines, smoothly blended
// at the edges.  The max(halfW, fw) guarantee ensures lines are never rendered
// thinner than one pixel regardless of distance or camera angle.
// ─────────────────────────────────────────────────────────────────────────────
float lineCoverage(float coord, float spacing, float halfW, float fw) {
    float f        = fract(coord / spacing);
    float dist     = min(f, 1.0 - f) * spacing;
    float hw       = max(halfW, fw);
    float coverage = min(halfW / fw, 1.0);   // ← sub-pixel attenuation
    return (1.0 - smoothstep(hw - fw, hw + fw, dist)) * coverage;
}

void main() {
    float wx  = vWorld.x;
    float wz  = vWorld.z;

    // Screen-space derivatives: how many world units change per pixel here.
    // These are the foundation of all anti-aliasing below.
    float fwx = fwidth(wx);
    float fwz = fwidth(wz);

    // ── Checkerboard tiles ────────────────────────────────────────────────────
    vec2 tidx = floor(vec2(wx, wz) / uTileSize);
    vec4 checker4 = (mod(tidx.x + tidx.y, 2.0) < 0.5) ? uColorA : uColorB;
    vec3 checker = checker4.rgb;
    float tileAlpha = checker4.a;

    // As tiles shrink below ~1 pixel the two colours create moire by competing
    // for the same pixels.  Blend toward their average to prevent this.
    float tileFade  = smoothstep(0.25, 1.0, max(fwx, fwz) / uTileSize);
    vec3  tileColor = mix(checker, (uColorA.rgb + uColorB.rgb) * 0.5, tileFade);

    // ── Major grid lines ──────────────────────────────────────────────────────
    float majHW = uMajorWidth * 0.5;
    float majA  = max(lineCoverage(wx, uTileSize, majHW, fwx),
                      lineCoverage(wz, uTileSize, majHW, fwz));

    // ── Minor dashed lines ────────────────────────────────────────────────────
    float minA = 0.0;

    if (bool(uHasMinorGrid)) {
        float minHW = uMinorWidth * 0.5;
        float minFade = 1.0 - smoothstep(0.25, 1.0, max(fwx, fwz) / uMinorSpacing);
    
        // X-parallel lines (at z = n*minorSpacing, stipple runs along x)
        float nearXP = lineCoverage(wz, uMinorSpacing, minHW, fwz);
        
        // X-parallel lines — replace the shiftXP line:
        float shiftXP = float(uStipplePhase) * mod(round(wz / uMinorSpacing), 2.0) * uTileSize * 0.5;
        
        float segXP = mod(wx + shiftXP, uTileSize) / uTileSize;   // 0..1 within tile
        uint  bitXP = min(uint(segXP * 32.0), 31u);
        float dashXP = float((uStipplePattern >> bitXP) & 1u);
    
        // Z-parallel lines (at x = n*minorSpacing, stipple runs along z)
        float nearZP = lineCoverage(wx, uMinorSpacing, minHW, fwx);
        
        // Z-parallel lines — replace the shiftZP line:
        float shiftZP = float(uStipplePhase) * mod(round(wx / uMinorSpacing), 2.0) * uTileSize * 0.5;
        
        float segZP = mod(wz + shiftZP, uTileSize) / uTileSize;
        uint  bitZP = min(uint(segZP * 32.0), 31u);
        float dashZP = float((uStipplePattern >> bitZP) & 1u);
    
        minA = max(nearXP * dashXP, nearZP * dashZP) * minFade;
    }

    // ── Composite: tiles → minor lines → major lines ──────────────────────────
    vec3  color = tileColor;
    color = mix(color, uMinorColor.rgb, minA);
    color = mix(color, uMajorColor.rgb, majA);
    
    float alpha = tileAlpha;
    alpha = mix(alpha, uMinorColor.a, minA);
    alpha = mix(alpha, uMajorColor.a, majA);
    
    oColor = vec4(color, alpha);
}
"""


def compile_program():
    """Compile and link the procedural floor shader.

    Returns a single GL program (replaces the previous solid + dashed pair).
    """
    program = GL.glCreateProgram()

    vs = _compiler.compile(VERTEX_SHADER,   GL.GL_VERTEX_SHADER)
    fs = _compiler.compile(FRAGMENT_SHADER, GL.GL_FRAGMENT_SHADER)

    GL.glAttachShader(program, vs)
    GL.glAttachShader(program, fs)
    GL.glLinkProgram(program)

    if not GL.glGetProgramiv(program, GL.GL_LINK_STATUS):
        error = GL.glGetProgramInfoLog(program).decode()
        raise RuntimeError(f'Floor program linking failed: {error}')

    GL.glDeleteShader(vs)
    GL.glDeleteShader(fs)

    return program
