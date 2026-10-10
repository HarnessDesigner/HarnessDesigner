# harness_designer/database/global_db/mixins/adhesive.py

SQL calls in this module (AST count): 4.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `AdhesiveMixin.adhesives`: cached after first read.
- `AdhesiveMixin.adhesive_ids`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
