# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Wire-compat-lookup helpers reused by the object-owned wire
add-handlers (``add_handlers.editor_3d.wire``/``add_handlers.editor_
schematic.wire``/``add_handlers.editor_pegboard.wire``), which replaced
this module's own former ``AddWireHandler``.

Genuinely view-agnostic (a terminal's/splice's own crimp-range lookup
against the global wires table, no view-specific object access at all) --
unlike ``_wire_layout_end_wire``/``merge_wire_into``/``_pick_free_end``,
which used to live here too but were 3D-hardcoded despite peg-board
needing them just as much (peg-board's own ``WireMenu`` was already
calling ``_pick_free_end``, silently wrong whenever both ends were free).
Moved to ``handlers.wire_drag_base.WireDragMixin`` (2026-09-13) as
``wire_layout_end_wire``/``merge_wire_into``/``pick_free_end`` -- this
``handlers`` package is for view-agnostic code only; those three
genuinely need a specific view's own accessors, so they belong on the
class that already carries that contract, not here.
"""

from .. import check_types as _check_types


@_check_types.do
def _get_terminal_compat_pns(mainframe, terminal_obj):
    """Return wire part numbers whose outer diameter fits *terminal_obj*'s crimp range."""
    term_part = terminal_obj.db_obj.part
    if term_part is None:
        return []

    dia_min = term_part.wire_size_dia_min
    dia_max = term_part.wire_size_dia_max

    if dia_min is None and dia_max is None:
        return []

    table = mainframe.global_db.wires_table

    if dia_min is not None and dia_max is not None:
        table.execute(
            'SELECT part_number FROM wires WHERE od_mm>=? AND od_mm<=?;',
            (dia_min, dia_max))
    elif dia_min is not None:
        table.execute(
            'SELECT part_number FROM wires WHERE od_mm>=?;', (dia_min,))
    else:
        table.execute(
            'SELECT part_number FROM wires WHERE od_mm<=?;', (dia_max,))

    return [row[0] for row in table.fetchall()]


@_check_types.do
def _get_splice_compat_pns(mainframe, splice_obj):
    """Return wire part numbers whose outer diameter fits *splice_obj*'s crimp range."""
    splice_part = splice_obj.db_obj.part
    if splice_part is None:
        return []

    dia_min = splice_part.wire_size_dia_min
    dia_max = splice_part.wire_size_dia_max

    if dia_min is None and dia_max is None:
        return []

    table = mainframe.global_db.wires_table

    if dia_min is not None and dia_max is not None:
        table.execute(
            'SELECT part_number FROM wires WHERE od_mm>=? AND od_mm<=?;',
            (dia_min, dia_max))
    elif dia_min is not None:
        table.execute(
            'SELECT part_number FROM wires WHERE od_mm>=?;', (dia_min,))
    else:
        table.execute(
            'SELECT part_number FROM wires WHERE od_mm<=?;', (dia_max,))

    return [row[0] for row in table.fetchall()]
