# harness_designer/database/global_db/resource_state.py

SQL calls in this module (AST count): 29.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `ResourceState.image_id`: cached after first read.
- `ResourceState.datasheet_id`: cached after first read.
- `ResourceState.cad_id`: cached after first read.
- `ResourceState.model3d_id`: cached after first read.
- `ResourceState.progress`: cached after first read.
- `ResourceState.claimed_by_host`: cached after first read.
- `ResourceState.claimed_at`: cached after first read.
- `ResourceState.updated_at`: cached after first read.
- `ResourceState.retry_count`: cached after first read.
- `ResourceState.error_step`: cached after first read.
- `ResourceState.error_blob`: cached after first read.
- `ResourceState.error_at`: cached after first read.
- `ResourceState.error_host`: cached after first read.
- `ResourceState.allow_retry`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
