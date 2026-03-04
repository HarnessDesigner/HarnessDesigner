import numpy as np


class CullingThreadPool:

    def __init__(self, num_threads: int = 4):
        ...

    def cull(
        self,
        object_data_lists: list[
            list[list[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]],
            list[list[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]],
            list[list[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]],
            list[list[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]]
        ],
        frustum_normals: np.ndarray,
        frustum_distances: np.ndarray,
        camera_pos: np.ndarray
    ):
        """
        View Culling

        There is no reason to send objects to the GPU to be rendered if
        the object is not in view. Culling is expensive to do in python code
        and because we have the potential to deal with 10's of thousands of
        objects we need to make sure the culling is done as fast as possible.
        To achieve this the code is compiled using Cython. Using Cython allows
        us to do several things and the bigges one of those is the ability
        to execute the for loops in threads without using the GIL. This greatly
        speeds up the culling which is what takes the most amount of time to do
        when a frame is being rendered.

        For sake of providing some numbers. 480 objects takes roughly
        20 milliseconds to cull.


        Args:
            object_data_lists: List of 4 lists, each containing object rows:
                [
                    [  # Thread 0
                        [aabb_min: shape=(3,), aabb_max: shape=(3,), pos: shape=(3,), is_opaque:shape=(1,), obj: int],
                        ...
                    ],
                    [  # Thread 1
                        [aabb_min: shape=(3,), aabb_max: shape=(3,), pos: shape=(3,), is_opaque:shape=(1,), obj: int],
                        ...
                    ],
                    ...
                ]
            frustum_normals: Camera frustum normals shape=6, 3)
            frustum_distances: Camera frustum distances shape=(6,)
            camera_pos: Camera position shape=(3,)

        Returns:
            List of ORIGINAL row objects that passed culling, sorted:
            [
                [aabb_min, aabb_max, position, is_opaque, render_func],
                ...
            ]
        """
        ...

    def shutdown(self):
        """
        Shutdown all worker threads gracefully.

        Call this when app is closing.
        Event ensures threads exit cleanly.
        """
        ...

    def __del__(self):
        """Auto-shutdown on cleanup."""
        ...
