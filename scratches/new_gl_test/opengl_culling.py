from OpenGL import GL
import numpy as np
import ctypes
import math

# ---------------------------
# GLSL SHADERS (compute + render)
# ---------------------------

CULL_COMPUTE = r"""
#version 430
layout(local_size_x = 256) in;

layout(std430, binding = 0) readonly buffer Triangles {
    vec4 positions[]; // each triangle occupies 3 consecutive vec4s
};

layout(std430, binding = 1) buffer VisibleIndex {
    uint triIndex[]; // triIndex[visibleID]
};

layout(std430, binding = 2) buffer VisibleDepth {
    float depth[]; // depth[visibleID]
};

layout(binding = 0) uniform atomic_uint visibleCount;

uniform mat4 viewMatrix;
uniform float nearCull;
uniform float farCull;
uniform uint triCount;

void main() {
    uint gid = gl_GlobalInvocationID.x;
    if (gid >= triCount) return;

    // read triangle vertices (vec4 stored, w unused)
    vec3 p0 = positions[gid*3 + 0].xyz;
    vec3 p1 = positions[gid*3 + 1].xyz;
    vec3 p2 = positions[gid*3 + 2].xyz;

    // face normal (world space)
    vec3 e0 = p1 - p0;
    vec3 e1 = p2 - p0;
    vec3 normal = normalize(cross(e0, e1));

    // centroid and view-space depth
    vec4 centroidView = viewMatrix * vec4((p0 + p1 + p2) / 3.0, 1.0);
    float depthVal = -centroidView.z; // larger = farther from camera along view direction

    // backface culling: keep triangles whose normal faces camera
    vec3 viewDir = normalize(-centroidView.xyz);
    float ndotv = dot(normal, viewDir);
    // Cull if normal points away from camera
    if (ndotv > 0.0) {
        return;
    }

    // distance/frustum cull (simple near/far)
    if (depthVal < nearCull || depthVal > farCull) return;

    uint idx = atomicCounterIncrement(visibleCount);
    triIndex[idx] = uint(gid);
    depth[idx] = depthVal;
}
"""

BITONIC_COMPUTE = r"""
#version 430
layout(local_size_x = 256) in;

layout(std430, binding = 1) buffer VisibleIndex {
    uint triIndex[]; // triIndex[0..N-1]
};

layout(std430, binding = 2) buffer VisibleDepth {
    float depth[]; // depth[0..N-1]
};

uniform uint k; // stage size
uniform uint j; // inner size
uniform uint sortSize; // padded size (power of two)

void main() {
    uint idx = gl_GlobalInvocationID.x;
    if (idx >= sortSize) return;

    uint ixj = idx ^ j;
    if (ixj > idx) {
        bool ascending = ((idx & k) == 0u);
        float di = depth[idx];
        float dj = depth[ixj];
        // If (di > dj) == ascending then swap (standard bitonic compare/exchange)
        if ((di > dj) == ascending) {
            // swap depth
            float tmpd = depth[idx];
            depth[idx] = depth[ixj];
            depth[ixj] = tmpd;
            // swap index
            uint tmpi = triIndex[idx];
            triIndex[idx] = triIndex[ixj];
            triIndex[ixj] = tmpi;
        }
    }
}
"""

REORDER_COMPUTE = r"""
#version 430
layout(local_size_x = 256) in;

layout(std430, binding = 0) readonly buffer Triangles {
    vec4 positions[]; // tri*3 + 0..2
};

layout(std430, binding = 5) readonly buffer TriNormals {
    vec4 triNormal[]; // one normal per triangle (w unused)
};

layout(std430, binding = 1) readonly buffer VisibleIndex {
    uint triIndex[]; // sorted tri indices
};

layout(std430, binding = 3) writeonly buffer OutputVBO {
    vec4 verts[]; // output tri vertices, base = idx*3
};

layout(std430, binding = 4) writeonly buffer OutputNormals {
    vec4 normals[]; // output per-vertex normals (flat: same normal for all 3 vertices)
};

uniform uint outCount; // number of visible triangles (actual)

void main() {
    uint idx = gl_GlobalInvocationID.x;
    if (idx >= outCount) return;
    uint tri = triIndex[idx];
    uint base = idx * 3u;

    verts[base + 0] = positions[tri*3 + 0];
    verts[base + 1] = positions[tri*3 + 1];
    verts[base + 2] = positions[tri*3 + 2];

    vec4 n = triNormal[tri];
    normals[base + 0] = n;
    normals[base + 1] = n;
    normals[base + 2] = n;
}
"""

