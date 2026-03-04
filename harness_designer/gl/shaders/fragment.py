from OpenGL import GL

from . import compiler as _compiler


# Fragment Shader - Phong shading with materials and headlight
SHADER = """
#version 330 core

in vec3 fragPositionGeom;
in vec3 fragNormalGeom;
in float isReflection;

out vec4 FragColor;

uniform vec4 materialAmbient;
uniform vec4 materialDiffuse;
uniform vec4 materialSpecular;
uniform float materialShininess;

uniform vec3 lightPosition;
uniform vec4 lightAmbient;
uniform vec4 lightDiffuse;
uniform vec4 lightSpecular;

uniform vec3 viewPosition;
uniform float floorY;

void main() {
    vec3 normal = normalize(fragNormalGeom);
    vec3 viewDir = normalize(viewPosition - fragPositionGeom);

    // Determine which side of floor we're on
    bool fragAboveFloor = (fragPositionGeom.y > floorY);

    // Ambient
    vec3 ambient = lightAmbient.rgb * materialAmbient.rgb;

    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);

    // Mirror light if rendering reflection
    vec3 effectiveLightPos = lightPosition;
    if (isReflection > 0.5) {
        effectiveLightPos.y = 2.0 * floorY - lightPosition.y;
    }

    // Only apply light if on same side of floor
    bool lightAboveFloor = (effectiveLightPos.y > floorY);
    if (fragAboveFloor == lightAboveFloor) {
        vec3 lightDir = normalize(effectiveLightPos - fragPositionGeom);

        float diff = max(dot(normal, lightDir), 0.0);
        diffuse = lightDiffuse.rgb * (diff * materialDiffuse.rgb);

        if (diff > 0.0) {
            vec3 reflectDir = reflect(-lightDir, normal);
            float spec = pow(max(dot(viewDir, reflectDir), 0.0), materialShininess);
            specular = lightSpecular.rgb * (spec * materialSpecular.rgb);
        }
    }

    vec3 result = ambient + diffuse + specular;

    float alpha = materialDiffuse.a;

    if (isReflection > 0.5) {
        // Darken reflections slightly
        result *= 0.75;
    }

    FragColor = vec4(result, alpha);
}
"""

def compile_shader():
    return _compiler.compile(SHADER, GL.GL_FRAGMENT_SHADER)

