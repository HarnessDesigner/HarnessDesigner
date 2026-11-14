# harness_designer/database/global_db/mixins/base.py

Column mixin. 1 property getters read through `self._table.select('col', id=...)`, which `TableBase.select` answers from the per-wrapper row cache (one `SELECT` of the whole row when the wrapper is created, dropped when the wrapper is garbage collected). Reads after that are dict lookups; see `database/README.md`.
