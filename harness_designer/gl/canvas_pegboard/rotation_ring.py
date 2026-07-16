# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Single-ring rotation gizmo for the Peg Board Editor.

Right-clicking the already-selected anchor shows one ring + grab handle,
fixed flat in the board plane (normal = world +Y) and spun by the anchor's
live in-plane rotation (see ``objects.objectspeg.basepeg.BasePeg.angle``,
the anchor's own bound, DB-backed Y rotation). Unlike the 3D
editor's ``gl.canvas3d.rotation_rings.RotationRings``/``Rings3D`` (three
Euler-axis rings, tightly bound to ``Base3D``, the 3D editor's own
context/camera, and the object's *real* 3D angle), the peg board's spin is
a wholly separate, board-only value, always about the same fixed world-Y
axis -- so this module is a small, standalone class, not a subclass or
adaptation of those.

It does reuse the plain, already-decoupled mesh/orientation helpers from
``gl.canvas3d.rotation_rings`` directly (``_build_ring_mesh``/
``_build_handle_mesh``/``slot_ring_angle``/``HANDLE_LOCAL_DIRS``) -- those
have no ``Base3D``/3D-camera dependency of their own, just pure mesh
builders and orientation math, so importing them here does not pull in
any of the 3D editor's gizmo machinery.
"""

from typing import TYPE_CHECKING

import numpy as np
from OpenGL import GL

from .. import vbo as _vbo
from .. import materials as _materials
from ..canvas3d import rotation_rings as _rotation_rings
from ... import color as _color
from ...geometry import point as _point


if TYPE_CHECKING:
    from ...objects.objectspeg import basepeg as _basepeg


# Ring radius as a multiple of the anchor's own largest in-plane half-extent
# (derived from its live ``aabb``) -- keeps the ring clear of the part's rendered
# mesh regardless of its proportions, mirroring the *intent* of the 3D
# editor's own AABB-diagonal-based sizing (Config.editor3d.rotation_rings.
# diameter_scale) without needing a matching config knob of its own (no
# existing peg-board-specific sizing to match -- picked to be visually
# reasonable).
_RING_RADIUS_SCALE = 1.35

# Ring tube diameter, as a fraction of the ring's own radius-1.0 unit mesh
# (fed straight into gl.canvas3d.rotation_rings._build_ring_mesh, which
# expects this same "fraction of unit radius" convention).
_RING_TUBE_DIAMETER_SCALE = 0.03

# Grab handle diameter, as a fraction of the ring's world diameter.
_HANDLE_DIAMETER_SCALE = 0.12

# Minimum world-unit (mm) ring radius/handle size floor, so a degenerate
# (near-zero footprint) anchor still gets a pickable, visible gizmo.
_MIN_RADIUS_MM = 5.0

# Flat, medium-blue -- a simple, visually reasonable color distinct from
# both the anchors' own materials and the bundle-strand colors already
# drawn on this canvas (gl.canvas_pegboard.canvas.Canvas._build_strand_draws
# uses gl.materials.Generic the same way for its own ad hoc 2D meshes).
_RING_COLOR_RGB = (90, 160, 230)


class PegboardRotationRing:
    """A single, board-plane-only rotation ring + grab handle gizmo.

    Built for one target :class:`~harness_designer.objects.objectspeg.
    basepeg.BasePeg` -- sized from that anchor's own live ``aabb``
    footprint, centered on the anchor's current ``position`` (``.x``/``.y``
    standing in for world X/Z, this canvas's usual convention). The gizmo
    carries no rotation state of its own -- every call that needs "the
    current angle" (:meth:`render`, :meth:`handle_world_pos`) takes it as a
    parameter, since ``gl.canvas_pegboard.canvas.Canvas`` is what actually
    tracks the live, in-progress rotation-in-degrees during a drag
    (mirroring the existing drag-to-reposition feature's "mutate in memory
    during drag, commit once on release" discipline).

    Requires a current GL context to construct (``NonPooledVBOHandler.
    __init__`` calls ``glGenBuffers``/``glBufferData``) -- only ever built
    from ``Canvas._render_objects()`` (via a lazily-deferred rebuild, the
    same pattern ``Canvas._rebuild_strand_draws`` already uses), never at
    ``enter_rotation_mode()`` call time.
    """

    def __init__(self, anchor: "_basepeg.BasePeg"):
        """Initialise the :class:`PegboardRotationRing` instance.

        :param anchor: The anchor this gizmo surrounds.
        :type anchor: :class:`~harness_designer.objects.objectspeg.basepeg.BasePeg`
        """
        self._anchor = anchor

        aabb = anchor.aabb
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

    def _handle_world_offset(self, rotation_deg: float) -> np.ndarray:
        """Return the handle's world-space XZ offset from the anchor center.

        :param rotation_deg: The anchor's current in-plane rotation, in degrees.
        :type rotation_deg: float
        :returns: ``[x, y, z]`` offset (``y`` is always ~0 -- the handle
            stays in the board plane).
        :rtype: numpy.ndarray
        """
        ring_angle = _rotation_rings.slot_ring_angle('y', [0.0, rotation_deg, 0.0])
        local_dir = _rotation_rings.HANDLE_LOCAL_DIRS['y']
        world_dir = ring_angle @ local_dir

        return np.asarray(world_dir, dtype=np.float32) * self._radius

    def handle_world_pos(self, rotation_deg: float) -> "_point.Point":
        """Return the world position of the grab handle.

        :param rotation_deg: The anchor's current in-plane rotation, in degrees.
        :type rotation_deg: float
        :returns: A real 3D world position (``.y`` always ``0.0``, the board
            is flat) -- callers going through ``Camera2D.world_to_screen``
            (a generic screen/world 2D helper, unaware of a "z" axis) build
            their own transient ``Point(handle_world.x, handle_world.z)``
            for that one call, rather than this method returning something
            pre-mislabeled for it.
        :rtype: :class:`~harness_designer.geometry.point.Point`
        """
        offset = self._handle_world_offset(rotation_deg)

        return _point.Point(
            self._anchor.position.x + float(offset[0]),
            0.0,
            self._anchor.position.z + float(offset[2]),
        )

    def render(self, program: int, rotation_deg: float) -> None:
        """Render the ring and its grab handle under the already-bound
        ``schematic2d`` *program*.

        Uses the exact same ``objectPosition``/``objectRotation``/
        ``objectScale``/``normalMode`` uniform contract every other draw in
        ``Canvas._render_objects`` already uses -- caller is responsible
        for having the program bound (``GL.glUseProgram``) already.

        :param program: The active ``schematic2d`` shader program.
        :type program: int
        :param rotation_deg: The anchor's current in-plane rotation, in degrees.
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

        GL.glUniform3f(pos_loc, self._anchor.position.x, self._anchor.position.y,
                       self._anchor.position.z)
        GL.glUniform4f(rot_loc, quat_w, quat_x, quat_y, quat_z)
        GL.glUniform3f(scale_loc, self._radius, self._radius, self._radius)
        self._ring_buf.render()

        handle_pos = self.handle_world_pos(rotation_deg)
        GL.glUniform3f(pos_loc, handle_pos.x, 0.0, handle_pos.y)
        GL.glUniform4f(rot_loc, 1.0, 0.0, 0.0, 0.0)
        GL.glUniform3f(scale_loc, self._handle_scale, self._handle_scale, self._handle_scale)
        self._handle_buf.render()

    def release(self) -> None:
        """Release this gizmo's GL buffers.

        Mirrors ``Canvas._release_strand_draws``'s "release before
        replace"/"release on teardown" discipline -- called by
        ``Canvas.exit_rotation_mode``/``Canvas._rebuild_rotation_gizmo`` so
        repeated show/hide of the gizmo (or a project reload while it's
        active) never leaks GPU buffers.
        """
        self._ring_buf.release()
        self._handle_buf.release()
