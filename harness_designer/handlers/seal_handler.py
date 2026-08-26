# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Compatibility-lookup helpers for placing seals, reused by
``objects.objects_3d.seal.Seal.start_add`` (see
``add_handlers.editor_3d.seal`` for the actual interactive placement
session, which replaced this module's own former ``AddSealHandler``).
"""

from ..objects import terminal as _terminal
from .. import check_types as _check_types


@_check_types.do
def _find_attached_wire_part(mainframe, terminal: _terminal.Terminal):
    """Return the global wire part attached to *terminal*'s wire pin, or None."""
    pjt_terminal = terminal.db_obj
    wire_point3d_id = pjt_terminal.table.select(
        'wire_point3d_id', id=pjt_terminal.db_id)[0][0]

    if wire_point3d_id is None:
        return None

    pjt_wires_table = pjt_terminal.table.db.pjt_wires_table
    pjt_wires_table.execute(
        'SELECT part_id FROM pjt_wires '
        'WHERE start_point3d_id=? OR stop_point3d_id=? LIMIT 1;',
        (wire_point3d_id, wire_point3d_id))

    rows = pjt_wires_table.fetchall()
    if not rows:
        return None

    return mainframe.global_db.wires_table[rows[0][0]]


@_check_types.do
def _get_terminal_seal_pns(mainframe, terminal: _terminal.Terminal):
    """Return seal part numbers usable on *terminal*'s pin.

    The seal's OD (outer diameter — the part that sits in the cavity around
    the terminal) must always be larger than the terminal's footprint (max
    of width/height) or the seal won't fit snugly around the terminal.  When
    the terminal lists compatible seals, that list is used (narrowed further
    by wire diameter when a wire is already attached to the pin).  Otherwise
    the seals table is searched directly for Single Wire Seals, again
    narrowed by wire diameter when a wire is attached.

    Wire-diameter matching prefers the seal's explicit ``wire_size_dia_min``/
    ``wire_size_dia_max`` range.  When either bound is ``NULL``, it falls
    back to a range derived from the seal's ID/OD: the wire must be larger
    than the ID (so the seal grips it) and smaller than the midpoint between
    ID and OD (so the seal wall isn't stretched past half its own thickness).
    E.g. ID=5, OD=10 → derived usable range is (5, 7.5).
    """
    term_part = terminal.db_obj.part
    if term_part is None:
        return []

    term_size = max(term_part.width or 0.0, term_part.height or 0.0)
    compat_pns = [pn for pn in term_part.compat_seals_array if pn]

    wire_part = _find_attached_wire_part(mainframe, terminal)

    if wire_part is None:
        wire_od = None
    else:
        wire_od = wire_part.od_mm

    clauses = ['s.o_dia > ?']
    params = [term_size]

    if wire_od is not None:
        clauses.append(
            '((s.wire_size_dia_min IS NOT NULL AND ? >= s.wire_size_dia_min) '
            'OR (s.wire_size_dia_min IS NULL AND ? > s.i_dia))')
        params.extend([wire_od, wire_od])

        clauses.append(
            '((s.wire_size_dia_max IS NOT NULL AND ? <= s.wire_size_dia_max) '
            'OR (s.wire_size_dia_max IS NULL '
            'AND ? < (s.i_dia + (s.o_dia - s.i_dia) / 2.0)))')
        params.extend([wire_od, wire_od])

    table = mainframe.global_db.seals_table

    if compat_pns:
        placeholders = ', '.join('?' for _ in compat_pns)
        clauses.append(f's.part_number IN ({placeholders})')
        params.extend(compat_pns)

        table.execute(
            'SELECT DISTINCT s.part_number FROM seals s '
            f'WHERE {" AND ".join(clauses)};',
            tuple(params))
    else:
        clauses.append(
            '(UPPER(st.name) = "SWS" OR UPPER(st.name) = "SINGLE WIRE SEAL")')

        table.execute(
            'SELECT DISTINCT s.part_number FROM seals s '
            'JOIN seal_types st ON s.type_id = st.id '
            f'WHERE {" AND ".join(clauses)};',
            tuple(params))

    return [row[0] for row in table.fetchall()]
