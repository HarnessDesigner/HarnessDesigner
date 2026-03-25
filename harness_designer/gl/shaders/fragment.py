from OpenGL import GL

from . import compiler as _compiler


# Fragment Shader - Phong shading with materials and headlight
SHADER = """
#version 330 core

in vec3 fragPositionGeom;
in vec3 fragNormalGeom;
in float isReflection;
in vec3 debugColor;

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
    // Check if this is debug rendering (debugColor.x >= 0 indicates debug mode)
    if (debugColor.x >= 0.0) {
        FragColor = vec4(debugColor, 1.0);
        return;
    }
    
    // === Normal Phong Shading ===
    vec3 normal = normalize(fragNormalGeom);
    vec3 viewDir = normalize(viewPosition - fragPositionGeom);

    // Determine which side of floor we're on
    bool fragAboveFloor = (fragPositionGeom.y > floorY);

    // Ambient component
    vec3 ambient = lightAmbient.rgb * materialAmbient.rgb;

    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);

    // Mirror light position if rendering reflection
    vec3 effectiveLightPos = lightPosition;
    if (isReflection > 0.5) {
        effectiveLightPos.y = 2.0 * floorY - lightPosition.y;
    }

    // Only apply light if fragment and light are on same side of floor
    bool lightAboveFloor = (effectiveLightPos.y > floorY);
    if (fragAboveFloor == lightAboveFloor) {
        vec3 lightDir = normalize(effectiveLightPos - fragPositionGeom);

        // Diffuse component
        float diffuseStrength = max(dot(normal, lightDir), 0.0);
        diffuse = lightDiffuse.rgb * (diffuseStrength * materialDiffuse.rgb);

        // Specular component (only if surface faces light)
        if (diffuseStrength > 0.0) {
            vec3 reflectDir = reflect(-lightDir, normal);
            float specularStrength = pow(max(dot(viewDir, reflectDir), 0.0), materialShininess);
            specular = lightSpecular.rgb * (specularStrength * materialSpecular.rgb);
        }
    }

    vec3 result = ambient + diffuse + specular;
    float alpha = materialDiffuse.a;

    // Darken reflections slightly
    if (isReflection > 0.5) {
        result *= 0.75;
    }

    FragColor = vec4(result, alpha);
}
"""


def compile_shader():
    return _compiler.compile(SHADER, GL.GL_FRAGMENT_SHADER)

