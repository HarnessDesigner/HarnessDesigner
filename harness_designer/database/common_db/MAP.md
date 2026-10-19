## FILES

#### __init__.py

Package init; no real logic of its own.

#### callback.py

`CallbackMixin` and `Callback` — callback registration plumbing for database-backed model objects, letting a row's own object wrapper bind to property-change notifications. This is the mechanism `_update_position3d`-style cascades and the object-editor `*Control` widgets rely on; both `global_db/bases.py`'s `EntryBase` and `project_db/pjt_bases.py`'s `PJTEntryBase` mix it in.

#### lazy_tab_mixin.py

`LazyTabMixin` — lazy per-tab DB table loading, deferring building a table's control widget/data until its tab is actually shown.
