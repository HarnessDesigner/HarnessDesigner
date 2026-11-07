# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The maths and the draw call of a twisted wire (TWISTED_WIRE_DESIGN.md, sections 5 and 7).

A twisted pair or triple is drawn as one tube per conductor, per path segment. The tube has no mesh: the faces vertex shader
(``gl/shaders/faces/vertex.vert``) makes every vertex from ``gl_VertexID`` when its ``twistRings`` uniform is above 0, so a
change of the path or of the twist rate costs a few uniforms, not a new buffer. This module holds what is left on the Python side:

* :func:`profile` -- where each conductor's circle sits in the cable's cross-section.
* :func:`plan` -- the per-segment bookkeeping of a bent wire: the phase the twist carries from one segment into the next and the
  mitre that closes the gap on the outside of a bend.
* :class:`TwistedTube` -- sets the uniforms and issues the draw.

Frames: a segment's local +Z is its direction and its local X/Y are the columns of its rotation matrix (``Angle.as_matrix_numpy``,
a column-vector matrix: the columns are the local axes in world space). The cross-section turns rigidly about +Z by
``phase + rate * z``, which makes each conductor's centre follow a helix; the lay length is ``25.4 / tpi`` mm.
"""

from typing import TYPE_CHECKING
from typing import NamedTuple as _NamedTuple

import math
import numpy as np
from OpenGL import GL
from PySide6 import QtGui

from .. import check_types as _check_types

if TYPE_CHECKING:
    from ..geometry import point as _point
    from ..geometry import angle as _angle
    from ..gl import materials as _materials
    from ..gl.shaders import program as _program


# Must match TWIST_SIDES in gl/shaders/faces/vertex.vert.
SIDES = 16

# Rings per full turn of the twist. Sixteen puts a ring every 22.5 degrees; the chord of a circle of radius r that short is off
# by r * (1 - cos(11.25 degrees)), 2 percent of r.
SAMPLES_PER_TURN = 16

# Half the angular width of a conductor's stripe, radians (the stripe covers 60 degrees of the conductor's circumference).
STRIPE_HALF_ANGLE = math.radians(30.0)

# A segment never gets more rings than this (a 3 m run at 4 turns per inch is 470 turns).
MAX_RINGS = 8000

MM_PER_INCH = 25.4

# The shortest lay length (distance for one full turn) a twisted cable is drawn with, in cable diameters. The catalogue's TPI is a
# flat 1.0 for most pairs whatever their size, so a thick pair (a 6.3 mm 12 AWG pair is 4 diameters per turn) would be drawn as a
# steep, swollen, pinched helix that no real cable has: a real pair is laid 8 to 16 diameters per turn. A thin pair at 1 TPI is
# already 12 diameters or more and is not touched.
MIN_LAY_DIAMETERS = 8.0

# A bend sharper than this (cosine of the angle between the two directions) is a U-turn: the mitre is undefined at 180 degrees,
# so the two segments are drawn as if they did not touch.
_U_TURN = -0.99

# A bend smaller than this (radians) needs no mitre.
_STRAIGHT = 1e-4

# The centreline pitches discrete ribbon cable is made in, mm. The catalogue gives no pitch, so a ribbon is drawn at the smallest of
# these that holds its insulated conductor (28 AWG, 7 strands, is the 1.27 mm of the common IDC cable).
RIBBON_PITCHES = (0.635, 1.27, 2.54, 5.08)

# What insulation adds to a bare conductor's diameter, mm, when the catalogue gives no diameter over the insulation (the conductor
# rows of a cable made by the database builder have od_mm 0). 0.38 mm of metal gives 0.88 mm, the 0.89 mm of 28 AWG ribbon.
INSULATION_MM = 0.5

# The bare conductor assumed for a part with no size at all: 28 AWG, 7 strands.
DEFAULT_CONDUCTOR_MM = 0.38


class SegmentTwist(_NamedTuple):
    """What the shader needs, besides the segment's own position and angle, to draw one segment of a twisted wire."""

    phase: float
    """Rotation of the cross-section at the start of the segment, radians."""

    start: tuple[float, float, float, float]
    """Direction of the previous segment in THIS segment's frame (x, y, z) and the distance (w, mm) over which the start ring's mitre
    fades in; ``w`` of 0 means there is no previous segment, the start is cut square."""

    end: tuple[float, float, float, float]
    """The same for the next segment and the end ring."""


_NO_MITRE = (0.0, 0.0, 1.0, 0.0)


