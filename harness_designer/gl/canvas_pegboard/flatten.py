# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
"Lay it flat" rotation derivation for the Peg Board Editor.

A harness is removed from the vehicle and laid flat on a physical peg
board -- its as-mounted 3D scene angle (``db_obj.angle3d``) is irrelevant
to how it naturally lies on the table. What matters is purely which local
axis of the part's own model is "up", and that is exactly what
``Model3D.forward_up`` encodes: a ``[forward_face_idx, up_face_idx]`` pair
(ints 0-5, may be ``[-1, -1]`` if the part was never run through the
one-time :class:`~harness_designer.ui.dialogs.part_orientation.PartOrientationDialog`
flow) defined entirely in the model's LOCAL/canonical frame.

Because of that, deriving "which way is up" needs only the model's own
stored (unrotated) OBB -- the object's current 3D scene rotation never
enters into it. This module builds the quaternion that rotates whichever
local axis is "up" onto world +Y, so that projecting the rotated mesh's
local X/Z onto the peg board yields the part's natural flat footprint.
"""

import math

import numpy as np

from ...geometry.angle import quaternion as _quaternion


def compute_local_up_direction(local_obb: np.ndarray, up_face_idx: int) -> "np.ndarray | None":
    """Return the model's own local-space "up" direction, from its stored OBB.

    Calls :meth:`~harness_designer.handlers.handler_base.HandlerBase.obb_face_direction`
    with *local_obb* passed as both the "current" and "local" OBB (i.e. no
    rotation applied) -- this reads the face direction directly in the
    model's own local space, independent of any scene-graph rotation.

    :param local_obb: (8, 3) unrotated local-space OBB corners (either
        ``Model3D.obb`` or a live ``VBOHandlerBase.local_obb`` -- both are
        the same as-authored, un-rotated bounding box).
    :type local_obb: numpy.ndarray
    :param up_face_idx: Face index (0-5) identifying the model's "up" face
        in its own local frame (``Model3D.forward_up[1]``).
    :type up_face_idx: int
    :returns: Unit vector pointing "up" in the model's local space, or
        ``None`` when the face is degenerate (zero-area).
    :rtype: numpy.ndarray | None
    """
    from ...handlers.handler_base import HandlerBase

    return HandlerBase.obb_face_direction(local_obb, local_obb, up_face_idx)


def compute_flatten_quaternion(local_up_dir: np.ndarray) -> "_quaternion.Quaternion":
    """Return the quaternion that rotates *local_up_dir* onto world ``+Y``.

    Standard shortest-arc quaternion construction -- the same shape as
    :meth:`~harness_designer.geometry.angle.angle.Angle.from_direction`,
    just targeting ``+Y`` instead of ``+Z``. This is the rotation that
    lays a part flat on the peg board with its "up" face pointing straight
    out of the board.

    :param local_up_dir: Unit vector, the model's local "up" direction
        (see :func:`compute_local_up_direction`).
    :type local_up_dir: numpy.ndarray
    :returns: Quaternion rotating *local_up_dir* onto ``(0, 1, 0)``.
    :rtype: :class:`_quaternion.Quaternion`
    """
    target = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    dot = float(np.dot(local_up_dir, target))

    if abs(dot - 1.0) < 1e-4:
        # Already pointing up -- identity rotation.
        return _quaternion.Quaternion(1.0, 0.0, 0.0, 0.0)

    if abs(dot + 1.0) < 1e-4:
        # Exactly opposed -- 180 degree flip about any axis perpendicular
        # to local_up_dir. Cross with +X first; fall back to +Z on the
        # degenerate case where local_up_dir is itself parallel to +X.
        perp = np.cross(local_up_dir, np.array([1.0, 0.0, 0.0], dtype=np.float32))
        if np.linalg.norm(perp) < 1e-6:
            perp = np.cross(local_up_dir, np.array([0.0, 0.0, 1.0], dtype=np.float32))

        return _quaternion.Quaternion.from_axis_angle(perp, math.pi)

    axis = np.cross(local_up_dir, target)
    axis = axis / np.linalg.norm(axis)
    angle = math.acos(max(-1.0, min(1.0, dot)))

    return _quaternion.Quaternion.from_axis_angle(axis, angle)


def flatten_quaternion_for_model3d(
        local_obb: np.ndarray,
        forward_up: list[int, int] | tuple[int, int]) -> "_quaternion.Quaternion":
    """Return the flatten quaternion for any Model3D-backed part (housing,
    splice, terminal, etc).

    :param local_obb: (8, 3) unrotated local-space OBB corners --
        ``obj3d._vbo.local_obb``.
    :type local_obb: numpy.ndarray
    :param forward_up: ``Model3D.forward_up`` -- ``[forward_face_idx,
        up_face_idx]``, either may be ``-1`` when never set.
    :type forward_up: list[int, int] | tuple[int, int]
    :returns: Quaternion that lays the part flat on the peg board.
    :rtype: :class:`_quaternion.Quaternion`
    """
    up_face = forward_up[1]

    if up_face == -1:
        # No forward_up ever set for this model (never run through the
        # PartOrientationDialog one-time flow) -- fall back to the local
        # axis of smallest OBB extent as a synthetic up-axis (parts are
        # usually flattest along their thinnest dimension). Either sign
        # (low/high face) of that axis is an equally valid "up" guess
        # when there is no real data to prefer one over the other.
        extents = local_obb.max(axis=0) - local_obb.min(axis=0)
        axis = int(np.argmin(extents))
        up_face = axis * 2

    local_up = compute_local_up_direction(local_obb, up_face)
    if local_up is None:
        return _quaternion.Quaternion(1.0, 0.0, 0.0, 0.0)

    return compute_flatten_quaternion(local_up)


def flatten_quaternion_for_transition(local_obb: np.ndarray) -> "_quaternion.Quaternion":
    """Return the flatten quaternion for a transition.

    Transitions have no ``Model3D``/``forward_up`` at all, but
    ``objects.objects3d.transition._build_model`` confines every branch to
    the local XY plane (every branch point's local Z is forced to 0, and
    the extrusion planes are only ever rotated about local Z) -- so local
    Z is the transition's inherent thickness axis by construction. Local
    face index 4 (axis 2 = Z, low side) is used directly, no heuristic
    needed.

    :param local_obb: (8, 3) unrotated local-space OBB corners -- the
        transition's own live ``obj3d._vbo.local_obb`` (transitions have
        no ``Model3D`` OBB of their own).
    :type local_obb: numpy.ndarray
    :returns: Quaternion that lays the transition flat on the peg board.
    :rtype: :class:`_quaternion.Quaternion`
    """
    local_up = compute_local_up_direction(local_obb, 4)
    if local_up is None:
        return _quaternion.Quaternion(1.0, 0.0, 0.0, 0.0)

    return compute_flatten_quaternion(local_up)
