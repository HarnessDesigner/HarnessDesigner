# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The electrical and thermal solution of one circuit.

Given the tree ``PJTCircuit._trace`` walks out from the voltage terminal,
:func:`solve_circuit` works out what current flows through every wire and
junction (terminal, splice, wire service loop), what voltage reaches each of
them once the wires upstream have dropped their share, what every load
terminal actually draws, how hot every part runs, and which parts run hotter
than they are rated for.

The model, kept in this one place so it is easy to change:

* The voltage terminal is an ideal source of ``volts``. Its own resistance is
  not in the circuit (the voltage is defined at the terminal), though it still
  carries the whole current and so still heats.
* Every wire, splice, wire service loop and load terminal is a series
  resistance, taken at the part's own temperature (see below).
* A load terminal's ``load`` is the current its device is rated to draw at the
  voltage of the circuit, as the manufacturer states it. How the device
  reacts to the voltage that really reaches it is its :class:`LoadType`:
  ``RESISTIVE`` acts as a resistor of ``volts / load`` ohms (draws less as the
  voltage sags), ``CONSTANT_CURRENT`` draws ``load`` whatever the voltage, and
  ``CONSTANT_POWER`` draws ``volts * load`` watts (draws more as the voltage
  sags, the worst case for wire drop). A terminal with a load and wires
  leaving it has the load in parallel with what continues beyond it.
* How the current gets back to the source is the circuit's :class:`ReturnType`.
  ``CHASSIS`` leaves the return out (a chassis or body return, taken as zero
  resistance); ``MIRRORED`` gives the return the same resistance as the supply
  side, so every series resistance counts twice. The voltages reported are what
  a device connected at that point sees across it.
* A part heats by ``theta * I**2 * R(T)``: ``theta`` is its thermal resistance
  to the air around it in kelvin per watt, ``I`` the current through it, and
  ``R(T) = r20 * (1 + alpha * (T - 20))`` its resistance at its own temperature
  ``T = ambient + rise``. The resistance changes the current and the current
  changes the heating, so the solve repeats until the temperatures, and the
  currents of constant-power loads, stop moving. A part that heats itself
  faster than it can shed the heat (runaway) is reported as such.
* A wire in a bundle is warmed by the other wires in it. What every wire of the
  bundle gives off per metre (``I**2 * R(T) / length``) leaves through the
  bundle's outer surface, ``pi * diameter``, at :data:`BUNDLE_HEAT_TRANSFER`
  (times a packing factor for the :class:`BundleType`), and the rise that
  makes from the OTHER wires' heat is added to the wire's own ambient. Its own
  heat still leaves through its own surface as above, so a wire alone in a
  bundle is no hotter than one in free air; a wire in several bundles takes the
  warmest. A bundle's type is derived, never stored: concentric when it has
  concentric rows, unorganized when it has wires without them, and a wire in no
  bundle is unpacked and unchanged. The diameter already reflects the type (the
  real packed diameter, or the area-sum estimate with its allowance for gaps).
  Where the manufacturer's table gives a factor for the number of
  current-carrying conductors bundled together (rows with a ``conductor_count``)
  that replaces this calculation for the wire: its thermal resistance is
  divided by the factor squared, since the current it may carry scales with the
  factor. Circuits that share a bundle heat each other, so they are solved
  together (:func:`solve_bundled`).
* A part is over temperature when it is hotter than its rated maximum. A part
  with no rated maximum is never flagged.
* Wires side by side (two or more joining the same two junctions) share the
  current: they act as one series resistance ``1 / sum(1 / R)`` and the current
  through the group divides in proportion to each wire's conductance ``1 / R``,
  so every wire has the same drop and the shorter or thicker one carries more.
  Each wire's own heating then follows from its own share. The ``parallel``
  argument of :func:`solve_circuit` names these groups.
* Any other loop in the wiring (a ring through three or more junctions) is cut
  where it closes (see ``PJTCircuit._trace``); that closing wire carries nothing.

