# harness_designer/database/global_db/housing.py

SQL calls in this module (AST count): 60.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `Housing.compat_covers`: cached after first read.
- `Housing.compat_covers_array`: cached after first read.
- `Housing.compat_boots`: cached after first read.
- `Housing.compat_boots_array`: cached after first read.
- `Housing.compat_cpas`: cached after first read.
- `Housing.compat_cpas_array`: cached after first read.
- `Housing.compat_tpas`: cached after first read.
- `Housing.compat_tpas_array`: cached after first read.
- `Housing.ip_rating_id`: cached after first read.
- `Housing.cavity_lock_id`: cached after first read.
- `Housing.seal_type_id`: cached after first read.
- `Housing.cpa_lock_type_id`: cached after first read.
- `Housing.terminal_sizes`: cached after first read.
- `Housing.terminal_size_counts`: cached after first read.
- `Housing.sealing`: cached after first read.
- `Housing.centerline`: cached after first read.
- `Housing.rows`: cached after first read.
- `Housing.num_pins`: cached after first read.
- `Housing.cavities`: cached after first read.
- `Housing.cover_position3d`: cached after first read.
- `Housing.seal_position3d`: cached after first read.
- `Housing.boot_position3d`: cached after first read.
- `Housing.tpa_lock_1_position3d`: cached after first read.
- `Housing.tpa_lock_2_position3d`: cached after first read.
- `Housing.cpa_lock_position3d`: cached after first read.
- `Housing.angle3d`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
