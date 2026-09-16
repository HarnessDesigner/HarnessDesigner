// ASCII characters only -- this file is read with encoding='ascii' (see
// texture.py's own compile_program()); a non-ASCII byte here raises
// UnicodeDecodeError instead of compiling.
#version 330 core

layout(location = 0) in vec3 in_vertexLocal;

uniform mat4 projection;
uniform mat4 view;
uniform vec3 objectPosition;
uniform vec3 objectScale;

out vec2 fragUV;

void main() {
    vec3 worldPosition = (in_vertexLocal * objectScale) + objectPosition;
    gl_Position = projection * view * vec4(worldPosition, 1.0);

    // Force the nearest possible depth (NDC z just short of -1),
    // regardless of objectPosition.y/the peg-board camera's own
    // Y-as-depth projection (see canvas_pegboard.canvas.Canvas.
    // _set_view) -- a floating table (or its selection border) is
    // meant to always render on top of ordinary scene geometry.
    // objects_pegboard.pegboard_table.PegboardTable.render() already
    // brackets its own draw call in glDepthFunc(GL_ALWAYS), which
    // guarantees THIS draw wins against whatever was drawn BEFORE it
    // this frame, but does nothing for whatever draws AFTER it, which
    // tests normally (GL_LESS) against whatever depth THIS draw wrote
    // -- confirmed 2026-09-16 as "on top while selected [drawn last,
    // via the shared render loop's deferred pass for the selected
    // object] but behind other objects once unselected [drawn in
    // arbitrary main-loop order, so objects rendered afterward pass
    // their own normal depth test against this table's TABLE_DEPTH_Y-
    // based depth]". Forcing gl_Position.z to the nearest valid depth
    // here, in the vertex shader itself, means every LATER draw's own
    // ordinary GL_LESS test against it fails correctly regardless of
    // draw order, without needing objectPosition.y's relationship to
    // ordinary (Y=0) geometry under that projection to be relied on at
    // all. gl_Position.w is always 1.0 for this orthographic
    // projection (no perspective divide), so this is exactly NDC z;
    // 0.999 (not 1.0 exactly) keeps it a hair inside the valid clip
    // range rather than sitting exactly on the near-plane boundary.
    gl_Position.z = -gl_Position.w * 0.999;

    fragUV = vec2(in_vertexLocal.x, in_vertexLocal.z + 0.5);
}