# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The always-visible, click-to-activate ring for one rotation axis.

Round-tube (torus) cross-section -- unlike the flat disc-ring shape used
by :mod:`.inner_ring`/:mod:`.outer_ring`, a torus's tube only stays
circular under *uniform* scale, and this ring's diameter has to match
whatever object it's wrapped around. So this class builds its own
mesh, sized for the tracked object, rather than reusing the shared
unit VBO the disc-based rings use.

Clicking anywhere on this ring's band (no separate grab handle)
activates that axis's protractor -- see :mod:`..rotation_ring` for the
per-axis assembly and the show/hide state machine between this ring
and the protractor.
"""

import math
from typing import TYPE_CHECKING

import numpy as np
from OpenGL import GL

from . import _hit_test
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl import materials as _materials
from ...gl import vbo as _vbo_handler
from ...gl.canvas_base import rotation_mesh as _rotation_mesh
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ...gl.canvas_base import camera_base as _camera_base
    from ...gl import shaders as _shaders


class TorusRing:
    """One axis's activation ring.

    :param position: World-space center -- shared with whatever it's
        wrapped around (not copied), same reasoning as the rest of this
        gizmo: always exactly centered with no follow-the-leader
        callback needed.
    :param angle: World-space orientation of the ring's plane.
    :param radius: World-space ring radius.
    :param tube_diameter_scale: Tube thickness as a fraction of *radius*
        (see ``Config.rotation_rings.tube_diameter_scale``).
    :param material: Material this ring renders with.
    """

    @_check_types.do
    def __init__(self, position: _point.Point, angle: _angle.Angle,
                 radius: float, tube_diameter_scale: float,
                 material: _materials.GLMaterial, context):

        self.position = position
        self.angle = angle
        self.radius = radius
        self.material = material

        self.is_visible = True
        # Only the torus rings that are NOT currently the active axis
        # stay pickable -- the assembler in rotation_ring/__init__.py
        # flips this off for the active one (and the other two once a
        # protractor is showing).
        self.is_pickable = True

        self._tube_diameter_scale = tube_diameter_scale

        packed, count = _rotation_mesh.build_ring_mesh(tube_diameter_scale)
        with context:
            self._vbo = _vbo_handler.NonPooledVBOHandler(packed, count)
            self._vbo.acquire()

    @_check_types.do
    def rebuild(self, tube_diameter_scale: float, context) -> None:
        """Rebuild the mesh -- only needed when the tube-thickness config
        value changes (the mesh bakes it in; radius/position/angle are
        all applied as render-time uniforms and never need a rebuild).
        """
        if tube_diameter_scale == self._tube_diameter_scale:
            return

        self._tube_diameter_scale = tube_diameter_scale
        packed, count = _rotation_mesh.build_ring_mesh(tube_diameter_scale)

        with context:
            self._vbo.update(packed, count)

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram") -> None:
        if not self.is_visible:
            return

        faces_program = shaders.faces

        with faces_program:
            self.material.set(faces_program)

            # Dimmed (a sibling axis's protractor is active) -- blend needs
            # to be explicitly enabled for the alpha RotationRing.set_dimmed()
            # wrote into materialDiffuse to actually show as transparency
            # rather than just darker lighting math.
            dimmed = float(self.material.diffuse[3]) < 1.0
            if dimmed:
                GL.glEnable(GL.GL_BLEND)
                GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

            self._vbo.render(
                faces_program,
                self.position, self.angle,
                _point.Point(self.radius, self.radius, self.radius), None)

            if dimmed:
                GL.glDisable(GL.GL_BLEND)

    @_check_types.do
    def hit_test(self, mouse_pos: _point.Point,
                camera: "_camera_base.CameraBase", tolerance: float = 6.0,
                samples: int = 64) -> bool:
        """Sample points around the ring's circumference, project each to
        screen space, and check whether *mouse_pos* falls within
        *tolerance* pixels of the resulting polyline -- there's no
        single fixed handle position to test against anymore, the whole
        band is the click target.
        """
        if not self.is_visible or not self.is_pickable:
            return False

        px = float(mouse_pos.x)
        py = float(mouse_pos.y)

        prev = None
        for i in range(samples + 1):
            theta = 2.0 * math.pi * i / samples
            local = np.array(
                [math.cos(theta) * self.radius, math.sin(theta) * self.radius, 0.0],
                dtype=np.float32)
            world = self.angle @ local

            world_pt = _point.Point(
                float(self.position.x) + float(world[0]),
                float(self.position.y) + float(world[1]),
                float(self.position.z) + float(world[2]))
            screen = camera.ProjectPoint(world_pt)

            cur = (float(screen.x), float(screen.y))
            if prev is not None:
                if _hit_test.point_near_segment(
                        px, py, prev[0], prev[1], cur[0], cur[1], tolerance):
                    return True

            prev = cur

        return False

    @_check_types.do
    def delete(self, context) -> None:
        try:
            with context:
                self._vbo.release()
        except Exception:  # NOQA
            # Context may be unavailable during shutdown -- the buffer
            # dies with the context in that case.
            pass
