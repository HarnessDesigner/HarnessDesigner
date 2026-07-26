# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Flat triangle mesh generation helpers.

The functions in this module build a flat (Y=0), isoceles triangle for use
by :class:`harness_designer.gl.vbo.PooledVBOHandler` instances -- the
2D-editor counterpart to :mod:`harness_designer.shapes.box`. The generated
triangle lies in the XZ plane, apex toward +Z, matching every other flat/
ground-plane mesh in this codebase (floor, grid, Peg Board strands). Not yet
consumed by any object type -- reserved for future direction/pointer
markers (e.g. wire direction indicators).
"""

import math
import numpy as np

from .. import utils as _utils
from ..gl import vbo as _vbo_handler


_vbo: _vbo_handler.PooledVBOHandler = None


def create_vbo(
    uuid,
    *,
    side_a: int | float | None = None,
    side_b: int | float | None = None,
    side_c: int | float | None = None,
    angle_A: int | float | None = None,
    angle_B: int | float | None = None,
    angle_C: int | float | None = None
) -> _vbo_handler.PooledVBOHandler:

    global _vbo

    if _vbo is None:
        vertices, faces = create(side_a=side_a, side_b=side_b, side_c=side_c,
                                 angle_A=angle_A, angle_B=angle_B, angle_C=angle_C)

        packed, count = _utils.compute_normals(vertices, faces)

        unpacked_verts = packed[:count * 3].reshape(-1, 3)
        aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
        aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
        obb = _utils.compute_obb(aabb1, aabb2)

        _vbo = _vbo_handler.PooledVBOHandler(
            uuid, packed, count, aabb=aabb, obb=obb,
            arena_kind=_vbo_handler.VBO_TYPE_PRIMITIVE)

    return _vbo


def create(
    *,
    side_a: int | float | None = None,
    side_b: int | float | None = None,
    side_c: int | float | None = None,
    angle_A: int | float | None = None,
    angle_B: int | float | None = None,
    angle_C: int | float | None = None
) -> tuple[np.ndarray, np.ndarray]:

    # [Step 1-5: Same internal calculation logic as previous step to get baseline points]
    sides = {'a': side_a, 'b': side_b, 'c': side_c}
    angles = {'A': angle_A, 'B': angle_B, 'C': angle_C}
    known_sides = {k: v for k, v in sides.items() if v is not None}
    known_angles = {k: v for k, v in angles.items() if v is not None}

    if len(known_sides) + len(known_angles) != 3 or len(known_sides) == 0:
        raise ValueError("Provide exactly 3 inputs, including at least one side.")

    angles_rad = {k: math.radians(v) for k, v in known_angles.items()}
    if len(angles_rad) == 2:
        missing_key = [k for k in angles if angles[k] is None][0]
        angles_rad[missing_key] = math.radians(180.0 - sum(known_angles.values()))

    # SSS Triangle Configuration
    if len(known_sides) == 3:
        a, b, c = sides['a'], sides['b'], sides['c']
        cos_A = ((b ** 2) + (c ** 2) - (a ** 2)) / (2 * b * c)
        angles_rad['A'] = math.acos(max(-1.0, min(cos_A, 1.0)))

    # SAS / SSA Triangle Configuration
    elif len(known_sides) == 2 and len(angles_rad) == 1:
        side_keys, angle_key = list(known_sides.keys()), list(angles_rad.keys())[0]

        if angle_key.lower() not in side_keys:
            if 'a' not in known_sides:
                sides['a'] = math.sqrt(
                    (sides['b'] ** 2) +
                    (sides['c'] ** 2) -
                    (2 * sides['b'] * sides['c'] * math.cos(angles_rad['A'])))

            elif 'b' not in known_sides:
                sides['b'] = math.sqrt(
                    (sides['a'] ** 2) +
                    (sides['c'] ** 2) -
                    (2 * sides['a'] * sides['c'] * math.cos(angles_rad['B'])))

            elif 'c' not in known_sides:
                sides['c'] = math.sqrt(
                    (sides['a'] ** 2) +
                    (sides['b'] ** 2) -
                    (2 * sides['a'] * sides['b'] * math.cos(angles_rad['C'])))

            cos_A = ((sides['b'] ** 2 + sides['c'] ** 2 - sides['a'] ** 2) /
                     (2 * sides['b'] * sides['c']))

            angles_rad['A'] = math.acos(max(-1.0, min(cos_A, 1.0)))

        else:
            known_side_opp = known_sides[angle_key.lower()]
            other_side = known_sides[[k for k in side_keys if k != angle_key.lower()][0]]
            sin_other = (other_side * math.sin(angles_rad[angle_key])) / known_side_opp

            angles_rad[[k for k in side_keys if k != angle_key.lower()][0].upper()] = math.asin(sin_other)

            rem_key = [k for k in angles if k not in angles_rad][0]
            angles_rad[rem_key] = (
                math.pi - angles_rad[angle_key] -
                angles_rad[[k for k in side_keys if k != angle_key.lower()][0].upper()])

            missing_side_key = [k for k in sides if sides[k] is None][0]
            sides[missing_side_key] = (
                (known_side_opp * math.sin(angles_rad[missing_side_key.upper()])) /
                math.sin(angles_rad[angle_key]))

    # ASA / AAS Triangle Configuration
    elif len(known_sides) == 1 and len(angles_rad) == 3:
        k_side_key = list(known_sides.keys())[0]
        for k in sides:
            if sides[k] is None:
                sides[k] = (
                    (known_sides[k_side_key] * math.sin(angles_rad[k.upper()])) /
                    math.sin(angles_rad[k_side_key.upper()]))

        cos_A = (((sides['b'] ** 2) + (sides['c'] ** 2) - (sides['a'] ** 2)) /
                 (2 * sides['b'] * sides['c']))

        angles_rad['A'] = math.acos(max(-1.0, min(cos_A, 1.0)))

    # Step 6: Generate baseline coordinates (with A at 0,0)
    c, b, A_rad = sides['c'], sides['b'], angles_rad['A']
    ax, ay = 0.0, 0.0
    bx, by = float(c), 0.0
    cx, cy = float(b * math.cos(A_rad)), float(b * math.sin(A_rad))

    # Step 7: Find the centroid of the baseline triangle
    centroid_x = (ax + bx + cx) / 3.0
    centroid_y = (ay + by + cy) / 3.0

    # Step 8: Shift all vertices so the centroid moves to (0, 0)
    coord_A = [round(ax - centroid_x, 6), 0.0, round(ay - centroid_y, 6)]
    coord_B = [round(bx - centroid_x, 6), 0.0, round(by - centroid_y, 6)]
    coord_C = [round(cx - centroid_x, 6), 0.0, round(cy - centroid_y, 6)]

    vertices = np.array([coord_A, coord_B, coord_C], dtype=np.float32)
    faces = np.array([[0, 2, 1]], dtype=np.int32)
    return vertices, faces
