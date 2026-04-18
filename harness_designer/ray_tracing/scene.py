from typing import TYPE_CHECKING

import os
from PIL import Image
import numpy as np

from .. import config as _config
from . import bvh_processor as _bvh_processor
from . import light as _light


if TYPE_CHECKING:
    from ..gl.canvas3d import camera as _camera


Config = _config.Config.ray_trace


class Scene:

    def __init__(self, width, height, camera: "_camera.Camera"):
        self.objects = []
        self.environment_map = None
        self.width = width
        self.height = height
        self.camera_origin = camera.position.as_numpy.copy()
        self.camera_target = camera.focal_position.as_numpy.copy()
        self.camera_up = camera.up
        self.fov = camera.field_of_view

    def add_object(self, obj):
        self.objects.append(obj)

    def load_environment_map(self, image_path):
        self.environment_map = Image.open(image_path).convert('RGB')
        Config.environment_map.enable = True

    def generate_environment(self, size):
        img = Image.new('RGB', size)
        pixels = img.load()

        for y in range(size[1]):
            for x in range(size[0]):
                t = y / size[1]
                r = int(135 + (240 - 135) * t)
                g = int(206 + (240 - 206) * t)
                b = int(235 + (255 - 235) * t)
                pixels[x, y] = (r, g, b)

        self.environment_map = img

    def build(self):
        thread_count = os.cpu_count() - 1

        processor = _bvh_processor.ThreadedBVHProcessor(num_threads=thread_count)
        processor.start()

        object_data_list = []
        materials = []

        for obj_id, obj in enumerate(self.objects):
            obj_data = _bvh_processor.ObjectData(
                object_id=obj_id,
                vertices=obj.vertices.astype(np.float32),
                faces=obj.faces.astype(np.int32),
                normals=obj.normals.astype(np.float32),
                position=obj.position.as_numpy,
                rotation=obj.angle.as_quat_numpy,
                material_id=obj_id
            )

            object_data_list.append(obj_data)
            materials.append(obj.material.cl_array)

        processed_objects = processor.process_objects(object_data_list)

        all_vertices = []
        all_faces = []
        all_bvh_bounds = []
        all_bvh_structure = []
        all_bvh_indices = []
        object_ids = []

        vertex_offset = 0
        bvh_node_offset = 0
        bvh_index_offset = 0

        for processed in processed_objects:
            # Vertices
            all_vertices.append(processed.vertices)

            # Faces (adjust indices)
            adjusted_faces = processed.faces + vertex_offset
            all_faces.append(adjusted_faces)

            # BVH (adjust indices and offsets)
            all_bvh_bounds.append(processed.bvh_bounds)

            # Adjust BVH structure node indices
            structure = processed.bvh_structure.copy()
            num_nodes = len(structure) // 4
            for i in range(num_nodes):
                left = structure[i * 4 + 0]
                right = structure[i * 4 + 1]
                first_prim = structure[i * 4 + 2]

                # Adjust child indices (if not -1)
                if left != -1:
                    structure[i * 4 + 0] = left + bvh_node_offset
                if right != -1:
                    structure[i * 4 + 1] = right + bvh_node_offset

                # Adjust primitive index
                if first_prim != -1:
                    structure[i * 4 + 2] = first_prim + bvh_index_offset

            all_bvh_structure.append(structure)

            # Adjust BVH indices
            adjusted_indices = processed.bvh_indices + vertex_offset
            all_bvh_indices.append(adjusted_indices)

            # Object IDs
            object_ids.extend([processed.material_id] * len(processed.faces))

            # Update offsets
            vertex_offset += len(processed.vertices)
            bvh_node_offset += num_nodes
            bvh_index_offset += len(processed.bvh_indices)

        # Concatenate all arrays
        vertices = np.vstack(all_vertices)
        faces = np.vstack(all_faces)
        bvh_bounds = np.concatenate(all_bvh_bounds)
        bvh_structure = np.concatenate(all_bvh_structure)
        bvh_indices = np.concatenate(all_bvh_indices)
        object_ids = np.array(object_ids, dtype=np.int32)
        materials = np.array(materials, dtype=np.float32)

        lights = np.array(
            [_light.Light(**light).to_array() for light in Config.lighting.lights], dtype=np.float32)

        return vertices, faces, bvh_bounds, bvh_structure, bvh_indices, object_ids, materials, lights
