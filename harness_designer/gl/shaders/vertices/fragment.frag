// ASCII characters only -- this file is read with encoding='ascii' (see
// vertices.py's own compile_program()); a non-ASCII byte here raises
// UnicodeDecodeError instead of compiling.
#version 330 core

in vec3 pointColor;
out vec4 FragColor;

void main() {
    FragColor = vec4(pointColor, 1.0);
}