VS_SRC = r"""
#version 330 core
layout(location = 0) in vec4 inPos;
layout(location = 1) in vec4 inNormal; // w unused
uniform mat4 vp;
uniform mat4 viewMatrix; // for transforming normals to view space
out vec3 vNormal;
void main() {
    gl_Position = vp * inPos;
    // transform normal into view-space (assumes no non-uniform scale in model)
    vNormal = mat3(viewMatrix) * inNormal.xyz;
}
"""

FS_SRC = r"""
#version 330 core
in vec3 vNormal;
out vec4 outColor;
void main() {
    vec3 n = normalize(vNormal);
    vec3 lightDir = normalize(vec3(0.4, 0.7, 0.2));
    float lambert = max(dot(n, lightDir), 0.0);
    vec3 baseColor = vec3(0.95, 0.65, 0.3);
    vec3 ambient = vec3(0.12, 0.12, 0.14);
    vec3 color = ambient + lambert * baseColor;
    outColor = vec4(color, 1.0);
}
"""


# ---------------------------
# GL helper functions
# ---------------------------
def compile_shader(src, shader_type):
    sh = GL.glCreateShader(shader_type)
    GL.glShaderSource(sh, src)
    GL.glCompileShader(sh)
    ok = GL.glGetShaderiv(sh, GL.GL_COMPILE_STATUS)
    if not ok:
        log = GL.glGetShaderInfoLog(sh).decode()
        raise RuntimeError(f"Shader compile failed: {log}")
    return sh


def link_program(shaders):
    prog = GL.glCreateProgram()
    for sh in shaders:
        GL.glAttachShader(prog, sh)
    GL.glLinkProgram(prog)
    ok = GL.glGetProgramiv(prog, GL.GL_LINK_STATUS)
    if not ok:
        log = GL.glGetProgramInfoLog(prog).decode()
        raise RuntimeError(f"Program link failed: {log}")
    for sh in shaders:
        GL.glDetachShader(prog, sh)
        GL.glDeleteShader(sh)
    return prog


def create_compute_program(src):
    sh = compile_shader(src, GL.GL_COMPUTE_SHADER)
    return link_program([sh])


def create_program(vs_src, fs_src):
    vs = compile_shader(vs_src, GL.GL_VERTEX_SHADER)
    fs = compile_shader(fs_src, GL.GL_FRAGMENT_SHADER)
    return link_program([vs, fs])


def next_power_of_two(x):
    return 1 if x == 0 else 2 ** int(np.ceil(np.log2(x)))


# Camera (simple look-at) -> view matrix
def look_at(eye, center, up):
    f = (center - eye)
    f = f / np.linalg.norm(f)
    u = up / np.linalg.norm(up)
    s = np.cross(f, u)  # NOQA
    s = s / np.linalg.norm(s)
    u = np.cross(s, f)  # NOQA
    M = np.identity(4, dtype=np.float32)
    M[0, :3] = s
    M[1, :3] = u
    M[2, :3] = -f
    T = np.identity(4, dtype=np.float32)
    T[:3, 3] = -eye
    return M @ T


def perspective(fovy, aspect, zn, zf):
    f = 1.0 / math.tan(fovy / 2.0)
    M = np.zeros((4, 4), dtype=np.float32)
    M[0, 0] = f / aspect
    M[1, 1] = f
    M[2, 2] = (zf + zn) / (zn - zf)
    M[2, 3] = (2 * zf * zn) / (zn - zf)
    M[3, 2] = -1.0
    return M


