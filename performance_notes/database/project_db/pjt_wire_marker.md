# harness_designer/database/project_db/pjt_wire_marker.py

SQL calls in this module (AST count): 4.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTWireMarker.wire_id`: cached after first read.
- `PJTWireMarker.label`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
