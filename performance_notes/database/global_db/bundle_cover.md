# harness_designer/database/global_db/bundle_cover.py

SQL calls in this module (AST count): 17.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `BundleCover.rigidity`: cached after first read.
- `BundleCover.shrink_temp_id`: cached after first read.
- `BundleCover.shrink_ratio`: cached after first read.
- `BundleCover.wall`: cached after first read.
- `BundleCover.min_dia`: cached after first read.
- `BundleCover.max_dia`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
