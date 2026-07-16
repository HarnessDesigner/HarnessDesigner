# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Wire-row sourcing for the Peg Board Editor's per-anchor data tables.

Each anchor type sources its table rows from a different part of the
schema (there is no single "wires at this point" query that covers every
case):

- Housing: ``housing.cavities`` (sorted ascending by the cavity's own
  template ``part.idx``), each seated cavity's ``.terminal`` resolved to
  its attached wire via :func:`wire_for_point3d` -- no ``terminal -> wire``
  reverse lookup exists anywhere in this codebase today, so this module
  adds the one needed.
- Splice: ``PJTSplice.wires`` already returns ``[start_wires, stop_wires,
  branch_wires]`` -- flattened in that order.
- Transition: **one table per branch** (not one combined table) -- each
  ``PJTTransitionBranch`` has its own independent ``position3d_id``
  (``Position3DMixin``), so it keys its own ``pjt_pegboard_tables`` row
  exactly like any other anchor point. ``branch.wires`` gives
  ``PJTConcentricWire`` rows; filler wires are skipped.
- Bare terminal: the single wire via :func:`wire_for_point3d`.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtGui import QColor

from ... import image as _image


if TYPE_CHECKING:
    from PySide6.QtGui import QPixmap
    from ...objects import project as _project
    from ...database.project_db import pjt_wire as _pjt_wire
    from ...database.project_db import pjt_cavity as _pjt_cavity
    from ...database.project_db import pjt_housing as _pjt_housing
    from ...database.project_db import pjt_splice as _pjt_splice
    from ...database.project_db import pjt_transition_branch as _pjt_transition_branch
    from ...database.project_db import pjt_terminal as _pjt_terminal


# Fixed, visually-distinct palette for multi-conductor cable row grouping.
# Cycled per-table (not globally) by order of first appearance -- see
# _expand_multi_conductor -- so a table never repeats a color between
# ADJACENT cable groups even though the palette itself is small and fixed.
_CABLE_GROUP_PALETTE_RGB = (
    (255, 214, 214),
    (214, 255, 214),
    (214, 224, 255),
    (255, 245, 194),
    (230, 214, 255),
    (214, 255, 250),
    (255, 224, 194),
    (224, 224, 224),
)


@dataclass
class WireTableRow:
    """One row in a Peg Board Editor data table.

    ``conductor_index``/``conductor_count`` are only set when the owning
    wire's part is a multi-conductor cable (``wire.part.num_conductors >
    1``) -- see :func:`_expand_multi_conductor`. ``group_color`` is the
    shared background swatch (``QColor | None``) that visually links every
    row expanded from the same multi-conductor wire; ``None`` for an
    ordinary single-conductor wire.

    ``image_pixmap`` starts ``None`` and is filled in lazily, once, the
    first time this row's image cell is actually painted (see
    ``table_model.WireImageDelegate``) -- a wire never scrolled into view
    never pays for image generation.
    """
    wire: "_pjt_wire.PJTWire"
    conductor_index: "int | None" = None
    conductor_count: "int | None" = None
    group_color: "QColor | None" = None
    cavity: "_pjt_cavity.PJTCavity | None" = None
    image_pixmap: "QPixmap | None" = None


def wire_image_pixmap(wire: "_pjt_wire.PJTWire") -> "QPixmap":
    """Build (or fetch, via ``image.images.build_wire``'s own internal
    color-triple cache) the 400x100 rendered wire swatch for *wire*.

    Insulation colors come straight from ``part.color``/``part.stripe_color``.
    The bare conductor tip color is ``part.core_material.color`` -- the
    same :class:`~harness_designer.database.global_db.plating.Plating`
    class a terminal's own ``.plating`` is, and the same ``.color``
    property (plating-symbol-to-color-name, resolved against
    ``colors_table``) ``objects.objects3d.terminal.Terminal`` uses for its
    own material.

    ``part.stripe_color`` raises ``KeyError`` (pre-existing, unrelated bug
    in ``global_db.wire.Wire.stripe_color``) when ``stripe_color_id`` is
    ``NULL`` instead of returning ``None`` -- checked here via
    ``stripe_color_id`` first rather than fixed, matching this codebase's
    convention of leaving unrelated pre-existing bugs alone.

    :param wire: The wire to render.
    :type wire: :class:`~harness_designer.database.project_db.pjt_wire.PJTWire`
    :returns: The rendered wire swatch.
    :rtype: :class:`PySide6.QtGui.QPixmap`
    """
    part = wire.part
    primary_color = part.color
    stripe_color = None if part.stripe_color_id is None else part.stripe_color
    conductor_color = part.core_material.color

    image = _image.images.build_wire(primary_color, stripe_color, conductor_color)
    return image.pixmap


