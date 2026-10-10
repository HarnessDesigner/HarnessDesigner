# harness_designer/database/global_db/terminal.py

SQL calls in this module (AST count): 38.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `Terminal.compat_seals`: no cache guard found (queries on every read).
- `Terminal.sealing`: cached after first read.
- `Terminal.blade_size`: cached after first read.
- `Terminal.resistance`: cached after first read.
- `Terminal.mating_cycles`: cached after first read.
- `Terminal.max_vibration_g`: cached after first read.
- `Terminal.max_current_ma`: cached after first read.
- `Terminal.round_terminal`: cached after first read.
- `Terminal.length`: cached after first read.
- `Terminal.width`: cached after first read.
- `Terminal.height`: cached after first read.
- `Terminal.scale`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