class Renderer:

    def __init__(self, canvas):
        self.canvas = canvas

        self.cull_prog = None
        self.bitonic_prog = None
        self.reorder_prog = None
        self.render_prog = None
        self.counter_buf = None
        self.loc_view = None
        self.loc_near = None
        self.loc_far = None
        self.loc_triCount = None
        self.loc_k = None
        self.loc_j = None
        self.loc_sortSize = None
        self.loc_outCount = None
        self.loc_vp = None
        self.loc_view_render = None

    def init(self):
        self.cull_prog = create_compute_program(CULL_COMPUTE)
        self.bitonic_prog = create_compute_program(BITONIC_COMPUTE)
        self.reorder_prog = create_compute_program(REORDER_COMPUTE)
        self.render_prog = create_program(VS_SRC, FS_SRC)

        # atomic counter (binding point 0 for atomic counters)
        self.counter_buf = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ATOMIC_COUNTER_BUFFER, self.counter_buf)
        zero = np.array([0], dtype=np.uint32)
        GL.glBufferData(GL.GL_ATOMIC_COUNTER_BUFFER, zero.nbytes, zero, GL.GL_DYNAMIC_COPY)
        GL.glBindBufferBase(GL.GL_ATOMIC_COUNTER_BUFFER, 0, self.counter_buf)

        # Setup VAO for rendering reading from the two output buffers
        vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(vao)

        # Uniform locations
        GL.glUseProgram(self.cull_prog)
        self.loc_view = GL.glGetUniformLocation(self.cull_prog, "viewMatrix")
        self.loc_near = GL.glGetUniformLocation(self.cull_prog, "nearCull")
        self.loc_far = GL.glGetUniformLocation(self.cull_prog, "farCull")
        self.loc_triCount = GL.glGetUniformLocation(self.cull_prog, "triCount")

        GL.glUseProgram(self.bitonic_prog)
        self.loc_k = GL.glGetUniformLocation(self.bitonic_prog, "k")
        self.loc_j = GL.glGetUniformLocation(self.bitonic_prog, "j")
        self.loc_sortSize = GL.glGetUniformLocation(self.bitonic_prog, "sortSize")

        GL.glUseProgram(self.reorder_prog)
        self.loc_outCount = GL.glGetUniformLocation(self.reorder_prog, "outCount")

        GL.glUseProgram(self.render_prog)
        self.loc_vp = GL.glGetUniformLocation(self.render_prog, "vp")
        self.loc_view_render = GL.glGetUniformLocation(self.render_prog, "viewMatrix")

        GL.glUseProgram(self.cull_prog)
        GL.glUseProgram(self.bitonic_prog)
        GL.glUseProgram(self.reorder_prog)

    def render(self, triangles, normals, count):
        tri_ssbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, tri_ssbo)
        GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, triangles.nbytes,
                        triangles, GL.GL_STATIC_DRAW)

        GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 0, tri_ssbo)

        # TriNormals SSBO (binding = 5 read-only in reorder shader)
        tri_normals_ssbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, tri_normals_ssbo)
        GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, normals.nbytes,
                        normals, GL.GL_STATIC_DRAW)

        GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 5, tri_normals_ssbo)

        # visible arrays (indices and depths) - allocate padded size for bitonic
        max_slots = next_power_of_two(count)
        visible_indices = np.zeros((max_slots,), dtype=np.uint32)
        visible_depths = np.full((max_slots,), -1e30, dtype=np.float32)

        idx_ssbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, idx_ssbo)
        GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, visible_indices.nbytes,
                        visible_indices, GL.GL_DYNAMIC_COPY)

        GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 1, idx_ssbo)

        depth_ssbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, depth_ssbo)
        GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, visible_depths.nbytes,
                        visible_depths, GL.GL_DYNAMIC_COPY)

        GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 2, depth_ssbo)

        # atomic counter (binding point 0 for atomic counters)
        counter_buf = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ATOMIC_COUNTER_BUFFER, counter_buf)
        zero = np.array([0], dtype=np.uint32)
        GL.glBufferData(GL.GL_ATOMIC_COUNTER_BUFFER, zero.nbytes,
                        zero, GL.GL_DYNAMIC_COPY)

        GL.glBindBufferBase(GL.GL_ATOMIC_COUNTER_BUFFER, 0, counter_buf)

        # output VBOs (expanded sorted triangles):
        out_vertex_count = max_slots * 3
        out_vbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, out_vbo)

        # vec4 per vertex
        GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, out_vertex_count * 16,
                        None, GL.GL_DYNAMIC_COPY)

        # binding = 3 in reorder shader
        GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 3, out_vbo)

        out_nbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, out_nbo)

        # vec4 per vertex normal
        GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, out_vertex_count * 16,
                        None, GL.GL_DYNAMIC_COPY)

        # binding = 4 in reorder shader
        GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 4, out_nbo)

        # Setup VAO for rendering reading from the two output buffers
        vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(vao)

        # position attribute (location 0)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, out_vbo)
        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(0, 4, GL.GL_FLOAT, GL.GL_FALSE,
                                 16, ctypes.c_void_p(0))

        # normal attribute (location 1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, out_nbo)
        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(1, 4, GL.GL_FLOAT, GL.GL_FALSE,
                                 16, ctypes.c_void_p(0))
        GL.glBindVertexArray(0)

        width, height = self.canvas.GetSize()

        c_eye = self.canvas.camera_eye.as_array
        c_pos = self.canvas.camera_pos.as_array

        view = look_at(c_eye, c_pos, self.canvas.up)

        proj = perspective(math.radians(45.0),
                           float(width) / float(height), 0.1, 1000.0)
        vp = proj @ view

        # 1) Reset atomic counter to zero and clear visible buffers
        GL.glBindBuffer(GL.GL_ATOMIC_COUNTER_BUFFER, self.counter_buf)
        GL.glBufferSubData(GL.GL_ATOMIC_COUNTER_BUFFER, 0, zero.nbytes, zero)

        neg_inf = np.full((max_slots,), -1e30, dtype=np.float32)
        GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, depth_ssbo)
        GL.glBufferSubData(GL.GL_SHADER_STORAGE_BUFFER, 0, neg_inf.nbytes, neg_inf)

        # 2) Dispatch cull compute
        GL.glUniformMatrix4fv(self.loc_view, 1, GL.GL_FALSE, view.T)
        GL.glUniform1f(self.loc_near, 0.1)
        GL.glUniform1f(self.loc_far, 1000.0)
        GL.glUniform1ui(self.loc_triCount, count)

        local_size = 256
        groups = (count + local_size - 1) // local_size
        GL.glDispatchCompute(groups, 1, 1)
        GL.glMemoryBarrier(GL.GL_SHADER_STORAGE_BARRIER_BIT |
                           GL.GL_ATOMIC_COUNTER_BARRIER_BIT)

        # 3) Read back visible count
        GL.glBindBuffer(GL.GL_ATOMIC_COUNTER_BUFFER, counter_buf)
        counter_data = (ctypes.c_uint * 1)()  # NOQA
        GL.glGetBufferSubData(GL.GL_ATOMIC_COUNTER_BUFFER, 0,
                              ctypes.sizeof(counter_data), counter_data)
        visible_count = int(counter_data[0])

        if visible_count == 0:
            return

        sort_size = next_power_of_two(visible_count)
        GL.glUniform1ui(self.loc_sortSize, sort_size)
        k = 2
        while k <= sort_size:
            j = k // 2
            while j >= 1:
                GL.glUniform1ui(self.loc_k, k)
                GL.glUniform1ui(self.loc_j, j)
                groups = (sort_size + local_size - 1) // local_size
                GL.glDispatchCompute(groups, 1, 1)
                GL.glMemoryBarrier(GL.GL_SHADER_STORAGE_BARRIER_BIT)
                j //= 2
            k *= 2

        # 5) Reorder into output VBOs according to
        # sorted indices (also write normals)
        GL.glUniform1ui(self.loc_outCount, visible_count)
        groups = (visible_count + local_size - 1) // local_size
        GL.glDispatchCompute(groups, 1, 1)
        GL.glMemoryBarrier(GL.GL_SHADER_STORAGE_BARRIER_BIT |
                           GL.GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT)

        GL.glUseProgram(self.render_prog)
        GL.glUniformMatrix4fv(self.loc_vp, 1, GL.GL_FALSE, vp.T)
        GL.glUniformMatrix4fv(self.loc_view_render, 1, GL.GL_FALSE, view.T)

        GL.glBindVertexArray(vao)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, visible_count * 3)
