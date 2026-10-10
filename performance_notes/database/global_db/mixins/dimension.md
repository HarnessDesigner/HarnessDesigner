# harness_designer/database/global_db/mixins/dimension.py

SQL calls in this module (AST count): 12.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `DimensionMixin.scale`: cached after first read.
- `DimensionMixin.length`: cached after first read.
- `DimensionMixin.width`: cached after first read.
- `DimensionMixin.height`: cached after first read.
- `DimensionMixin.size`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
