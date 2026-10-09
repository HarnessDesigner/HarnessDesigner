# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union

from ... import check_types as _check_types


if TYPE_CHECKING:
    from ..global_db import bases as _glb_bases
    from ..project_db import pjt_bases as _pjt_bases


class LazyTabMixin:
    """Defer per-tab DB queries until the tab is first shown.

    Mix this in alongside QTabWidget. Call _init_lazy_tabs() at the end
    of __init__, and call _lazy_set_obj(db_obj) from set_obj.
    Subclasses must implement _load_tab(index).
    """

    @_check_types.do
    def _init_lazy_tabs(self) -> None:
        self._tab_loaded = []
        self.currentChanged.connect(self._on_tab_changed)

    @_check_types.do
    def _lazy_set_obj(
        self, db_obj: _Union["_glb_bases.EntryBase", "_pjt_bases.PJTEntryBase"]
    ) -> None:
        self.db_obj = db_obj
        self._tab_loaded = [False] * self.count()
        self._load_tab(self.currentIndex())

    @_check_types.do
    def _on_tab_changed(self, index: int) -> None:
        if not self._tab_loaded[index]:
            self._load_tab(index)

    @_check_types.do
    def _load_tab(self, index: int) -> None:
        raise NotImplementedError
