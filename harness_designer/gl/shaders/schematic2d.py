from OpenGL import GL
from . import compiler as _compiler


VERTEX_SHADER = """
#version 330 core

layout(location = 0) in vec3 in_vertexLocal;
layout(location = 1) in vec3 in_smoothNormalLocal;
layout(location = 2) in vec3 in_faceNormalLocal;

uniform mat4 projection;
uniform mat4 view;
uniform vec3 objectPosition;
uniform vec4 objectRotation;
uniform vec3 objectScale;
uniform int normalMode;

// 2D-specific uniforms
uniform int flipY;  // 1 = flip Y-axis (screen coords), 0 = keep Y-up

out vec3 fragNormal;    // Normal in 2D space for lighting
out vec2 fragPos2D;     // 2D position
out vec3 fragPos3D;     // Original 3D position (for height-based effects)

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
        1.0 - 2.0 * (yy + zz), 2.0 * (xy + wz), 2.0 * (xz - wy),
        2.0 * (xy - wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz + wx),
        2.0 * (xz + wy), 2.0 * (yz - wx), 1.0 - 2.0 * (xx + yy)
    );
}

void main() {
    // Apply object transformations
    vec3 scaledVertex = in_vertexLocal * objectScale;
    mat3 rotationMatrix = quaternionToMatrix(objectRotation);
    vec3 rotatedVertex = rotationMatrix * scaledVertex;
    vec3 worldPosition = rotatedVertex + objectPosition;
    
    // Transform normal
    vec3 in_normalLocal = normalMode == 0 ? in_smoothNormalLocal : in_faceNormalLocal;
    vec3 scaledNormal = in_normalLocal / objectScale;
    vec3 worldNormal = rotationMatrix * scaledNormal;
    
    // PROJECT 3D → 2D: Top-down view looking down Y-axis
    // 3D: X=right, Y=up, Z=forward
    // 2D: X=right, Y=vertical (screen or world coords based on flipY)
    vec2 pos2D;
    pos2D.x = worldPosition.x;
    
    if (flipY == 1) {
        pos2D.y = -worldPosition.z;  // Screen coords (Y-down)
    } else {
        pos2D.y = worldPosition.z;   // World coords (Y-up)
    }
    
    // Transform normal to 2D space (project XZ components)
    // For top-down view, normal Y component becomes Z in screen space
    vec3 normal2D;
    normal2D.x = worldNormal.x;
    normal2D.y = flipY == 1 ? -worldNormal.z : worldNormal.z;
    normal2D.z = worldNormal.y;  // Y normal becomes height/depth
    
    gl_Position = projection * view * vec4(pos2D, 0.0, 1.0);
    
    fragNormal = normalize(normal2D);
    fragPos2D = pos2D;
    fragPos3D = worldPosition;
}
"""


FRAGMENT_SHADER = """
#version 330 core

in vec3 fragNormal;
in vec2 fragPos2D;
in vec3 fragPos3D;

out vec4 FragColor;

uniform vec4 materialDiffuse;
uniform vec4 materialAmbient;
uniform vec4 outlineColor;
uniform int renderMode;  // 0 = filled, 1 = outline, 2 = both

// Lighting (camera-based headlight)
uniform vec2 cameraPos2D;    // Camera position in 2D
uniform vec3 lightColor;     // Headlight color
uniform float lightIntensity;

void main() {
    vec3 normal = normalize(fragNormal);
    
    // Light direction: from camera toward fragment
    // In 2D top-down view, light is perpendicular to screen (pointing down)
    // Add slight angle based on distance from camera for depth effect
    vec2 toFragment = fragPos2D - cameraPos2D;
    float distFromCamera = length(toFragment);
    vec2 lightDir2D = distFromCamera > 0.001 ? normalize(toFragment) : vec2(0.0);
    
    // Light comes from "above" (out of screen) with slight angle toward camera
    vec3 lightDir = normalize(vec3(lightDir2D * 0.3, 1.0));
    
    // Ambient lighting
    vec3 ambient = materialAmbient.rgb * 0.4;
    
    // Diffuse lighting
    float diffuseStrength = max(dot(normal, lightDir), 0.0);
    vec3 diffuse = lightColor * lightIntensity * diffuseStrength * materialDiffuse.rgb;
    
    // Optional: Add slight rim lighting for edges
    vec3 viewDir = vec3(0.0, 0.0, 1.0);  // Looking down at 2D
    float rimAmount = 1.0 - max(dot(viewDir, normal), 0.0);
    rimAmount = pow(rimAmount, 3.0);
    vec3 rim = lightColor * rimAmount * 0.2;
    
    // Combine lighting
    vec3 result = ambient + diffuse + rim;
    
    // Height-based subtle shading (optional visual feedback)
    float heightFactor = clamp((fragPos3D.y + 50.0) / 100.0, 0.8, 1.0);
    result *= heightFactor;
    
    // Apply render mode
    if (renderMode == 1) {
        // Outline only
        FragColor = outlineColor;
    } else if (renderMode == 2) {
        // Both - with slight transparency
        FragColor = vec4(result, 0.7);
    } else {
        // Filled with lighting
        FragColor = vec4(result, materialDiffuse.a);
    }
}
"""


def compile_program():
    """Compile and link the 2D schematic shader program with lighting."""
    vertex_shader = _compiler.compile(VERTEX_SHADER, GL.GL_VERTEX_SHADER)
    fragment_shader = _compiler.compile(FRAGMENT_SHADER, GL.GL_FRAGMENT_SHADER)

    program = GL.glCreateProgram()
    GL.glAttachShader(program, vertex_shader)
    GL.glAttachShader(program, fragment_shader)
    GL.glLinkProgram(program)

    if not GL.glGetProgramiv(program, GL.GL_LINK_STATUS):
        error = GL.glGetProgramInfoLog(program).decode()
        raise RuntimeError(f"2D schematic program linking failed: {error}")

    GL.glDeleteShader(vertex_shader)
    GL.glDeleteShader(fragment_shader)

    return program