@_check_types.do
def rate_from_tpi(tpi: float) -> float:
    """The twist rate, radians per mm, of a wire with ``tpi`` twists (turns) per inch.

    :param tpi: Twists per inch, above 0.
    :returns: Radians of rotation of the cross-section per mm of wire.
    """
    return 2.0 * math.pi * tpi / MM_PER_INCH


@_check_types.do
def rate_for(tpi: float, outer_diameter: float) -> float:
    """The twist rate, radians per mm, a cable is drawn with: that of ``tpi`` unless the lay length would then be shorter than
    :data:`MIN_LAY_DIAMETERS` cable diameters, in which case the lay length is stretched to that.

    :param tpi: Twists per inch, above 0.
    :param outer_diameter: Diameter of the circle that holds the whole cable, mm.
    :returns: Radians of rotation of the cross-section per mm of wire.
    """
    lay = max(MM_PER_INCH / tpi, MIN_LAY_DIAMETERS * outer_diameter)

    return 2.0 * math.pi / lay


@_check_types.do
def profile(count: int, outer_diameter: float) -> list[tuple[float, float, float]]:
    """Where the conductors of a twisted cable sit, as ``(centre x, centre y, radius)`` in mm, conductor 0 first.

    The conductors are equal circles touching each other and the outside of the cable, so the radius ``r`` and the radius of the
    circle the centres lie on ``c`` follow from the outer diameter: ``c = r / sin(pi / n)`` and ``outer radius = c + r``. A pair has
    ``r`` = diameter / 4 and a triple diameter / 4.309 (the conductor is 1 / 2.155 of the cable's diameter).

    Up to five conductors lie on one ring, the first on the +X axis, the rest evenly around. From six on, conductor 0 is the
    centre one (centre ``(0, 0)``; the shader takes a stripe on it to be on the +X side) and the rest lie around it: on one ring
    while that is nine or fewer (``1 + 5``, ``1 + 6``, ``1 + 7`` ...), otherwise in layers as a stranded cable is built (layer ``k`` is
    at ``2 k r`` and holds up to ``floor(pi / asin(1 / 2k))`` conductors, innermost layer filled first, a part-filled layer spaced
    evenly). Every circle is the same size, ``r`` following from the outer diameter, so there is no limit on the count.

    :param count: Number of conductors, 2 or more.
    :param outer_diameter: Diameter of the circle that holds the whole cable, mm.
    :returns: One circle per conductor.
    """
    if count <= 5:
        radius = outer_diameter * 0.5 / (1.0 + 1.0 / math.sin(math.pi / count))
        centre = radius / math.sin(math.pi / count)
        result = []

        for i in range(count):
            angle = 2.0 * math.pi * i / count
            result.append((centre * math.cos(angle), centre * math.sin(angle), radius))

        return result

    # in units of the conductor's radius
    around = count - 1
    unit = [(0.0, 0.0)]

    if around <= 9:
        distance = max(2.0, 1.0 / math.sin(math.pi / around))

        for i in range(around):
            angle = 2.0 * math.pi * i / around
            unit.append((distance * math.cos(angle), distance * math.sin(angle)))
    else:
        remaining = around
        layer = 1

        while remaining > 0:
            fits = int(math.pi / math.asin(1.0 / (2.0 * layer)))
            here = min(fits, remaining)
            distance = 2.0 * layer
            start = 0.0
            if layer % 2 == 0:
                start = math.pi / here

            for i in range(here):
                angle = start + 2.0 * math.pi * i / here
                unit.append((distance * math.cos(angle), distance * math.sin(angle)))

            remaining -= here
            layer += 1

    reach = max(math.hypot(x, y) for x, y in unit)
    radius = outer_diameter * 0.5 / (1.0 + reach)

    return [(x * radius, y * radius, radius) for x, y in unit]


@_check_types.do
def insulated_diameter(conductor_diameter: float, od: float = 0.0) -> float:
    """The diameter over a conductor's insulation, mm: *od* when the catalogue gave one, else the bare conductor's plus
    :data:`INSULATION_MM` (:data:`DEFAULT_CONDUCTOR_MM` for a part with no size).

    :param conductor_diameter: The metal's diameter, mm; 0 for none.
    :param od: The diameter over the insulation, mm; 0 for none.
    """
    if od > 0.0:
        return od

    return (conductor_diameter if conductor_diameter > 0.0 else DEFAULT_CONDUCTOR_MM) + INSULATION_MM


