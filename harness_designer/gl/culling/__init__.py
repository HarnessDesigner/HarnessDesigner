# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np

from . import culling as _culling


class __CullingLoader:

    def __init__(self):
        import sys

        mod = sys.modules[__name__]

        self.__dict__['__name__'] = __name__
        self.__dict__['__file__'] = mod.__file__
        self.__dict__['__package__'] = mod.__package__
        self.__dict__['__doc__'] = mod.__doc__
        self.__dict__['__loader__'] = mod.__loader__
        self.__dict__['__spec__'] = mod.__spec__
        self.__dict__['__path__'] = mod.__path__
        self.__dict__['___cached__'] = mod.__cached__

        self.__original_module__ = mod

        sys.modules[__name__] = self

        self.__culling__ = _culling.CullingThreadPool()

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
        if self.__culling__ is None:
            return []

        return self.__culling__.cull(object_data_lists, frustum_normals,
                                     frustum_distances, camera_pos)

    def shutdown(self):
        if self.__culling__ is not None:
            self.__culling__.shutdown()
            self.__culling__ = None


__culling = __CullingLoader()


if TYPE_CHECKING:
    def cull(
        object_data_lists: list[  # NOQA
            list[list[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]],
            list[list[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]],
            list[list[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]],
            list[list[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]]
        ],
        frustum_normals: np.ndarray,   # NOQA
        frustum_distances: np.ndarray,   # NOQA
        camera_pos: np.ndarray   # NOQA
    ):
        pass


    def shutdown(self):
        pass


