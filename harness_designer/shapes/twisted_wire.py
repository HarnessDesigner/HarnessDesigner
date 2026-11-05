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

# A bend sharper than this (cosine of the angle between the two directions) is a U-turn: the mitre is undefined at 180 degrees,
# so the two segments are drawn as if they did not touch.
_U_TURN = -0.99

# A bend smaller than this (radians) needs no mitre.
_STRAIGHT = 1e-4


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
def profile(count: int, outer_diameter: float) -> list[tuple[float, float, float]]:
    """Where the conductors of a twisted cable sit, as ``(centre x, centre y, radius)`` in mm, conductor 0 first.

    The conductors are equal circles touching each other and the outside of the cable, so the radius ``r`` and the radius of the
    circle the centres lie on ``c`` follow from the outer diameter: ``c = r / sin(pi / n)`` and ``outer radius = c + r``. A pair has
    ``r`` = diameter / 4 and a triple diameter / 4.309 (the conductor is 1 / 2.155 of the cable's diameter).

    :param count: Number of conductors, 2 or more.
    :param outer_diameter: Diameter of the circle that holds the whole cable, mm.
    :returns: One circle per conductor, the first on the +X axis, the rest evenly around.
    """
    radius = outer_diameter * 0.5 / (1.0 + 1.0 / math.sin(math.pi / count))
    centre = radius / math.sin(math.pi / count)
    result = []

    for i in range(count):
        angle = 2.0 * math.pi * i / count
        result.append((centre * math.cos(angle), centre * math.sin(angle), radius))

    return result


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
def plan(rotations: list[np.ndarray], lengths: list[float], joined: list[bool], rate: float, outer_radius: float) -> list[SegmentTwist]:
    """Work out the twist phase and the mitre of every segment of a bent wire.

    :param rotations: One 3x3 column-vector rotation matrix per segment; its columns are the segment's local axes in world space.
    :param lengths: The segments' lengths, mm.
    :param joined: ``joined[i]`` is True when segment ``i`` starts where segment ``i - 1`` ends (``joined[0]`` is never read). A
        segment hidden inside a bundle breaks the chain.
    :param rate: Twist rate, radians per mm (:func:`rate_from_tpi`).
    :param outer_radius: Radius of the circle that holds the whole cable, mm.
    :returns: One :class:`SegmentTwist` per segment.
    """
    count = len(rotations)
    phases = [0.0] * count
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
