// © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

typedef struct {
    float r, g, b;
    float ambient;
    float diffuse;
    float specular;
    float shininess;
    float metallic;
    float roughness;
    float reflectivity;
    float transparency;
    float ior;
} Material;

typedef struct {
    float x, y, z;
    float intensity;
    float r, g, b;
} Light;

// Helper function to get node bounds
void get_node_bounds(
    __global const float* bvh_bounds,
    int node_idx,
    float* min_x, float* min_y, float* min_z,
    float* max_x, float* max_y, float* max_z
) {
    int offset = node_idx * 6;
    *min_x = bvh_bounds[offset + 0];
    *min_y = bvh_bounds[offset + 1];
    *min_z = bvh_bounds[offset + 2];
    *max_x = bvh_bounds[offset + 3];
    *max_y = bvh_bounds[offset + 4];
    *max_z = bvh_bounds[offset + 5];
}

// Helper function to get node structure
void get_node_structure(
    __global const int* bvh_structure,
    int node_idx,
    int* left_child,
    int* right_child,
    int* first_prim,
    int* prim_count
) {
    int offset = node_idx * 4;
    *left_child = bvh_structure[offset + 0];
    *right_child = bvh_structure[offset + 1];
    *first_prim = bvh_structure[offset + 2];
    *prim_count = bvh_structure[offset + 3];
}

// Sample environment map
float3 sample_environment(__global const uchar* env_map, int env_width, int env_height,
                         float dir_x, float dir_y, float dir_z) {
    float phi = atan2(dir_z, dir_x);
    float theta = asin(clamp(dir_y, -1.0f, 1.0f));

    float u = 0.5f + phi / (2.0f * M_PI);
    float v = 0.5f - theta / M_PI;

    int tex_x = ((int)(u * env_width)) % env_width;
    int tex_y = ((int)(v * env_height)) % env_height;

    if (tex_x < 0) tex_x += env_width;
    if (tex_y < 0) tex_y += env_height;

    int tex_idx = (tex_y * env_width + tex_x) * 3;

    float3 color;
    color.x = env_map[tex_idx + 0] / 255.0f;
    color.y = env_map[tex_idx + 1] / 255.0f;
    color.z = env_map[tex_idx + 2] / 255.0f;

    return color;
}

// Reciprocal that stays finite for a direction component of exactly zero
float safe_inverse(float v) {
    return 1.0f / (fabs(v) < 1e-12f ? copysign(1e-12f, v) : v);
}

// Ray-AABB intersection
bool intersect_aabb(
    float orig_x, float orig_y, float orig_z,
    float dir_x, float dir_y, float dir_z,
    float inv_dir_x, float inv_dir_y, float inv_dir_z,
    float min_x, float min_y, float min_z,
    float max_x, float max_y, float max_z,
    float t_max
) {
    float t1 = (min_x - orig_x) * inv_dir_x;
    float t2 = (max_x - orig_x) * inv_dir_x;
    float tmin = fmin(t1, t2);
    float tmax = fmax(t1, t2);

    t1 = (min_y - orig_y) * inv_dir_y;
    t2 = (max_y - orig_y) * inv_dir_y;
    tmin = fmax(tmin, fmin(t1, t2));
    tmax = fmin(tmax, fmax(t1, t2));

    t1 = (min_z - orig_z) * inv_dir_z;
    t2 = (max_z - orig_z) * inv_dir_z;
    tmin = fmax(tmin, fmin(t1, t2));
    tmax = fmin(tmax, fmax(t1, t2));

    return tmax >= fmax(0.0f, tmin) && tmin < t_max;
}

// How far past a triangle's edge (in barycentric units) a ray still counts as hitting it. Rounding in the
// test can put a ray that crosses the shared edge of two triangles outside both; for a long thin triangle
// (a wire is 0.03 mm wide and hundreds of mm long) that error is large in the narrow direction. A ray
// that slips through such a crack sees the inside of the far wall instead of the surface. Neighbouring
// triangles overlapping by this much costs nothing, since the nearest hit wins. (The bigger cause of such
// cracks is a far-away ray origin, see ``approach_origin``.)
#define BARY_EPS 1e-5f

// Ray-triangle intersection (Möller-Trumbore)
bool intersect_triangle(
    float orig_x, float orig_y, float orig_z,
    float dir_x, float dir_y, float dir_z,
    float v0_x, float v0_y, float v0_z,
    float v1_x, float v1_y, float v1_z,
    float v2_x, float v2_y, float v2_z,
    float* t_out
) {
    float edge1_x = v1_x - v0_x;
    float edge1_y = v1_y - v0_y;
    float edge1_z = v1_z - v0_z;

    float edge2_x = v2_x - v0_x;
    float edge2_y = v2_y - v0_y;
    float edge2_z = v2_z - v0_z;

    float h_x = dir_y * edge2_z - dir_z * edge2_y;
    float h_y = dir_z * edge2_x - dir_x * edge2_z;
    float h_z = dir_x * edge2_y - dir_y * edge2_x;

    float a = edge1_x * h_x + edge1_y * h_y + edge1_z * h_z;

    if (fabs(a) < 1e-8f) return false;

    float f = 1.0f / a;
    float s_x = orig_x - v0_x;
    float s_y = orig_y - v0_y;
    float s_z = orig_z - v0_z;

    float u = f * (s_x * h_x + s_y * h_y + s_z * h_z);
    if (u < -BARY_EPS || u > 1.0f + BARY_EPS) return false;

    float q_x = s_y * edge1_z - s_z * edge1_y;
    float q_y = s_z * edge1_x - s_x * edge1_z;
    float q_z = s_x * edge1_y - s_y * edge1_x;

    float v = f * (dir_x * q_x + dir_y * q_y + dir_z * q_z);
    if (v < -BARY_EPS || u + v > 1.0f + BARY_EPS) return false;

    float t = f * (edge2_x * q_x + edge2_y * q_y + edge2_z * q_z);

    if (t > 1e-8f) {
        *t_out = t;
        return true;
    }

    return false;
}