What a part's ``PartData`` holds is the job of the part itself (the
``part_data`` method of each project row): where the manufacturer's derating
table for that part is in the database it takes the thermal resistance from it
(:func:`calibrate_theta`), and it calculates the value otherwise. This module
only consumes the result.
"""

import math
from dataclasses import dataclass, field, replace
from enum import IntEnum
from typing import Any

from ... import check_types as _check_types


# Resistances are given at this temperature, in degrees Celsius.
REFERENCE_C = 20.0

# Temperature coefficient of resistance of copper, per degree Celsius.
COPPER_ALPHA = 0.00393

# The temperature of a part nobody has set one on.
DEFAULT_AMBIENT_C = 20.0

# Calculated (no table): heat shed by an insulated wire in still air through its
# outer surface, in W/(m^2 K), convection and radiation together. Not
# calibrated against a published ampacity yet.
WIRE_HEAT_TRANSFER = 10.0

# Calculated (no table): thermal resistance of a terminal or splice to the air
# around it, in K/W. An assumption: the database holds nothing to derive it from.
CONTACT_THERMAL_RESISTANCE = 40.0

# A part that cannot settle below this is reported as running away.
RUNAWAY_C = 1000.0

_TOLERANCE = 1e-9
_MAX_ITERATIONS = 200

# Circuits that heat each other through a shared bundle are solved again until the
# warming of every wire moves by less than this many kelvin (or this share of a
# thermal resistance), for at most this many rounds.
_BUNDLE_TOLERANCE = 1e-7
_MAX_BUNDLE_ITERATIONS = 50

# A wire carries current when it carries more than this many amps.
_CURRENT_EPSILON = 1e-9


class ReturnType(IntEnum):
    """How a circuit's current returns to its source. Stored as an integer in
    ``pjt_circuits.return_type``, so keep the values.
    """
    CHASSIS = 0
    """Not modelled: a chassis or body return, taken as zero resistance."""

    MIRRORED = 1
    """The return is as long and as heavy as the supply side, so every series
    resistance counts twice."""


class LoadType(IntEnum):
    """How a load terminal's device reacts to the voltage that reaches it.
    Stored as an integer in ``pjt_terminals.load_type``, so keep the values.
    """
    RESISTIVE = 0
    """Acts as a resistor: the current falls with the voltage."""

    CONSTANT_POWER = 1
    """Draws the same power: the current rises as the voltage falls."""

    CONSTANT_CURRENT = 2
    """Draws the same current whatever the voltage."""


class BundleType(IntEnum):
    """How the wires of a bundle are packed. Derived from the data (see the
    module docstring), never stored.
    """
    UNPACKED = 0
    """In no bundle: free air around the wire."""

    UNORGANIZED = 1
    """In a bundle, loosely packed: the wires have no concentric rows."""

    CONCENTRIC = 2
    """In a bundle with concentric rows: tightly packed in layers."""


# Calculated (no table): heat shed by the outer surface of a bundle, in
# W/(m^2 K). An assumption, not calibrated; the same figure as one wire's.
BUNDLE_HEAT_TRANSFER = WIRE_HEAT_TRANSFER

# Calculated (no table): how much of a bundle's outer cylinder does the work of
# shedding heat, by packing. 1.0 for both: the diameter already differs between
# them (the real packed one against the area-sum estimate with its gap
# allowance), and nothing is known that would justify a second difference.
BUNDLE_PACKING_FACTOR = {
    BundleType.UNORGANIZED: 1.0,
    BundleType.CONCENTRIC: 1.0
}


@dataclass
class PartData:
    """What the solver needs to know about one part (wire, wire service loop,
    splice or terminal). Each project row builds its own in ``part_data``.
    """
    r20: float = 0.0
    """Resistance at 20 degrees Celsius, in ohms. 0.0 when the part has no
    resistance data, which means it neither drops voltage nor heats."""

    alpha: float = COPPER_ALPHA
    """Temperature coefficient of that resistance, per degree Celsius."""

    theta: float = 0.0
    """Thermal resistance to the surrounding air, in K/W. 0.0 means the rise
    cannot be worked out, so the part is taken to run at its ambient."""

    ambient_c: float = DEFAULT_AMBIENT_C
    """The temperature around the part, in degrees Celsius."""

    rated_max_c: float | None = None
    """The hottest the part is rated for, or ``None`` when that is unknown."""

    length_m: float = 0.0
    """The length of the run, in metres: a wire's routed length. 0.0 for a part
    that is not a run (a terminal, a splice), which gives off no heat per metre."""

    bundling: tuple[tuple[int, float], ...] = ()
    """The manufacturer's bundling derating, by conductor count: ``(number of
    current-carrying conductors bundled together, the factor on the current the
    part may carry)``. Empty when the manufacturer gave none."""


@dataclass
class LoadData:
    """One load terminal's load."""
    amps: float
    """The current the device is rated to draw at the circuit's voltage."""

    kind: LoadType = LoadType.RESISTIVE
    """How the device reacts to the voltage that really reaches it."""


