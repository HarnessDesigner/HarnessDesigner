// ASCII characters only -- this file is read with encoding='ascii' (see
// grid2d.py's own compile_program()); a non-ASCII byte here raises
// UnicodeDecodeError instead of compiling.
#version 330 core

in vec2 vWorld;

out vec4 FragColor;

// current world-space dot spacing -- see gl.floor.Floor._current_spacing
uniform float uSpacing;

// converts a pixel dot radius to world units
uniform float uWorldPerPixel;

uniform vec4 uDotColor;

// Procedural dot grid: computed entirely from world position, no precomputed
// per-dot vertex data. Single tier only -- gl.floor.Floor._current_spacing
// already picks whichever power-of-2 spacing keeps this tier's own
// on-screen spacing within [target/2, target] (see its own docstring for
// why), so there is nothing left for the shader itself to decide.

void main() {
    // fixed on-screen dot size (pixels), at current zoom
    float radius = 2.0 * 0.5 * uWorldPerPixel;

    vec2 cell = fract(vWorld / uSpacing);
    vec2 d = min(cell, 1.0 - cell) * uSpacing;
    float dist = length(d);
    float alpha = (1.0 - smoothstep(radius * 0.6, radius, dist)) * uDotColor.a;

    if (alpha < 0.003) {
        discard;
    }

    FragColor = vec4(uDotColor.rgb, alpha);
}