// BVH traversal - closest hit
bool traverse_bvh(
    __global const float* bvh_bounds,
    __global const int* bvh_structure,
    __global const int* bvh_indices,
    __global const float* vertices,
    __global const int* faces,
    float orig_x, float orig_y, float orig_z,
    float dir_x, float dir_y, float dir_z,
    float* t_out,
    int* face_out
) {
    float inv_dir_x = safe_inverse(dir_x);
    float inv_dir_y = safe_inverse(dir_y);
    float inv_dir_z = safe_inverse(dir_z);

    int stack[64];
    int stack_ptr = 0;
    stack[stack_ptr++] = 0;  // Start with root

    float closest_t = 1e10f;
    int closest_face = -1;

    while (stack_ptr > 0) {
        int node_idx = stack[--stack_ptr];

        // Get node bounds
        float min_x, min_y, min_z, max_x, max_y, max_z;
        get_node_bounds(bvh_bounds, node_idx, &min_x, &min_y, &min_z, &max_x, &max_y, &max_z);

        // Check if ray intersects this node's AABB
        if (!intersect_aabb(orig_x, orig_y, orig_z,
                           dir_x, dir_y, dir_z,
                           inv_dir_x, inv_dir_y, inv_dir_z,
                           min_x, min_y, min_z,
                           max_x, max_y, max_z,
                           closest_t)) {
            continue;
        }

        // Get node structure
        int left_child, right_child, first_prim, prim_count;
        get_node_structure(bvh_structure, node_idx, &left_child, &right_child, &first_prim, &prim_count);

        // Leaf node - test primitives
        if (left_child == -1) {
            for (int i = 0; i < prim_count; i++) {
                int face_idx = bvh_indices[first_prim + i];

                int idx0 = faces[face_idx * 3 + 0] * 3;
                int idx1 = faces[face_idx * 3 + 1] * 3;
                int idx2 = faces[face_idx * 3 + 2] * 3;

                float t;
                if (intersect_triangle(
                    orig_x, orig_y, orig_z,
                    dir_x, dir_y, dir_z,
                    vertices[idx0 + 0], vertices[idx0 + 1], vertices[idx0 + 2],
                    vertices[idx1 + 0], vertices[idx1 + 1], vertices[idx1 + 2],
                    vertices[idx2 + 0], vertices[idx2 + 1], vertices[idx2 + 2],
                    &t
                )) {
                    if (t < closest_t) {
                        closest_t = t;
                        closest_face = face_idx;
                    }
                }
            }
        } else {
            // Internal node - add children to stack
            if (right_child != -1 && stack_ptr < 63) {
                stack[stack_ptr++] = right_child;
            }
            if (left_child != -1 && stack_ptr < 63) {
                stack[stack_ptr++] = left_child;
            }
        }
    }

    if (closest_face != -1) {
        *t_out = closest_t;
        *face_out = closest_face;
        return true;
    }

    return false;
}

// Shadow ray (any-hit)
bool is_occluded(
    __global const float* bvh_bounds,
    __global const int* bvh_structure,
    __global const int* bvh_indices,
    __global const float* vertices,
    __global const int* faces,
    float orig_x, float orig_y, float orig_z,
    float dir_x, float dir_y, float dir_z,
    float max_dist
) {
    float inv_dir_x = safe_inverse(dir_x);
    float inv_dir_y = safe_inverse(dir_y);
    float inv_dir_z = safe_inverse(dir_z);

    int stack[64];
    int stack_ptr = 0;
    stack[stack_ptr++] = 0;

    while (stack_ptr > 0) {
        int node_idx = stack[--stack_ptr];

        // Get node bounds
        float min_x, min_y, min_z, max_x, max_y, max_z;
        get_node_bounds(bvh_bounds, node_idx, &min_x, &min_y, &min_z, &max_x, &max_y, &max_z);

        if (!intersect_aabb(orig_x, orig_y, orig_z,
                           dir_x, dir_y, dir_z,
                           inv_dir_x, inv_dir_y, inv_dir_z,
                           min_x, min_y, min_z,
                           max_x, max_y, max_z,
                           max_dist)) {
            continue;
        }

        // Get node structure
        int left_child, right_child, first_prim, prim_count;
        get_node_structure(bvh_structure, node_idx, &left_child, &right_child, &first_prim, &prim_count);

        if (left_child == -1) {
            for (int i = 0; i < prim_count; i++) {
                int face_idx = bvh_indices[first_prim + i];

                int idx0 = faces[face_idx * 3 + 0] * 3;
                int idx1 = faces[face_idx * 3 + 1] * 3;
                int idx2 = faces[face_idx * 3 + 2] * 3;

                float t;
                if (intersect_triangle(
                    orig_x, orig_y, orig_z,
                    dir_x, dir_y, dir_z,
                    vertices[idx0 + 0], vertices[idx0 + 1], vertices[idx0 + 2],
                    vertices[idx1 + 0], vertices[idx1 + 1], vertices[idx1 + 2],
                    vertices[idx2 + 0], vertices[idx2 + 1], vertices[idx2 + 2],
                    &t
                )) {
                    if (t > 1e-4f && t < max_dist - 1e-4f) {
                        return true;  // Any hit is enough for shadows
                    }
                }
            }
        } else {
            if (right_child != -1 && stack_ptr < 63) {
                stack[stack_ptr++] = right_child;
            }
            if (left_child != -1 && stack_ptr < 63) {
                stack[stack_ptr++] = left_child;
            }
        }
    }

    return false;
}

