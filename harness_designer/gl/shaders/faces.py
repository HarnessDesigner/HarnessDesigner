# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

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

// <= 0.0 means "not a stripe, no clipping" -- every object sets this every
// draw call (see Base3D._render_geometry), since program uniform state
// persists across draw calls sharing the same bound program. When active,
// the mesh already has real-world units baked into local Z (see
// shapes/helix.py), so local Z scaling is skipped entirely instead of
// being stretched to the segment length like every other axis/object --
// objectScale.z is repurposed as the clip length instead.
uniform float stripeClipLength;

out vec3 fragPositionWorld;
out vec3 fragNormalWorld;
out float fragLocalZ;

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
    vec3 effectiveScale = stripeClipLength > 0.0 ? vec3(objectScale.xy, 1.0) : objectScale;

    vec3 scaledVertex = in_vertexLocal * effectiveScale;
    mat3 rotationMatrix = quaternionToMatrix(objectRotation);
    vec3 rotatedVertex = rotationMatrix * scaledVertex;
    vec3 worldPosition = rotatedVertex + objectPosition;

    vec3 in_normalLocal = normalMode == 0 ? in_smoothNormalLocal : in_faceNormalLocal;
    vec3 scaledNormal = in_normalLocal / effectiveScale;
    vec3 worldNormal = rotationMatrix * scaledNormal;

    gl_Position = projection * view * vec4(worldPosition, 1.0);
    fragPositionWorld = worldPosition;
    fragNormalWorld = normalize(worldNormal);
    fragLocalZ = in_vertexLocal.z;
}
"""

GEOMETRY_SHADER = """
#version 330 core

layout(triangles) in;
layout(triangle_strip, max_vertices = 6) out;  // 3 for original triangle + 3 for reflection

in vec3 fragPositionWorld[];
in vec3 fragNormalWorld[];
in float fragLocalZ[];

out vec3 fragPositionGeom;
out vec3 fragNormalGeom;
out float isReflection;
out float fragLocalZGeom;

uniform mat4 projection;
uniform mat4 view;
uniform float floorY;
uniform int objectHasReflection;

void main() {
    // Emit the original triangle
    for (int i = 0; i < 3; i++) {
        gl_Position = gl_in[i].gl_Position;
        fragPositionGeom = fragPositionWorld[i];
        fragNormalGeom = fragNormalWorld[i];
        fragLocalZGeom = fragLocalZ[i];
        isReflection = 0.0;
        EmitVertex();
    }
    EndPrimitive();

    // Emit reflection if enabled
    if (objectHasReflection == 1) {
        for (int i = 2; i >= 0; i--) {
            vec3 reflectedPos = fragPositionWorld[i];
            reflectedPos.y = 2.0 * floorY - reflectedPos.y;

            vec3 reflectedNormal = fragNormalWorld[i];
            reflectedNormal.y = -reflectedNormal.y;

            gl_Position = projection * view * vec4(reflectedPos, 1.0);
            fragPositionGeom = reflectedPos;
            fragNormalGeom = normalize(reflectedNormal);
            fragLocalZGeom = fragLocalZ[i];
            isReflection = 1.0;
            EmitVertex();
        }
        EndPrimitive();
    }
}
"""

FRAGMENT_SHADER = """
#version 330 core

in vec3 fragPositionGeom;
in vec3 fragNormalGeom;
in float isReflection;
in float fragLocalZGeom;

out vec4 FragColor;

uniform vec4 materialAmbient;
uniform vec4 materialDiffuse;
uniform vec4 materialSpecular;
uniform float materialShininess;
uniform vec4 materialEmissive;

uniform vec3 lightPosition;
uniform vec4 lightAmbient;
uniform vec4 lightDiffuse;
uniform vec4 lightSpecular;

uniform vec3 viewPosition;
uniform float floorY;
uniform float stripeClipLength;

// ===== EMISSIVE GLOW CONTROLS =====
uniform float emissiveRimPower;      // Controls glow width (2.0-5.0, default 3.0)
uniform float emissiveRimIntensity;  // Controls glow brightness (1.0-10.0, default 4.0)
// ==================================

void main() {
    if (stripeClipLength > 0.0 && fragLocalZGeom > stripeClipLength) {
        discard;
    }

    vec3 normal = normalize(fragNormalGeom);
    vec3 viewDir = normalize(viewPosition - fragPositionGeom);

    bool fragAboveFloor = (fragPositionGeom.y > floorY);

    // Check if material is emissive
    float emissiveStrength = max(max(materialEmissive.r, materialEmissive.g), materialEmissive.b);
    bool isEmissive = emissiveStrength > 0.0;

    vec3 ambient = lightAmbient.rgb * materialAmbient.rgb;

    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);

    // Only apply lighting to non-emissive materials
    if (!isEmissive) {
        vec3 effectiveLightPos = lightPosition;
        if (isReflection > 0.5) {
            effectiveLightPos.y = 2.0 * floorY - lightPosition.y;
        }

        bool lightAboveFloor = (effectiveLightPos.y > floorY);
        if (fragAboveFloor == lightAboveFloor) {
            vec3 lightDir = normalize(effectiveLightPos - fragPositionGeom);

            float diffuseStrength = max(dot(normal, lightDir), 0.0);
            diffuse = lightDiffuse.rgb * (diffuseStrength * materialDiffuse.rgb);

            if (diffuseStrength > 0.0) {
                vec3 reflectDir = reflect(-lightDir, normal);
                float specularStrength = pow(max(dot(viewDir, reflectDir), 0.0), materialShininess);
                specular = lightSpecular.rgb * (specularStrength * materialSpecular.rgb);
            }
        }
    }

    vec3 result = ambient + diffuse + specular;
    
    // ===== EMISSIVE GLOW =====
    if (isEmissive) {
        // ALL faces get the full emissive color
        result = materialEmissive.rgb;
        
        // Edges get EXTRA brightness on top
        float rimAmount = 1.0 - max(dot(viewDir, normal), 0.0);
        rimAmount = pow(rimAmount, emissiveRimPower);
        vec3 rimGlow = materialEmissive.rgb * rimAmount * emissiveRimIntensity;
        result += rimGlow;
    }
    // =========================
    
    float alpha = materialDiffuse.a;

    if (isReflection > 0.5) {
        result *= 0.75;
    }
        
    FragColor = vec4(result, alpha);
}
"""


def compile_program():
    """Compile and link the faces shader program."""
    vertex_shader = _compiler.compile(VERTEX_SHADER, GL.GL_VERTEX_SHADER)
    geometry_shader = _compiler.compile(GEOMETRY_SHADER, GL.GL_GEOMETRY_SHADER)
    fragment_shader = _compiler.compile(FRAGMENT_SHADER, GL.GL_FRAGMENT_SHADER)

    program = GL.glCreateProgram()
    GL.glAttachShader(program, vertex_shader)
    GL.glAttachShader(program, geometry_shader)
    GL.glAttachShader(program, fragment_shader)
    GL.glLinkProgram(program)

    if not GL.glGetProgramiv(program, GL.GL_LINK_STATUS):
        error = GL.glGetProgramInfoLog(program).decode()
        raise RuntimeError(f"Faces program linking failed: {error}")

    GL.glDeleteShader(vertex_shader)
    GL.glDeleteShader(geometry_shader)
    GL.glDeleteShader(fragment_shader)

    return program
