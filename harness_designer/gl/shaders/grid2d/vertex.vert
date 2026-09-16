// ASCII characters only -- this file is read with encoding='ascii' (see
// grid2d.py's own compile_program()); a non-ASCII byte here raises
// UnicodeDecodeError instead of compiling.
#version 330 core

// world-space (X, Z), one full-viewport quad
layout(location = 0) in vec2 in_position;

uniform mat4 projection;

out vec2 vWorld;

void main() {
    vWorld = in_position;

    // `projection` (built by canvas_pegboard/canvas_schematic's own
    // _set_view) maps vertex component 0 -> screen X, component 2 ->
    // screen Y, component 1 -> depth (ground height, 0.0) -- see
    // gl.canvas_pegboard.canvas.Canvas._set_view's own comment for why.
    // in_position is (world X, world Z), so it has to land in components
    // 0 and 2, not 0 and 1 -- packing it as vec4(in_position, 0.0, 1.0)
    // (world X, world Z, 0.0) fed world Z into the depth row and the
    // fixed 0.0 into the screen-Y row instead, collapsing the floor to a
    // degenerate line at the wrong depth once the projection's row/column
    // mapping was corrected to actually look down world Y.
    gl_Position = projection * vec4(in_position.x, -100.0, in_position.y, 1.0);
}