// Ambient occlusion
float calculate_ao(
    __global const float* bvh_bounds,
    __global const int* bvh_structure,
    __global const int* bvh_indices,
    __global const float* vertices,
    __global const int* faces,
    float point_x, float point_y, float point_z,
    float normal_x, float normal_y, float normal_z,
    float radius,
    int samples,
    uint* seed
) {
    float occlusion = 0.0f;

    for (int i = 0; i < samples; i++) {
        *seed = (*seed * 1103515245u + 12345u);
        float r1 = (*seed & 0x7FFFFFFF) / (float)0x7FFFFFFF;
        *seed = (*seed * 1103515245u + 12345u);
        float r2 = (*seed & 0x7FFFFFFF) / (float)0x7FFFFFFF;

        float phi = 2.0f * M_PI * r1;
        float cos_theta = sqrt(1.0f - r2);
        float sin_theta = sqrt(r2);

        float sample_x = cos(phi) * sin_theta;
        float sample_y = sin(phi) * sin_theta;
        float sample_z = cos_theta;

        float3 up = (float3)(0, 1, 0);
        if (fabs(normal_y) > 0.999f) up = (float3)(1, 0, 0);

        float3 tangent;
        tangent.x = up.y * normal_z - up.z * normal_y;
        tangent.y = up.z * normal_x - up.x * normal_z;
        tangent.z = up.x * normal_y - up.y * normal_x;
        float len = sqrt(tangent.x*tangent.x + tangent.y*tangent.y + tangent.z*tangent.z);
        tangent.x /= len;
        tangent.y /= len;
        tangent.z /= len;

        float3 bitangent;
        bitangent.x = normal_y * tangent.z - normal_z * tangent.y;
        bitangent.y = normal_z * tangent.x - normal_x * tangent.z;
        bitangent.z = normal_x * tangent.y - normal_y * tangent.x;

        float dir_x = tangent.x * sample_x + bitangent.x * sample_y + normal_x * sample_z;
        float dir_y = tangent.y * sample_x + bitangent.y * sample_y + normal_y * sample_z;
        float dir_z = tangent.z * sample_x + bitangent.z * sample_y + normal_z * sample_z;

        float start_x = point_x + normal_x * 0.001f;
        float start_y = point_y + normal_y * 0.001f;
        float start_z = point_z + normal_z * 0.001f;

        if (is_occluded(bvh_bounds, bvh_structure, bvh_indices, vertices, faces,
                       start_x, start_y, start_z,
                       dir_x, dir_y, dir_z,
                       radius)) {
            occlusion += 1.0f;
        }
    }

    return 1.0f - (occlusion / samples);
}

// Distance along the ray to where it first meets the scene's bounding box (the BVH root), less a margin;
// 0 when the origin is already inside or the box is behind it. A ray that misses the box returns false.
//
// Every triangle test subtracts a vertex from the ray origin, so with the camera tens of metres from the
// model each of those subtractions is off by the rounding at that distance (about 2e-3 mm at 30 m), which
// is about as wide as a wire's thin triangles: the test then misses the surface and the ray finds the
// inside of the far wall (black speckles, worse the further out you zoom). Starting the ray at the model
// keeps the arithmetic at the model's own scale.
bool approach_distance(
    __global const float* bvh_bounds,
    float orig_x, float orig_y, float orig_z,
    float dir_x, float dir_y, float dir_z,
    float* start_out
) {
    float min_x, min_y, min_z, max_x, max_y, max_z;
    get_node_bounds(bvh_bounds, 0, &min_x, &min_y, &min_z, &max_x, &max_y, &max_z);

    float t1 = (min_x - orig_x) * safe_inverse(dir_x);
    float t2 = (max_x - orig_x) * safe_inverse(dir_x);
    float tmin = fmin(t1, t2);
    float tmax = fmax(t1, t2);

    t1 = (min_y - orig_y) * safe_inverse(dir_y);
    t2 = (max_y - orig_y) * safe_inverse(dir_y);
    tmin = fmax(tmin, fmin(t1, t2));
    tmax = fmin(tmax, fmax(t1, t2));

    t1 = (min_z - orig_z) * safe_inverse(dir_z);
    t2 = (max_z - orig_z) * safe_inverse(dir_z);
    tmin = fmax(tmin, fmin(t1, t2));
    tmax = fmin(tmax, fmax(t1, t2));

    if (tmax < 0.0f || tmax < tmin) return false;

    float extent = fmax(max_x - min_x, fmax(max_y - min_y, max_z - min_z));
    *start_out = fmax(0.0f, tmin - 0.01f * extent - 1.0f);
    return true;
}

// ---- Multisampling ----------------------------------------------------------
// Each pass of a render looks through a different point inside every pixel and the passes are averaged.

float fraction(float v) {
    return v - floor(v);
}

// Offset inside the pixel for pass ``sample_index`` of ``sample_count``: the R2 low-discrepancy sequence, shifted
// by a per-pixel random amount so neighbouring pixels do not share one pattern. A single pass samples the
// pixel centre.
float2 pixel_jitter(int x, int y, int width, int sample_index, int sample_count) {
    if (sample_count <= 1) return (float2)(0.5f, 0.5f);

    uint h = (uint)(y * width + x) * 747796405u + 2891336453u;
    h = ((h >> ((h >> 28u) + 4u)) ^ h) * 277803737u;
    h = (h >> 22u) ^ h;

    float shift_x = (float)(h & 0xFFFFu) / 65536.0f;
    float shift_y = (float)((h >> 16) & 0xFFFFu) / 65536.0f;
    float k = (float)(sample_index + 1);

    return (float2)(fraction(0.7548776662f * k + shift_x), fraction(0.5698402910f * k + shift_y));
}

// Write one pass's colour: the first pass stores it, later passes fold it into the running average. A
// colour that is not a number (a degenerate triangle, a zero-length vector) is dropped instead of
// turning the pixel black for good.
void store_pixel(__global float* image, int index, float3 color, int sample_index) {
    if (!isfinite(color.x) || !isfinite(color.y) || !isfinite(color.z)) {
        if (sample_index == 0) {
            image[index + 0] = 0.0f;
            image[index + 1] = 0.0f;
            image[index + 2] = 0.0f;
        }
        return;
    }

    color = clamp(color, 0.0f, 1.0f);

    if (sample_index == 0) {
        image[index + 0] = color.x;
        image[index + 1] = color.y;
        image[index + 2] = color.z;
        return;
    }

    float weight = 1.0f / (float)(sample_index + 1);
    image[index + 0] += (color.x - image[index + 0]) * weight;
    image[index + 1] += (color.y - image[index + 1]) * weight;
    image[index + 2] += (color.z - image[index + 2]) * weight;
}

