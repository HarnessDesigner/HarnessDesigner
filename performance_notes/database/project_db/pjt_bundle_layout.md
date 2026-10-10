# harness_designer/database/project_db/pjt_bundle_layout.py

SQL calls in this module (AST count): 5.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `PJTBundleLayout.position3d_id`: cached after first read.
- `PJTBundleLayout.position_pegboard_id`: cached after first read.
- `PJTBundleLayout.attached_bundles`: no cache guard found (queries on every read).


Status: static read of the code only. Nothing here has been profiled.
