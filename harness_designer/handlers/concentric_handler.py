# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Wires in a concentric: adding one, planning where they sit, and building
what the concentric section widget (``ui.concentric_section``) shows.

**What "in a concentric" means.** A wire is in a concentric when a
``pjt_concentric_wires`` row of one of its layers names it (nothing reads the
``concentric_id`` tag of a wire's ``pjt_wire_paths`` rows). A new wire goes in
the outermost layer; a concentric with no layers gets layer 0.

**Which concentric a bundle or a branch uses.** Its own, if it has one; else
the one belonging to whatever it is plugged into (a bundle: the branches at its
two ends; a branch: its bundle) -- so a connected bundle and branch find ONE
concentric and show ONE widget (:func:`find_concentric_for_bundle` /
:func:`find_concentric_for_branch`, read-only; :func:`concentric_for_bundle` /
:func:`concentric_for_branch` make one only when there is none). Reusing a
counterpart's concentric deliberately does NOT write the other party's id onto
it: that would make ``bundle_diameter`` read the shared concentric's layer as
that bundle's size, which it has never done. A bundle and a branch that each
already have their OWN concentric are not merged (nothing merges concentrics
yet), so each keeps its own widget.

**Layer diameters are NOT touched, beyond one case.** ``bundle_diameter.
_wires_diameter`` takes the OUTERMOST layer's ``diameter`` as the bundle's size
the moment its concentric has any layer, so writing a placeholder -- or this
module's interim layout figure -- into one would silently resize the bundle in
3D and on the peg board. A new first layer is therefore given the diameter the
bundle has right now (its wires' estimate, else the attached branch's own
diameter, else the wire's own OD), which changes nothing; an existing layer's
diameter is never rewritten.

**The layout is interim.** :func:`replan` packs every cable of the concentric
as tightly as it can inside a circle (``ui.concentric_section.packing``) and
stores each cable's place in its ``point2d``. It does NOT yet follow the layer
rules of MIL-STD-339 (CONCENTRIC_TWIST_DESIGN.md sections 4-8) -- when that
solver exists it replaces :func:`replan`, and nothing else here changes.

**The cables are drawn from what the catalog knows**, which has no jacket flag
and no jacket or shield thickness: a coaxial part or a shielded part gets a
shield and a jacket (``_SHIELD_FRACTION`` / ``_JACKET_FRACTION`` of its OD), any
other wire none (several conductors are a twisted group).
"""

from typing import TYPE_CHECKING, Union as _Union, Any

from . import bundle_diameter as _bundle_diameter
from ..database import id_generator as _id_generator
from ..ui.concentric_section import packing as _packing
from ..ui.concentric_section import section_model as _section_model
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..database.project_db import pjt_bases as _pjt_bases
    from ..database.project_db import pjt_bundle as _pjt_bundle
    from ..database.project_db import pjt_transition_branch as _pjt_transition_branch
    from ..database.project_db import pjt_concentric as _pjt_concentric
    from ..database.project_db import pjt_concentric_layer as _pjt_concentric_layer
    from ..database.project_db import pjt_concentric_wire as _pjt_concentric_wire
    from ..database.project_db import pjt_wire as _pjt_wire


# Not in the catalog data; proportions of the overall OD.
_SHIELD_FRACTION = 0.04
_JACKET_FRACTION = 0.10

# A colour the catalog left unset draws as light grey; a coax's dielectric is near white.
_NEUTRAL_RGB = (200, 200, 200)
_DIELECTRIC_RGB = (240, 240, 240)

# Air kept between cables by the interim layout, and the margin drawn round the bundle outline.
_PACK_GAP_MM = 0.05
_OUTLINE_MARGIN_MM = 0.3


@_check_types.do
def _is_set(db_id: bytes | None) -> bool:
    """Whether a catalog reference is set: it has an id, and not the nil id the database uses for "none"."""
    return db_id is not None and db_id != _id_generator.NIL_UUID.bytes


@_check_types.do
def _rgb(color: Any) -> tuple[int, int, int]:
    """A catalog ``Color``'s red, green and blue."""
    red, green, blue, _alpha = color.rgb
    return int(red), int(green), int(blue)


@_check_types.do
def _cable_for(part: Any, key: bytes) -> _section_model.CableSpec:
    """The cable a catalog wire part is drawn as -- see the module docstring for the rules and what is assumed."""
    od = float(part.od_mm or 0.0)
    conductor_dia = float(part.conductor_dia_mm or 0.0)
    count = int(part.num_conductors or 1)

    insulation = _NEUTRAL_RGB
    if _is_set(part.color_id):
        insulation = _rgb(part.color)

    stripe = None
    if _is_set(part.stripe_color_id):
        stripe = _rgb(part.stripe_color)

    metal = _section_model.conductor_rgb('copper')
    if _is_set(part.core_material_id):
        metal = _rgb(part.core_material.color)

    wire_type = ''
    if _is_set(part.wire_type_id):
        wire_type = part.wire_type.name or ''

    if wire_type.lower() == 'coaxial':
        shield = _section_model.ShieldSpec(od * _SHIELD_FRACTION)
        jacket = _section_model.JacketSpec(od * _JACKET_FRACTION, insulation)
        return _section_model.CableSpec.fit_to_od(
            key, 1, od, conductor_dia, metal, _DIELECTRIC_RGB, None, shield, jacket)

    if part.shielded:
        shield = _section_model.ShieldSpec(od * _SHIELD_FRACTION)
        jacket = _section_model.JacketSpec(od * _JACKET_FRACTION, insulation)
        return _section_model.CableSpec.fit_to_od(
            key, count, od, conductor_dia, metal, _DIELECTRIC_RGB, None, shield, jacket)

    return _section_model.CableSpec.fit_to_od(key, count, od, conductor_dia, metal, insulation, stripe)


@_check_types.do
def _gauge_text(awg: Any, mm2: Any) -> str:
    """``18 AWG / 0.75 mm²``, whichever of the two the part has (the circuit editor's wording)."""
    parts = []
    if awg is not None:
        parts.append(f'{awg} AWG')

    if mm2 is not None:
        parts.append(f'{mm2} mm²')

    return ' / '.join(parts)


@_check_types.do
def _detail_for(wire: "_pjt_wire.PJTWire", part: Any, layer: "_pjt_concentric_layer.PJTConcentricLayer",
                solutions: dict) -> _section_model.WireDetail:
    """What the information pane shows for *wire*. The current and the temperature are what the circuit solver
    finds for the wire's circuit (``None`` for a wire in no circuit); *solutions* caches one solve per circuit."""
    detail = _section_model.WireDetail(
        name=part.part_number or 'Wire', part_number=part.part_number or '',
        size=_gauge_text(part.size_awg, part.size_mm2), conductors=int(part.num_conductors or 1),
        shielded=bool(part.shielded), layer=f'Layer {layer.idx + 1}')

    if _is_set(part.color_id):
        detail.color = part.color.name or ''

    if _is_set(part.stripe_color_id):
        detail.stripe_color = part.stripe_color.name or ''

    if _is_set(part.material_id):
        detail.insulation = part.material.name or ''

    if _is_set(part.core_material_id):
        core = part.core_material
        detail.conductor_material = core.description or core.symbol or ''

    circuit = wire.circuit
    if circuit is None:
        return detail

    detail.name = f'Circuit {circuit.circuit_num}'

    if circuit.db_id not in solutions:
        solutions[circuit.db_id] = circuit.solve()

    solution = solutions[circuit.db_id]
    if solution is not None:
        detail.current_a = solution.amps.get(wire.db_id)
        detail.max_temp_c = solution.temperature.get(wire.db_id)
        detail.over_temp = wire.db_id in solution.over_temp
        detail.runaway = wire.db_id in solution.runaway

    return detail


@_check_types.do
def find_concentric_for_bundle(bundle: "_pjt_bundle.PJTBundle") -> _Union["_pjt_concentric.PJTConcentric", None]:
    """The concentric *bundle* uses -- its own, else the first one belonging to a transition branch plugged into either
    end -- or ``None`` if neither has one. Read-only."""
    own = bundle.concentric
    if own is not None:
        return own

    for branch in _bundle_diameter._attached_branches(bundle):  # NOQA
        shared = branch.concentric
        if shared is not None:
            return shared

    return None


@_check_types.do
def find_concentric_for_branch(branch: "_pjt_transition_branch.PJTTransitionBranch") -> _Union["_pjt_concentric.PJTConcentric", None]:
    """The concentric *branch* uses -- its own, else its bundle's -- or ``None`` if neither has one. Read-only."""
    own = branch.concentric
    if own is not None:
        return own

    bundle = branch.bundle
    if bundle is not None:
        return bundle.concentric

    return None


@_check_types.do
def concentric_for_bundle(ptables: "_pjt_bases.PJTTables", bundle: "_pjt_bundle.PJTBundle") -> "_pjt_concentric.PJTConcentric":
    """:func:`find_concentric_for_bundle`, making an (empty) concentric for *bundle* when there is none."""
    found = find_concentric_for_bundle(bundle)
    if found is not None:
        return found

    return ptables.pjt_concentrics_table.insert(bundle.db_id, None)


@_check_types.do
def concentric_for_branch(ptables: "_pjt_bases.PJTTables", branch: "_pjt_transition_branch.PJTTransitionBranch") -> "_pjt_concentric.PJTConcentric":
    """:func:`find_concentric_for_branch`, making an (empty) concentric for *branch* when there is none."""
    found = find_concentric_for_branch(branch)
    if found is not None:
        return found

    return ptables.pjt_concentrics_table.insert(None, branch.db_id)


@_check_types.do
def _entries(concentric: "_pjt_concentric.PJTConcentric") -> list[tuple["_pjt_concentric_layer.PJTConcentricLayer", "_pjt_concentric_wire.PJTConcentricWire"]]:
    """Every wire row of the concentric with its layer, innermost layer first, then by place in the layer."""
    entries = []
    for layer in concentric.layers:
        for concentric_wire in sorted(layer.wires, key=lambda row: row.idx):
            entries.append((layer, concentric_wire))

    return entries


@_check_types.do
def needs_plan(concentric: "_pjt_concentric.PJTConcentric") -> bool:
    """Whether two wires of the concentric sit on the same spot -- the state a concentric made by
    ``transition_handler._create_branch_concentric`` (every wire at the origin) or by a drop is in until it is planned."""
    places = []
    for _layer, concentric_wire in _entries(concentric):
        point = concentric_wire.position2d
        places.append((round(point.x, 6), round(point.y, 6)))

    return len(set(places)) < len(places)


@_check_types.do
def replan(ptables: "_pjt_bases.PJTTables", concentric: "_pjt_concentric.PJTConcentric") -> None:
    """Work out where every cable of the concentric sits and store it.

    INTERIM: the tightest circle packing of the cables (see the module docstring), not the layer plan of MIL-STD-339.
    Also keeps each layer's wire and filler counts right; never a layer's diameter.
    """
    entries = _entries(concentric)

    cables = []
    for _layer, concentric_wire in entries:
        wire = concentric_wire.wire
        cables.append(_cable_for(wire.part, wire.db_id))

    radii = tuple([cable.radius_mm + _PACK_GAP_MM for cable in cables])
    centers, _envelope = _packing.pack_circles(radii)

    for (_layer, concentric_wire), (x, y) in zip(entries, centers):
        point = concentric_wire.position2d
        with point:
            point.x = x
            point.y = y

        # `with point:` batches the writes but does not fire the bound callbacks, which is what stores the point
        point._process_callbacks()  # NOQA

    for layer in concentric.layers:
        rows = layer.wires
        layer.num_wires = len(rows)
        layer.num_fillers = len([row for row in rows if row.is_filler])


@_check_types.do
def _first_layer_diameter(concentric: "_pjt_concentric.PJTConcentric", wire: "_pjt_wire.PJTWire") -> float:
    """The diameter a new first layer is given: what the bundle is right now, so creating the layer changes nothing."""
    bundle = concentric.bundle
    if bundle is not None:
        diameter = _bundle_diameter.wires_diameter(bundle)
        if diameter is not None:
            return diameter

    branch = concentric.transition_branch
    if branch is not None:
        return branch.diameter

    return float(wire.part.od_mm or 0.0)


@_check_types.do
def add_wire(ptables: "_pjt_bases.PJTTables", concentric: "_pjt_concentric.PJTConcentric",
             wire: "_pjt_wire.PJTWire") -> bool:
    """Add *wire* to the concentric's outermost layer (layer 0 is made if there is none) and plan the layout again.

    :returns: ``False`` if the wire is already in the concentric (nothing changed), else ``True``.
    """
    for _layer, concentric_wire in _entries(concentric):
        if concentric_wire.wire_id == wire.db_id:
            return False

    layers = concentric.layers
    if layers:
        layer = layers[-1]
    else:
        layer = ptables.pjt_concentric_layers_table.insert(
            0, 0, 0, concentric.db_id, _first_layer_diameter(concentric, wire))

    point = ptables.pjt_points2d_table.insert(0.0, 0.0, 0.0)
    ptables.pjt_concentric_wires_table.insert(
        layer.db_id, len(layer.wires), wire.db_id, point.db_id, bool(wire.is_filler_wire))

    replan(ptables, concentric)
    return True


@_check_types.do
def build_section(concentric: "_pjt_concentric.PJTConcentric") -> tuple[_section_model.SectionSpec, dict]:
    """What the section widget shows for *concentric*: its cables where they are stored, and the details of each
    wire (keyed by the wire's row id, which is also the cable's key).

    :returns: ``(section, details)``.
    """
    placed = []
    details = {}
    solutions = {}

    for layer, concentric_wire in _entries(concentric):
        wire = concentric_wire.wire
        part = wire.part

        point = concentric_wire.position2d
        placed.append(_section_model.PlacedCable(_cable_for(part, wire.db_id), point.x, point.y))
        details[wire.db_id] = _detail_for(wire, part, layer, solutions)

    run_length = 0.0
    bundle = concentric.bundle
    if bundle is not None:
        run_length = float(bundle.length_mm or 0.0)

    section = _section_model.SectionSpec(placed, run_length_mm=run_length)
    section.envelope_dia_mm = 2.0 * (section.content_radius_mm() + _OUTLINE_MARGIN_MM)

    return section, details