@_check_types.do
def ribbon_pitch(conductor_diameter: float, od: float = 0.0) -> float:
    """The centreline pitch a ribbon cable is drawn with, mm: the smallest of :data:`RIBBON_PITCHES` that holds the insulated
    conductor (the conductor itself when it is wider than the largest).

    :param conductor_diameter: The metal's diameter, mm; 0 for none.
    :param od: The diameter over the insulation, mm; 0 for none.
    """
    insulated = insulated_diameter(conductor_diameter, od)

    for pitch in RIBBON_PITCHES:
        if pitch >= insulated - 1e-9:
            return pitch

    return insulated


@_check_types.do
def ribbon_profile(count: int, pitch: float) -> list[tuple[float, float, float]]:
    """Where the conductors of a ribbon cable sit, as ``(centre x, centre y, radius)`` in mm, conductor 0 (pin 1) at the -X edge.

    The conductors lie in a row across X, a pitch apart and centred on the axis, each touching the next (radius = half the
    pitch): the web between them is not drawn. The cable is ``count * pitch`` wide and one pitch thick.

    :param count: Number of conductors, 1 or more.
    :param pitch: Centreline pitch, mm.
    """
    middle = (count - 1) * 0.5

    return [((i - middle) * pitch, 0.0, pitch * 0.5) for i in range(count)]


@_check_types.do
def jacket_diameter(count: int, insulated: float) -> float:
    """The outside diameter, mm, of a round jacketed cable that holds *count* equal insulated conductors of diameter
    *insulated*, packed as :func:`profile` packs them. For a cable whose part gives no diameter.

    :param count: Number of conductors.
    :param insulated: Diameter over a conductor's insulation, mm.
    """
    if count <= 1:
        return insulated / 0.6

    return insulated / (2.0 * profile(count, 1.0)[0][2])


@_check_types.do
def rolled(rotation: np.ndarray, phase: float) -> np.ndarray:
    """A segment's rotation matrix turned by *phase* about its own +Z (the way the shader turns the cross-section): the frame whose
    X axis is the cross-section's own X axis at the segment's start.

    :param rotation: A 3x3 column-vector rotation matrix (the columns are the local axes in world space).
    :param phase: The turn, radians.
    """
    cosine = math.cos(phase)
    sine = math.sin(phase)

    return np.asarray(rotation, dtype=np.float64) @ np.array(
        [[cosine, -sine, 0.0], [sine, cosine, 0.0], [0.0, 0.0, 1.0]])


@_check_types.do
def _transport_delta(previous: np.ndarray, current: np.ndarray) -> float:
    """The angle, about the current segment's direction, from its own X axis to the previous segment's X axis carried round the bend
    by the minimal rotation (parallel transport).

    A point at angle ``a`` of the cross-section in the previous segment's frame is at angle ``a + delta`` in the current one's.
    """
    d1 = previous[:, 2]
    d2 = current[:, 2]
    x1 = previous[:, 0]

    axis = np.cross(d1, d2)
    sine = float(np.linalg.norm(axis))
    cosine = float(np.dot(d1, d2))

    if sine < 1e-9:
        carried = x1
    else:
        k = axis / sine
        angle = math.atan2(sine, cosine)
        carried = x1 * math.cos(angle) + np.cross(k, x1) * math.sin(angle) + k * float(np.dot(k, x1)) * (1.0 - math.cos(angle))

    return math.atan2(float(np.dot(carried, current[:, 1])), float(np.dot(carried, current[:, 0])))


