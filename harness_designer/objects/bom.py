# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""BOM aggregation/traversal for the BOM Builder dialog.

Pure data-computation module -- no Qt widgets here, only the row
dataclasses the dialog's view widgets render and the functions that walk
:class:`~harness_designer.objects.project.Project` to build them.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .. import image as _image
from .. import check_types as _check_types

if TYPE_CHECKING:
    from . import project as _project
    from ..database.project_db import pjt_wire as _pjt_wire


@dataclass
class BomLineItem:
    """One row of the flat parts-list view (view 1)."""
    manufacturer: str
    part_number: str
    description: str
    quantity: float
    is_length: bool


@dataclass
class HousingTreeNode:
    """One node of the housing tree view (view 2).

    :attr:`kind` is one of ``'housing'``, ``'cpa_lock'``, ``'cover'``,
    ``'boot'``, ``'seal'``, ``'tpa_lock_1'``, ``'tpa_lock_2'``,
    ``'terminal'`` -- the dialog maps these to display labels.
    """
    kind: str
    manufacturer: str
    part_number: str
    description: str
    awg_min: int | None = None
    awg_max: int | None = None
    children: list["HousingTreeNode"] = field(default_factory=list)


@dataclass
class WireCutRow:
    """One row of the wire cut-sheet view (view 3), one per wire instance."""
    manufacturer: str
    part_number: str
    description: str
    awg: int
    mm2: float
    num_conductors: int
    shielded: bool
    exact_length_mm: float
    length_with_excess_mm: float
    icon: "_image.Image"


@dataclass
class BundleCutRow:
    """One row of the bundle cut-sheet view (view 4), one per bundle instance."""
    manufacturer: str
    part_number: str
    description: str
    dia_min_mm: float
    dia_max_mm: float
    exact_length_mm: float
    length_with_excess_mm: float


@_check_types.do
def resolve_wire_icon(pjt_wire: "_pjt_wire.PJTWire") -> "_image.Image":
    """Return a 100x25 wire-color swatch for *pjt_wire*, falling back to
    ``images.no_image`` for shielded wires or when resolution fails --
    the color-image module only supports single-conductor, unshielded
    wires today (see :func:`harness_designer.gl.canvas_pegboard.table_rows.
    wire_image_pixmap`, the existing precedent this mirrors).

    :param pjt_wire: The wire instance to render a swatch for.
    :type pjt_wire: :class:`~harness_designer.database.project_db.pjt_wire.PJTWire`
    :returns: A 100x25 :class:`~harness_designer.image.Image`.
    :rtype: :class:`~harness_designer.image.Image`
    """
    part = pjt_wire.part
    try:
        if part.shielded:
            raise ValueError('shielded wires have no icon support yet')

        primary = part.color
        stripe = None if part.stripe_color_id is None else part.stripe_color
        conductor = part.core_material.color

        img = _image.images.build_wire(primary, stripe, conductor)
    except Exception:
        img = _image.images.no_image

    return img.resize(100, 25)


@_check_types.do
def build_flat_list(
        project: "_project.Project",
        wire_excess_pct: float,
        bundle_excess_pct: float) -> list[BomLineItem]:
    """Aggregate every distinct catalog part used anywhere in *project*
    into one row per part number.

    Wire and bundle rows show a summed length (in mm, with their
    respective excess percentage applied) instead of an instance count --
    every other part type is a plain count. ``project.housings``,
    ``.terminals``, etc. are already flat, all-instance lists (loaded
    straight from their full project-db table), so housing-seated and
    loose/unattached instances of the same part type are both counted
    here without any special-casing.

    :param project: The project to aggregate.
    :type project: :class:`~harness_designer.objects.project.Project`
    :param wire_excess_pct: Fabrication excess percentage applied to wire lengths.
    :type wire_excess_pct: float
    :param bundle_excess_pct: Fabrication excess percentage applied to bundle lengths.
    :type bundle_excess_pct: float
    :returns: One :class:`BomLineItem` per distinct part number.
    :rtype: list[BomLineItem]
    """
    counts: dict[str, list] = {}  # part_number -> [manufacturer, description, count]
    lengths: dict[str, list] = {}  # part_number -> [manufacturer, description, total_mm]

    count_collections = (
        project.housings, project.terminals, project.seals, project.covers,
        project.boots, project.cpa_locks, project.tpa_locks, project.splices,
    )

    for collection in count_collections:
        for obj in collection:
            part = obj.db_obj.part
            if part is None:
                continue

            entry = counts.setdefault(
                part.part_number, [part.manufacturer.name, part.description, 0])
            entry[2] += 1

    for wire in project.wires:
        part = wire.db_obj.part
        if part is None:
            continue

        entry = lengths.setdefault(
            part.part_number, [part.manufacturer.name, part.description, 0.0])
        entry[2] += wire.db_obj.length_mm

    wire_part_numbers = set(lengths.keys())

    for bundle in project.bundles:
        part = bundle.db_obj.part
        if part is None:
            continue

        entry = lengths.setdefault(
            part.part_number, [part.manufacturer.name, part.description, 0.0])
        entry[2] += bundle.db_obj.length_mm

    rows = [
        BomLineItem(mfg, part_number, desc, qty, is_length=False)
        for part_number, (mfg, desc, qty) in counts.items()
    ]

    for part_number, (mfg, desc, total_mm) in lengths.items():
        pct = wire_excess_pct if part_number in wire_part_numbers else bundle_excess_pct
        rows.append(BomLineItem(
            mfg, part_number, desc, total_mm * (1.0 + pct / 100.0), is_length=True))

    return rows


