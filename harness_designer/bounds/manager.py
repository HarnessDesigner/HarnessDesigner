# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import aabb as _aabb
from . import obb as _obb
from . import segment_pool as _segment_pool
from .. import check_types as _check_types


class View:

    @_check_types.do
    def __init__(self):
        self._aabb = _aabb.AABB()
        self._obb = _obb.OBB()
        self._segments = _segment_pool.SegmentPool()

    @_check_types.do
    def reset(self) -> None:
        """Empty every pool of this view, in place."""
        self._aabb.reset()
        self._obb.reset()
        self._segments.reset()

    @property
    @_check_types.do
    def aabb(self) -> _aabb.AABB:
        return self._aabb

    @property
    @_check_types.do
    def obb(self) -> _obb.OBB:
        return self._obb

    @property
    @_check_types.do
    def segments(self) -> _segment_pool.SegmentPool:
        return self._segments


class Manager:

    @_check_types.do
    def __init__(self):
        self._editor_3d = View()
        self._editor_schematic = View()
        self._editor_pegboard = View()

    @_check_types.do
    def reset(self) -> None:
        """Empty every view's pools, in place -- the View objects (and the
        pools inside them) are what canvases/objects hold references to,
        so they must stay the same objects. Called when a project unloads.
        """
        self._editor_3d.reset()
        self._editor_schematic.reset()
        self._editor_pegboard.reset()

    @property
    @_check_types.do
    def editor_3d(self) -> View:
        return self._editor_3d

    @property
    @_check_types.do
    def editor_schematic(self) -> View:
        return self._editor_schematic

    @property
    @_check_types.do
    def editor_pegboard(self) -> View:
        return self._editor_pegboard
