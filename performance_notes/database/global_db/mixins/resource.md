# harness_designer/database/global_db/mixins/resource.py

SQL calls in this module (AST count): 17.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `ResourceMixin.cad_id`: cached after first read.
- `ResourceMixin.image_id`: cached after first read.
- `ResourceMixin.datasheet_id`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
