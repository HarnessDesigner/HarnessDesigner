from typing import TYPE_CHECKING

import weakref

from . import base3d as _base3d
from .. import model_loader as _model_loader
from ..geometry import angle as _angle
from ..geometry import point as _point


if TYPE_CHECKING:
    from ..ui import editor_3d as _editor_3d
    from .. import gl_materials as _glm


class _ModelDataMeta(type):
    _cache = {}

    def __remove_ref(cls, ref):
        for key, value in list(cls._cache.items()):
            if value == ref:
                del cls._cache[key]
                return

    def __call__(cls, file):
        if file in cls._cache:
            instance = cls._cache[file]()
            if instance is None:
                instance = super().__call__(file)
                cls._cache[file] = weakref.ref(instance, cls.__remove_ref)
        else:
            instance = super().__call__(file)
            cls._cache[file] = weakref.ref(instance, cls.__remove_ref)

        return instance


class _ModelData(metaclass=_ModelDataMeta):

    def __init__(self, file):
        self.file = file
        self.data = _model_loader.load(file)


class MeshModel(_base3d.Base3D):

    def __init__(self, canvas: "_editor_3d.Editor3D", material: "_glm.GLMaterial",
                 selected_material: "_glm.GLMaterial", smooth: bool,
                 file: str | None, position: _point.Point | None = None,
                 angle: _angle.Angle | None = None):
        self._model_data = None

        if file is None:
            data = []
        else:
            data = self.load_file(file)

        _base3d.Base3D.__init__(self, canvas, material, selected_material,
                                smooth, data, position, angle)

    def load_file(self, file):
        self._model_data = _ModelData(file)
        return self._model_data.data[:]
