# harness_designer/database/global_db/temperature.py

SQL calls in this module (AST count): 1.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `TemperaturesTable.choices`: no cache guard found (queries on every read).


Status: static read of the code only. Nothing here has been profiled.
