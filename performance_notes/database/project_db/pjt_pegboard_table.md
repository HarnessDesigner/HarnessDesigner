# harness_designer/database/project_db/pjt_pegboard_table.py

SQL calls in this module (AST count): 5.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTPegboardTable.anchor`: cached after first read.
- `PJTPegboardTable.size`: cached after first read.
- `PJTPegboardTable.visible_columns`: cached after first read.

## Functions that issue SQL inside a loop
Each iteration makes its own query. Batching these outside the loop is the first thing to measure.
- `PJTPegboardTable.anchor`.


Status: static read of the code only. Nothing here has been profiled.
