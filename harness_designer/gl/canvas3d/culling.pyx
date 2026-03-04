# distutils: include_dirs = c:\python3.11.14\Lib\site-packages\numpy\_core\include
# culling_nogil.pyx
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

import numpy as np
cimport numpy as np
from libc.stdlib cimport malloc, free
from libc.math cimport fabs
import threading
from queue import Queue, Empty
import ctypes
cimport cython


# Fast AABB-frustum test (pure C, no GIL)
cdef bint aabb_in_frustum_nogil(double* frustum_normals, double* frustum_distances,
                                double* aabb_min, double* aabb_max) nogil:

    """Test if AABB intersects frustum."""
    cdef double cx, cy, cz, ex, ey, ez
    cdef double s, r
    cdef int i, idx

    # Center
    cx = (aabb_min[0] + aabb_max[0]) * 0.5
    cy = (aabb_min[1] + aabb_max[1]) * 0.5
    cz = (aabb_min[2] + aabb_max[2]) * 0.5

    # Extents
    ex = (aabb_max[0] - aabb_min[0]) * 0.5
    ey = (aabb_max[1] - aabb_min[1]) * 0.5
    ez = (aabb_max[2] - aabb_min[2]) * 0.5

    # Test each frustum plane
    for i in range(6):
        idx = i * 3

        s = (frustum_normals[idx + 0] * cx +
             frustum_normals[idx + 1] * cy +
             frustum_normals[idx + 2] * cz +
             frustum_distances[i])

        r = (fabs(frustum_normals[idx + 0]) * ex +
             fabs(frustum_normals[idx + 1]) * ey +
             fabs(frustum_normals[idx + 2]) * ez)

        if s + r < 0.0:
            return False

    return True


@cython.boundscheck(False)
@cython.wraparound(False)
def cull_batch(list object_rows, double[:, ::1] frustum_normals_2d,
                      double[::1] frustum_distances, double[::1] camera_pos):
    """
    Python-facing function that unpacks object rows and calls nogil culling.

    VOODOO MAGIC: Takes the raw list format from Canvas and unpacks it
    with minimal GIL operations, then processes in pure C.

    Returns list of ORIGINAL row objects that are visible, sorted for rendering.
    """

    cdef int n = len(object_rows)

    if n == 0:
        return []

    cdef int i, idx
    cdef double* frustum_normals = &frustum_normals_2d[0, 0]
    cdef double cam_x = camera_pos[0]
    cdef double cam_y = camera_pos[1]
    cdef double cam_z = camera_pos[2]

    # Allocate output arrays
    cdef int* visible = <int*>malloc(n * sizeof(int))
    cdef double* dist_sq = <double*>malloc(n * sizeof(double))
    cdef int* is_opaque_arr = <int*>malloc(n * sizeof(int))

    # Temporary storage for numpy array pointers
    cdef double** aabb_mins = <double**>malloc(n * sizeof(double*))
    cdef double** aabb_maxs = <double**>malloc(n * sizeof(double*))
    cdef double** positions = <double**>malloc(n * sizeof(double*))

    # Unpack object rows (WITH GIL - but minimal work)
    cdef double[::1] aabb_min_view, aabb_max_view, pos_view
    cdef object row, is_opaque_obj

    for i in range(n):
        row = object_rows[i]

        # Extract numpy array views
        aabb_min_view = row[0]  # numpy array (3,)
        aabb_max_view = row[1]  # numpy array (3,)
        pos_view = row[2]       # numpy array (3,)
        is_opaque_obj = row[3]  # numpy array (1,) or int

        # Get pointers to array data
        aabb_mins[i] = &aabb_min_view[0]
        aabb_maxs[i] = &aabb_max_view[0]
        positions[i] = &pos_view[0]

       # Extract is_opaque (handle both array and int)
        if isinstance(is_opaque_obj, np.ndarray):
            # It's a numpy array - extract the value
            is_opaque_array = <np.ndarray>is_opaque_obj
            is_opaque_arr[i] = <int>is_opaque_array.flat[0]
        else:
            # It's already an int
            is_opaque_arr[i] = <int>is_opaque_obj

    # CULLING WITH NO GIL!
    cdef double dx, dy, dz

    with nogil:
        for i in range(n):
            # Frustum test
            if aabb_in_frustum_nogil(frustum_normals, &frustum_distances[0],
                                     aabb_mins[i], aabb_maxs[i]):
                visible[i] = 1

                # Distance calculation
                dx = cam_x - positions[i][0]
                dy = cam_y - positions[i][1]
                dz = cam_z - positions[i][2]
                dist_sq[i] = dx * dx + dy * dy + dz * dz
            else:
                visible[i] = 0
                dist_sq[i] = 0.0

    # Gather results (WITH GIL) - keep ORIGINAL row objects!
    cdef list opaque = []
    cdef list transparent = []

    for i in range(n):
        if visible[i]:
            # Append tuple: (distance, original_row_object)
            if is_opaque_arr[i]:
                opaque.append((dist_sq[i], object_rows[i]))
            else:
                transparent.append((dist_sq[i], object_rows[i]))

    # Sort: opaque front-to-back, transparent back-to-front
    opaque = sorted(opaque, key=lambda x: x[0])
    transparent = sorted(transparent, key=lambda x: x[0], reverse=True)

    # Build final list of ORIGINAL row objects (sorted for rendering)
    cdef list result_rows = []
    for dist, row in opaque:
        result_rows.append(row)  # Original row object!

    for dist, row in transparent:
        result_rows.append(row)  # Original row object!

    # Cleanup
    free(visible)
    free(dist_sq)
    free(is_opaque_arr)
    free(aabb_mins)
    free(aabb_maxs)
    free(positions)

    return result_rows


