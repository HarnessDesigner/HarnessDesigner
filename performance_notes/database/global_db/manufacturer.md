# harness_designer/database/global_db/manufacturer.py

SQL calls in this module (AST count): 13.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `ManufacturersTable.choices`: no cache guard found (queries on every read).
- `Manufacturer.address`: cached after first read.
- `Manufacturer.contact_person`: cached after first read.
- `Manufacturer.phone`: cached after first read.
- `Manufacturer.ext`: cached after first read.
- `Manufacturer.email`: cached after first read.
- `Manufacturer.website`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
