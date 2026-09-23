# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Wire-compat search-param builders reused by the object-owned wire
add-handlers (``add_handlers.editor_3d.wire``/``add_handlers.editor_
schematic.wire``/``add_handlers.editor_pegboard.wire``), which replaced
this module's own former ``AddWireHandler``.

Genuinely view-agnostic (a terminal's/splice's own crimp-range against
the global wires table, no view-specific object access at all) --
unlike ``_wire_layout_end_wire``/``merge_wire_into``/``_pick_free_end``,
which used to live here too but were 3D-hardcoded despite peg-board
needing them just as much (peg-board's own ``WireMenu`` was already
calling ``_pick_free_end``, silently wrong whenever both ends were free).
Moved to ``handlers.wire_drag_base.WireDragMixin`` (2026-09-13) as
``wire_layout_end_wire``/``merge_wire_into``/``pick_free_end`` -- this
``handlers`` package is for view-agnostic code only; those three
genuinely need a specific view's own accessors, so they belong on the
class that already carries that contract, not here.

These used to eagerly run a ``SELECT part_number FROM wires WHERE
od_mm...`` query and hand the whole compat part-number list to the
search dialog as ``SearchParameters.from_part_numbers(...)`` -- a
`part_number: "PN1","PN2",...` clause with one entry per matching wire,
which could run into the thousands and was crashing the dialog. It also
compared the wrong quantity: ``od_mm`` on the wires table is the wire's
full INSULATED outer diameter, but a terminal's/splice's own
``wire_size_dia_min``/``_max`` (and the ``wire_size_cross_min``/``_max``/
``wire_size_awg_min``/``_max`` always kept in lock-step with them -- see
``database.global_db.mixins.wire_size.WireSizeMixin``) describe the bare
CONDUCTOR crimp range, a different physical quantity entirely.

The wires table's own ``wire_size_cross`` column (bare-conductor
cross-section, mm²) is what's actually comparable to a terminal's/
splice's ``wire_size_cross_min``/``_max``, and -- unlike AWG -- it's
monotonic the same direction (bigger number == bigger wire, so a plain
``>=``/``<=`` range works without inverting the operators the way AWG's
"smaller number is bigger wire" convention would need). So there's no
need to pre-fetch matching rows at all -- these just seed the search box
with the terminal's/splice's own min/max crimp cross-section as a
``wire_size_cross`` range, and the dialog runs that query itself (see
``ui.dialogs.part_search``).
"""
from typing import TYPE_CHECKING, Union

from .. import check_types as _check_types

if TYPE_CHECKING:
    from ..ui.dialogs import part_search as _part_search


@_check_types.do
def _wire_cross_search_params(
    cross_min: float | None, cross_max: float | None
) -> Union["_part_search.SearchParameters", None]:

    """Build a ``wire_size_cross`` min/max range search-box seed, or
    None if neither bound is known."""

    if cross_min is None and cross_max is None:
        return None

    from ..ui.dialogs import part_search as _part_search

    terms = []
    if cross_min is not None:
        terms.append(_part_search.SearchTerm(operator='>=', value=str(cross_min)))

    if cross_max is not None:
        terms.append(_part_search.SearchTerm(operator='<=', value=str(cross_max)))

    params = _part_search.SearchParameters()
    params.add('wire_size_cross', *terms)

    return params


@_check_types.do
def terminal_wire_search_params(terminal_obj) -> Union["_part_search.SearchParameters", None]:
    """Wire cross-section range search-box seed for *terminal_obj*'s crimp range."""

    term_part = terminal_obj.db_obj.part
    if term_part is None:
        return None

    return _wire_cross_search_params(
        term_part.wire_size_cross_min, term_part.wire_size_cross_max)


@_check_types.do
def splice_wire_search_params(splice_obj) -> Union["_part_search.SearchParameters", None]:
    """Wire cross-section range search-box seed for *splice_obj*'s crimp range."""

    splice_part = splice_obj.db_obj.part
    if splice_part is None:
        return None

    return _wire_cross_search_params(
        splice_part.wire_size_cross_min, splice_part.wire_size_cross_max)