@dataclass
class BundleData:
    """One bundle, as far as the heat of its wires is concerned."""
    kind: BundleType
    """How it is packed."""

    diameter_m: float
    """Its outside diameter, in metres. 0.0 when unknown, which leaves its wires
    unadjusted (nothing is known to say how the heat escapes)."""

    wire_ids: tuple[bytes, ...]
    """Every wire in it, whichever circuit it is in."""


@dataclass
class CircuitInput:
    """Everything :func:`solve_circuit` needs for one circuit, for
    :func:`solve_bundled` to solve several together."""
    children: dict[bytes, list[bytes]]
    parts: dict[bytes, PartData]
    loads: dict[bytes, LoadData]
    volts: float
    return_type: ReturnType
    parallel: dict[bytes, list[bytes]] = field(default_factory=dict)


@dataclass
class CircuitSolution:
    """What :func:`solve_circuit` found. Every dict is keyed by row id and
    holds an entry for each member the walk reached.
    """
    total_amps: float = 0.0
    """The current drawn from the voltage terminal."""

    amps: dict[bytes, float] = field(default_factory=dict)
    """The current through each wire, and into each junction (everything
    beyond its own resistance). Upstream wires and side branches are not part
    of a member's number: it is what flows from there outward."""

    volts: dict[bytes, float] = field(default_factory=dict)
    """The voltage where each member is entered, after the drop through
    everything upstream (the return side too, for a mirrored return)."""

    draw: dict[bytes, float] = field(default_factory=dict)
    """What each load terminal draws, at the voltage that reaches it."""

    temperature: dict[bytes, float] = field(default_factory=dict)
    """How hot each member runs, in degrees Celsius: its ambient plus its own
    rise at the current through it."""

    rise: dict[bytes, float] = field(default_factory=dict)
    """Each member's rise above its ambient, in kelvin."""

    over_temp: set[bytes] = field(default_factory=set)
    """The members hotter than their rated maximum."""

    runaway: set[bytes] = field(default_factory=set)
    """The members that cannot settle at a temperature (they heat themselves
    faster than they shed it). Their temperature is :data:`RUNAWAY_C`."""

    converged: bool = True
    """False when the temperatures, or the constant-power loads, did not
    settle, or a constant-power load was starved of voltage. The numbers are
    then the last ones reached and should not be trusted."""


_NO_PART = PartData()


@_check_types.do
def wire_theta(od_mm: float, length_mm: float) -> float:
    """Return a wire's thermal resistance to the air around it, in K/W.

    Calculated, not looked up: the heat has to leave through the wire's outer
    surface, ``pi * od * length``, at :data:`WIRE_HEAT_TRANSFER`.

    :param od_mm: The wire's outside diameter, in millimetres.
    :type od_mm: float
    :param length_mm: The wire's length, in millimetres.
    :type length_mm: float
    :returns: The thermal resistance, or 0.0 when the surface is not known
        (no diameter or no length), meaning the rise cannot be worked out.
    :rtype: float
    """
    surface = math.pi * (od_mm / 1000.0) * (length_mm / 1000.0)

    if surface <= 0.0:
        return 0.0

    return 1.0 / (WIRE_HEAT_TRANSFER * surface)


@_check_types.do
def resistance_at(part: PartData, temperature_c: float) -> float:
    """Return a part's resistance at a temperature, in ohms.

    :param part: The part.
    :type part: PartData
    :param temperature_c: The temperature, in degrees Celsius.
    :type temperature_c: float
    :returns: ``r20 * (1 + alpha * (T - 20))``, never below zero.
    :rtype: float
    """
    return max(0.0, part.r20 * (1.0 + part.alpha * (temperature_c - REFERENCE_C)))


