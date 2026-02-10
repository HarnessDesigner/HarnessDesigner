from OpenGL import GL


# Vertex Shader - applies position and rotation per instance
VERTEX_SHADER = """
#version 330 core

layout(location = 0) in vec3 in_position;
layout(location = 1) in vec3 in_normal;

uniform mat4 projection;
uniform mat4 view;
uniform vec3 objectPosition;
uniform vec4 objectRotation;  // quaternion (w, x, y, z)
uniform vec3 objectScale;      // NEW: x, y, z scaling

out vec3 fragPosition;
out vec3 fragNormal;

// Convert quaternion to rotation matrix
mat3 quaternionToMatrix(vec4 q) {
    float w = q.x;
    float x = q.y;
    float y = q.z;
    float z = q.w;
    
    float xx = x * x;
    float yy = y * y;
    float zz = z * z;
    float xy = x * y;
    float xz = x * z;
    float yz = y * z;
    float wx = w * x;
    float wy = w * y;
    float wz = w * z;
    
    return mat3(
        1.0 - 2.0 * (yy + zz), 2.0 * (xy - wz), 2.0 * (xz + wy),
        2.0 * (xy + wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz - wx),
        2.0 * (xz - wy), 2.0 * (yz + wx), 1.0 - 2.0 * (xx + yy)
    );
}

void main() {
    // Apply scale first (in local space)
    vec3 scaledPosition = in_position * objectScale;
    
    // Then apply rotation
    mat3 rotationMatrix = quaternionToMatrix(objectRotation);
    vec3 rotatedPosition = rotationMatrix * scaledPosition;
    
    // Finally apply translation
    vec3 worldPosition = rotatedPosition + objectPosition;
    
    // Transform normal (use inverse transpose for non-uniform scaling)
    // For uniform or axis-aligned scaling, this simplified version works:
    vec3 scaledNormal = in_normal / objectScale;  // Inverse scale for normals
    vec3 rotatedNormal = rotationMatrix * scaledNormal;
    
    gl_Position = projection * view * vec4(worldPosition, 1.0);
    
    fragPosition = worldPosition;
    fragNormal = normalize(rotatedNormal);
}
"""

# Fragment Shader - Phong shading with materials and headlight
FRAGMENT_SHADER = """
#version 330 core

in vec3 fragPosition;
in vec3 fragNormal;

out vec4 FragColor;

// Material properties
uniform vec3 materialAmbient;
uniform vec3 materialDiffuse;
uniform vec3 materialSpecular;
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
    vec3 ambient = lightAmbient * materialAmbient;

    // Diffuse and specular from main light
    vec3 lightDir = normalize(lightPosition - fragPosition);
    vec3 reflectDir = reflect(-lightDir, normal);

    float diff = max(dot(normal, lightDir), 0.0);
    vec3 diffuse = lightDiffuse * (diff * materialDiffuse);

    float spec = pow(max(dot(viewDir, reflectDir), 0.0), materialShininess);
    vec3 specular = lightSpecular * (spec * materialSpecular);

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
            vec3 headlightContrib = headlightDiffuse * (headlightDiff * materialDiffuse);
            result += headlightContrib;
        }
    }

    // Add yellow tint for selected objects
    if (isSelected) {
        result = mix(result, vec3(1.0, 1.0, 0.0), 0.3);
    }

    FragColor = vec4(result, 1.0);
}
"""


def compile_shader(source, shader_type):
    """Compile a shader"""
    shader = GL.glCreateShader(shader_type)
    GL.glShaderSource(shader, source)
    GL.glCompileShader(shader)

    if not GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS):
        error = GL.glGetShaderInfoLog(shader).decode()
        raise RuntimeError(f"Shader compilation failed: {error}")

    return shader


def create_program():
    """Create shader program"""
    vertex_shader = compile_shader(VERTEX_SHADER, GL.GL_VERTEX_SHADER)
    fragment_shader = compile_shader(FRAGMENT_SHADER, GL.GL_FRAGMENT_SHADER)

    program = GL.glCreateProgram()
    GL.glAttachShader(program, vertex_shader)
    GL.glAttachShader(program, fragment_shader)
    GL.glLinkProgram(program)

    if not GL.glGetProgramiv(program, GL.GL_LINK_STATUS):
        error = GL.glGetProgramInfoLog(program).decode()
        raise RuntimeError(f"Program linking failed: {error}")

    GL.glDeleteShader(vertex_shader)
    GL.glDeleteShader(fragment_shader)

    return program
