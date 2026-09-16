// ASCII characters only -- this file is read with encoding='ascii' (see
// floor.py's own compile_program()); a non-ASCII byte here raises
// UnicodeDecodeError instead of compiling.
#version 330 core

layout(location = 0) in vec3 aPos;

uniform mat4 uMVP;

out vec3 vWorld;

void main() {
    vWorld      = aPos;
    gl_Position = uMVP * vec4(aPos, 1.0);
}