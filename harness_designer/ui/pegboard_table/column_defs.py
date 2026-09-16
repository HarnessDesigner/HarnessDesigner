# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The full catalog of optional columns for the peg-board wire table.

``COLUMN_DEFS`` is a FIXED, STABLE, index-addressed list -- its order must
never change (only append to the end) once shipped, since
``PJTPegboardTable.visible_columns`` stores a project's chosen columns as a
list of ints indexing into this exact list. Reordering or removing an entry
would silently repoint every saved project's column choices at the wrong
column.

Each entry is ``(label, info)`` where ``info`` is either:

- ``{'alias': ..., 'sql': ...}`` -- a real column, directly selectable in
  SQL. ``sql`` is the fully-qualified expression (table alias + column) as
  used in :meth:`WireTable._build_query`'s JOINs.
- ``{'alias': ..., 'computed': True}`` -- one of the circuit aggregate
  columns (resistance, volts, load, voltage drop, weight, length) that
  ``project_db.pjt_circuit.PJTCircuit`` computes by walking terminals/
  splices/wire-service-loops in Python, not something a single JOINed SELECT
  can express. :meth:`WireTable._build_query` still selects a placeholder
  value (the row's own ``circuit_id``) at this column's position so row
  indexing stays aligned with every other column; :meth:`WireTable.
  _get_cell_text` overrides the displayed text for these specific columns by
  looking up the real :class:`PJTCircuit` object and reading the real
  property, ignoring the placeholder.
"""

# Indices into this list are what PJTPegboardTable.visible_columns stores --
# APPEND ONLY, never reorder or remove an existing entry.
COLUMN_DEFS: list[tuple[str, dict]] = [
    ('Part Number', {'alias': 'part_number', 'sql': 'part.part_number'}),  # 0
    ('Description', {'alias': 'description', 'sql': 'part.description'}),  # 1
    ('Mfg', {'alias': 'manufacturer', 'sql': 'mfg.name'}),  # 2
    ('Family', {'alias': 'family', 'sql': 'family.name'}),  # 3
    ('Series', {'alias': 'series', 'sql': 'series.name'}),  # 4
    ('Color', {'alias': 'color', 'sql': 'color.name'}),  # 5
    ('Stripe Color', {'alias': 'stripe_color', 'sql': 'stripe_color.name'}),  # 6
    ('Min Temp (°F)', {'alias': 'min_temp', 'sql': 'min_temp.name'}),  # 7
    ('Max Temp (°F)', {'alias': 'max_temp', 'sql': 'max_temp.name'}),  # 8
    ('Jacket Material', {'alias': 'material', 'sql': 'material.name'}),  # 9
    ('Core Material', {'alias': 'core_material', 'sql': 'core_material.description'}),  # 10
    ('Conductor Count', {'alias': 'num_conductors', 'sql': 'part.num_conductors'}),  # 11
    ('Shielded', {'alias': 'shielded', 'sql': 'part.shielded'}),  # 12
    ('TPI', {'alias': 'tpi', 'sql': 'part.tpi'}),  # 13
    ('Size (dia mm)', {'alias': 'wire_size_dia', 'sql': 'part.wire_size_dia'}),  # 14
    ('Size (mm²)', {'alias': 'wire_size_cross', 'sql': 'part.wire_size_cross'}),  # 15
    ('Size (AWG)', {'alias': 'wire_size_awg', 'sql': 'part.wire_size_awg'}),  # 16
    ('OD (mm)', {'alias': 'od_mm', 'sql': 'part.od_mm'}),  # 17
    ('Strand Count', {'alias': 'strands', 'sql': 'part.strands'}),  # 18
    ('Filler Wire', {'alias': 'is_filler_wire', 'sql': 't.is_filler_wire'}),  # 19
    ('Notes', {'alias': 'wire_notes', 'sql': 't.notes'}),  # 20
    ('Circuit Number', {'alias': 'circuit_num', 'sql': 'circuit.circuit_num'}),  # 21
    ('Circuit Name', {'alias': 'circuit_name', 'sql': 'circuit.name'}),  # 22
    ('Circuit Notes', {'alias': 'circuit_notes', 'sql': 'circuit.notes'}),  # 23
    ('Circuit Description', {'alias': 'circuit_description', 'sql': 'circuit.description'}),  # 24
    ('Circuit Resistance', {'alias': 'circuit_resistance', 'computed': True}),  # 25
    ('Circuit Volts (V)', {'alias': 'circuit_volts', 'computed': True}),  # 26
    ('Circuit Load (ma)', {'alias': 'circuit_load', 'computed': True}),  # 27
    ('Circuit Voltage Drop (V)', {'alias': 'circuit_voltage_drop', 'computed': True}),  # 28
    ('Circuit Voltage Drop (%)', {'alias': 'circuit_voltage_drop_pct', 'computed': True}),  # 29
    ('Circuit Weight', {'alias': 'circuit_weight', 'computed': True}),  # 30
    ('Circuit Length', {'alias': 'circuit_length', 'computed': True}),  # 31
]

# Shown when a peg-board table has never had its column selection saved
# (PJTPegboardTable.visible_columns == []) -- matches the columns asked for
# when this table was first proposed: circuit number, circuit name,
# manufacturer, part number ("wire model number"), AWG, mm².
DEFAULT_VISIBLE_COLUMNS: list[int] = [21, 22, 2, 0, 16, 15]

# Reverse lookup (SQL alias -> COLUMN_DEFS index), used to translate a
# dragged header's new logical-column order back into COLUMN_DEFS indices
# for PJTPegboardTable.visible_columns.
ALIAS_TO_DEF_INDEX: dict[str, int] = {
    info['alias']: i for i, (_label, info) in enumerate(COLUMN_DEFS)
}
