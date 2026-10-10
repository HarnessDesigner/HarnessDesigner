# harness_designer/database/global_db/mixins/wire_size.py

SQL calls in this module (AST count): 24.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `WireSizeMixin.wire_size_dia_min`: cached after first read.
- `WireSizeMixin.wire_size_dia_max`: cached after first read.
- `WireSizeMixin.wire_size_cross_min`: cached after first read.
- `WireSizeMixin.wire_size_cross_max`: cached after first read.
- `WireSizeMixin.wire_size_awg_min`: cached after first read.
- `WireSizeMixin.wire_size_awg_max`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
