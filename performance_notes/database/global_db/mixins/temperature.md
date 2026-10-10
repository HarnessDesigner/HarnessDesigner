# harness_designer/database/global_db/mixins/temperature.py

SQL calls in this module (AST count): 14.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `TemperatureMixin.min_temp`: cached after first read.
- `TemperatureMixin.min_temp_id`: cached after first read.
- `TemperatureMixin.max_temp`: cached after first read.
- `TemperatureMixin.max_temp_id`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
