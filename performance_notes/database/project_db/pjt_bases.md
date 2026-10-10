# harness_designer/database/project_db/pjt_bases.py

SQL calls in this module (AST count): 22.

## Functions that issue SQL inside a loop
Each iteration makes its own query. Batching these outside the loop is the first thing to measure.
- `PJTTableBase.__getitem__`.
- `PJTTableBase.__iter__`.


Status: static read of the code only. Nothing here has been profiled.
