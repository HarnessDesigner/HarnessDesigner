# harness_designer/database/global_db/mixins/manufacturer.py

SQL calls in this module (AST count): 9.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `ManufacturerMixin.manufacturer`: cached after first read.
- `ManufacturerMixin.mfg_id`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
