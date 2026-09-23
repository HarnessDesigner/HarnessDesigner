
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


class StandaloneManager:
    """Bounds manager for a dialog with its own self-contained 3D scene
    (see ui.dialogs.part_orientation.PartOrientationDialog and
    ui.dialogs.housing_editor.HousingEditorDialog) -- exposes a single
    pooled View under ``editor_3d``, the only editor context such a
    dialog ever has, instead of Manager's three. Objects added to the
    dialog's own canvas get their own isolated AABB/OBB pool this way
    rather than sharing (or needlessly allocating) the real mainframe's
    editor_schematic/editor_pegboard pools, which that canvas never uses.
    """

    def __init__(self):
        self._editor_3d = View()

    @property
    def editor_3d(self) -> View:
        return self._editor_3d
