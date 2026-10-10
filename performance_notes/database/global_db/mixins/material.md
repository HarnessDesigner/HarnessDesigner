# harness_designer/database/global_db/mixins/material.py

SQL calls in this module (AST count): 8.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `MaterialMixin.material`: cached after first read.
- `MaterialMixin.material_id`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
