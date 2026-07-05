# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>


class LazyTabMixin:
    """Defer per-tab DB queries until the tab is first shown.

    Mix this in alongside QTabWidget. Call _init_lazy_tabs() at the end
    of __init__, and call _lazy_set_obj(db_obj) from set_obj.
    Subclasses must implement _load_tab(index).
    """

    def _init_lazy_tabs(self):
        self._tab_loaded = []
        self.currentChanged.connect(self._on_tab_changed)

    def _lazy_set_obj(self, db_obj):
        self.db_obj = db_obj
        self._tab_loaded = [False] * self.count()
        self._load_tab(self.currentIndex())

    def _on_tab_changed(self, index: int):
        if not self._tab_loaded[index]:
            self._load_tab(index)

    def _load_tab(self, index: int):
        raise NotImplementedError
