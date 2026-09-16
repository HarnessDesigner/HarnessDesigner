// ASCII characters only -- this file is read with encoding='ascii' (see
// edges.py's own compile_program()); a non-ASCII byte here raises
// UnicodeDecodeError instead of compiling.
#version 330 core

in float fragLocalZGeom;

out vec4 FragColor;

uniform vec4 materialAmbient;
uniform vec4 materialDiffuse;
uniform vec4 materialSpecular;
uniform float materialShininess;
uniform vec4 materialEmissive;
uniform float stripeClipStop;
uniform float stripeClipStart;


void main() {
    // See gl.shaders.faces' identical discard for the full explanation.
    if (stripeClipStop > 0.0 &&
        (fragLocalZGeom > stripeClipStop || fragLocalZGeom < stripeClipStart)) {
        discard;
    }

    vec3 result = materialAmbient.rgb + materialDiffuse.rgb + materialSpecular.rgb + materialEmissive.rgb;

    // See gl.shaders.faces' identical fix -- rescale all channels
    // together on overflow instead of letting the implicit per-channel
    // clamp on write desaturate/shift the material's true color.
    float peak = max(result.r, max(result.g, result.b));
    if (peak > 1.0) {
        result /= peak;
    }

    float alpha = materialDiffuse.a;

    FragColor = vec4(result, alpha);
}