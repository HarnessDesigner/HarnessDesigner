# harness_designer/ui/editor_db/wire.py

## `WiresPage._get_icon` - swatch built on demand, cached per row, never evicted
Each wire row gets a generated swatch via `image.images.build_wire` the first time the row is painted. The result goes into the base class's `bitmap_indexes`, so a row is rendered once per filter/sort generation. Painting the same row again is a dict hit. The cost is a single `build_wire` call per distinct visible row, which is acceptable. The cache is unbounded for the same reason as in [base.md](base.md): it is only cleared on filter/sort changes.

## `WiresPage._get_icon` - `get_row` on the hot path
The override calls `self.get_row(row_id)` for every `DecorationRole` request. A cache hit is O(1). A miss triggers the paged SQL fetch described in [base.md](base.md), so the override inherits that cost, not a new one.
