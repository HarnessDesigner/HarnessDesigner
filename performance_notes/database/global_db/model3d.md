# harness_designer/database/global_db/model3d.py

SQL calls in this module (AST count): 38.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `Model3D.data_path`: no cache guard found (queries on every read).
- `Model3D.path`: cached after first read.
- `Model3D.uuid`: cached after first read.
- `Model3D.vertex_count`: cached after first read.
- `Model3D.aabb`: no cache guard found (queries on every read).
- `Model3D.obb`: cached after first read.
- `Model3D.file_type_id`: cached after first read.
- `Model3D.angle3d`: no cache guard found (queries on every read).
- `Model3D.position3d`: cached after first read.
- `Model3D.scale`: cached after first read.
- `Model3D.forward_up`: cached after first read.
- `Model3D.target_count`: cached after first read.
- `Model3D.aggressiveness`: cached after first read.
- `Model3D.update_rate`: cached after first read.
- `Model3D.simplify`: cached after first read.
- `Model3D.iterations`: cached after first read.

## Load-time functions
These run when the database is opened or built, not on every interaction.
- `Model3D.load`.


Status: static read of the code only. Nothing here has been profiled.
