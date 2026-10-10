# harness_designer/database/global_db/bases.py

SQL calls in this module (AST count): 29.

## Functions that issue SQL inside a loop
Each iteration makes its own query. Batching these outside the loop is the first thing to measure.
- `TableBase.__getitem__`.
- `TableBase.__iter__`.
- `TableBase.export_as_json`.


Status: static read of the code only. Nothing here has been profiled.
