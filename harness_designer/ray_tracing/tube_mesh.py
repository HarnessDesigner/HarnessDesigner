# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The mesh of a wire, a cable or a bundle for the ray tracer: the tubes the viewport draws, built on the CPU.

The viewport makes the vertices of a tube in the vertex shader (``gl/shaders/faces/vertex.vert``, ``twistVertex``) from the rows of
``gl/wire_pool.py``. The ray tracer needs triangles it can put in its BVH, so this module does what that shader does with numpy, on
the same pieces (``TubeMixin._twist_segments``: the straights, the short chords of a rounded corner, each with its twist phase and
mitres), so the ray traced picture has the same curved corners, twisted conductors, mitred joints and smooth shading as the
viewport:

* a ring of ``SIDES`` points round the conductor's circle, turned about the piece's axis by ``phase + rate * z``;
* both ends of a piece are moved onto the plane that bisects the bend (the mitre), faded in over the distance the shader fades it;
* the normal is the sheared tube's own, turned toward the bisector of the joint over that same distance (``smoothAcrossJoint``), so
  the rounded corner shades as one surface and not as the facets it is cut into.

A conductor with a stripe gets a second mesh for the stripe: the quads of the tube between ``centre - half`` and ``centre + half``
round the conductor (the stripe runs along the side facing away from the cable's axis, snapped to the viewport's own 16 sides), cut
exactly at those two angles. The body mesh leaves them out, so the two meshes meet edge to edge and take a material each.

The only difference from the viewport is the number of sides: the viewport draws 16, a picture rendered for its own sake gets
``SIDES`` (a multiple of 16, so the stripe's centre still lands on a vertex).
"""

import math

import numpy as np

from ..shapes import twisted_wire as _twisted_wire
from .. import check_types as _check_types


# Sides of a conductor's polygon (the viewport's is shapes.twisted_wire.SIDES = 16; keep a multiple of it).
SIDES = 32

_TWO_PI = 2.0 * math.pi

# Same as the shader: a joint turned further than this (cosine) is a U-turn and gets no smoothing
_U_TURN = -0.99


def _unit(vectors: np.ndarray) -> np.ndarray:
    """*vectors* (last axis 3) made unit length; a zero vector stays zero."""
    length = np.linalg.norm(vectors, axis=-1, keepdims=True)
    length[length < 1e-30] = 1.0
    return vectors / length


def _smooth_across_joint(normals: np.ndarray, neighbour: tuple[float, float, float, float]) -> np.ndarray:
    """The normal at a joint as a smooth bend has it (``smoothAcrossJoint`` in vertex.vert): the bisector of this piece's radial
    normal and the one the neighbouring piece has at the same vertex, which is this one turned by the minimal rotation taking this
    piece's +Z to *neighbour*, the neighbour's direction in this piece's frame (Rodrigues' form)."""
    direction = np.array((-neighbour[1], neighbour[0], 0.0))
    across = np.cross(direction, normals)
    rotated = normals + across + np.cross(direction, across) / (1.0 + neighbour[2])

    return _unit(normals + rotated)


def _around_angles(circle: tuple[float, float, float], stripe_half: float, sides: int) -> tuple[np.ndarray, np.ndarray, float]:
    """The angles round the conductor's circle at which a ring has a vertex, and which of the quads between them are the stripe.

    :returns: The angles (ascending, ``sides`` evenly spaced plus, with a stripe, its two edges), a boolean per quad (quad ``j``
        runs from angle ``j`` to angle ``j + 1``, the last back to the first) that is true inside the stripe, and the stripe's
        centre.
    """
    angles = [_TWO_PI * i / sides for i in range(sides)]
    centre = 0.0

    if stripe_half <= 0.0:
        return np.array(angles), np.zeros(sides, dtype=bool), centre

    centre_x, centre_y, _radius = circle

    # the stripe is on the side of the conductor that faces away from the cable's axis, snapped to the viewport's own vertices (the
    # centre conductor of a cable, which sits on the axis, takes +X)
    profile_angle = 0.0

    if centre_x * centre_x + centre_y * centre_y > 1e-8:
        profile_angle = math.atan2(centre_y, centre_x)

    side_angle = _TWO_PI / _twisted_wire.SIDES
    centre = round(profile_angle / side_angle) * side_angle

    angles.append((centre - stripe_half) % _TWO_PI)
    angles.append((centre + stripe_half) % _TWO_PI)

    angles = np.sort(np.array(angles))
    angles = angles[np.concatenate(([True], np.diff(angles) > 1e-9))]

    following = np.concatenate((angles[1:], [angles[0] + _TWO_PI]))
    middle = (angles + following) * 0.5
    distance = np.abs((middle - centre + math.pi) % _TWO_PI - math.pi)

    return angles, distance < stripe_half, centre


def _piece_grid(piece, rate: float, circle: tuple[float, float, float], angles: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The vertices and normals of one piece, world space, as ``(rings, angles, 3)`` arrays.

    :param piece: A ``TubeMixin`` plan piece (position, matrix, length, twist, rings).
    """
    centre_x, centre_y, radius = circle
    rings = int(piece.rings)
    length = float(piece.length)
    phase, start, end = piece.twist

    z = length * np.arange(rings, dtype=np.float64) / (rings - 1)
    theta = phase + rate * z
    cos_t = np.cos(theta)[:, None]
    sin_t = np.sin(theta)[:, None]

    cos_a = np.cos(angles)[None, :]
    sin_a = np.sin(angles)[None, :]

    # the circle's point, turned about the axis
    point_x = centre_x + radius * cos_a
    point_y = centre_y + radius * sin_a
    x = cos_t * point_x - sin_t * point_y
    y = sin_t * point_x + cos_t * point_y

    # d(position)/d(around) and d(position)/d(z) of the sheared tube; their cross product is the outward normal
    around_x = cos_t * (-radius * sin_a) - sin_t * (radius * cos_a)
    around_y = sin_t * (-radius * sin_a) + cos_t * (radius * cos_a)
    normals = _unit(np.stack((around_y, -around_x, rate * (around_x * x + around_y * y)), axis=-1))

    shift = np.zeros((rings, 1))

    # a bend turns the normal toward the joint's bisector, and moves the ring onto the plane bisecting the bend, both over the
    # distance (w) the mitre fades in over
    if end[3] > 0.0:
        fade = np.clip((z - (length - end[3])) / end[3], 0.0, 1.0)[:, None]

        if end[2] > _U_TURN:
            normals = _unit(normals + (_smooth_across_joint(normals, end) - normals) * fade[:, :, None])

        shift = shift + (-(end[0] * x + end[1] * y) / (1.0 + end[2])) * fade

    if start[3] > 0.0:
        fade = np.clip(1.0 - z / start[3], 0.0, 1.0)[:, None]

        if start[2] > _U_TURN:
            normals = _unit(normals + (_smooth_across_joint(normals, start) - normals) * fade[:, :, None])

        shift = shift + (-(start[0] * x + start[1] * y) / (1.0 + start[2])) * fade

    local = np.stack((x, y, np.broadcast_to(z[:, None] + shift, x.shape)), axis=-1)
    rotation = np.asarray(piece.matrix, dtype=np.float64)

    # (the plan's matrix has the piece's axes as its columns, so world = matrix @ local)
    return local @ rotation.T + np.asarray(piece.position, dtype=np.float64), normals @ rotation.T


