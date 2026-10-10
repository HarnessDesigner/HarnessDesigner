# harness_designer/database/project_db/project.py

SQL calls in this module (AST count): 16.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `Project.name`: cached after first read.
- `Project.description`: cached after first read.
- `Project.creator`: cached after first read.
- `Project.wire_stripe_max_length`: cached after first read.
- `Project.model_id`: cached after first read.
- `Project.bounds_3d`: cached after first read.
- `Project.bounds_schematic`: cached after first read.
- `Project.bounds_pegboard`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