def _expand_multi_conductor(wire: "_pjt_wire.PJTWire", palette_index: list) -> list["WireTableRow"]:
    """Expand *wire* into 1..N :class:`WireTableRow`\\ s.

    *palette_index* is a single-element mutable ``[int]`` cycling counter
    shared across one table's whole row-build pass -- incremented each time
    a *new* multi-conductor wire is encountered, so distinct cable groups
    within the same table cycle through :data:`_CABLE_GROUP_PALETTE_RGB`
    without an adjacent repeat.

    This is deliberately the ONE place "how many rows does a wire become,
    and how are they colored" is decided -- today that's purely
    ``wire.part.num_conductors`` (one ``PJTWire`` row standing in for the
    whole physical cable, same circuit/AWG/etc. on every expanded row).
    When the user's own planned per-conductor connection-point table (a
    new table keyed by ``pjt_wire.db_id``, one row per additional
    conductor beyond the first, no hard limit) lands, only this function
    needs to change.

    :param wire: The wire to expand.
    :type wire: :class:`~harness_designer.database.project_db.pjt_wire.PJTWire`
    :param palette_index: Single-element ``[int]`` cycling counter, shared
        across one table's whole row-build pass.
    :type palette_index: list[int]
    :returns: One or more rows for *wire*.
    :rtype: list[:class:`WireTableRow`]
    """
    num_conductors = wire.part.num_conductors or 1

    if num_conductors <= 1:
        return [WireTableRow(wire=wire)]

    r, g, b = _CABLE_GROUP_PALETTE_RGB[palette_index[0] % len(_CABLE_GROUP_PALETTE_RGB)]
    palette_index[0] += 1
    group_color = QColor(r, g, b)

    return [
        WireTableRow(wire=wire, conductor_index=i + 1,
                     conductor_count=num_conductors, group_color=group_color)
        for i in range(num_conductors)
    ]


def wire_for_point3d(project: "_project.Project", point3d_id: "int | None") -> "_pjt_wire.PJTWire | None":
    """Reverse-resolve the :class:`PJTWire` attached at *point3d_id*.

    Mirrors ``PJTSplice.wires``'s own ``start_point3d_id``/
    ``stop_point3d_id`` select pattern -- no such reverse lookup exists on
    ``PJTWiresTable`` itself today.

    :param project: The currently open project.
    :type project: :class:`harness_designer.objects.project.Project`
    :param point3d_id: A terminal's own ``wire_point3d_id``.
    :type point3d_id: int | None
    :returns: The attached wire, or ``None``.
    :rtype: :class:`~harness_designer.database.project_db.pjt_wire.PJTWire` | None
    """
    if point3d_id is None:
        return None

    wires_table = project.ptables.pjt_wires_table
    ids = wires_table.select('id', start_point3d_id=point3d_id)
    if not ids:
        ids = wires_table.select('id', stop_point3d_id=point3d_id)

    if not ids:
        return None

    return wires_table[ids[0][0]]


def build_rows_for_housing(
    housing: "_pjt_housing.PJTHousing", project: "_project.Project",
) -> list["WireTableRow"]:
    """Build a housing table's rows: every seated cavity's wire, sorted
    ascending by the cavity's own template ``part.idx``.

    :param housing: The housing anchor's owning row.
    :type housing: :class:`~harness_designer.database.project_db.pjt_housing.PJTHousing`
    :param project: The currently open project.
    :type project: :class:`harness_designer.objects.project.Project`
    :returns: One or more rows per seated cavity, cavity-index order.
    :rtype: list[:class:`WireTableRow`]
    """
    cavities = sorted(housing.cavities, key=lambda c: c.part.idx)

    rows = []
    palette_index = [0]

    for cavity in cavities:
        terminal = cavity.terminal
        if terminal is None:
            continue

        wire = wire_for_point3d(project, terminal.wire_point3d_id)
        if wire is None:
            continue

        for row in _expand_multi_conductor(wire, palette_index):
            row.cavity = cavity
            rows.append(row)

    return rows


def build_rows_for_splice(splice: "_pjt_splice.PJTSplice") -> list["WireTableRow"]:
    """Build a splice table's rows: start-side wires, then stop-side, then
    branch-side (``PJTSplice.wires``'s own group order).

    :param splice: The splice anchor's owning row.
    :type splice: :class:`~harness_designer.database.project_db.pjt_splice.PJTSplice`
    :returns: One or more rows per connected wire, grouped by side.
    :rtype: list[:class:`WireTableRow`]
    """
    start_wires, stop_wires, branch_wires = splice.wires

    rows = []
    palette_index = [0]

    for wire in [*start_wires, *stop_wires, *branch_wires]:
        rows.extend(_expand_multi_conductor(wire, palette_index))

    return rows


def build_rows_for_transition_branch(
    branch: "_pjt_transition_branch.PJTTransitionBranch",
) -> list["WireTableRow"]:
    """Build one transition branch's table rows (one table per branch,
    not one combined table for the whole transition).

    :param branch: The branch this table belongs to.
    :type branch: :class:`~harness_designer.database.project_db.pjt_transition_branch.PJTTransitionBranch`
    :returns: One or more rows per non-filler wire in this branch.
    :rtype: list[:class:`WireTableRow`]
    """
    rows = []
    palette_index = [0]

    for concentric_wire in branch.wires:
        if concentric_wire.is_filler:
            continue

        rows.extend(_expand_multi_conductor(concentric_wire.wire, palette_index))

    return rows


def build_rows_for_terminal(
    terminal: "_pjt_terminal.PJTTerminal", project: "_project.Project",
) -> list["WireTableRow"]:
    """Build a bare terminal table's rows: its single attached wire.

    :param terminal: The bare terminal anchor's owning row.
    :type terminal: :class:`~harness_designer.database.project_db.pjt_terminal.PJTTerminal`
    :param project: The currently open project.
    :type project: :class:`harness_designer.objects.project.Project`
    :returns: One or more rows for the attached wire, or an empty list.
    :rtype: list[:class:`WireTableRow`]
    """
    wire = wire_for_point3d(project, terminal.wire_point3d_id)
    if wire is None:
        return []

    return _expand_multi_conductor(wire, [0])
