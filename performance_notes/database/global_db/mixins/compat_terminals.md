# harness_designer/database/global_db/mixins/compat_terminals.py

SQL calls in this module (AST count): 4.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `CompatTerminalsMixin.compat_terminals`: cached after first read.
- `CompatTerminalsMixin.compat_terminals_array`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
