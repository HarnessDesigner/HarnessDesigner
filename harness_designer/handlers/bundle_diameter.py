# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Bundle diameter calculation -- shared by the 3D and peg-board views
(a bundle's own physical diameter is a single project fact, not a
per-view rendering choice, so both read it from here rather than each
deriving its own).

**The rule (user, 2026-10-01).** A bundle's diameter is the larger of
two things: the diameter its own wires actually need, and -- when
either of its ends is plugged into a transition branch -- that branch's
own catalog minimum hole size (``part.min_dia``; the bundle can never be
rendered thinner than a hole it has to pass through). When the
wire-driven diameter is ITSELF bigger than that floor, the bundle is not
squeezed down to fit -- instead the branch's own *project-level*
``diameter`` (the value it's actually set to right now, within its
catalog ``min_dia``/``max_dia`` range -- not the catalog range itself)
grows to meet the bundle: "If the diameter of the bundle [is] not able
to shrink down small enough to align with the smallest diameter of the
transition branch then the bundle diameter should be set to its
minimum and the transition branch[']s diameter should increase to meet
the minimum size of the bundle." This is symmetric, not a one-way
ratchet: :func:`effective_diameter` keeps every attached branch's own
``diameter`` equal to ``max(wire-driven diameter, branch's own
min_dia)`` every time it runs, so a branch that was previously grown by
a bigger bundle shrinks back down again once the wires no longer need
the room, same as it grows.

**Wire-driven diameter.** Uses the bundle's own concentric
(organized-twist) packing layer diameter when it has one -- an exact,
already-computed figure. Otherwise estimates an "unorganized packing"
diameter from the wires' own OD alone: the diameter of the circle whose
area equals the sum of the wires' own cross-sectional areas
(``sqrt(sum(od**2))`` -- the gap-free, perfect-packing minimum), scaled
up by :data:`Config.unorganized_pack_fudge_factor` to account for the
real gaps a loose, unorganized bundle of wires actually has (deferred by
the user, 2026-09-30/2026-10-01, until the branch-floor rule above was
ready; this is that formula).
"""

from typing import TYPE_CHECKING

import math

from .. import config as _config
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..database.project_db import pjt_bundle as _pjt_bundle
    from ..database.project_db import pjt_transition_branch as _pjt_transition_branch
    from .. import bundle as _bundle_obj


Config = _config.Config.bundle


@_check_types.do
def _wires_diameter(bundle_db_obj: "_pjt_bundle.PJTBundle") -> float | None:
    """The diameter *bundle_db_obj*'s own wires need, or ``None`` if it
    has no wires at all -- an empty/skeleton bundle has no wire-driven
    floor, only whatever an attached branch's own minimum dictates (see
    :func:`effective_diameter`).
    """
    concentric = bundle_db_obj.concentric
    if concentric is not None:
        layers = concentric.layers
        if layers:
            return layers[-1].diameter

    wires = bundle_db_obj.wires
    if not wires:
        return None

    area_equivalent = math.sqrt(sum(wire.part.od_mm ** 2 for wire in wires))
    return area_equivalent * Config.unorganized_pack_fudge_factor


@_check_types.do
def _attached_branches(
    bundle_db_obj: "_pjt_bundle.PJTBundle"
) -> list["_pjt_transition_branch.PJTTransitionBranch"]:
    """Every transition branch *bundle_db_obj*'s own start or stop end
    plugs into directly -- a bundle's trunk end can only ever attach to
    a Transition, specifically one of its branches, whose own 3D point
    the bundle's own start/stop point id then IS (BUNDLE_PLACEMENT.md's
    anchor model), so matching on that point id finds it with no
    dependency on the (weakref-based, object-graph-only, not always
    live) ``objects.bundle.Bundle.start_sibling``/``stop_sibling``.
    """
    branches_table = bundle_db_obj.table.db.pjt_transition_branches_table

    branches = []
    for point_id in (bundle_db_obj.start_position3d_id, bundle_db_obj.stop_position3d_id):
        if point_id is None:
            continue

        for row in branches_table.select('id', point3d_id=point_id):
            branches.append(branches_table[row[0]])

    return branches


@_check_types.do
def effective_diameter(bundle_db_obj: "_pjt_bundle.PJTBundle") -> float:
    """The diameter to render *bundle_db_obj* at right now -- see the
    module docstring for the rule. Growing an attached branch's own
    ``diameter`` to match, when the wires need more room than its own
    minimum allows, is a side effect of calling this.
    """
    branches = _attached_branches(bundle_db_obj)
    branch_floor = max((branch.part.min_dia for branch in branches), default=0.0)

    wires_diameter = _wires_diameter(bundle_db_obj)
    if wires_diameter is None:
        diameter = branch_floor if branches else bundle_db_obj.part.min_dia
    else:
        diameter = max(wires_diameter, branch_floor)

    for branch in branches:
        if diameter != branch.diameter:
            branch.diameter = diameter

    return diameter


@_check_types.do
def refresh_diameter(bundle_obj: "_bundle_obj.Bundle") -> None:
    """Recompute *bundle_obj*'s own effective diameter and apply it to
    both view facades -- call after anything that could change either
    its wire content or which branch(es) it's attached to (a merge, a
    concentric repack, attaching/detaching a transition; see
    :meth:`objects.bundle.Bundle.set_sibling`). Each view's own
    ``refresh_diameter()`` independently calls :func:`effective_diameter`
    (a harmless, idempotent re-run of the same branch-growth side
    effect) and recomputes its own geometry -- mirrors every other
    view-pair refresh in this codebase (e.g. ``refresh_waypoints()``),
    which has no single cross-view entry point either.
    """
    bundle_obj.obj3d.refresh_diameter()
    bundle_obj.objpegboard.refresh_diameter()
