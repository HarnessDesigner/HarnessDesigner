# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Single-ring rotation gizmo, shared by every 2D-plane editor (schematic,
peg board).

Right-clicking the already-selected object/anchor shows one ring + grab
handle, fixed flat in the editor's plane (normal = world +Y) and spun by
the target's live ``angle.y`` -- as opposed to the 3D editor's three-
Euler-axis ``gl.canvas3d.rotation_rings.RotationRings``, every 2D-plane
editor only ever needs a single-axis ring, so this one class covers all of
them. *target* only needs to duck-type ``.position`` (``.x``/``.y``/``.z``),
``.angle.y``, and ``.aabb`` -- both ``objects.objects_schematic.base_schematic.BaseSchematic``
(schematic) and ``objects.objectspeg.basepeg.BasePeg`` (peg board) already
satisfy that shape, so nothing here is specific to either. The one place
2D editors *do* differ -- the schematic forces a hard 90-degree detent
while the peg board's detent is optional/user-configurable -- is a
drag-input concern (see ``gl.canvas2d.mouse_handler.MouseHandler.
_rotation_snap_angle``), not a gizmo one: this class has no snap logic of
its own at all.

Reuses the plain, already-decoupled mesh/orientation helpers from
``gl.canvas3d.rotation_rings`` directly (``_build_ring_mesh``/
``_build_handle_mesh``/``slot_ring_angle``/``HANDLE_LOCAL_DIRS``) -- those
have no ``Base3D``/3D-camera dependency of their own, just pure mesh
builders and orientation math.
"""

from typing import TYPE_CHECKING, Union

import numpy as np
from OpenGL import GL

from .. import vbo as _vbo
from .. import materials as _materials
from ..canvas3d import rotation_rings as _rotation_rings
from ... import color as _color
from ...geometry import point as _point
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...objects.objects_schematic import base_schematic as _base_schematic
    from ...objects.objectspeg import basepeg as _basepeg


# Ring radius as a multiple of the target's own largest in-plane half-extent
# (derived from its live ``aabb``) -- keeps the ring clear of the object's
# rendered rectangle regardless of its proportions.
_RING_RADIUS_SCALE = 1.35

# Ring tube diameter, as a fraction of the ring's own radius-1.0 unit mesh
# (fed straight into gl.canvas3d.rotation_rings._build_ring_mesh, which
# expects this same "fraction of unit radius" convention).
_RING_TUBE_DIAMETER_SCALE = 0.03

# Grab handle diameter, as a fraction of the ring's world diameter.
_HANDLE_DIAMETER_SCALE = 0.12

# Minimum world-unit (mm) ring radius/handle size floor, so a degenerate
# (near-zero footprint) target still gets a pickable, visible gizmo.
_MIN_RADIUS_MM = 5.0

# Flat, medium-blue -- a simple, visually reasonable color distinct from
# every real part's own material.
_RING_COLOR_RGB = (90, 160, 230)


class RotationRing:
    """A single, plane-only rotation ring + grab handle gizmo.

    Built for one *target* -- any object exposing ``.position`` (``.x``/
    ``.y``/``.z``), ``.angle.y``, and ``.aabb``, which both
    ``objects.objects_schematic.base_schematic.BaseSchematic`` (schematic) and
    ``objects.objectspeg.basepeg.BasePeg`` (peg board) already satisfy --
    sized from the target's own live ``aabb`` footprint, centered on its
    current ``position`` (``.x``/``.z``, every 2D-plane editor's usual
    convention). The gizmo carries no rotation state of its own -- every
    call that needs "the current angle" (:meth:`render`,
    :meth:`handle_world_pos`) takes it as a parameter, since
    ``gl.canvas2d.canvas.Canvas`` is what actually tracks the live,
    in-progress rotation-in-degrees during a drag (mirrors the existing
    drag-to-reposition feature's "mutate in memory during drag, commit
    once on release" discipline -- except here every intermediate value is
    also already a real, immediate DB write via the target's own bound
    ``angle``, so there is nothing left to commit on release either).

    Requires a current GL context to construct (``NonPooledVBOHandler.
    __init__`` calls ``glGenBuffers``/``glBufferData``) -- only ever built
    from ``Canvas._rebuild_rotation_gizmo()``.
    """

    @_check_types.do
    def __init__(self, target: Union["_base_schematic.BaseSchematic", "_basepeg.BasePeg"]):
        """Initialise the :class:`RotationRing` instance.

        :param target: The object/anchor this gizmo surrounds.
        :type target: :class:`~harness_designer.objects.objects_schematic.base_schematic.BaseSchematic` |
            :class:`~harness_designer.objects.objectspeg.basepeg.BasePeg`
        """
        self._target = target

        aabb = target.aabb
        half_width = (aabb[1][0] - aabb[0][0]) / 2.0
        half_depth = (aabb[1][2] - aabb[0][2]) / 2.0
        footprint = max(half_width, half_depth)
        self._radius = max(footprint * _RING_RADIUS_SCALE, _MIN_RADIUS_MM)
        self._handle_scale = max(
            self._radius * 2.0 * _HANDLE_DIAMETER_SCALE, _MIN_RADIUS_MM * 0.3)

        ring_packed, ring_count = _rotation_rings._build_ring_mesh(  # NOQA
            _RING_TUBE_DIAMETER_SCALE)
        handle_packed, handle_count = _rotation_rings._build_handle_mesh()  # NOQA

        self._ring_buf = _vbo.NonPooledVBOHandler(ring_packed, ring_count)
        self._handle_buf = _vbo.NonPooledVBOHandler(handle_packed, handle_count)
        self._material = _materials.Generic(_color.Color(*_RING_COLOR_RGB))

    @_check_types.do
    def _handle_world_offset(self, rotation_deg: float) -> np.ndarray:
        """Return the handle's world-space XZ offset from the target center.

        :param rotation_deg: The target's current in-plane rotation, in degrees.
        :type rotation_deg: float
        :returns: ``[x, y, z]`` offset (``y`` is always ~0 -- the handle
            stays in the schematic plane).
        :rtype: numpy.ndarray
        """
        ring_angle = _rotation_rings.slot_ring_angle('y', [0.0, rotation_deg, 0.0])
        local_dir = _rotation_rings.HANDLE_LOCAL_DIRS['y']
        world_dir = ring_angle @ local_dir

        return np.asarray(world_dir, dtype=np.float32) * self._radius

    @_check_types.do
    def handle_world_pos(self, rotation_deg: float) -> _point.Point:
        """Return the world position of the grab handle.

        :param rotation_deg: The target's current in-plane rotation, in degrees.
        :type rotation_deg: float
        :returns: A real 3D world position (``.y`` always ``0.0``, every
            2D-plane editor is flat) -- callers going through
            ``Camera.world_to_screen`` (a generic screen/world 2D
            helper, unaware of a "z" axis) build their own transient
            ``Point(handle_world.x, handle_world.z)`` for that one call,
            rather than this method returning something pre-mislabeled
            for it.
        :rtype: :class:`~harness_designer.geometry.point.Point`
        """
        offset = self._handle_world_offset(rotation_deg)

        return _point.Point(
            self._target.position.x + float(offset[0]),
            0.0,
            self._target.position.z + float(offset[2]),
        )

    @_check_types.do
    def render(self, program: int, rotation_deg: float) -> None:
        """Render the ring and its grab handle under the already-bound
        ``schematic2d`` *program*.

        Uses the exact same ``objectPosition``/``objectRotation``/
        ``objectScale``/``normalMode`` uniform contract every other draw in
        ``Canvas._render_scene`` already uses -- caller is
        responsible for having the program bound (``GL.glUseProgram``)
        already.

        :param program: The active ``schematic2d`` shader program.
        :type program: int
        :param rotation_deg: The target's current in-plane rotation, in degrees.
        :type rotation_deg: float
        """
        pos_loc = GL.glGetUniformLocation(program, "objectPosition")
        rot_loc = GL.glGetUniformLocation(program, "objectRotation")
        scale_loc = GL.glGetUniformLocation(program, "objectScale")
        normal_loc = GL.glGetUniformLocation(program, "normalMode")

        self._material.set(program)
        GL.glUniform1i(normal_loc, 0)

        ring_angle = _rotation_rings.slot_ring_angle('y', [0.0, rotation_deg, 0.0])
        quat_w, quat_x, quat_y, quat_z = ring_angle.as_quat_float

        GL.glUniform3f(pos_loc, self._target.position.x, 0.0, self._target.position.z)
        GL.glUniform4f(rot_loc, quat_w, quat_x, quat_y, quat_z)
        GL.glUniform3f(scale_loc, self._radius, self._radius, self._radius)
        self._ring_buf.render()

        handle_pos = self.handle_world_pos(rotation_deg)
        GL.glUniform3f(pos_loc, handle_pos.x, 0.0, handle_pos.z)
        GL.glUniform4f(rot_loc, 1.0, 0.0, 0.0, 0.0)
        GL.glUniform3f(scale_loc, self._handle_scale, self._handle_scale, self._handle_scale)
        self._handle_buf.render()

    @_check_types.do
    def release(self) -> None:
        """Release this gizmo's GL buffers.

        Called by ``Canvas.exit_rotation_mode``/
        ``Canvas._rebuild_rotation_gizmo`` so repeated show/hide of the
        gizmo (or a project reload while it's active) never leaks GPU
        buffers.
        """
        self._ring_buf.release()
        self._handle_buf.release()
