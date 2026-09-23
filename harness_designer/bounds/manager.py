
from . import aabb as _aabb
from . import obb as _obb
from . import segment_pool as _segment_pool


class View:

    def __init__(self):
        self._aabb = _aabb.AABB()
        self._obb = _obb.OBB()
        self._segments = _segment_pool.SegmentPool()

    @property
    def aabb(self) -> _aabb.AABB:
        return self._aabb

    @property
    def obb(self) -> _obb.OBB:
        return self._obb

    @property
    def segments(self) -> _segment_pool.SegmentPool:
        return self._segments


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
        return self._editor_pegboard