@_check_types.do
def build_housing_tree(project: "_project.Project") -> list[HousingTreeNode]:
    """Build one tree node per housing, with its directly-attached
    accessories and seated terminals nested underneath.

    Mirrors the traversal order in
    :meth:`~harness_designer.objects.housing.Housing.delete` (cpa lock,
    cover, boot, seal, tpa locks, then each seated cavity's terminal and
    that terminal's own seal), reading instead of deleting. Loose/
    unattached parts never appear here -- only in :func:`build_flat_list`.

    :param project: The project to walk.
    :type project: :class:`~harness_designer.objects.project.Project`
    :returns: One :class:`HousingTreeNode` per housing.
    :rtype: list[HousingTreeNode]
    """
    nodes = []

    for housing in project.housings:
        db_housing = housing.db_obj
        h_part = db_housing.part
        if h_part is None:
            continue

        root = HousingTreeNode(
            kind='housing', manufacturer=h_part.manufacturer.name,
            part_number=h_part.part_number, description=h_part.description)

        cpa_lock = db_housing.cpa_lock
        if cpa_lock is not None and cpa_lock.part is not None:
            part = cpa_lock.part
            root.children.append(HousingTreeNode(
                kind='cpa_lock', manufacturer=part.manufacturer.name,
                part_number=part.part_number, description=part.description))

        cover = db_housing.cover
        if cover is not None and cover.part is not None:
            part = cover.part
            root.children.append(HousingTreeNode(
                kind='cover', manufacturer=part.manufacturer.name,
                part_number=part.part_number, description=part.description))

        boot = db_housing.boot
        if boot is not None and boot.part is not None:
            part = boot.part
            root.children.append(HousingTreeNode(
                kind='boot', manufacturer=part.manufacturer.name,
                part_number=part.part_number, description=part.description))

        seal = db_housing.seal
        if seal is not None and seal.part is not None:
            part = seal.part
            root.children.append(HousingTreeNode(
                kind='seal', manufacturer=part.manufacturer.name,
                part_number=part.part_number, description=part.description))

        for kind, tpa_lock in (('tpa_lock_1', db_housing.tpa_lock1),
                               ('tpa_lock_2', db_housing.tpa_lock2)):
            if tpa_lock is None or tpa_lock.part is None:
                continue

            part = tpa_lock.part
            root.children.append(HousingTreeNode(
                kind=kind, manufacturer=part.manufacturer.name,
                part_number=part.part_number, description=part.description))

        for cavity in db_housing.cavities:
            if cavity is None:
                continue

            terminal = cavity.terminal
            if terminal is None or terminal.part is None:
                continue

            t_part = terminal.part
            terminal_node = HousingTreeNode(
                kind='terminal', manufacturer=t_part.manufacturer.name,
                part_number=t_part.part_number, description=t_part.description,
                awg_min=t_part.wire_size_awg_min, awg_max=t_part.wire_size_awg_max)

            # A terminal's own seal is linked via terminal_id (distinct
            # from the cavity-level seal, linked via cavity_id) -- see
            # PJTTerminal.seal / PJTCavity.seal.
            t_seal = terminal.seal
            if t_seal is not None and t_seal.part is not None:
                s_part = t_seal.part
                terminal_node.children.append(HousingTreeNode(
                    kind='seal', manufacturer=s_part.manufacturer.name,
                    part_number=s_part.part_number, description=s_part.description))

            root.children.append(terminal_node)

        nodes.append(root)

    return nodes


@_check_types.do
def build_wire_cut_sheet(
        project: "_project.Project", wire_excess_pct: float) -> list[WireCutRow]:
    """Build one row per physical wire instance in *project* -- a literal
    cut list, not an aggregation by part number.

    :param project: The project to walk.
    :type project: :class:`~harness_designer.objects.project.Project`
    :param wire_excess_pct: Fabrication excess percentage applied to each length.
    :type wire_excess_pct: float
    :returns: One :class:`WireCutRow` per wire instance.
    :rtype: list[WireCutRow]
    """
    rows = []

    for wire in project.wires:
        db_wire = wire.db_obj
        part = db_wire.part
        if part is None:
            continue

        exact = db_wire.length_mm
        rows.append(WireCutRow(
            manufacturer=part.manufacturer.name,
            part_number=part.part_number,
            description=part.description,
            awg=part.size_awg,
            mm2=part.size_mm2,
            num_conductors=part.num_conductors,
            shielded=part.shielded,
            exact_length_mm=exact,
            length_with_excess_mm=exact * (1.0 + wire_excess_pct / 100.0),
            icon=resolve_wire_icon(db_wire)))

    return rows


@_check_types.do
def build_bundle_cut_sheet(
        project: "_project.Project", bundle_excess_pct: float) -> list[BundleCutRow]:
    """Build one row per bundle-covering instance in *project*.

    Diameter comes from the catalog part's ``min_dia``/``max_dia`` --
    ``PJTBundle.diameter`` is a pre-existing, unrelated bug (its getter
    returns a ``pjt_concentrics`` row id, not a diameter) and must not be
    used here.

    :param project: The project to walk.
    :type project: :class:`~harness_designer.objects.project.Project`
    :param bundle_excess_pct: Fabrication excess percentage applied to each length.
    :type bundle_excess_pct: float
    :returns: One :class:`BundleCutRow` per bundle instance.
    :rtype: list[BundleCutRow]
    """
    rows = []

    for bundle in project.bundles:
        db_bundle = bundle.db_obj
        part = db_bundle.part
        if part is None:
            continue

        exact = db_bundle.length_mm
        rows.append(BundleCutRow(
            manufacturer=part.manufacturer.name,
            part_number=part.part_number,
            description=part.description,
            dia_min_mm=part.min_dia,
            dia_max_mm=part.max_dia,
            exact_length_mm=exact,
            length_with_excess_mm=exact * (1.0 + bundle_excess_pct / 100.0)))

    return rows
