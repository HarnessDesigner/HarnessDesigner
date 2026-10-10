# harness_designer/database/global_db/tpa_lock.py

SQL calls in this module (AST count): 6.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `TPALock.pins`: cached after first read.
- `TPALock.lock_type`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