// ---- Viewport floor ------------------------------------------------------
// The 3D editor's floor (gl/shaders/floor/fragment.frag) as a plane: checkerboard tiles, solid major
// lines at the tile edges and dashed minor lines between them. ``fw`` is the world size of a pixel
// on the floor, which anti-aliases the lines and fades the pattern out where it gets finer than a pixel.

float positive_mod(float a, float b) {
    return a - b * floor(a / b);
}

float line_coverage(float coord, float spacing, float half_w, float fw) {
    float f = coord / spacing;
    f = f - floor(f);
    float dist = fmin(f, 1.0f - f) * spacing;
    float hw = fmax(half_w, fw);
    float coverage = fmin(half_w / fw, 1.0f);
    return (1.0f - smoothstep(hw - fw, hw + fw, dist)) * coverage;
}

// Sub-samples per axis the floor pattern is averaged over in each pixel (FLOOR_SAMPLES x FLOOR_SAMPLES).
// The pattern is cheap to evaluate (no BVH), and averaging it is what keeps fine tiles and lines from
// turning into moire.
#define FLOOR_SAMPLES 4

// Where the ray through pixel position (pixel_x, pixel_y) meets the floor plane, if it does inside the floor.
bool floor_intersect(
    float cam_x, float cam_y, float cam_z,
    float forward_x, float forward_y, float forward_z,
    float right_x, float right_y, float right_z,
    float up_x, float up_y, float up_z,
    float scale, float aspect_ratio, int width, int height,
    float floor_y, float half_size, float pixel_x, float pixel_y,
    float* out_x, float* out_z, float* out_t
) {
    float px = (2.0f * pixel_x / width - 1.0f) * aspect_ratio * scale;
    float py = (1.0f - 2.0f * pixel_y / height) * scale;

    float dx = forward_x + right_x * px + up_x * py;
    float dy = forward_y + right_y * px + up_y * py;
    float dz = forward_z + right_z * px + up_z * py;

    float len = sqrt(dx * dx + dy * dy + dz * dz);
    dx /= len;
    dy /= len;
    dz /= len;

    if (fabs(dy) < 1e-6f) return false;

    float t = (floor_y - cam_y) / dy;
    if (t <= 1e-4f) return false;

    float x = cam_x + dx * t;
    float z = cam_z + dz * t;
    if (fabs(x) > half_size || fabs(z) > half_size) return false;

    *out_x = x;
    *out_z = z;
    *out_t = t;
    return true;
}

// The floor at world position (wx, wz). ``fwx`` / ``fwz`` are how far the sample's footprint reaches along
// each axis (GLSL fwidth), which anti-aliases the lines and fades the tiles and the dash pattern to their
// average where they are finer than the footprint.
float4 floor_color(
    __global const float* fp, uint stipple_pattern, int stipple_phase,
    float wx, float wz, float fwx, float fwz
) {
    float tile = fp[3];
    float minor_spacing = fp[4];
    int has_minor = fp[5] > 0.5f;
    float major_width = fp[6];
    float minor_width = fp[7];

    float4 color_a = (float4)(fp[8], fp[9], fp[10], fp[11]);
    float4 color_b = (float4)(fp[12], fp[13], fp[14], fp[15]);
    float4 major_color = (float4)(fp[16], fp[17], fp[18], fp[19]);
    float4 minor_color = (float4)(fp[20], fp[21], fp[22], fp[23]);

    float fw_max = fmax(fwx, fwz);

    float tx = floor(wx / tile);
    float tz = floor(wz / tile);
    float4 checker = (positive_mod(tx + tz, 2.0f) < 0.5f) ? color_a : color_b;

    float tile_fade = smoothstep(0.25f, 1.0f, fw_max / tile);
    float3 tile_color = mix(checker.xyz, (color_a.xyz + color_b.xyz) * 0.5f, tile_fade);

    float major = fmax(line_coverage(wx, tile, major_width * 0.5f, fwx),
                       line_coverage(wz, tile, major_width * 0.5f, fwz));

    float minor = 0.0f;
    if (has_minor) {
        float min_hw = minor_width * 0.5f;
        float min_fade = 1.0f - smoothstep(0.25f, 1.0f, fw_max / minor_spacing);

        // One bit of the dash pattern is tile / 32 long; once that is finer than the footprint the dashes
        // are just a lighter line, so use the pattern's average coverage instead.
        float bit_length = tile / 32.0f;
        float dash_average = (float)popcount(stipple_pattern) / 32.0f;

        float near_x = line_coverage(wz, minor_spacing, min_hw, fwz);
        float shift_x = (float)stipple_phase * positive_mod(round(wz / minor_spacing), 2.0f) * tile * 0.5f;
        float seg_x = positive_mod(wx + shift_x, tile) / tile;
        uint bit_x = min((uint)(seg_x * 32.0f), 31u);
        float dash_x = mix((float)((stipple_pattern >> bit_x) & 1u), dash_average,
                           smoothstep(0.5f, 1.5f, fwx / bit_length));

        float near_z = line_coverage(wx, minor_spacing, min_hw, fwx);
        float shift_z = (float)stipple_phase * positive_mod(round(wx / minor_spacing), 2.0f) * tile * 0.5f;
        float seg_z = positive_mod(wz + shift_z, tile) / tile;
        uint bit_z = min((uint)(seg_z * 32.0f), 31u);
        float dash_z = mix((float)((stipple_pattern >> bit_z) & 1u), dash_average,
                           smoothstep(0.5f, 1.5f, fwz / bit_length));

        minor = fmax(near_x * dash_x, near_z * dash_z) * min_fade;
    }

    float3 color = mix(tile_color, minor_color.xyz, minor);
    color = mix(color, major_color.xyz, major);

    float alpha = mix(checker.w, minor_color.w, minor);
    alpha = mix(alpha, major_color.w, major);

    return (float4)(color, alpha);
}