@_check_types.do
def temperature_rise(part: PartData, amps: float) -> tuple[float, bool]:
    """Return how far above its ambient a part runs at a given current.

    The resistance depends on the temperature the part reaches, so the rise
    is solved exactly:
    ``rise = h * (1 + alpha * (ambient - 20)) / (1 - h * alpha)`` with
    ``h = theta * I**2 * r20``.

    :param part: The part.
    :type part: PartData
    :param amps: The current through it.
    :type amps: float
    :returns: ``(rise, runaway)``. On runaway (``1 - h * alpha <= 0``, or a
        rise beyond :data:`RUNAWAY_C`) the rise is the one that reaches
        :data:`RUNAWAY_C`.
    :rtype: tuple[float, bool]
    """
    heat = part.theta * amps * amps * part.r20

    if heat <= 0.0:
        return 0.0, False

    headroom = RUNAWAY_C - part.ambient_c
    denominator = 1.0 - heat * part.alpha

    if denominator <= 0.0:
        return max(0.0, headroom), True

    rise = max(0.0, heat * (1.0 + part.alpha * (part.ambient_c - REFERENCE_C)) / denominator)

    if rise > headroom:
        return max(0.0, headroom), True

    return rise, False


@_check_types.do
def calibrate_theta(limits: list[tuple[float, float]], r20: float, alpha: float, rated_max_c: float | None,
                    ambient_c: float) -> float | None:
    """Return the thermal resistance a manufacturer's current limits imply, in K/W.

    A derating table says how much current a part may carry at each ambient
    temperature, and a part carrying its limit is at its rated maximum. So at
    the limit ``I`` for an ambient ``Ta``: ``rated_max - Ta = theta * I**2 *
    R(rated_max)``, which gives ``theta``. Fed back through
    :func:`temperature_rise`, that theta makes a part reach its rated maximum
    at exactly the manufacturer's limit.

    The limit used is the one at *ambient_c*: interpolated linearly between
    the table's neighbouring ambients, with the limit falling to 0 A at the
    rated maximum (a row there is not needed) and the coolest row's limit
    holding for anything cooler. Two rows at one ambient count as the lower
    limit. Rows with no current or no room below the rated maximum are ignored.

    :param limits: ``(ambient in degrees Celsius, the most amps at it)`` pairs, in any order.
    :type limits: list[tuple[float, float]]
    :param r20: The part's resistance at 20 degrees Celsius, in ohms.
    :type r20: float
    :param alpha: The temperature coefficient of that resistance.
    :type alpha: float
    :param rated_max_c: The hottest the part is rated for, or ``None`` when unknown.
    :type rated_max_c: float | None
    :param ambient_c: The temperature around the part.
    :type ambient_c: float
    :returns: The thermal resistance, or ``None`` when the table cannot say
        (no rated maximum, no resistance, no usable row, or an ambient already at
        the rated maximum), in which case the calculation is used instead.
    :rtype: float | None
    """
    if rated_max_c is None or r20 <= 0.0 or ambient_c >= rated_max_c:
        return None

    lowest = {}
    for ambient, amps in limits:
        if amps > 0.0 and ambient < rated_max_c:
            lowest[ambient] = min(amps, lowest.get(ambient, amps))

    if not lowest:
        return None

    points = sorted(lowest.items())
    points.append((rated_max_c, 0.0))

    if ambient_c <= points[0][0]:
        amps = points[0][1]
    else:
        amps = points[-2][1]

        for (cool, cool_amps), (warm, warm_amps) in zip(points, points[1:]):
            if ambient_c <= warm:
                amps = cool_amps + (warm_amps - cool_amps) * (ambient_c - cool) / (warm - cool)
                break

    resistance_hot = r20 * (1.0 + alpha * (rated_max_c - REFERENCE_C))

    if resistance_hot <= 0.0:
        return None

    return (rated_max_c - ambient_c) / (amps * amps * resistance_hot)


