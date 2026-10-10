# harness_designer/database/project_db/mixins/housing.py

SQL calls in this module (AST count): 2.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `HousingMixin.housing_id`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