// Shade the surface a ray hit: ambient (with optional occlusion), every light (with shadows), specular,
// and the material's own reflection. ``cam_*`` is the ray's origin and ``ray_dir_*`` its direction.
// With ``mirror`` set the lights are mirrored in the plane y = ``mirror_y``, for a reflection in the floor.
float3 shade_hit(
    __global const float* vertices,
    __global const float* vertex_normals,
    int has_vertex_normals,
    __global const int* faces,
    __global const int* object_ids,
    __global const Material* materials,
    __global const Light* lights,
    int num_lights,
    __global const float* bvh_bounds,
    __global const int* bvh_structure,
    __global const int* bvh_indices,
    int hit_face,
    float min_dist,
    float cam_x, float cam_y, float cam_z,
    float ray_dir_x, float ray_dir_y, float ray_dir_z,
    float ambient_intensity,
    float bg_top_r, float bg_top_g, float bg_top_b,
    float bg_bottom_r, float bg_bottom_g, float bg_bottom_b,
    __global const uchar* environment_map,
    int env_width,
    int env_height,
    int enable_gradient,
    int enable_environment_map,
    int enable_reflections,
    int enable_shadows,
    int enable_ambient_occlusion,
    float ao_samples,
    float ao_radius,
    uint seed_in,
    int mirror,
    float mirror_y
) {
    uint seed = seed_in;

    // Hit something
    int object_id = object_ids[hit_face];
    Material mat = materials[object_id];

    // Calculate hit point and normal
    int idx0 = faces[hit_face * 3 + 0] * 3;
    int idx1 = faces[hit_face * 3 + 1] * 3;
    int idx2 = faces[hit_face * 3 + 2] * 3;

    float v0_x = vertices[idx0 + 0];
    float v0_y = vertices[idx0 + 1];
    float v0_z = vertices[idx0 + 2];

    float v1_x = vertices[idx1 + 0];
    float v1_y = vertices[idx1 + 1];
    float v1_z = vertices[idx1 + 2];

    float v2_x = vertices[idx2 + 0];
    float v2_y = vertices[idx2 + 1];
    float v2_z = vertices[idx2 + 2];

    float edge1_x = v1_x - v0_x;
    float edge1_y = v1_y - v0_y;
    float edge1_z = v1_z - v0_z;

    float edge2_x = v2_x - v0_x;
    float edge2_y = v2_y - v0_y;
    float edge2_z = v2_z - v0_z;

    float normal_x = edge1_y * edge2_z - edge1_z * edge2_y;
    float normal_y = edge1_z * edge2_x - edge1_x * edge2_z;
    float normal_z = edge1_x * edge2_y - edge1_y * edge2_x;

    float normal_len = sqrt(normal_x*normal_x + normal_y*normal_y + normal_z*normal_z);
    normal_x /= normal_len;
    normal_y /= normal_len;
    normal_z /= normal_len;

    // Kept as it is for the barycentric weights below (normal_len is twice the triangle's area).
    float geo_x = normal_x;
    float geo_y = normal_y;
    float geo_z = normal_z;
    float double_area = normal_len;

    // Triangle winding is not guaranteed, so face the normal toward the viewer
    if (normal_x*ray_dir_x + normal_y*ray_dir_y + normal_z*ray_dir_z > 0.0f) {
        normal_x = -normal_x;
        normal_y = -normal_y;
        normal_z = -normal_z;
    }

    float hit_x = cam_x + ray_dir_x * min_dist;
    float hit_y = cam_y + ray_dir_y * min_dist;
    float hit_z = cam_z + ray_dir_z * min_dist;

    // Origin + direction * distance cannot place the hit better than about a float's rounding at that
    // distance (~2e-3 mm at 30 m), which is more than a thin wire's shadow offset: the shadow ray then
    // starts inside the wire and hits its own far wall, so the pixel loses its direct light and the wire
    // turns speckled with dark spots the further away it is. Snap the point back onto the triangle's own
    // plane (the vertices are near the geometry, so their precision does not depend on the camera) ...
    float plane_distance = (hit_x - v0_x) * normal_x + (hit_y - v0_y) * normal_y + (hit_z - v0_z) * normal_z;
    hit_x -= normal_x * plane_distance;
    hit_y -= normal_y * plane_distance;
    hit_z -= normal_z * plane_distance;

    // ... and lift shadow rays off it by more than the rounding of the coordinates they start from.
    float shadow_bias = fmax(1e-3f, 1e-6f * fmax(fabs(hit_x), fmax(fabs(hit_y), fabs(hit_z))));

    // The normal the surface is shaded with: the face normal, or, for an object drawn smooth in the viewport,
    // its vertex normals blended by where in the triangle the ray hit (what the rasterizer interpolates).
    // Rays are still offset along the face normal, which is the one that is exact for the geometry.
    float shade_x = normal_x;
    float shade_y = normal_y;
    float shade_z = normal_z;

    if (has_vertex_normals && double_area > 0.0f) {
        float p_x = hit_x - v0_x;
        float p_y = hit_y - v0_y;
        float p_z = hit_z - v0_z;

        // Barycentric weights from cross products rather than from dot products: a thin sliver of a
        // triangle (a wire's) loses most of its precision to cancellation in the dot-product form.
        float c1_x = p_y * edge2_z - p_z * edge2_y;
        float c1_y = p_z * edge2_x - p_x * edge2_z;
        float c1_z = p_x * edge2_y - p_y * edge2_x;

        float c2_x = edge1_y * p_z - edge1_z * p_y;
        float c2_y = edge1_z * p_x - edge1_x * p_z;
        float c2_z = edge1_x * p_y - edge1_y * p_x;

        float w1 = clamp((c1_x * geo_x + c1_y * geo_y + c1_z * geo_z) / double_area, 0.0f, 1.0f);
        float w2 = clamp((c2_x * geo_x + c2_y * geo_y + c2_z * geo_z) / double_area, 0.0f, 1.0f);
        float w0 = fmax(0.0f, 1.0f - w1 - w2);

        float w_sum = w0 + w1 + w2;
        w0 /= w_sum;
        w1 /= w_sum;
        w2 /= w_sum;

        float smooth_x = vertex_normals[idx0 + 0] * w0 + vertex_normals[idx1 + 0] * w1 + vertex_normals[idx2 + 0] * w2;
        float smooth_y = vertex_normals[idx0 + 1] * w0 + vertex_normals[idx1 + 1] * w1 + vertex_normals[idx2 + 1] * w2;
        float smooth_z = vertex_normals[idx0 + 2] * w0 + vertex_normals[idx1 + 2] * w1 + vertex_normals[idx2 + 2] * w2;

        float smooth_len = sqrt(smooth_x * smooth_x + smooth_y * smooth_y + smooth_z * smooth_z);

        // No vertex normals (a flat object, or a piece of mesh that was cut) leave a zero vector: keep the face normal.
        if (smooth_len > 1e-4f) {
            smooth_x /= smooth_len;
            smooth_y /= smooth_len;
            smooth_z /= smooth_len;

            // Same side as the face normal, which already faces the viewer.
            if (smooth_x * normal_x + smooth_y * normal_y + smooth_z * normal_z < 0.0f) {
                smooth_x = -smooth_x;
                smooth_y = -smooth_y;
                smooth_z = -smooth_z;
            }

            shade_x = smooth_x;
            shade_y = smooth_y;
            shade_z = smooth_z;
        }
    }

    // Ambient occlusion
    float ao = 1.0f;
    if (enable_ambient_occlusion) {
        ao = calculate_ao(bvh_bounds, bvh_structure, bvh_indices, vertices, faces,
                         hit_x, hit_y, hit_z,
                         normal_x, normal_y, normal_z,
                         ao_radius,
                         (int)ao_samples,
                         &seed);
    }

    // Lighting. The sums are RGB because each light has a colour.
    float3 albedo = (float3)(mat.r, mat.g, mat.b);
    float3 total_diffuse = (float3)(0.0f, 0.0f, 0.0f);
    float3 total_specular = (float3)(0.0f, 0.0f, 0.0f);

    // A dielectric keeps a white highlight; a metal's is tinted by its own colour
    // (the same rule GLMaterial uses for the rasterizer).
    float3 specular_tint = (float3)(1.0f, 1.0f, 1.0f) + mat.metallic * (albedo - (float3)(1.0f, 1.0f, 1.0f));

    for (int i = 0; i < num_lights; i++) {
        Light light = lights[i];
        if (mirror) {
            // A reflection in the floor is lit by the lights as they are mirrored in it.
            light.y = 2.0f * mirror_y - light.y;
        }
        float3 light_color = (float3)(light.r, light.g, light.b);

        float light_dir_x = light.x - hit_x;
        float light_dir_y = light.y - hit_y;
        float light_dir_z = light.z - hit_z;

        float light_dist = sqrt(light_dir_x*light_dir_x + light_dir_y*light_dir_y + light_dir_z*light_dir_z);
        light_dir_x /= light_dist;
        light_dir_y /= light_dist;
        light_dir_z /= light_dist;

        // Check shadows with BVH
        bool in_shadow = false;
        if (enable_shadows) {
            float shadow_orig_x = hit_x + normal_x * shadow_bias;
            float shadow_orig_y = hit_y + normal_y * shadow_bias;
            float shadow_orig_z = hit_z + normal_z * shadow_bias;

            in_shadow = is_occluded(bvh_bounds, bvh_structure, bvh_indices, vertices, faces,
                                   shadow_orig_x, shadow_orig_y, shadow_orig_z,
                                   light_dir_x, light_dir_y, light_dir_z,
                                   light_dist);
        }

        if (!in_shadow) {
            // Diffuse
            float n_dot_l = fmax(0.0f, shade_x*light_dir_x + shade_y*light_dir_y + shade_z*light_dir_z);
            total_diffuse += light_color * (n_dot_l * light.intensity * mat.diffuse);

            // Specular (Blinn-Phong)
            float half_x = light_dir_x - ray_dir_x;
            float half_y = light_dir_y - ray_dir_y;
            float half_z = light_dir_z - ray_dir_z;
            float half_len = sqrt(half_x*half_x + half_y*half_y + half_z*half_z);
            half_x /= half_len;
            half_y /= half_len;
            half_z /= half_len;

            float n_dot_h = fmax(0.0f, shade_x*half_x + shade_y*half_y + shade_z*half_z);
            // The rasterizer uses Phong; a Blinn-Phong exponent of about 4x gives the same highlight size.
            float spec_power = pow(n_dot_h, mat.shininess * 4.0f);
            total_specular += light_color * specular_tint * (spec_power * light.intensity * mat.specular);
        }
    }

    // Reflection
    float3 reflection_color = (float3)(0, 0, 0);
    if (enable_reflections && mat.reflectivity > 0.01f) {
        float n_dot_v = shade_x*(-ray_dir_x) + shade_y*(-ray_dir_y) + shade_z*(-ray_dir_z);
        float reflect_x = ray_dir_x + 2.0f * n_dot_v * shade_x;
        float reflect_y = ray_dir_y + 2.0f * n_dot_v * shade_y;
        float reflect_z = ray_dir_z + 2.0f * n_dot_v * shade_z;

        if (enable_environment_map && environment_map != 0) {
            reflection_color = sample_environment(environment_map, env_width, env_height,
                                                 reflect_x, reflect_y, reflect_z);
        } else if (enable_gradient) {
            float t = (reflect_y + 1.0f) * 0.5f;
            t = clamp(t, 0.0f, 1.0f);
            reflection_color.x = bg_bottom_r + (bg_top_r - bg_bottom_r) * t;
            reflection_color.y = bg_bottom_g + (bg_top_g - bg_bottom_g) * t;
            reflection_color.z = bg_bottom_b + (bg_top_b - bg_bottom_b) * t;
        } else {
            reflection_color = (float3)(bg_top_r, bg_top_g, bg_top_b);
        }
    }

    // A metal's reflection is tinted by its own colour; without this a polished copper or tin
    // conductor reflects the sky unchanged and looks pale blue.
    reflection_color *= (float3)(1.0f, 1.0f, 1.0f) + mat.metallic * (albedo - (float3)(1.0f, 1.0f, 1.0f));

    // Fresnel effect
    float fresnel = 0.0f;
    if (enable_reflections && mat.reflectivity > 0.01f) {
        float n_dot_v = fabs(shade_x*(-ray_dir_x) + shade_y*(-ray_dir_y) + shade_z*(-ray_dir_z));
        float f0 = mat.reflectivity;
        fresnel = f0 + (1.0f - f0) * pow(1.0f - n_dot_v, 5.0f);
    }

    // Combine all lighting
    float ambient = mat.ambient * ambient_intensity * ao;

    float3 base = albedo * (ambient + total_diffuse);
    float3 final_color = base * (1.0f - fresnel) + reflection_color * fresnel + total_specular;

    // On overflow scale all three channels together so the colour keeps its hue; clamping each
    // channel on its own shifts it (the rasterizer's fragment shader does the same).
    float peak = fmax(final_color.x, fmax(final_color.y, final_color.z));
    if (peak > 1.0f) {
        final_color /= peak;
    }

    return final_color;
}