@_check_types.do
def _parallel_resistance(resistances: list[float]) -> float:
    """Return the resistance of wires side by side, ``1 / sum(1 / R)``.

    :param resistances: The resistance of each wire, in ohms.
    :type resistances: list[float]
    :returns: The combined resistance. ``0.0`` when any wire has none, since it
        shorts the rest.
    :rtype: float
    """
    if any(resistance <= 0.0 for resistance in resistances):
        return 0.0

    return 1.0 / sum(1.0 / resistance for resistance in resistances)


@_check_types.do
def _split_current(total: float, resistances: list[float]) -> list[float]:
    """Divide the current through wires side by side between them, in
    proportion to each one's conductance ``1 / R`` (so each has the same drop).

    :param total: The current through the whole group, in amps.
    :type total: float
    :param resistances: The resistance of each wire, in ohms.
    :type resistances: list[float]
    :returns: Each wire's share, in the order given. A wire with no resistance
        takes the current: equally with any others that have none, and the wires
        that have some carry nothing.
    :rtype: list[float]
    """
    shorted = [resistance <= 0.0 for resistance in resistances]

    if any(shorted):
        count = sum(shorted)

        return [total / count if is_shorted else 0.0 for is_shorted in shorted]

    conductances = [1.0 / resistance for resistance in resistances]
    whole = sum(conductances)

    return [total * conductance / whole for conductance in conductances]


@_check_types.do
def _linear_pass(
        order: list[bytes],
        children: dict[bytes, list[bytes]],
        is_wire: dict[bytes, bool],
        series: dict[bytes, float],
        loads: dict[bytes, LoadData],
        sinks: dict[bytes, float],
        volts: float) -> tuple[dict[bytes, float], dict[bytes, float], dict[bytes, float], dict[bytes, float]]:
    """Solve the tree once with every resistance and every constant-power
    sink held fixed.

    Each branch is reduced, bottom up, to the pair ``(g, c)`` such that the
    current it takes is ``g * V + c`` at the voltage ``V`` it is entered at: a
    resistive load adds to ``g``, a constant-current one (or a constant-power
    one at its present sink) to ``c``, and a series resistance ``R`` turns
    ``(g, c)`` into ``(g, c) / (1 + g * R)``. Then the voltage is carried down.

    :returns: ``(amps, entered, leaving, draw)``: the current into each
        member, the voltage it is entered at, the voltage after its own
        resistance, and what each load terminal draws.
    :rtype: tuple[dict[bytes, float], dict[bytes, float], dict[bytes, float], dict[bytes, float]]
    """
    root_id = order[0]
    conductance = {}
    constant = {}

    for node_id in reversed(order):
        beyond_g = 0.0
        beyond_c = 0.0

        for next_id in children[node_id]:
            beyond_g += conductance[next_id]
            beyond_c += constant[next_id]

        if node_id == root_id:
            conductance[node_id] = beyond_g
            constant[node_id] = beyond_c
            continue

        load = loads.get(node_id)

        if load is not None and load.amps > 0.0 and not is_wire[node_id]:
            if load.kind == LoadType.RESISTIVE:
                beyond_g += load.amps / volts
            elif load.kind == LoadType.CONSTANT_CURRENT:
                beyond_c += load.amps
            else:
                beyond_c += sinks[node_id]

        denominator = 1.0 + beyond_g * series.get(node_id, 0.0)
        conductance[node_id] = beyond_g / denominator
        constant[node_id] = beyond_c / denominator

    entered = {root_id: volts}
    amps = {}
    leaving = {}
    draw = {}

    for node_id in order:
        arriving = entered[node_id]
        current = conductance[node_id] * arriving + constant[node_id]
        amps[node_id] = current

        if node_id == root_id:
            after = volts
        else:
            after = arriving - current * series.get(node_id, 0.0)

        leaving[node_id] = after

        load = loads.get(node_id)

        if load is not None and load.amps > 0.0 and not is_wire[node_id] and node_id != root_id:
            if load.kind == LoadType.RESISTIVE:
                draw[node_id] = after * load.amps / volts
            elif load.kind == LoadType.CONSTANT_CURRENT:
                draw[node_id] = load.amps
            else:
                draw[node_id] = sinks[node_id]

        for next_id in children[node_id]:
            entered[next_id] = after

    return amps, entered, leaving, draw


