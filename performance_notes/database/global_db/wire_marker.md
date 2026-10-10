# harness_designer/database/global_db/wire_marker.py

SQL calls in this module (AST count): 10.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `WireMarker.weight`: cached after first read.
- `WireMarker.has_label`: cached after first read.
- `WireMarker.min_diameter`: cached after first read.
- `WireMarker.max_diameter`: cached after first read.
- `WireMarker.length`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
