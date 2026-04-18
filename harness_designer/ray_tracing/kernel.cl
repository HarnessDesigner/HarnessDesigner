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
    if (u < 0.0f || u > 1.0f) return false;

    float q_x = s_y * edge1_z - s_z * edge1_y;
    float q_y = s_z * edge1_x - s_x * edge1_z;
    float q_z = s_x * edge1_y - s_y * edge1_x;

    float v = f * (dir_x * q_x + dir_y * q_y + dir_z * q_z);
    if (v < 0.0f || u + v > 1.0f) return false;

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
    float inv_dir_x = 1.0f / dir_x;
    float inv_dir_y = 1.0f / dir_y;
    float inv_dir_z = 1.0f / dir_z;

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
    float inv_dir_x = 1.0f / dir_x;
    float inv_dir_y = 1.0f / dir_y;
    float inv_dir_z = 1.0f / dir_z;

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
    float shadow_softness
) {
    int x = get_global_id(0);
    int y = get_global_id(1) + start_y;

    if (x >= width || y >= end_y || y >= height) return;

    uint seed = (y * width + x) * 1103515245u + 12345u;

    float px = (2.0f * (x + 0.5f) / width - 1.0f) * aspect_ratio * scale;
    float py = (1.0f - 2.0f * (y + 0.5f) / height) * scale;

    float ray_dir_x = forward_x + right_x * px + up_x * py;
    float ray_dir_y = forward_y + right_y * px + up_y * py;
    float ray_dir_z = forward_z + right_z * px + up_z * py;

    float len = sqrt(ray_dir_x*ray_dir_x + ray_dir_y*ray_dir_y + ray_dir_z*ray_dir_z);
    ray_dir_x /= len;
    ray_dir_y /= len;
    ray_dir_z /= len;

    // Traverse BVH
    float min_dist;
    int hit_face;
    bool hit = traverse_bvh(bvh_bounds, bvh_structure, bvh_indices, vertices, faces,
                           cam_x, cam_y, cam_z,
                           ray_dir_x, ray_dir_y, ray_dir_z,
                           &min_dist, &hit_face);

    int pixel_idx = ((y - start_y) * width + x) * 3;

    // Background
    if (!hit) {
        if (enable_environment_map && environment_map != 0) {
            float3 env_color = sample_environment(environment_map, env_width, env_height,
                                                  ray_dir_x, ray_dir_y, ray_dir_z);
            image[pixel_idx + 0] = env_color.x;
            image[pixel_idx + 1] = env_color.y;
            image[pixel_idx + 2] = env_color.z;
        } else if (enable_gradient) {
            float t = (ray_dir_y + 1.0f) * 0.5f;
            t = clamp(t, 0.0f, 1.0f);

            image[pixel_idx + 0] = bg_bottom_r + (bg_top_r - bg_bottom_r) * t;
            image[pixel_idx + 1] = bg_bottom_g + (bg_top_g - bg_bottom_g) * t;
            image[pixel_idx + 2] = bg_bottom_b + (bg_top_b - bg_bottom_b) * t;
        } else {
            image[pixel_idx + 0] = bg_top_r;
            image[pixel_idx + 1] = bg_top_g;
            image[pixel_idx + 2] = bg_top_b;
        }
        return;
    }

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

    float hit_x = cam_x + ray_dir_x * min_dist;
    float hit_y = cam_y + ray_dir_y * min_dist;
    float hit_z = cam_z + ray_dir_z * min_dist;

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

    // Lighting
    float total_diffuse = 0.0f;
    float total_specular = 0.0f;

    for (int i = 0; i < num_lights; i++) {
        Light light = lights[i];

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
            float shadow_orig_x = hit_x + normal_x * 0.001f;
            float shadow_orig_y = hit_y + normal_y * 0.001f;
            float shadow_orig_z = hit_z + normal_z * 0.001f;

            in_shadow = is_occluded(bvh_bounds, bvh_structure, bvh_indices, vertices, faces,
                                   shadow_orig_x, shadow_orig_y, shadow_orig_z,
                                   light_dir_x, light_dir_y, light_dir_z,
                                   light_dist);
        }

        if (!in_shadow) {
            // Diffuse
            float n_dot_l = fmax(0.0f, normal_x*light_dir_x + normal_y*light_dir_y + normal_z*light_dir_z);
            total_diffuse += n_dot_l * light.intensity * mat.diffuse;

            // Specular (Blinn-Phong)
            float half_x = light_dir_x - ray_dir_x;
            float half_y = light_dir_y - ray_dir_y;
            float half_z = light_dir_z - ray_dir_z;
            float half_len = sqrt(half_x*half_x + half_y*half_y + half_z*half_z);
            half_x /= half_len;
            half_y /= half_len;
            half_z /= half_len;

            float n_dot_h = fmax(0.0f, normal_x*half_x + normal_y*half_y + normal_z*half_z);
            float spec_power = pow(n_dot_h, mat.shininess);
            total_specular += spec_power * light.intensity * mat.specular;
        }
    }

    // Reflection
    float3 reflection_color = (float3)(0, 0, 0);
    if (enable_reflections && mat.reflectivity > 0.01f) {
        float n_dot_v = normal_x*(-ray_dir_x) + normal_y*(-ray_dir_y) + normal_z*(-ray_dir_z);
        float reflect_x = ray_dir_x + 2.0f * n_dot_v * normal_x;
        float reflect_y = ray_dir_y + 2.0f * n_dot_v * normal_y;
        float reflect_z = ray_dir_z + 2.0f * n_dot_v * normal_z;

        if (enable_environment_map && environment_map != 0) {
            reflection_color = sample_environment(environment_map, env_width, env_height,
                                                 reflect_x, reflect_y, reflect_z);
        } else if (enable_gradient) {
            float t = (reflect_y + 1.0f) * 0.5f;
            t = clamp(t, 0.0f, 1.0f);
            reflection_color.x = bg_bottom_r + (bg_top_r - bg_bottom_r) * t;
            reflection_color.y = bg_bottom_g + (bg_top_g - bg_bottom_g) * t;
            reflection_color.z = bg_bottom_b + (bg_top_b - bg_bottom_b) * t;
        }
    }

    // Fresnel effect
    float fresnel = 0.0f;
    if (mat.reflectivity > 0.01f) {
        float n_dot_v = fabs(normal_x*(-ray_dir_x) + normal_y*(-ray_dir_y) + normal_z*(-ray_dir_z));
        float f0 = mat.reflectivity;
        fresnel = f0 + (1.0f - f0) * pow(1.0f - n_dot_v, 5.0f);
    }

    // Combine all lighting
    float ambient = mat.ambient * ambient_intensity * ao;

    float base_r = mat.r * (ambient + total_diffuse);
    float base_g = mat.g * (ambient + total_diffuse);
    float base_b = mat.b * (ambient + total_diffuse);

    float final_r = base_r * (1.0f - fresnel) + reflection_color.x * fresnel + total_specular;
    float final_g = base_g * (1.0f - fresnel) + reflection_color.y * fresnel + total_specular;
    float final_b = base_b * (1.0f - fresnel) + reflection_color.z * fresnel + total_specular;

    image[pixel_idx + 0] = clamp(final_r, 0.0f, 1.0f);
    image[pixel_idx + 1] = clamp(final_g, 0.0f, 1.0f);
    image[pixel_idx + 2] = clamp(final_b, 0.0f, 1.0f);
}