# Worker thread - PERSISTENT with Event for graceful shutdown
# Worker thread - CLEAN AND EFFICIENT
class CullingWorker(threading.Thread):
    """
    Persistent worker thread with blocking Queue.

    Uses Event for graceful shutdown on app exit.
    Threads stay alive, block on Queue.get() with ZERO CPU usage.
    """

    def __init__(self, thread_num):
        super().__init__(daemon=True, name=f"CullingWorker-{thread_num}")
        self.thread_num = thread_num

        # Queues for work/results
        self.work_queue = Queue(maxsize=1)
        self.result_queue = Queue(maxsize=1)

        # Event for graceful shutdown
        self._stop_event = threading.Event()

        self.start()

    def run(self):
        """Worker loop - blocks on Queue.get() with ZERO CPU usage."""

        while not self._stop_event.is_set():
            try:
                work = self.work_queue.get()

                if work is None:
                    break

                object_rows, normals, distances, camera_pos = work

                # Call Cython function
                results = cull_batch(
                    object_rows, normals, distances, camera_pos
                )

                self.result_queue.put(results)

            except Exception as e:
                try:
                    self.result_queue.put([])
                except:
                    pass


    def cull(self, object_rows, frustum_normals, frustum_distances, camera_pos):
        """
        Submit work to this worker thread.

        Wakes sleeping worker instantly when work is added to queue.
        """

        self.work_queue.put((object_rows, frustum_normals, frustum_distances, camera_pos))

    def finish(self):
        """
        Get results from this worker thread.

        Blocks until worker completes - efficient sleep!
        """

        return self.result_queue.get()

    def stop(self):
        """
        Stop this worker thread gracefully.

        Sets Event and sends poison pill to wake and exit cleanly.
        """

        self._stop_event.set()
        self.work_queue.put(None)  # Poison pill wakes thread
        self.join(timeout=1.0)


# Thread pool
class CullingThreadPool:
    """
    Thread pool with persistent workers.
    """

    def __init__(self, num_threads=10):
        """
        Create persistent worker threads.

        Threads are created ONCE and reused for entire app lifetime.
        """

        self.workers = [CullingWorker(i) for i in range(num_threads)]
        self._num_threads = num_threads

    def cull(self, object_data_lists, normals, distances, camera_pos):
        # Dispatch work to worker threads
        num_jobs = 0
        for i, worker in enumerate(self.workers):
            if i < len(object_data_lists) and object_data_lists[i]:
                worker.cull(object_data_lists[i], normals, distances, camera_pos)
                num_jobs += 1

        # Gather results
        all_visible_rows = []
        for i in range(num_jobs):
            visible_rows = self.workers[i].finish()
            all_visible_rows.extend(visible_rows)

        return all_visible_rows

    def shutdown(self):
        """
        Shutdown all worker threads gracefully.

        Call this when app is closing.
        Event ensures threads exit cleanly.
        """

        for worker in self.workers:
            worker.stop()

    def __del__(self):
        """Auto-shutdown on cleanup."""

        try:
            self.shutdown()
        except:
            pass