__kernel void ray_trace_kernel(
    __global const float* vertices,
    __global const int* faces,
    __global const int* object_ids,
    __global const Material* materials,
    int num_faces,
    __global const Light* lights,
    int num_lights,
    __global const float* bvh_bounds,
    __global const int* bvh_structure,
    __global const int* bvh_indices,
    __global float* image,
    int width,
    int height,
    float cam_x, float cam_y, float cam_z,
    float center_x, float center_y, float center_z,
    float right_x, float right_y, float right_z,
    float up_x, float up_y, float up_z,
    float forward_x, float forward_y, float forward_z,
    float scale,
    float aspect_ratio,
    int start_y,
    int end_y,
    float ambient_intensity,
    float bg_top_r, float bg_top_g, float bg_top_b,
    float bg_bottom_r, float bg_bottom_g, float bg_bottom_b,
    __global const uchar* environment_map,
    int env_width,
    int env_height,
    int enable_gradient,
    int enable_environment_map,
    int enable_reflections,
    int enable_shadows,
    int enable_ambient_occlusion,
    int enable_depth_of_field,
    float ao_samples,
    float ao_radius,
    float shadow_softness,
    __global const float* floor_params,
    uint stipple_pattern,
    int stipple_phase,
    int sample_index,
    int sample_count,
    __global const float* vertex_normals,
    int has_vertex_normals
) {
    int x = get_global_id(0);
    int y = get_global_id(1) + start_y;

    if (x >= width || y >= end_y || y >= height) return;

    uint seed = (y * width + x) * 1103515245u + 12345u + (uint)sample_index * 2654435761u;

    float2 jitter = pixel_jitter(x, y, width, sample_index, sample_count);
    float jx = jitter.x;
    float jy = jitter.y;

    float px = (2.0f * (x + jx) / width - 1.0f) * aspect_ratio * scale;
    float py = (1.0f - 2.0f * (y + jy) / height) * scale;

    float ray_dir_x = forward_x + right_x * px + up_x * py;
    float ray_dir_y = forward_y + right_y * px + up_y * py;
    float ray_dir_z = forward_z + right_z * px + up_z * py;

    float len = sqrt(ray_dir_x*ray_dir_x + ray_dir_y*ray_dir_y + ray_dir_z*ray_dir_z);
    ray_dir_x /= len;
    ray_dir_y /= len;
    ray_dir_z /= len;

    // Traverse BVH, starting the ray where it reaches the model (see approach_distance). ``min_dist`` is
    // measured from there; ``hit_total`` from the camera.
    float start_t = 0.0f;
    bool reaches_scene = approach_distance(bvh_bounds, cam_x, cam_y, cam_z,
                                           ray_dir_x, ray_dir_y, ray_dir_z, &start_t);
    float ray_ox = cam_x + ray_dir_x * start_t;
    float ray_oy = cam_y + ray_dir_y * start_t;
    float ray_oz = cam_z + ray_dir_z * start_t;

    float min_dist = 0.0f;
    int hit_face = 0;
    bool hit = false;

    if (reaches_scene) {
        hit = traverse_bvh(bvh_bounds, bvh_structure, bvh_indices, vertices, faces,
                           ray_ox, ray_oy, ray_oz,
                           ray_dir_x, ray_dir_y, ray_dir_z,
                           &min_dist, &hit_face);
    }

    float hit_total = start_t + min_dist;

    // The viewport floor: a plane the ray may reach before any geometry (or with none behind it).
    bool floor_in_front = false;
    float floor_hit_x = 0.0f;
    float floor_hit_z = 0.0f;
    float3 floor_rgb = (float3)(0.0f, 0.0f, 0.0f);
    float floor_alpha = 0.0f;

    if (floor_params[0] > 0.5f) {
        float floor_y = floor_params[1];
        float half_size = floor_params[2];
        float wx0, wz0, t0;

        if (floor_intersect(cam_x, cam_y, cam_z, forward_x, forward_y, forward_z,
                            right_x, right_y, right_z, up_x, up_y, up_z,
                            scale, aspect_ratio, width, height, floor_y, half_size,
                            x + jx, y + jy, &wx0, &wz0, &t0) &&
            (!hit || t0 < hit_total)) {

            // How far one pixel reaches along each floor axis (like GLSL fwidth), from the floor point
            // under the neighbouring pixels. Where a neighbour misses the floor, estimate it instead.
            float wx1, wz1, t1, wx2, wz2, t2;
            float fwx, fwz;

            bool next_x = floor_intersect(cam_x, cam_y, cam_z, forward_x, forward_y, forward_z,
                                          right_x, right_y, right_z, up_x, up_y, up_z,
                                          scale, aspect_ratio, width, height, floor_y, half_size,
                                          x + jx + 1.0f, y + jy, &wx1, &wz1, &t1);
            bool next_y = floor_intersect(cam_x, cam_y, cam_z, forward_x, forward_y, forward_z,
                                          right_x, right_y, right_z, up_x, up_y, up_z,
                                          scale, aspect_ratio, width, height, floor_y, half_size,
                                          x + jx, y + jy + 1.0f, &wx2, &wz2, &t2);

            if (next_x && next_y) {
                fwx = fabs(wx1 - wx0) + fabs(wx2 - wx0);
                fwz = fabs(wz1 - wz0) + fabs(wz2 - wz0);
            } else {
                fwx = fwz = t0 * (2.0f * scale / height) / fmax(fabs(ray_dir_y), 0.02f);
            }

            fwx = fmax(fwx, 1e-5f);
            fwz = fmax(fwz, 1e-5f);

            // Average the pattern over the pixel. Colour is summed premultiplied by alpha, so the
            // result composites exactly as the average of the samples would.
            float3 sum_rgb = (float3)(0.0f, 0.0f, 0.0f);
            float sum_alpha = 0.0f;

            // With several passes each one already looks through a different point of the pixel, so the
            // floor needs fewer sub-samples per pass.
            int floor_n = sample_count > 1 ? max(1, FLOOR_SAMPLES / 2) : FLOOR_SAMPLES;

            for (int j = 0; j < floor_n; j++) {
                for (int i = 0; i < floor_n; i++) {
                    float sample_wx, sample_wz, sample_t;

                    if (floor_intersect(cam_x, cam_y, cam_z, forward_x, forward_y, forward_z,
                                        right_x, right_y, right_z, up_x, up_y, up_z,
                                        scale, aspect_ratio, width, height, floor_y, half_size,
                                        x + (i + jx) / floor_n, y + (j + jy) / floor_n,
                                        &sample_wx, &sample_wz, &sample_t)) {
                        float4 fc = floor_color(floor_params, stipple_pattern, stipple_phase,
                                                sample_wx, sample_wz,
                                                fwx / floor_n, fwz / floor_n);
                        sum_rgb += fc.xyz * fc.w;
                        sum_alpha += fc.w;
                    }
                }
            }

            if (sum_alpha > 0.0f) {
                floor_rgb = sum_rgb / sum_alpha;
                floor_alpha = sum_alpha / (floor_n * floor_n);
                floor_in_front = true;
                floor_hit_x = wx0;
                floor_hit_z = wz0;
            }
        }
    }

    // What the floor reflects, as the viewport shows it: the scene mirrored in the floor, seen through
    // the translucent floor at 75% (the rasterizer darkens its mirrored copies by that much).
    bool floor_reflects = false;
    float3 floor_reflection = (float3)(0.0f, 0.0f, 0.0f);

    if (floor_in_front && enable_reflections && cam_y > floor_params[1]) {
        float origin_y = floor_params[1] + 1e-3f;
        float mirror_dir_y = -ray_dir_y;
        float mirror_dist;
        int mirror_face;

        if (traverse_bvh(bvh_bounds, bvh_structure, bvh_indices, vertices, faces,
                         floor_hit_x, origin_y, floor_hit_z,
                         ray_dir_x, mirror_dir_y, ray_dir_z,
                         &mirror_dist, &mirror_face)) {
            floor_reflection = 0.75f * shade_hit(
                vertices, vertex_normals, has_vertex_normals, faces, object_ids, materials, lights, num_lights,
                bvh_bounds, bvh_structure, bvh_indices,
                mirror_face, mirror_dist,
                floor_hit_x, origin_y, floor_hit_z,
                ray_dir_x, mirror_dir_y, ray_dir_z,
                ambient_intensity,
                bg_top_r, bg_top_g, bg_top_b,
                bg_bottom_r, bg_bottom_g, bg_bottom_b,
                environment_map, env_width, env_height,
                enable_gradient, enable_environment_map, enable_reflections, enable_shadows,
                0, ao_samples, ao_radius, seed,
                1, floor_params[1]);
            floor_reflects = true;
        }
    }

    int pixel_idx = ((y - start_y) * width + x) * 3;

    // Background
    if (!hit) {
        float3 background;

        if (enable_environment_map && environment_map != 0) {
            background = sample_environment(environment_map, env_width, env_height,
                                            ray_dir_x, ray_dir_y, ray_dir_z);
        } else if (enable_gradient) {
            float t = (ray_dir_y + 1.0f) * 0.5f;
            t = clamp(t, 0.0f, 1.0f);

            background = (float3)(bg_bottom_r + (bg_top_r - bg_bottom_r) * t,
                                  bg_bottom_g + (bg_top_g - bg_bottom_g) * t,
                                  bg_bottom_b + (bg_top_b - bg_bottom_b) * t);
        } else {
            background = (float3)(bg_top_r, bg_top_g, bg_top_b);
        }

        if (floor_in_front) {
            if (floor_reflects) {
                background = floor_reflection;
            }

            background = mix(background, floor_rgb, floor_alpha);
        }

        store_pixel(image, pixel_idx, background, sample_index);
        return;
    }

    float3 final_color = shade_hit(
        vertices, vertex_normals, has_vertex_normals, faces, object_ids, materials, lights, num_lights,
        bvh_bounds, bvh_structure, bvh_indices,
        hit_face, min_dist,
        ray_ox, ray_oy, ray_oz,
        ray_dir_x, ray_dir_y, ray_dir_z,
        ambient_intensity,
        bg_top_r, bg_top_g, bg_top_b,
        bg_bottom_r, bg_bottom_g, bg_bottom_b,
        environment_map, env_width, env_height,
        enable_gradient, enable_environment_map, enable_reflections, enable_shadows,
        enable_ambient_occlusion, ao_samples, ao_radius, seed,
        0, 0.0f);

    // A translucent floor in front of the geometry lets it show through.
    if (floor_in_front) {
        final_color = mix(final_color, floor_rgb, floor_alpha);
    }

    store_pixel(image, pixel_idx, final_color, sample_index);
}