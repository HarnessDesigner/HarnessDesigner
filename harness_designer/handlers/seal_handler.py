# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Compatibility-lookup helpers for placing seals, reused by
``objects.objects_3d.seal.Seal.start_add`` (see
``add_handlers.editor_3d.seal`` for the actual interactive placement
session, which replaced this module's own former ``AddSealHandler``).
"""

from typing import TYPE_CHECKING, Union as _Union

from ..objects import terminal as _terminal
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..ui.dialogs import part_search as _part_search
    from ..database.global_db import wire as _global_wire
    from ..database.global_db import seal as _global_seal
    from .. import ui as _ui


# A housing's own seal_type is MAT whenever it's none of these -- see
# objects.objects_3d.seal.Seal.start_add's housing dispatch and
# objects.objects_3d.housing.HousingMenu's "Add Mat Seal" visibility
# gate, both of which need the same classification.
NON_MAT_SEAL_TYPE_NAMES = frozenset({'dummy terminal', 'plug', 'sws', 'single wire seal'})


@_check_types.do
def is_mat_seal_type(type_name: str) -> bool:
    """Whether *type_name* (a seal or housing seal-type's own ``.name``)
    counts as MAT -- i.e. is none of :data:`NON_MAT_SEAL_TYPE_NAMES`.
    """
    return type_name.strip().lower() not in NON_MAT_SEAL_TYPE_NAMES


@_check_types.do
def _find_attached_wire_part(mainframe: "_ui.MainFrame",
                              terminal: _terminal.Terminal) -> _Union["_global_wire.Wire", None]:
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
def terminal_seal_search_params(
    mainframe: "_ui.MainFrame", terminal: _terminal.Terminal
) -> _Union["_part_search.SearchParameters", None]:

    """Seal search-box seed for *terminal*'s pin.

    The seal's OD (outer diameter — the part that sits in the cavity around
    the terminal) must always be larger than the terminal's footprint (max
    of width/height) or the seal won't fit snugly around the terminal.  When
    the terminal lists compatible seals, that's seeded as a part-number
    filter (narrowed further by wire diameter when a wire is already
    attached to the pin).  Otherwise the seed filters to Single Wire Seals,
    again narrowed by wire diameter when a wire is attached.

    Wire-diameter matching is seeded against the seal's explicit
    ``wire_size_dia_min``/``wire_size_dia_max`` range only -- the old SQL
    version of this search also fell back, for a seal with either bound
    left ``NULL``, to a range derived from that seal's ID/OD (wire larger
    than the ID, smaller than the ID/OD midpoint). That fallback needs a
    per-row computed bound (``i_dia + (o_dia - i_dia) / 2``) compared
    against a column from a DIFFERENT seal than the explicit-bound check,
    which the search-box grammar has no way to express (it only compares
    one column to a literal value, and only ANDs different columns
    together, never ORs across two of them) -- so a seal relying on that
    derived range just won't turn up from the seed. It's still reachable
    by hand in the dialog itself (clear/widen the wire-diameter bound),
    same as every other approximate seed in this module.
    """
    term_part = terminal.db_obj.part
    if term_part is None:
        return None

    from ..ui.dialogs import part_search as _part_search

    term_size = max(term_part.width or 0.0, term_part.height or 0.0)
    compat_pns = [pn for pn in term_part.compat_seals_array if pn]

    wire_part = _find_attached_wire_part(mainframe, terminal)

    if wire_part is None:
        wire_od = None
    else:
        wire_od = wire_part.od_mm

    if compat_pns:
        params = _part_search.SearchParameters.from_part_numbers(compat_pns)
    else:
        params = _part_search.SearchParameters()
        params.add('type_id', _part_search.SearchTerm(phrase='SWS'))
        params.add('type_id', _part_search.SearchTerm(phrase='Single Wire Seal'))

    if term_size > 0.0:
        params.add('o_dia', _part_search.SearchTerm(operator='>', value=str(term_size)))

    if wire_od is not None:
        params.add('wire_size_dia_min', _part_search.SearchTerm(operator='<=', value=str(wire_od)))
        params.add('wire_size_dia_max', _part_search.SearchTerm(operator='>=', value=str(wire_od)))

    return params


@_check_types.do
def wire_seal_fit_ok(mainframe: "_ui.MainFrame", terminal: _terminal.Terminal,
                      seal_part: "_global_seal.Seal") -> bool:
    """Whether *seal_part* (an SWS/single-wire-seal global part) fits
    the wire actually attached to *terminal*'s pin.

    Same bounds :func:`_get_terminal_seal_pns` already uses to build
    its own SQL ``WHERE`` clause (explicit ``wire_size_dia_min``/``max``
    when set, otherwise a range derived from the seal's own ID/OD) --
    kept here as the equivalent Python-side per-part check, since this
    is evaluated once per candidate terminal DURING an interactive snap
    session (to decide its highlight color), not as a SQL filter over
    the whole catalog.

    ``True`` when *terminal* has no wire attached yet -- nothing to
    flag as a mismatch against.
    """
    wire_part = _find_attached_wire_part(mainframe, terminal)
    if wire_part is None:
        return True

    wire_od = wire_part.od_mm
    if wire_od is None:
        return True

    dia_min = seal_part.wire_size_dia_min
    if dia_min is not None:
        if wire_od < dia_min:
            return False
    elif wire_od <= seal_part.i_dia:
        return False

    dia_max = seal_part.wire_size_dia_max
    if dia_max is not None:
        if wire_od > dia_max:
            return False
    else:
        derived_high = seal_part.i_dia + (seal_part.o_dia - seal_part.i_dia) / 2.0
        if wire_od >= derived_high:
            return False

    return True
