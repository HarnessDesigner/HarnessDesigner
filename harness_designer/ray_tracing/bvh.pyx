# bvh_fast.pyx
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: initializedcheck=False
# cython: nonecheck=False

# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Fast BVH (Bounding Volume Hierarchy) builder for ray tracing
Optimized with Cython for maximum performance

Features:
- Parallel centroid calculation (OpenMP)
- GIL-free BVH construction
- Pre-allocated memory for zero-copy operation
- Returns NumPy arrays for OpenCL compatibility
"""

import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
cimport numpy as cnp
from cython.parallel import prange
from libc.stdlib cimport malloc, free
from libc.math cimport fminf, fmaxf, sqrtf, INFINITY
from libc.string cimport memcpy

# Type definitions
ctypedef cnp.float32_t FLOAT
ctypedef cnp.int32_t INT

# BVH node structure (C struct for speed)
cdef struct BVHNodeC:
    float min_bounds[3]    # Min bounding box corner
    float max_bounds[3]    # Max bounding box corner
    int left_child         # Index of left child (-1 if leaf)
    int right_child        # Index of right child (-1 if leaf)
    int first_prim         # Index of first primitive (for leaf nodes)
    int prim_count         # Number of primitives in leaf


# ==============================================================================
# PUBLIC API
# ==============================================================================

def calculate_centroids_parallel(
    FLOAT[:, ::1] vertices,  # Shape: (num_vertices, 3)
    INT[:, ::1] faces        # Shape: (num_faces, 3)
):
    """
    Calculate triangle centroids in parallel

    Args:
        vertices: Vertex positions (N, 3) - must be C-contiguous
        faces: Triangle indices (M, 3) - must be C-contiguous

    Returns:
        centroids: Triangle centroids (M, 3) as NumPy array

    Performance: ~150ms for 12M triangles on 8-core CPU
    """
    cdef:
        Py_ssize_t num_faces = faces.shape[0]
        Py_ssize_t i
        INT v0_idx, v1_idx, v2_idx
        cnp.ndarray[FLOAT, ndim=2] centroids = np.empty((num_faces, 3), dtype=np.float32)
        FLOAT[:, ::1] centroids_view = centroids

    # Parallel loop - OpenMP distributes across CPU cores
    # nogil = releases Python GIL for true parallelism
    for i in prange(num_faces, nogil=True, schedule='static', num_threads=10):
        v0_idx = faces[i, 0]
        v1_idx = faces[i, 1]
        v2_idx = faces[i, 2]

        # Calculate centroid: (v0 + v1 + v2) / 3
        # Manual calculation is faster than NumPy operations in tight loop
        # Divide by integer 3 (not 3.0) to avoid promoting float32 to double.
        centroids_view[i, 0] = (vertices[v0_idx, 0] + vertices[v1_idx, 0] + vertices[v2_idx, 0]) / 3
        centroids_view[i, 1] = (vertices[v0_idx, 1] + vertices[v1_idx, 1] + vertices[v2_idx, 1]) / 3
        centroids_view[i, 2] = (vertices[v0_idx, 2] + vertices[v1_idx, 2] + vertices[v2_idx, 2]) / 3

    return centroids


# Trees with fewer triangles than this are built on one thread; a thread pool would cost more than it saves.
cdef int PARALLEL_MIN_PRIMITIVES = 20000

# The top of a big tree is split on one thread down to this depth, then the 2 ** depth subtrees below it are
# built in parallel.
cdef int PARALLEL_SPLIT_DEPTH = 6


cdef int count_nodes(int n, int leaf_threshold) noexcept nogil:
    """
    Number of nodes of the tree FastBVHBuilder makes for ``n`` primitives, without building it.

    A node holding more than ``leaf_threshold`` primitives is split into halves of ``n // 2`` and the rest, so
    the shape of the tree depends only on the counts. Knowing it lets every subtree be given its own range of
    node indices before it is built, which is what allows the subtrees to be built at the same time.

    Each level of the tree holds only two sizes, ``size`` and ``size + 1``, so it is walked level by level.
    """
    cdef:
        long total = 0
        long size = n
        long count_a = 1
        long count_b = 0
        long sizes[4]
        long counts[4]
        long base, next_a, next_b, s, c, half
        int found, k, m

    while count_a + count_b > 0:
        total += count_a + count_b
        found = 0

        for k in range(2):
            c = count_a if k == 0 else count_b
            s = size + k

            if c == 0 or s <= leaf_threshold:
                continue

            half = s // 2
            sizes[found] = half
            counts[found] = c
            found += 1
            sizes[found] = s - half
            counts[found] = c
            found += 1

        if found == 0:
            break

        base = sizes[0]
        for m in range(1, found):
            if sizes[m] < base:
                base = sizes[m]

        next_a = 0
        next_b = 0
        for m in range(found):
            if sizes[m] == base:
                next_a += counts[m]
            else:
                next_b += counts[m]

        size = base
        count_a = next_a
        count_b = next_b

    return <int>total


cdef class FastBVHBuilder:
    """
    Fast BVH builder using C structs and no-GIL recursion

    Usage:
        builder = FastBVHBuilder(vertices, faces, centroids)
        bounds, structure, indices = builder.build()

    Each node is split at the median centroid of its longest axis. The median is found with a selection
    (quickselect, O(n) per level) rather than a sort, every triangle's bounding box is computed once up front,
    and for a big scene the subtrees below the top few levels are built in parallel (a thread pool).
    """

    # C-level member variables (no Python overhead)
    cdef:
        FLOAT[:, ::1] vertices      # Memory view of vertices
        INT[:, ::1] faces           # Memory view of faces
        FLOAT[:, ::1] centroids     # Memory view of centroids
        FLOAT[:, ::1] tri_bounds    # Per triangle: min x, y, z, max x, y, z
        INT[::1] indices            # Reorderable primitive indices
        BVHNodeC* nodes             # Pre-allocated C array of nodes
        int node_count              # Current node count
        int max_nodes               # Maximum nodes allocated
        int leaf_threshold          # Max primitives per leaf
        int* task_nodes             # Subtrees left for the parallel phase: node index,
        int* task_starts            # first primitive
        int* task_ends              # and end of its range
        int task_count
        int task_capacity

    def __init__(
        self,
        cnp.ndarray[FLOAT, ndim=2] vertices,
        cnp.ndarray[INT, ndim=2] faces,
        cnp.ndarray[FLOAT, ndim=2] centroids,
        int leaf_threshold=4
    ):
        """
        Initialize BVH builder

        Args:
            vertices: Vertex array (N, 3)
            faces: Face indices (M, 3)
            centroids: Pre-calculated centroids (M, 3)
            leaf_threshold: Max triangles per leaf node (default: 4)
        """
        if vertices.shape[1] != 3:
            raise ValueError(f"Vertices must have shape (N, 3)")
        if faces.shape[1] != 3:
            raise ValueError(f"Faces must have shape (M, 3)")
        if centroids.shape[1] != 3:
            raise ValueError(f"Centroids must have shape (M, 3)")
        if faces.shape[0] != centroids.shape[0]:
            raise ValueError(f"Faces and centroids must have same count")

        # Store memory views (zero-copy reference to NumPy arrays)
        self.vertices = vertices
        self.faces = faces
        self.centroids = centroids
        self.leaf_threshold = leaf_threshold

        self.nodes = NULL
        self.task_nodes = NULL
        self.task_starts = NULL
        self.task_ends = NULL
        self.task_count = 0
        self.task_capacity = 0

        cdef:
            int num_faces = <int>faces.shape[0]
            Py_ssize_t i
            int a, b, c
            cnp.ndarray[FLOAT, ndim=2] bounds = np.empty((num_faces, 6), dtype=np.float32)
            FLOAT[:, ::1] bounds_view = bounds

        # Each triangle's box, once: a node's box is then a min/max over contiguous rows instead of nine
        # scattered vertex reads per triangle at every level of the tree.
        for i in prange(num_faces, nogil=True, schedule='static'):
            a = self.faces[i, 0]
            b = self.faces[i, 1]
            c = self.faces[i, 2]

            bounds_view[i, 0] = fminf(self.vertices[a, 0], fminf(self.vertices[b, 0], self.vertices[c, 0]))
            bounds_view[i, 1] = fminf(self.vertices[a, 1], fminf(self.vertices[b, 1], self.vertices[c, 1]))
            bounds_view[i, 2] = fminf(self.vertices[a, 2], fminf(self.vertices[b, 2], self.vertices[c, 2]))
            bounds_view[i, 3] = fmaxf(self.vertices[a, 0], fmaxf(self.vertices[b, 0], self.vertices[c, 0]))
            bounds_view[i, 4] = fmaxf(self.vertices[a, 1], fmaxf(self.vertices[b, 1], self.vertices[c, 1]))
            bounds_view[i, 5] = fmaxf(self.vertices[a, 2], fmaxf(self.vertices[b, 2], self.vertices[c, 2]))

        self.tri_bounds = bounds_view

        # Initialize primitive indices (will be reordered during build)
        self.indices = np.arange(num_faces, dtype=np.int32)

        # The tree's shape is fixed by the primitive count, so its node count is known exactly.
        self.max_nodes = count_nodes(num_faces, leaf_threshold)
        self.nodes = <BVHNodeC*>malloc(self.max_nodes * sizeof(BVHNodeC))
        if self.nodes == NULL:
            raise MemoryError(f"Failed to allocate {self.max_nodes} BVH nodes")

        self.node_count = 0

        print(f"FastBVHBuilder initialized: {num_faces} triangles, "
              f"{num_faces * 3} vertices, leaf_threshold={leaf_threshold}")

    def __dealloc__(self):
        """Clean up allocated memory"""
        if self.nodes != NULL:
            free(self.nodes)
            self.nodes = NULL

        if self.task_nodes != NULL:
            free(self.task_nodes)
            self.task_nodes = NULL

        if self.task_starts != NULL:
            free(self.task_starts)
            self.task_starts = NULL

        if self.task_ends != NULL:
            free(self.task_ends)
            self.task_ends = NULL

    def build(self):
        """
        Build BVH and return arrays for OpenCL

        Returns:
            tuple: (bounds, structure, indices)
                - bounds: float32 array (num_nodes * 6,) - flattened min/max bounds
                - structure: int32 array (num_nodes * 4,) - flattened node structure
                - indices: int32 array (num_faces,) - reordered primitive indices

        Performance: releases the GIL, and builds the subtrees of a big scene on all cores
        """
        cdef:
            int num_faces = <int>self.faces.shape[0]
            int split_depth = 1 << 30

        print(f"Building BVH tree...")

        if num_faces >= PARALLEL_MIN_PRIMITIVES:
            split_depth = PARALLEL_SPLIT_DEPTH
            self.task_capacity = (1 << split_depth) + 1
            self.task_nodes = <int*>malloc(self.task_capacity * sizeof(int))
            self.task_starts = <int*>malloc(self.task_capacity * sizeof(int))
            self.task_ends = <int*>malloc(self.task_capacity * sizeof(int))
            if self.task_nodes == NULL or self.task_starts == NULL or self.task_ends == NULL:
                raise MemoryError("Failed to allocate the BVH task list")

        self.task_count = 0

        with nogil:
            # The top levels, on this thread. Below split_depth a node is only noted down.
            self.build_node(0, 0, num_faces, 0, split_depth)

        # Each noted subtree owns its own range of nodes and primitives, so they can be built at once. This
        # is a thread pool and not OpenMP's prange: the project's builder compiles without OpenMP, where a
        # prange would quietly run on one thread, and _build_task holds no GIL.
        if self.task_count:
            with ThreadPoolExecutor(max_workers=min(self.task_count, os.cpu_count() or 1)) as pool:
                list(pool.map(self._build_task, range(self.task_count)))

        self.node_count = self.max_nodes

        print(f"BVH tree built: {self.node_count} nodes")

        # Convert C structs to NumPy arrays for OpenCL
        return self._convert_to_numpy_arrays()

    def _build_task(self, int task):
        """Build one subtree left for the parallel phase (called from a worker thread)."""
        with nogil:
            self.build_node(self.task_nodes[task], self.task_starts[task], self.task_ends[task], 0, 1 << 30)

    cdef void build_node(self, int node_idx, int start, int end, int depth, int split_depth) noexcept nogil:
        """
        Build the node ``node_idx`` over ``indices[start:end]`` and everything below it.

        The left subtree takes the node indices right after this one and the right subtree the ones after
        that, so a subtree's range is known before it is built. Past ``split_depth`` the node is not built:
        it is put on the task list for the parallel phase.
        """
        cdef:
            BVHNodeC* node = &self.nodes[node_idx]
            int num_prims = end - start
            int i, face_idx, axis, mid, left_idx, right_idx
            float extent[3]

        if depth >= split_depth and num_prims > self.leaf_threshold:
            self.task_nodes[self.task_count] = node_idx
            self.task_starts[self.task_count] = start
            self.task_ends[self.task_count] = end
            self.task_count += 1
            return

        # Initialize node bounds to infinity
        node.min_bounds[0] = node.min_bounds[1] = node.min_bounds[2] = INFINITY
        node.max_bounds[0] = node.max_bounds[1] = node.max_bounds[2] = -INFINITY
        node.left_child = -1
        node.right_child = -1
        node.first_prim = -1
        node.prim_count = 0

        # Bounding box of every primitive in this node
        for i in range(start, end):
            face_idx = self.indices[i]

            node.min_bounds[0] = fminf(node.min_bounds[0], self.tri_bounds[face_idx, 0])
            node.min_bounds[1] = fminf(node.min_bounds[1], self.tri_bounds[face_idx, 1])
            node.min_bounds[2] = fminf(node.min_bounds[2], self.tri_bounds[face_idx, 2])
            node.max_bounds[0] = fmaxf(node.max_bounds[0], self.tri_bounds[face_idx, 3])
            node.max_bounds[1] = fmaxf(node.max_bounds[1], self.tri_bounds[face_idx, 4])
            node.max_bounds[2] = fmaxf(node.max_bounds[2], self.tri_bounds[face_idx, 5])

        # Leaf node check
        if num_prims <= self.leaf_threshold:
            node.first_prim = start
            node.prim_count = num_prims
            return

        # Choose split axis (longest extent)
        extent[0] = node.max_bounds[0] - node.min_bounds[0]
        extent[1] = node.max_bounds[1] - node.min_bounds[1]
        extent[2] = node.max_bounds[2] - node.min_bounds[2]

        axis = 0
        if extent[1] > extent[axis]:
            axis = 1
        if extent[2] > extent[axis]:
            axis = 2

        # Split at the median centroid: only the middle element has to be in place, the halves need no order.
        mid = start + num_prims // 2
        self.select_nth_nogil(start, end, mid, axis)

        left_idx = node_idx + 1
        right_idx = left_idx + count_nodes(mid - start, self.leaf_threshold)
        node.left_child = left_idx
        node.right_child = right_idx

        self.build_node(left_idx, start, mid, depth + 1, split_depth)
        self.build_node(right_idx, mid, end, depth + 1, split_depth)

    cdef void select_nth_nogil(self, int start, int end, int nth, int axis) noexcept nogil:
        """
        Reorder ``indices[start:end]`` so that element ``nth`` is the one a full sort by centroid would put
        there, everything before it is not greater and everything after it is not smaller (Hoare's quickselect).
        """
        cdef:
            int left = start
            int right = end - 1
            int i, j, temp, middle
            float pivot, a, b, c

        while left < right:
            # Median of three, so data that is already in order does not make it quadratic.
            middle = left + (right - left) // 2
            a = self.centroids[self.indices[left], axis]
            b = self.centroids[self.indices[middle], axis]
            c = self.centroids[self.indices[right], axis]

            if a < b:
                if b < c:
                    pivot = b
                elif a < c:
                    pivot = c
                else:
                    pivot = a
            else:
                if a < c:
                    pivot = a
                elif b < c:
                    pivot = c
                else:
                    pivot = b

            i = left
            j = right

            while i <= j:
                while self.centroids[self.indices[i], axis] < pivot:
                    i += 1

                while self.centroids[self.indices[j], axis] > pivot:
                    j -= 1

                if i <= j:
                    temp = self.indices[i]
                    self.indices[i] = self.indices[j]
                    self.indices[j] = temp
                    i += 1
                    j -= 1

            if nth <= j:
                right = j
            elif nth >= i:
                left = i
            else:
                break

    cdef tuple _convert_to_numpy_arrays(self):
        """Convert C structs to NumPy arrays for OpenCL"""
        cdef:
            int num_nodes = self.node_count
            cnp.ndarray[FLOAT, ndim=1] bounds = np.empty(num_nodes * 6, dtype=np.float32)
            cnp.ndarray[INT, ndim=1] structure = np.empty(num_nodes * 4, dtype=np.int32)
            int i
            BVHNodeC* node

        # Copy node data to NumPy arrays
        for i in range(num_nodes):
            node = &self.nodes[i]

            # Bounds: [min_x, min_y, min_z, max_x, max_y, max_z]
            bounds[i * 6 + 0] = node.min_bounds[0]
            bounds[i * 6 + 1] = node.min_bounds[1]
            bounds[i * 6 + 2] = node.min_bounds[2]
            bounds[i * 6 + 3] = node.max_bounds[0]
            bounds[i * 6 + 4] = node.max_bounds[1]
            bounds[i * 6 + 5] = node.max_bounds[2]

            # Structure: [left_child, right_child, first_prim, prim_count]
            structure[i * 4 + 0] = node.left_child
            structure[i * 4 + 1] = node.right_child
            structure[i * 4 + 2] = node.first_prim
            structure[i * 4 + 3] = node.prim_count

        # Return flattened NumPy arrays (zero-copy reference to self.indices)
        return bounds, structure, np.asarray(self.indices)

    def get_stats(self):
        """
        Get BVH statistics

        Returns:
            dict: Statistics about the built BVH
        """
        if self.node_count == 0:
            return {"error": "BVH not built yet"}

        cdef:
            int num_nodes = self.node_count
            int num_leaves = 0
            int num_internal = 0
            int max_depth = 0
            int total_prims_in_leaves = 0
            int i
            BVHNodeC* node

        for i in range(num_nodes):
            node = &self.nodes[i]
            if node.left_child == -1:  # Leaf node
                num_leaves += 1
                total_prims_in_leaves += node.prim_count
            else:
                num_internal += 1

        avg_prims_per_leaf = total_prims_in_leaves / float(num_leaves) if num_leaves > 0 else 0

        return {
            "total_nodes": num_nodes,
            "leaf_nodes": num_leaves,
            "internal_nodes": num_internal,
            "avg_prims_per_leaf": avg_prims_per_leaf,
            "total_primitives": self.faces.shape[0],
        }


# ==============================================================================
# TRANSFORM UTILITIES
# ==============================================================================

def apply_transform_parallel(
    FLOAT[:, ::1] vertices,       # Input vertices (N, 3)
    FLOAT[:, ::1] normals,        # Input normals (M, 3)
    FLOAT[::1] position,          # Translation vector (3,)
    FLOAT[:, ::1] rotation_mat    # Rotation matrix (3, 3)
):
    """
    Apply rigid transformation (rotation + translation) to vertices and normals

    Args:
        vertices: Vertex positions (N, 3)
        normals: Normal vectors (M, 3)
        position: Translation vector (3,)
        rotation_mat: 3x3 rotation matrix (row-major)

    Returns:
        tuple: (transformed_vertices, transformed_normals)

    Performance: ~200ms for 800 objects × 15K vertices on 8-core CPU
    """
    cdef:
        Py_ssize_t num_verts = vertices.shape[0]
        Py_ssize_t num_normals = normals.shape[0]
        Py_ssize_t i

        cnp.ndarray[FLOAT, ndim=2] transformed_verts = np.empty((num_verts, 3), dtype=np.float32)
        cnp.ndarray[FLOAT, ndim=2] transformed_normals = np.empty((num_normals, 3), dtype=np.float32)

        FLOAT[:, ::1] tv_view = transformed_verts
        FLOAT[:, ::1] tn_view = transformed_normals

        FLOAT x, y, z, norm

    # Transform vertices: v' = R * v + t
    for i in prange(num_verts, nogil=True, schedule='static', num_threads=10):
        # Matrix multiply: R * v
        x = (rotation_mat[0, 0] * vertices[i, 0] +
             rotation_mat[0, 1] * vertices[i, 1] +
             rotation_mat[0, 2] * vertices[i, 2])

        y = (rotation_mat[1, 0] * vertices[i, 0] +
             rotation_mat[1, 1] * vertices[i, 1] +
             rotation_mat[1, 2] * vertices[i, 2])

        z = (rotation_mat[2, 0] * vertices[i, 0] +
             rotation_mat[2, 1] * vertices[i, 1] +
             rotation_mat[2, 2] * vertices[i, 2])

        # Add translation
        tv_view[i, 0] = x + position[0]
        tv_view[i, 1] = y + position[1]
        tv_view[i, 2] = z + position[2]

    # Transform normals: n' = normalize(R * n)
    # Note: No translation for normals (they're directions, not points)
    for i in prange(num_normals, nogil=True, schedule='static', num_threads=10):
        # Matrix multiply: R * n
        x = (rotation_mat[0, 0] * normals[i, 0] +
             rotation_mat[0, 1] * normals[i, 1] +
             rotation_mat[0, 2] * normals[i, 2])

        y = (rotation_mat[1, 0] * normals[i, 0] +
             rotation_mat[1, 1] * normals[i, 1] +
             rotation_mat[1, 2] * normals[i, 2])

        z = (rotation_mat[2, 0] * normals[i, 0] +
             rotation_mat[2, 1] * normals[i, 1] +
             rotation_mat[2, 2] * normals[i, 2])

        # Normalize (rotation matrices preserve length, but floating point errors accumulate)
        norm = sqrtf(x*x + y*y + z*z)
        if norm > 0.0:
            tn_view[i, 0] = x / norm
            tn_view[i, 1] = y / norm
            tn_view[i, 2] = z / norm
        else:
            # Degenerate case (shouldn't happen with valid input)
            tn_view[i, 0] = 0.0
            tn_view[i, 1] = 1.0
            tn_view[i, 2] = 0.0

    return transformed_verts, transformed_normals


def quaternion_to_rotation_matrix(FLOAT[::1] quat):
    """
    Convert quaternion to 3x3 rotation matrix

    Args:
        quat: Quaternion as [w, x, y, z] (4,)

    Returns:
        rotation_mat: 3x3 rotation matrix (NumPy array)
    """
    cdef:
        FLOAT w = quat[0]
        FLOAT x = quat[1]
        FLOAT y = quat[2]
        FLOAT z = quat[3]

        FLOAT xx = x * x
        FLOAT yy = y * y
        FLOAT zz = z * z
        FLOAT xy = x * y
        FLOAT xz = x * z
        FLOAT yz = y * z
        FLOAT wx = w * x
        FLOAT wy = w * y
        FLOAT wz = w * z

        cnp.ndarray[FLOAT, ndim=2] mat = np.empty((3, 3), dtype=np.float32)

    # Row 0 — integer literals (1, 2) prevent double promotion of float32 operands
    mat[0, 0] = 1 - 2 * (yy + zz)
    mat[0, 1] = 2 * (xy - wz)
    mat[0, 2] = 2 * (xz + wy)

    # Row 1
    mat[1, 0] = 2 * (xy + wz)
    mat[1, 1] = 1 - 2 * (xx + zz)
    mat[1, 2] = 2 * (yz - wx)

    # Row 2
    mat[2, 0] = 2 * (xz - wy)
    mat[2, 1] = 2 * (yz + wx)
    mat[2, 2] = 1 - 2 * (xx + yy)

    return mat