@_check_types.do
def solve_circuit(
        children: dict[bytes, list[bytes]],
        parts: dict[bytes, PartData],
        loads: dict[bytes, LoadData],
        volts: float,
        return_type: ReturnType,
        parallel: dict[bytes, list[bytes]] | None = None) -> CircuitSolution:
    """Solve a circuit tree for current, voltage and temperature.

    :param children: The tree ``_walk_circuit`` made: root (the voltage
        terminal) first in breadth-first order, each id mapped to the ids
        visited from it. Junctions and wires alternate down every branch.
    :type children: dict[bytes, list[bytes]]
    :param parts: What is known about each member (resistance, temperature,
        rating). A member left out is taken to have no resistance and to sit at
        :data:`DEFAULT_AMBIENT_C`.
    :type parts: dict[bytes, PartData]
    :param loads: The load of each load terminal. Terminals with no load may
        be left out.
    :type loads: dict[bytes, LoadData]
    :param volts: The voltage on the voltage terminal.
    :type volts: float
    :param return_type: How the current returns to the source. A mirrored
        return doubles every member's series resistance; the loads' own
        resistance is unchanged.
    :type return_type: ReturnType
    :param parallel: Wires side by side: a wire that is in the tree as the way
        between two junctions, mapped to the other wires joining the same two
        junctions (leaves in the tree, as ``_walk_circuit`` leaves a closing
        wire). The group shares the current as the module docstring says; every
        wire of it appears in the solution with its own share.
    :type parallel: dict[bytes, list[bytes]] | None
    :returns: The solution. With no voltage nothing flows, but a part can still
        be over temperature because of the air around it.
    :rtype: CircuitSolution
    """
    solution = CircuitSolution()
    order = list(children)

    if not order:
        return solution

    if return_type == ReturnType.MIRRORED:
        factor = 2.0
    else:
        factor = 1.0

    if volts <= 0.0:
        for node_id in order:
            part = parts.get(node_id, _NO_PART)

            solution.amps[node_id] = 0.0
            solution.volts[node_id] = 0.0
            solution.temperature[node_id] = part.ambient_c
            solution.rise[node_id] = 0.0

            if loads.get(node_id) is not None and loads[node_id].amps > 0.0:
                solution.draw[node_id] = 0.0

        _flag_over_temperature(solution, order, parts)

        return solution

    root_id = order[0]

    # The walk alternates junction, wire, junction, ... from the root.
    is_wire = {root_id: False}
    for node_id in order:
        for next_id in children[node_id]:
            is_wire[next_id] = not is_wire[node_id]

    temperature = {node_id: parts.get(node_id, _NO_PART).ambient_c for node_id in order}

    # Wires side by side, without anything the tree does not hold.
    groups = {}
    for primary, siblings in (parallel or {}).items():
        siblings = [sibling for sibling in siblings if is_wire.get(sibling) and sibling != primary]

        if is_wire.get(primary) and siblings:
            groups[primary] = (primary, *siblings)

    # A constant-power load starts at its rating (power / volts, at the
    # supply voltage) and is refined from the voltage that reaches it.
    sinks = {}
    for node_id, load in loads.items():
        if node_id in is_wire and load.kind == LoadType.CONSTANT_POWER and load.amps > 0.0:
            sinks[node_id] = load.amps

    converged = False
    runaway = set()
    amps = entered = draw = {}
    rises = {}

    for _ in range(_MAX_ITERATIONS):
        own = {}
        for node_id in order:
            own[node_id] = factor * resistance_at(parts.get(node_id, _NO_PART), temperature[node_id])

        # a group of wires side by side is one resistance to the rest of the circuit
        series = dict(own)
        for primary, members in groups.items():
            series[primary] = _parallel_resistance([own[member] for member in members])

        amps, entered, leaving, draw = _linear_pass(
            order, children, is_wire, series, loads, sinks, volts)

        # ... and the current through it divides between the wires, each at its own temperature
        for members in groups.values():
            shares = _split_current(amps[members[0]], [own[member] for member in members])

            for member, share in zip(members, shares):
                amps[member] = share

        change = 0.0
        runaway = set()
        new_temperature = {}

        for node_id in order:
            part = parts.get(node_id, _NO_PART)
            rise, ran_away = temperature_rise(part, amps[node_id])

            rises[node_id] = rise
            new_temperature[node_id] = part.ambient_c + rise

            if ran_away:
                runaway.add(node_id)

            change = max(change, abs(new_temperature[node_id] - temperature[node_id]))

        starved = False
        new_sinks = {}

        for node_id, sink in sinks.items():
            node_volts = leaving[node_id]

            if node_volts <= 1e-6:
                starved = True
                new_sinks[node_id] = sink
                continue

            new_sinks[node_id] = loads[node_id].amps * volts / node_volts
            change = max(change, abs(new_sinks[node_id] - sink) / max(1.0, abs(sink)))

        temperature = new_temperature
        sinks = new_sinks

        if starved:
            break

        if change <= _TOLERANCE:
            converged = True
            break

    solution.total_amps = amps[root_id]
    solution.amps = amps
    solution.volts = entered
    solution.draw = draw
    solution.temperature = temperature
    solution.rise = rises
    solution.runaway = runaway
    solution.converged = converged

    _flag_over_temperature(solution, order, parts)

    return solution


