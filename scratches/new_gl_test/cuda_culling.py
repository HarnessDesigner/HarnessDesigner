import cupy as cp

kernel_code = r'''
extern "C" __global__
void cull_triangles(
    const float* tris,
    const float* planes,
    const float* cam_pos,
    int* visible,
    float* dist2,
    int tri_count
){
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= tri_count) return;

    const float* t = tris + i * 18;

    // vertices
    float3 v0 = make_float3(t[0], t[1], t[2]);
    float3 v1 = make_float3(t[3], t[4], t[5]);
    float3 v2 = make_float3(t[6], t[7], t[8]);

    // normal
    float3 n = make_float3(t[9], t[10], t[11]);

    // centroid
    float3 c = make_float3(t[12], t[13], t[14]);

    // -------- Frustum culling --------
    for (int p = 0; p < 6; ++p) {
        const float* pl = planes + p * 4;
        float d0 = v0.x*pl[0] + v0.y*pl[1] + v0.z*pl[2] + pl[3];
        float d1 = v1.x*pl[0] + v1.y*pl[1] + v1.z*pl[2] + pl[3];
        float d2 = v2.x*pl[0] + v2.y*pl[1] + v2.z*pl[2] + pl[3];
        if (d0 < 0 && d1 < 0 && d2 < 0) {
            visible[i] = 0;
            return;
        }
    }

    // -------- Back-face culling --------
    float3 view = make_float3(
        c.x - cam_pos[0],
        c.y - cam_pos[1],
        c.z - cam_pos[2]
    );

    float dot = n.x*view.x + n.y*view.y + n.z*view.z;
    if (dot >= 0) {
        visible[i] = 0;
        return;
    }

    // -------- Distance --------
    dist2[i] = view.x*view.x + view.y*view.y + view.z*view.z;
    visible[i] = 1;
}
'''
kernel = cp.RawKernel(kernel_code, "cull_triangles")

THREADS = 256

blocks = (tri_count + THREADS - 1) // THREADS


def cull(triangles, planes, camera_pos, visible, dist2, triangle_count):
    kernel(
        (blocks,),
        (THREADS,),
        (
            triangles,
            planes,
            camera_pos,
            visible,
            dist2,
            triangle_count
        )
    )

    visible_idx = cp.nonzero(visible)[0]
    visible_tris = triangles[visible_idx]
    visible_dist = dist2[visible_idx]

    order = cp.argsort(visible_dist)
    visible_tris = visible_tris[order]



