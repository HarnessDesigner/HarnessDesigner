
from . import aabb as _aabb
from . import obb as _obb


class View:

    def __init__(self):
        self._aabb = _aabb.AABB()
        self._obb = _obb.OBB

    @property
    def aabb(self) -> _aabb.AABB:
        return self._aabb

    @property
    def obb(self) -> _obb.OBB:
        return self._obb


class Manager:

    def __init__(self):
        self._editor_3d = View()
        self._editor_schematic = View()
        self._editor_pegboard = View()

    @property
    def editor_3d(self) -> View:
        return self._editor_3d

    @property
    def editor_schematic(self) -> View:
        return self._editor_schematic

    @property
    def editor_pegboard(self) -> View:
        return self._editor_schematic
