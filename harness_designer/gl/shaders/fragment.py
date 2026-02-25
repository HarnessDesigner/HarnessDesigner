from OpenGL import GL

from . import compiler as _compiler


# Fragment Shader - Phong shading with materials and headlight
SHADER = """
#version 330 core

in vec3 fragPosition;
in vec3 fragNormal;

out vec4 FragColor;

// Material properties
uniform vec4 materialAmbient;
uniform vec4 materialDiffuse;
uniform vec4 materialSpecular;
uniform float materialShininess;

// Light properties
uniform vec3 lightPosition;
uniform vec3 lightAmbient;
uniform vec3 lightDiffuse;
uniform vec3 lightSpecular;

// Headlight properties
uniform vec3 headlightPosition;
uniform vec3 headlightDirection;
uniform vec3 headlightDiffuse;
uniform float headlightDiameter;  // cone angle in radians
uniform bool headlightEnabled;

uniform vec3 viewPosition;
uniform bool isSelected;

void main() {
    vec3 normal = normalize(fragNormal);
    vec3 viewDir = normalize(viewPosition - fragPosition);

    // Ambient from scene light
    vec3 ambient = lightAmbient * materialAmbient.rgb;

    // Diffuse and specular from main light
    vec3 lightDir = normalize(lightPosition - fragPosition);
    vec3 reflectDir = reflect(-lightDir, normal);

    float diff = max(dot(normal, lightDir), 0.0);
    vec3 diffuse = lightDiffuse * (diff * materialDiffuse.rgb);

    float spec = pow(max(dot(viewDir, reflectDir), 0.0), materialShininess);
    vec3 specular = lightSpecular * (spec * materialSpecular.rgb);

    vec3 result = ambient + diffuse + specular;

    // Add headlight contribution
    if (headlightEnabled) {
        vec3 headlightDir = normalize(headlightPosition - fragPosition);
        vec3 headlightDirNorm = normalize(headlightDirection);

        // Calculate angle between headlight direction and fragment direction
        float theta = acos(dot(-headlightDir, headlightDirNorm));

        // Hard cutoff based on diameter (cone angle)
        if (theta < headlightDiameter / 2.0) {
            float headlightDiff = max(dot(normal, headlightDir), 0.0);
            vec3 headlightContrib = headlightDiffuse * (headlightDiff * materialDiffuse.rgb);
            result += headlightContrib;
        }
    }

    // Add yellow tint for selected objects
    if (isSelected) {
        result = mix(result, vec3(1.0, 1.0, 0.0), 0.3);
    }

    // Use alpha from material diffuse (or could use average of all alphas)
    float alpha = materialDiffuse.a;
    FragColor = vec4(result, alpha);
}
"""


def compile_shader():
    return _compiler.compile(SHADER, GL.GL_FRAGMENT_SHADER)