@_check_types.do
def _flag_over_temperature(solution: CircuitSolution, order: list[bytes], parts: dict[bytes, PartData]) -> None:
    """Put every member hotter than its rated maximum into
    ``solution.over_temp``. A member with no rating is never flagged.

    :param solution: The solution to fill in.
    :type solution: CircuitSolution
    :param order: Every member id.
    :type order: list[bytes]
    :param parts: What is known about each member.
    :type parts: dict[bytes, PartData]
    """
    for node_id in order:
        rated = parts.get(node_id, _NO_PART).rated_max_c

        if rated is not None and solution.temperature[node_id] > rated:
            solution.over_temp.add(node_id)


@_check_types.do
def bundle_derating_factor(rows: tuple[tuple[int, float], ...], count: int) -> float | None:
    """Return the manufacturer's factor on a wire's current for *count*
    current-carrying conductors bundled together.

    Linear between the table's counts; the first row's factor holds below the
    table and the last row's above it. Two rows at one count count as the
    lower factor.

    :param rows: ``(conductor count, factor)`` pairs, in any order.
    :type rows: tuple[tuple[int, float], ...]
    :param count: The number of current-carrying conductors in the bundle.
    :type count: int
    :returns: The factor, or ``None`` when there is no usable row (a factor of
        zero or less says nothing).
    :rtype: float | None
    """
    usable = sorted((conductors, factor) for conductors, factor in rows if factor > 0.0)

    if not usable:
        return None

    if count <= usable[0][0]:
        return usable[0][1]

    for (few, few_factor), (many, many_factor) in zip(usable, usable[1:]):
        if count <= many:
            return few_factor + (many_factor - few_factor) * (count - few) / (many - few)

    return usable[-1][1]


@_check_types.do
def wire_heat_per_m(part: PartData, amps: float, temperature_c: float) -> float:
    """Return the heat a wire gives off per metre of its run, in W/m.

    :param part: The wire.
    :type part: PartData
    :param amps: The current through it.
    :type amps: float
    :param temperature_c: Its temperature, which sets its resistance.
    :type temperature_c: float
    :returns: ``I**2 * R(T) / length``; 0.0 for a part with no length.
    :rtype: float
    """
    if part.length_m <= 0.0:
        return 0.0

    return amps * amps * resistance_at(part, temperature_c) / part.length_m