@_check_types.do
def plan(rotations: list[np.ndarray], lengths: list[float], joined: list[bool], rate: float, outer_radius: float,
         start_phase: float = 0.0) -> list[SegmentTwist]:
    """Work out the twist phase and the mitre of every segment of a bent wire.

    :param rotations: One 3x3 column-vector rotation matrix per segment; its columns are the segment's local axes in world space.
    :param lengths: The segments' lengths, mm.
    :param joined: ``joined[i]`` is True when segment ``i`` starts where segment ``i - 1`` ends (``joined[0]`` is never read). A
        segment hidden inside a bundle breaks the chain.
    :param rate: Twist rate, radians per mm (:func:`rate_from_tpi`).
    :param outer_radius: Radius of the circle that holds the whole cable, mm.
    :param start_phase: The first segment's phase, radians: the roll of a ribbon cable (rate 0), 0 for a twisted one.
    :returns: One :class:`SegmentTwist` per segment.
    """
    count = len(rotations)
    phases = [0.0] * count

    if count:
        phases[0] = start_phase

    starts = [_NO_MITRE] * count
    ends = [_NO_MITRE] * count

    for i in range(1, count):
        previous = np.asarray(rotations[i - 1], dtype=np.float64)
        current = np.asarray(rotations[i], dtype=np.float64)
        previous_end = phases[i - 1] + rate * lengths[i - 1]

        if not joined[i]:
            phases[i] = previous_end
            continue

        d1 = previous[:, 2]
        d2 = current[:, 2]
        cosine = float(np.dot(d1, d2))

        if cosine <= _U_TURN:
            phases[i] = previous_end
            continue

        phases[i] = previous_end + _transport_delta(previous, current)

        bend = math.acos(max(-1.0, min(1.0, cosine)))
        if bend < _STRAIGHT:
            continue

        # The ring shift is at most outer_radius * tan(bend / 2); fading it in over twice that keeps the rings in order.
        fade = 2.0 * outer_radius * math.tan(bend * 0.5)

        # each end gets the OTHER segment's direction, in its own frame
        previous_in_current = current.T @ d1
        current_in_previous = previous.T @ d2

        starts[i] = (float(previous_in_current[0]), float(previous_in_current[1]), float(previous_in_current[2]),
                     min(fade, lengths[i] * 0.5))
        ends[i - 1] = (float(current_in_previous[0]), float(current_in_previous[1]), float(current_in_previous[2]),
                       min(fade, lengths[i - 1] * 0.5))

    return [SegmentTwist(phases[i], starts[i], ends[i]) for i in range(count)]


@_check_types.do
def ring_count(length: float, rate: float, twist: SegmentTwist, outer_radius: float) -> int:
    """How many rings a segment's tube needs.

    Enough for :data:`SAMPLES_PER_TURN` per turn, and, when either end has a mitre, a ring about every ``outer_radius`` so that the
    fade of the mitre has rings to act on.
    """
    turns = abs(rate) * length / (2.0 * math.pi)
    rings = math.ceil(turns * SAMPLES_PER_TURN) + 1

    if twist.start[3] > 0.0 or twist.end[3] > 0.0:
        rings = max(rings, math.ceil(length / outer_radius) + 1)

    return int(min(max(rings, 2), MAX_RINGS))


class TwistedTube:
    """Draws a conductor's tube with the faces program's twist mode. One instance serves every wire."""

    def __init__(self):
        self._vaos: dict[int, int] = {}

    @_check_types.do
    def _vao(self) -> int:
        """An empty vertex array for the current GL context (the core profile will not draw without one bound)."""
        context = QtGui.QOpenGLContext.currentContext()
        if context is None:
            raise RuntimeError('context has not been acquired')

        key = id(context)

        if key not in self._vaos:
            self._vaos[key] = GL.glGenVertexArrays(1)

        return self._vaos[key]

    @_check_types.do
    def draw(self, program: "_program.FacesProgram", position: "_point.Point", angle: "_angle.Angle", length: float,
             twist: SegmentTwist, conductor: tuple[float, float, float], rate: float, rings: int,
             stripe: "_materials.GLMaterial | None") -> None:
        """Draw one conductor over one segment, in the material the caller has already set on ``program``.

        :param program: The faces program, already entered (``with program:``).
        :param position: World position of the segment's start.
        :param angle: The segment's rotation, local +Z along the segment.
        :param length: Segment length, mm.
        :param twist: This segment's phase and mitres from :func:`plan`.
        :param conductor: This conductor's ``(centre x, centre y, radius)`` from :func:`profile`.
        :param rate: Twist rate, radians per mm.
        :param rings: Ring count from :func:`ring_count`.
        :param stripe: The stripe's material, or ``None`` for a conductor without a stripe.
        """
        program.position = position.as_float
        program.rotation = [float(str(v)) for v in angle.as_quat_numpy.tolist()]
        program.scale = (1.0, 1.0, 1.0)

        program.twist_length = length
        program.twist_rate = rate
        program.twist_phase = twist.phase
        program.twist_profile = conductor
        program.twist_start = twist.start
        program.twist_end = twist.end
        program.twist_rings = rings

        if stripe is not None:
            program.twist_stripe_ambient = stripe.ambient
            program.twist_stripe_diffuse = stripe.diffuse
            program.twist_stripe_specular = stripe.specular
            program.twist_stripe_half = STRIPE_HALF_ANGLE

        try:
            GL.glBindVertexArray(self._vao())
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, (rings - 1) * SIDES * 6)
            GL.glBindVertexArray(0)
        finally:
            # every other draw relies on twistRings and twistStripeHalf already being 0 (see the notes on the uniforms in
            # vertex.vert and fragment.frag)
            program.twist_rings = 0
            program.twist_stripe_half = 0.0


TUBE = TwistedTube()
