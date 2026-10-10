# harness_designer/database/global_db/mixins/compat_housings.py

SQL calls in this module (AST count): 4.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `CompatHousingsMixin.compat_housings`: cached after first read.
- `CompatHousingsMixin.compat_housings_array`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
