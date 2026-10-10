# harness_designer/database/global_db/app_users.py

SQL calls in this module (AST count): 4.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `AppUser.mysql_account`: cached after first read.
- `AppUser.display_name`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
