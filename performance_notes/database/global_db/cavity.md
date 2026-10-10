# harness_designer/database/global_db/cavity.py

SQL calls in this module (AST count): 51.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `Cavity.housing_id`: cached after first read.
- `Cavity.idx`: cached after first read.
- `Cavity.terminal_sizes`: cached after first read.
- `Cavity.position3d`: cached after first read.
- `Cavity.position2d`: cached after first read.
- `Cavity.angle3d`: cached after first read.
- `Cavity.angle2d`: cached after first read.
- `Cavity.aabb`: cached after first read.
- `Cavity.obb`: cached after first read.
- `Cavity.round_terminal`: cached after first read.
- `Cavity.render_terminal_marker`: cached after first read.
- `Cavity.render_wire_marker`: cached after first read.
- `Cavity.terminal_surf_indices`: cached after first read.
- `Cavity.wire_surf_indices`: cached after first read.
- `Cavity.length`: cached after first read.
- `Cavity.width`: cached after first read.
- `Cavity.height`: cached after first read.
- `Cavity.scale`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
