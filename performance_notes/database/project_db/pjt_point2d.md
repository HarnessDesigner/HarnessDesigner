# harness_designer/database/project_db/pjt_point2d.py

SQL calls in this module (AST count): 19.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTPoint2D.x`: cached after first read.
- `PJTPoint2D.y`: cached after first read.
- `PJTPoint2D.z`: cached after first read.
- `PJTPoint2D.point`: no cache guard found (queries on every read).

## Load-time functions
These run when the database is opened or built, not on every interaction.
- `PJTPoints2DTable._update_table_in_db`.


Status: static read of the code only. Nothing here has been profiled.
