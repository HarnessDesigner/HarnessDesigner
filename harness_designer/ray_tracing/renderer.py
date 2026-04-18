import os

import pyopencl as cl
import numpy as np
import warnings

from .. import config as _config


# Suppress OpenCL compiler warnings
warnings.filterwarnings('ignore', category=cl.CompilerWarning)

Config = _config.Config.ray_trace


class Renderer:

    def __init__(self, scene, callback):
        self.scene = scene
        self.callback = callback
        self.ctx, self.queue = self.init_cl()
        self.program, self.kernel = self.compile_kernel()

    def init_cl(self):  # NOQA
        # Initialize OpenCL
        platforms = cl.get_platforms()
        if not platforms:
            raise RuntimeError("No OpenCL platforms found")

        for platform in platforms:
            try:
                devices = platform.get_devices(device_type=cl.device_type.GPU)
                if devices:
                    device = devices[0]
                    break
            except:  # NOQA
                continue
        else:
            for platform in platforms:
                try:
                    devices = platform.get_devices(device_type=cl.device_type.CPU)
                    if devices:
                        device = devices[0]
                        break
                except:  # NOQA
                    continue
            else:
                raise RuntimeError("No OpenCL devices found")

        ctx = cl.Context([device])
        queue = cl.CommandQueue(ctx)

        return ctx, queue

    def compile_kernel(self):
        kernel_path = os.path.join(os.path.dirname(__file__), 'bvh_kernel.cl')

        with open(kernel_path, 'r') as f:
            kernel_source = f.read()

        program = cl.Program(self.ctx, kernel_source).build()
        kernel = cl.Kernel(program, 'ray_trace_kernel')
        return program, kernel

    def start(self):
        (
            vertices, faces, bvh_bounds, bvh_structure,
            bvh_indices, object_ids, materials, lights
        ) = self.scene.build()

        # Upload geometry to GPU
        mf = cl.mem_flags
        vertices_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=vertices)
        faces_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=faces)
        object_ids_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=object_ids)
        materials_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=materials)
        lights_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=lights)

        # Upload BVH (separate buffers for bounds and structure)
        bvh_bounds_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=bvh_bounds)
        bvh_structure_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=bvh_structure)
        bvh_indices_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=bvh_indices)

        if self.scene.environment_map:
            env_array = np.array(self.scene.environment_map, dtype=np.uint8)
            env_height, env_width = env_array.shape[:2]
            env_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=env_array)
        else:
            dummy = np.zeros((1, 1, 3), dtype=np.uint8)
            env_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=dummy)
            env_width = 1
            env_height = 1

        forward = self.scene.camera_target - self.scene.camera_origin
        forward = forward / np.linalg.norm(forward)
        right = np.cross(forward, self.scene.camera_up)
        right = right / np.linalg.norm(right)
        up = np.cross(right, forward)

        aspect_ratio = self.scene.width / self.scene.height
        fov_rad = np.radians(self.scene.fov)
        scale = np.tan(fov_rad / 2)

        full_image = np.zeros((self.scene.height, self.scene.width, 3), dtype=np.float32)
        num_chunks = (self.scene.height + chunk_size - 1) // chunk_size

        for chunk_idx in range(num_chunks):
            start_y = chunk_idx * chunk_size
            end_y = min(start_y + chunk_size, self.scene.height)
            chunk_height = end_y - start_y

            chunk_image = np.zeros((chunk_height, self.scene.width, 3), dtype=np.float32)
            mf = cl.mem_flags
            chunk_buf = cl.Buffer(self.ctx, mf.WRITE_ONLY, chunk_image.nbytes)

            # Set all kernel arguments
            self.kernel.set_args(
                vertices_buf,
                faces_buf,
                object_ids_buf,
                materials_buf,
                np.int32(len(faces)),
                lights_buf,
                np.int32(len(lights)),
                bvh_bounds_buf,
                bvh_structure_buf,
                bvh_indices_buf,
                chunk_buf,
                np.int32(self.scene.width),
                np.int32(self.scene.height),
                np.float32(self.scene.camera_origin[0]),
                np.float32(self.scene.camera_origin[1]),
                np.float32(self.scene.camera_origin[2]),
                np.float32(self.scene.camera_target[0]),
                np.float32(self.scene.camera_target[1]),
                np.float32(self.scene.camera_target[2]),
                np.float32(right[0]),
                np.float32(right[1]),
                np.float32(right[2]),
                np.float32(up[0]),
                np.float32(up[1]),
                np.float32(up[2]),
                np.float32(forward[0]),
                np.float32(forward[1]),
                np.float32(forward[2]),
                np.float32(scale),
                np.float32(aspect_ratio),
                np.int32(start_y),
                np.int32(end_y),
                np.float32(Config.lighting.ambient_intensity),
                np.float32(Config.background.color1[0]),
                np.float32(Config.background.color1[1]),
                np.float32(Config.background.color1[2]),
                np.float32(Config.background.color2[0]),
                np.float32(Config.background.color2[1]),
                np.float32(Config.background.color2[2]),
                env_buf,
                np.int32(env_width),
                np.int32(env_height),
                np.int32(int(Config.background.enable_gradient)),
                np.int32(int(Config.environment_map.enable)),
                np.int32(int(Config.enable_reflections)),
                np.int32(int(Config.shadows.enable)),
                np.int32(int(Config.ambient_occlusion.enable)),
                np.int32(int(Config.enable_depth_of_field)),
                np.float32(Config.ambient_occlusion.samples),
                np.float32(Config.ambient_occlusion.radius),
                np.float32(Config.shadows.softness)
            )

            # Execute kernel
            cl.enqueue_nd_range_kernel(
                self.queue,
                self.kernel,
                (self.scene.width, chunk_height),
                None
            )

            # Copy result back to CPU
            cl.enqueue_copy(self.queue, chunk_image, chunk_buf).wait()
            full_image[start_y:end_y] = chunk_image

            # Call progress callback
            progress = ((chunk_idx + 1) / num_chunks) * 100
            if not self.callback((full_image * 255).astype(np.uint8), progress):
                break

        return (full_image * 255).astype(np.uint8)
