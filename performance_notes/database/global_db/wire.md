# harness_designer/database/global_db/wire.py

SQL calls in this module (AST count): 32.

## Property getters that issue SQL
A property read runs a query unless a cache branch returns first. Each getter below is listed with whether it has the `DefaultStoredValue` cache guard.
- `Wire.resistance_1km`: cached after first read.
- `Wire.weight_1km`: cached after first read.
- `Wire.volts`: cached after first read.
- `Wire.od_mm`: cached after first read.
- `Wire.shielded`: cached after first read.
- `Wire.strands`: cached after first read.
- `Wire.tpi`: cached after first read.
- `Wire.num_conductors`: cached after first read.
- `Wire.core_material_id`: cached after first read.
- `Wire.conductor_dia_mm`: cached after first read.
- `Wire.size_mm2`: cached after first read.
- `Wire.size_awg`: cached after first read.
- `Wire.stripe_color_id`: cached after first read.


Status: static read of the code only. Nothing here has been profiled.
