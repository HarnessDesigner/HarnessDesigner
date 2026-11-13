# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The shield ring: the dashed ellipse the schematic draws across the wires a solder sleeve shields (user, 2026-11-12).

The sleeve's schematic state is three columns of its ``pjt_splices`` row and its own ``point2d``:

* ``point2d`` is the ring's CONNECTED narrow end: where the shield wire (the pigtail, a black wire that is auto routed to its pin) ends.
* ``ring_dir`` (0 +X, 1 +Z, 2 -X, 3 -Z) is the direction from that end to the other narrow end: the long axis of the ellipse, which runs ACROSS
  the shielded wires.
* ``ring_size`` is the semi-long axis ``a`` (0 = not placed yet). The semi-short axis is ``a / RING_RATIO`` (1:3, user): the longer the
  ring, the wider it is.
* ``ring_hard`` is set once the user placed or sized the ring by hand: the automatic placement then leaves it where it is.

The wires of the cable (``objects.cable_conductor.ConductorRun``) are routed THROUGH the ring: each one crosses the ellipse straight, in
the direction of the wires, at the place where it leaves its terminal (:func:`gates`); ``wire_routing.reroute.reroute_wire`` routes
the wire in legs to the two ends of that crossing. Everything else routes around the ring: the sleeve's schematic view gives the ring's
box as its own bounds, which the router reads as an obstacle (``routing._housing_rects``), except for the cable's own wires
(``routing._obstacle_excludes``).