@_check_types.do
def bundle_adjusted_parts(
        parts: dict[bytes, PartData],
        bundles: list[BundleData],
        amps: dict[bytes, float],
        temperature: dict[bytes, float]) -> dict[bytes, PartData]:
    """Work out how the bundles change the wires in them.

    For each wire in a bundle: with a bundling table of its own, its thermal
    resistance is divided by the square of the table's factor for the number of
    wires in the bundle that carry current (the warmest bundle, if there are
    several); without one, its ambient rises by the heat of the OTHER wires in
    the bundle spread over the bundle's outer surface (the warmest bundle again).

    :param parts: Every wire's own part data, before any adjustment.
    :type parts: dict[bytes, PartData]
    :param bundles: The bundles.
    :type bundles: list[BundleData]
    :param amps: The current through each wire as it is now.
    :type amps: dict[bytes, float]
    :param temperature: Each wire's temperature as it is now.
    :type temperature: dict[bytes, float]
    :returns: The part data to solve with, for the wires a bundle changes only.
    :rtype: dict[bytes, PartData]
    """
    heat = {wire_id: wire_heat_per_m(part, amps.get(wire_id, 0.0), temperature.get(wire_id, part.ambient_c))
            for wire_id, part in parts.items()}

    ambient_rise = {}
    weakest_factor = {}

    for bundle in bundles:
        members = [wire_id for wire_id in bundle.wire_ids if wire_id in parts]
        carrying = sum(1 for wire_id in members if abs(amps.get(wire_id, 0.0)) > _CURRENT_EPSILON)
        total = sum(heat[wire_id] for wire_id in members)
        surface = (BUNDLE_HEAT_TRANSFER * math.pi * bundle.diameter_m *
                   BUNDLE_PACKING_FACTOR.get(bundle.kind, 1.0))

        for wire_id in members:
            if parts[wire_id].bundling:
                factor = bundle_derating_factor(parts[wire_id].bundling, carrying)

                if factor is not None:
                    weakest_factor[wire_id] = min(factor, weakest_factor.get(wire_id, factor))
                    continue

            if surface > 0.0:
                rise = min((total - heat[wire_id]) / surface, RUNAWAY_C)
                ambient_rise[wire_id] = max(rise, ambient_rise.get(wire_id, 0.0))

    adjusted = {}

    for wire_id, factor in weakest_factor.items():
        adjusted[wire_id] = replace(parts[wire_id], theta=parts[wire_id].theta / (factor * factor))

    for wire_id, rise in ambient_rise.items():
        part = adjusted.get(wire_id, parts[wire_id])
        adjusted[wire_id] = replace(part, ambient_c=part.ambient_c + rise)

    return adjusted


@_check_types.do
def solve_bundled(inputs: dict[Any, CircuitInput], bundles: list[BundleData]) -> dict[Any, CircuitSolution]:
    """Solve circuits that share bundles together.

    The wires of a bundle warm each other whichever circuit they belong to, so
    each round solves every circuit with the wires' present adjustments, works
    out the adjustments again from the solutions, and stops when they no longer
    move.

    :param inputs: Every circuit that shares a bundle with another (or with
        itself), by any key.
    :type inputs: dict[typing.Any, CircuitInput]
    :param bundles: Every bundle any of them is in.
    :type bundles: list[BundleData]
    :returns: Each circuit's solution under the same key. Every solution is
        marked not converged when the adjustments had not settled after
        :data:`_MAX_BUNDLE_ITERATIONS` rounds.
    :rtype: dict[typing.Any, CircuitSolution]
    """
    base = {}
    for circuit in inputs.values():
        base.update(circuit.parts)

    adjusted = {}
    solutions = {}
    settled = False

    for _ in range(_MAX_BUNDLE_ITERATIONS):
        for key, circuit in inputs.items():
            parts = {wire_id: adjusted.get(wire_id, part) for wire_id, part in circuit.parts.items()}

            solutions[key] = solve_circuit(
                circuit.children, parts, circuit.loads, circuit.volts, circuit.return_type, circuit.parallel)

        amps = {}
        temperature = {}
        for solution in solutions.values():
            amps.update(solution.amps)
            temperature.update(solution.temperature)

        new_adjusted = bundle_adjusted_parts(base, bundles, amps, temperature)

        change = 0.0
        for wire_id in set(adjusted) | set(new_adjusted):
            before = adjusted.get(wire_id, base[wire_id])
            after = new_adjusted.get(wire_id, base[wire_id])

            change = max(change, abs(after.ambient_c - before.ambient_c),
                         abs(after.theta - before.theta) / max(1.0, abs(before.theta)))

        adjusted = new_adjusted

        if change <= _BUNDLE_TOLERANCE:
            settled = True
            break

    if not settled:
        for solution in solutions.values():
            solution.converged = False

    return solutions