def _triangles(vertices: np.ndarray, normals: np.ndarray, columns: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The triangles of the quads between neighbouring rings, for the quads (angle ``j`` to ``j + 1``) in *columns*, as a soup of
    corners: ``(ring k, j) (k, j + 1) (k + 1, j)`` and ``(k + 1, j) (k, j + 1) (k + 1, j + 1)``, wound as the shader winds them so
    the outside is the counter-clockwise face."""
    ring_count, angle_count, _ = vertices.shape

    if not len(columns) or ring_count < 2:
        return np.empty((0, 3)), np.empty((0, 3))

    k = np.arange(ring_count - 1)[:, None]
    j = columns[None, :]
    j1 = (j + 1) % angle_count

    corners = np.broadcast_arrays(k, j, k, j1, k + 1, j, k + 1, j, k, j1, k + 1, j1)
    ring = np.stack(corners[0::2], axis=-1).reshape(-1)
    angle = np.stack(corners[1::2], axis=-1).reshape(-1)

    return vertices[ring, angle].reshape(-1, 3), normals[ring, angle].reshape(-1, 3)


@_check_types.do
def conductor_mesh(pieces: list, rate: float, circle: tuple[float, float, float], stripe_half: float, sides: int = SIDES
                   ) -> tuple[tuple[np.ndarray, np.ndarray] | None, tuple[np.ndarray, np.ndarray] | None]:
    """The triangles of one conductor along the pieces of a path.

    :param pieces: The path's pieces (``TubeMixin._twist_segments``): each has ``position``, ``matrix``, ``length``, ``twist``
        and ``rings``.
    :param rate: The twist, radians per mm.
    :param circle: The conductor's centre x, centre y and radius in the cable's cross-section, mm.
    :param stripe_half: Half the angular width of the conductor's stripe, radians; 0 or less for no stripe.
    :param sides: Sides of the conductor's polygon.
    :returns: ``(body, stripe)``, each ``(vertices, normals)`` (world space, ``(N, 3)`` float32, three corners per triangle) or
        ``None`` when it has no triangles (the stripe always, with no stripe).
    """
    angles, in_stripe, _centre = _around_angles(circle, stripe_half, sides)

    body_columns = np.flatnonzero(~in_stripe)
    stripe_columns = np.flatnonzero(in_stripe)

    body = []
    stripe = []

    for piece in pieces:
        vertices, normals = _piece_grid(piece, rate, circle, angles)

        body.append(_triangles(vertices, normals, body_columns))

        if len(stripe_columns):
            stripe.append(_triangles(vertices, normals, stripe_columns))

    return _join(body), _join(stripe)


def _join(parts: list[tuple[np.ndarray, np.ndarray]]) -> tuple[np.ndarray, np.ndarray] | None:
    """Put the pieces' triangle soups together as float32; ``None`` when there are no triangles."""
    parts = [part for part in parts if len(part[0])]

    if not parts:
        return None

    vertices = np.concatenate([part[0] for part in parts]).astype(np.float32)
    normals = np.concatenate([part[1] for part in parts]).astype(np.float32)

    return vertices, normals