:func:`auto_place` puts the ring at the closest place beyond the terminals' wire stubs where it can circle all of the cable's wires with no
other wire (and nothing else) in its box.
"""

import math
from typing import TYPE_CHECKING, NamedTuple, Union as _Union

from . import routing as _wire_routing
from ..geometry import point as _point
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..database.project_db import pjt_splice as _pjt_splice
    from ..objects import project as _project
    from ..objects import cable as _cable
    from ..objects import splice as _splice
    from ..objects import wire as _wire_obj


# long : short axis of the ellipse (user, 2026-11-12: 1:3; it was about 1:2)
RING_RATIO = 3.0

# the directions ``ring_dir`` stands for
DIRECTIONS = ((1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0))

# The ring is sized by the wires it circles (user, 2026-11-12): every wire is drawn the same size and stacks at one pitch (``routing._lane_spacing``:
# 3 wire diameters, the wire and the gap of two wires between wires, when no font metrics are known: ``Config.layout.wire_spacing``), so N wires
# fill N pitches and the ring is N pitches long (:func:`wires_length`), not more. Its shortest length, as a semi-long axis in pitches:
MIN_HALF_LENGTH = 1.0

# how many lane spacings the ring is tried further out, one at a time, before it is given up
MAX_STEPS = 80


class Ring(NamedTuple):
    """A shield ring: ``tip`` the connected narrow end, ``far`` the other, ``center``, ``u`` the unit direction tip -> far (across the wires),
    ``a`` / ``b`` the semi-long / semi-short axes."""
    tip: tuple[float, float]
    far: tuple[float, float]
    center: tuple[float, float]
    u: tuple[float, float]
    a: float
    b: float


@_check_types.do
def wires_length(low: float, high: float, pitch: float) -> float:
    """The length of a ring that circles wires from *low* to *high* across (their stubs' coordinates): one *pitch* for each wire, which is
    the span between the outer wires and one pitch more (half a pitch beyond each of them). N wires side by side are N pitches."""
    return (high - low) + pitch


@_check_types.do
def ring_from(tip: tuple[float, float], direction: int, size: float) -> Ring:
    """The ring with its connected end at *tip*, long axis in direction code *direction* and semi-long axis *size*."""
    ux, uz = DIRECTIONS[direction]

    return Ring(tip=(tip[0], tip[1]), far=(tip[0] + ux * 2.0 * size, tip[1] + uz * 2.0 * size),
                center=(tip[0] + ux * size, tip[1] + uz * size), u=(ux, uz), a=size, b=size / RING_RATIO)


@_check_types.do
def ring_of(splice_db: "_pjt_splice.PJTSplice") -> _Union[Ring, None]:
    """The ring a sleeve's row stores, or ``None`` while it has none (not a sleeve, or not placed yet)."""
    size = splice_db.ring_size

    if size <= 0.0:
        return None

    tip = splice_db.position2d

    return ring_from((float(tip.x), float(tip.z)), splice_db.ring_dir, size)


@_check_types.do
def ring_rect(ring: Ring) -> tuple[float, float, float, float]:
    """The box of a ring, ``(min_x, min_z, max_x, max_z)``: the long axis is along X or Z, so it is axis aligned."""
    half_x = ring.a if ring.u[0] != 0.0 else ring.b
    half_z = ring.a if ring.u[1] != 0.0 else ring.b

    return ring.center[0] - half_x, ring.center[1] - half_z, ring.center[0] + half_x, ring.center[1] + half_z


@_check_types.do
def direction_code(ux: float, uz: float) -> int:
    """The ``ring_dir`` code of the cardinal direction nearest to ``(ux, uz)``."""
    if abs(ux) >= abs(uz):
        return 0 if ux >= 0.0 else 2

    return 1 if uz >= 0.0 else 3


@_check_types.do
def runs_of(cable: "_cable.Cable") -> list["_wire_obj.Wire"]:
    """The drawn conductors of a cable (``ConductorRun``), the shield conductor left out."""
    runs = []

    for conductor in cable.db_obj.conductors:
        if conductor.is_shield:
            continue

        run = cable.conductor_object(conductor).run

        if run is not None and run.objschematic is not None and run.is_connected:
            runs.append(run)

    return runs


@_check_types.do
def beyond_sign(sleeve: "_splice.Splice") -> float:
    """Which side of the ring is the far side from the housing the cable's wires leave: ``+1`` when the ring lies beyond the wires' stubs
    in the direction ``v = (-uz, ux)`` of its short axis (its ``sin`` half is the far one), ``-1`` when it lies on the other side. ``+1`` when
    that can't be told (no cable, no drawn wire)."""
    row = sleeve.db_obj
    ring = ring_of(row)
    found = row.shield_cable

    if ring is None or found is None:
        return 1.0

    cable = found[0].get_object()

    if cable is None:
        return 1.0

    runs = runs_of(cable)

    if not runs:
        return 1.0

    pin, stub = end_stubs(runs[0], cable.shield_sleeve(True) == sleeve)
    s = stub if stub is not None else pin
    ux, uz = ring.u

    return 1.0 if (ring.center[0] - s[0]) * -uz + (ring.center[1] - s[1]) * ux >= 0.0 else -1.0


@_check_types.do
def end_stubs(run: "_wire_obj.Wire", at_start: bool) -> tuple[tuple[float, float], tuple[float, float] | None]:
    """``(pin, stub)`` of a run at one end: the 2D point the wire ends on, and the end of its mandatory straight exit stub (``None`` when
    it has none, e.g. it ends on a splice)."""
    from . import reroute as _reroute

    end = run.db_obj.start_position2d if at_start else run.db_obj.stop_position2d
    pin = (float(end.x), float(end.z))

    return pin, _reroute._terminal_exit_stub_point(run, 'start' if at_start else 'stop')  # NOQA


@_check_types.do
def gates(project: "_project.Project", run: "_wire_obj.Wire") -> list[tuple[bool, tuple[float, float], tuple[float, float]]]:
    """Where *run* crosses the shield rings of its cable, one ``(at_start, near, far)`` per end that has a ring.

    The wire crosses the ring straight, along the direction of the wires (across the ring's long axis), at the place where it leaves its
    terminal: ``near`` is the point just before the ring on the terminal's side and ``far`` the one just after it. The wire is routed up to
    ``near``, runs straight to ``far`` (through the ellipse) and is routed on from there.
    """
    cable = run.node.cable
    pitch = _wire_routing._lane_spacing()  # NOQA
    result = []

    for at_start in (True, False):
        sleeve = cable.shield_sleeve(at_start)

        if sleeve is None:
            continue

        ring = ring_of(sleeve.db_obj)

        if ring is None:
            continue

        pin, stub = end_stubs(run, at_start)
        s = stub if stub is not None else pin

        ux, uz = ring.u
        wx, wz = -uz, ux
        cx, cz = ring.center

        across = max(-0.9 * ring.a, min(0.9 * ring.a, (s[0] - cx) * ux + (s[1] - cz) * uz))
        gx, gz = cx + ux * across, cz + uz * across

        # the ring is on the far side of the terminal's stub
        sign = 1.0 if (cx - s[0]) * wx + (cz - s[1]) * wz >= 0.0 else -1.0
        reach = ring.b + pitch

        near = (gx - wx * sign * reach, gz - wz * sign * reach)
        far = (gx + wx * sign * reach, gz + wz * sign * reach)

        result.append((at_start, near, far))

    return result


@_check_types.do
def ordered_gates(project: "_project.Project", run: "_wire_obj.Wire") -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """:func:`gates` of *run* as ``(first, second)`` pairs in the order the wire runs from its start end to its stop end (at the stop end
    the wire reaches the far side of the ring first)."""
    legs = []

    for at_start, near, far in gates(project, run):
        legs.append((0 if at_start else 1, (near, far) if at_start else (far, near)))

    return [pair for _order, pair in sorted(legs, key=lambda item: item[0])]


@_check_types.do
def excluded_for(wire: "_wire_obj.Wire", splice: "_splice.Splice") -> bool:
    """Whether the ring of *splice* is no obstacle to *wire*: *wire* is a conductor of the cable that *splice* is the sleeve of."""
    from ..objects import cable_conductor as _cable_conductor

    if not isinstance(wire, _cable_conductor.ConductorRun):
        return False

    part = splice.db_obj.part

    if part is None or not part.is_solder_sleeve:
        return False

    found = splice.db_obj.shield_cable

    if found is None:
        return False

    node = wire.node

    return node is not None and node.cable is not None and found[0].db_id == node.cable.db_obj.db_id


@_check_types.do
def foreign_pins(project: "_project.Project", own: set, wire_dir: tuple[float, float], u: tuple[float, float], along: float,
                 low: float, high: float, pitch: float) -> int:
    """How many wires that are not in *own* (the cable's wires and the sleeve's) leave the housing between *low* and *high* across
    (``u``), on the housing's side the cable's wires leave from (*along*, in the direction of ``wire_dir``): one for each pin, in the order
    the pins are displayed, that is on the ring's span without being the cable's."""
    seen = set()

    for wire in project.schematic_wires:
        if wire in own or not wire.is_connected:
            continue

        for end in (wire.db_obj.start_position2d, wire.db_obj.stop_position2d):
            x, z = float(end.x), float(end.z)

            if abs(x * wire_dir[0] + z * wire_dir[1] - along) > pitch / 2.0:
                continue

            across = x * u[0] + z * u[1]

            if low + 1e-6 < across < high - 1e-6:
                seen.add(round(across, 3))

    return len(seen)


@_check_types.do
def _rect_blocked(project: "_project.Project", rect: tuple[float, float, float, float],
                  own_wires: set, own_aabb: list[int]) -> bool:
    """Whether anything but the cable's own wires is in *rect*: another wire's path, a housing, a note, another splice or ring."""
    from . import reroute as _reroute

    for wire in project.schematic_wires:
        if wire in own_wires or not wire.is_connected:
            continue

        if _reroute._path_overlaps_rect(wire, rect):  # NOQA
            return True

    return bool(_wire_routing._housing_rects(project, *rect, exclude=own_aabb))  # NOQA


@_check_types.do
def auto_place(project: "_project.Project", cable: "_cable.Cable", at_start: bool, sleeve: "_splice.Splice") -> bool:
    """Put the ring of the sleeve on one end of *cable* at the closest place where it circles all of the cable's wires and no other wire
    passes through it (user, 2026-11-12): straight out from the wires' terminal stubs, beyond them, one lane spacing further out at a time
    until its box is free. A hard set ring (``ring_hard``) is left alone.

    :returns: ``True`` when the ring is placed (or is hard set), ``False`` when no place was found (the ring is left as it was) or there is
        nothing to circle (no drawn wire of the cable).
    """
    row = sleeve.db_obj

    if row.ring_hard:
        return True

    runs = runs_of(cable)

    if not runs:
        return False

    pitch = _wire_routing._lane_spacing()  # NOQA

    pins = []
    stubs = []
    directions = []

    for run in runs:
        pin, stub = end_stubs(run, at_start)

        if stub is not None and (stub[0] - pin[0] or stub[1] - pin[1]):
            length = math.hypot(stub[0] - pin[0], stub[1] - pin[1])
            directions.append(((stub[0] - pin[0]) / length, (stub[1] - pin[1]) / length))

        pins.append(pin)
        stubs.append(stub if stub is not None else pin)

    # the direction of the wires where they leave their terminals; the ring's long axis is across it
    if directions:
        mean_x = sum(d[0] for d in directions)
        mean_z = sum(d[1] for d in directions)
    else:
        mean_x, mean_z = 1.0, 0.0

    if abs(mean_x) >= abs(mean_z):
        wire_dir = (1.0 if mean_x >= 0.0 else -1.0, 0.0)
    else:
        wire_dir = (0.0, 1.0 if mean_z >= 0.0 else -1.0)

    u = (-wire_dir[1], wire_dir[0])

    across = [(s[0] * u[0] + s[1] * u[1]) for s in stubs]
    along = [(s[0] * wire_dir[0] + s[1] * wire_dir[1]) for s in stubs]
    low, high = min(across), max(across)
    middle = (low + high) / 2.0
    half = (high - low) / 2.0

    a = max(wires_length(low, high, pitch) / 2.0, MIN_HALF_LENGTH * pitch)
    b = a / RING_RATIO
    furthest = max(along)

    # the connected end is the one on the side of what the shield wire goes to
    target = _pigtail_target(sleeve)

    # The shield wire comes straight out of its pin and ends on the ring's narrow end without a turn (user, 2026-11-12): when its pin
    # is beside the cable's wires (the wires are all on one side of it, and it leaves its terminal the same way they do), the connected
    # end is on the line of its stub and the ring runs from there across the wires.
    exit_ = _pigtail_exit(sleeve)

    if exit_ is not None:
        pin_s = exit_[0]
        exit_dir = (exit_[1][0] - exit_[0][0], exit_[1][1] - exit_[0][1])
        exit_len = math.hypot(*exit_dir)
        t = pin_s[0] * u[0] + pin_s[1] * u[1]

        if exit_len > 1e-9 and (exit_dir[0] * wire_dir[0] + exit_dir[1] * wire_dir[1]) / exit_len > 0.99 and (t < low - 1e-6 or t > high + 1e-6):
            sign = 1.0 if t < low else -1.0

            # the connected end is as close to the nearest wire as the wire spacing allows (never nearer than one lane spacing)
            if sign > 0.0:
                t = min(t, low - pitch) if low - t < pitch else t
                reach = high + pitch / 2.0 - t
            else:
                t = max(t, high + pitch) if t - high < pitch else t
                reach = t - (low - pitch / 2.0)

            # the ring is just long enough to circle all of the wires: from the connected end to the far side of the farthest wire's pitch
            a = max(reach / 2.0, MIN_HALF_LENGTH * pitch)
            b = a / RING_RATIO
            middle = t + sign * a
            target = (u[0] * t + wire_dir[0] * furthest, u[1] * t + wire_dir[1] * furthest)

    own = set(runs)
    own.update(sleeve.branch_wires)
    own_aabb = [sleeve.objschematic._aabb_index]  # NOQA

    # Wires that are not the cable's but leave the housing between the ring's two ends (user, 2026-11-12) are in the ring's way: each one
    # needs one more pitch of room before the ring to turn out of the ring's span, so the ring is pushed out by one pitch for each.
    along_pins = sum(pin[0] * wire_dir[0] + pin[1] * wire_dir[1] for pin in pins) / len(pins)
    between = foreign_pins(project, own, wire_dir, u, along_pins, middle - a, middle + a, pitch)

    for step in range(MAX_STEPS):
        out = furthest + b + 2.0 * pitch + between * pitch + step * pitch
        # (wire_dir and u are perpendicular unit vectors: the centre is `out` along the wires and `middle` across them)
        cx = wire_dir[0] * out + u[0] * middle
        cz = wire_dir[1] * out + u[1] * middle

        rect = _rect_for(cx, cz, u, a, b)

        if _rect_blocked(project, _padded(rect, pitch / 2.0), own, own_aabb):
            continue

        _write(project, sleeve, (cx, cz), u, a, target)
        return True

    return False


@_check_types.do
def _rect_for(cx: float, cz: float, u: tuple[float, float], a: float, b: float) -> tuple[float, float, float, float]:
    half_x = a if u[0] != 0.0 else b
    half_z = a if u[1] != 0.0 else b

    return cx - half_x, cz - half_z, cx + half_x, cz + half_z


@_check_types.do
def _padded(rect: tuple[float, float, float, float], by: float) -> tuple[float, float, float, float]:
    return rect[0] - by, rect[1] - by, rect[2] + by, rect[3] + by


@_check_types.do
def _pigtail_target(sleeve: "_splice.Splice") -> tuple[float, float] | None:
    """Where the sleeve's shield wire goes to: the 2D point of the far end of the first connected wire on the sleeve; ``None`` if none."""
    for wire in sleeve.branch_wires:
        if not wire.is_connected:
            continue

        other = wire.db_obj.start_position2d if wire.stop_sibling is sleeve else wire.db_obj.stop_position2d

        return float(other.x), float(other.z)

    return None


@_check_types.do
def _pigtail_exit(sleeve: "_splice.Splice") -> tuple[tuple[float, float], tuple[float, float]] | None:
    """``(pin, stub)`` at the far end of the sleeve's first connected wire (the shield wire): where it ends and the end of its straight exit
    stub; ``None`` when there is no such wire or its end has no stub (it does not end on a terminal)."""
    from . import reroute as _reroute

    for wire in sleeve.branch_wires:
        if not wire.is_connected:
            continue

        sleeve_is_stop = wire.stop_sibling is sleeve
        other = wire.db_obj.start_position2d if sleeve_is_stop else wire.db_obj.stop_position2d
        stub = _reroute._terminal_exit_stub_point(wire, 'start' if sleeve_is_stop else 'stop')  # NOQA

        if stub is None:
            return None

        return (float(other.x), float(other.z)), (float(stub[0]), float(stub[1]))

    return None


@_check_types.do
def _write(project: "_project.Project", sleeve: "_splice.Splice", center: tuple[float, float], u: tuple[float, float], a: float,
           target: tuple[float, float] | None) -> None:
    """Store a ring: the connected end is the narrow end nearer to *target*, its place is the sleeve's own point."""
    row = sleeve.db_obj

    first = (center[0] - u[0] * a, center[1] - u[1] * a)
    second = (center[0] + u[0] * a, center[1] + u[1] * a)

    if target is not None and math.hypot(second[0] - target[0], second[1] - target[1]) < math.hypot(first[0] - target[0], first[1] - target[1]):
        tip, direction = second, (-u[0], -u[1])
    else:
        tip, direction = first, u

    live = row.position2d
    shift = _point.Point(tip[0] - float(live.x), 0.0, tip[1] - float(live.z))

    if abs(shift.x) > 1e-9 or abs(shift.z) > 1e-9:
        live += shift

    code = direction_code(*direction)

    if row.ring_size != a:
        row.ring_size = a

    if row.ring_dir != code:
        row.ring_dir = code

    sleeve.objschematic.reload_ring()  # NOQA


@_check_types.do
def move_ring(project: "_project.Project", sleeve: "_splice.Splice", tip: tuple[float, float]) -> None:
    """The user moved the connected end of the ring: it is now hard set there, the shield wire is routed to it again and the cable's wires
    are routed through the ring."""
    row = sleeve.db_obj
    row.ring_hard = True

    live = row.position2d
    live += _point.Point(tip[0] - float(live.x), 0.0, tip[1] - float(live.z))

    sleeve.objschematic.reload_ring()  # NOQA
    refresh(project, sleeve)


@_check_types.do
def resize_ring(project: "_project.Project", sleeve: "_splice.Splice", far: tuple[float, float]) -> None:
    """The user dragged the far narrow end of the ring: the connected end stays, the ring is as long as the distance to the far end along
    its long axis (and so as wide as that over :data:`RING_RATIO`), and it is hard set."""
    row = sleeve.db_obj
    ring = ring_of(row)

    if ring is None:
        return

    pitch = _wire_routing._lane_spacing()  # NOQA
    reach = (far[0] - ring.tip[0]) * ring.u[0] + (far[1] - ring.tip[1]) * ring.u[1]

    row.ring_size = max(reach / 2.0, MIN_HALF_LENGTH * pitch)
    row.ring_hard = True

    sleeve.objschematic.reload_ring()  # NOQA
    refresh(project, sleeve)


@_check_types.do
def refresh(project: "_project.Project", sleeve: "_splice.Splice") -> None:
    """Route the sleeve's cable again after its ring changed: the wires through the ring, the shield wire to its end."""
    from . import reroute as _reroute

    found = sleeve.db_obj.shield_cable

    if found is None:
        return

    cable = found[0].get_object()

    if cable is not None:
        _reroute.route_shield_group(project, cable)
