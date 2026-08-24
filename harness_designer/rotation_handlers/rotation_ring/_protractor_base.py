# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared disc + tick-marks + numeric-label construction/rendering for
:mod:`.inner_ring`/:mod:`.outer_ring`.

Both protractor rings are a flat washer (:mod:`~harness_designer.shapes.disc_ring`)
with a ring of small radial tick marks (:mod:`~harness_designer.shapes.cylinder`)
and a :class:`~harness_designer.shapes.text.Text` numeric label at every
tick. A cylinder needs only one radius/length pair (vs. a box's three
independent scale components) and, being rotationally symmetric about
its own length axis, has no front/back face to worry about -- unlike
the flat text label, which does, and is flipped 180 degrees about the
tick's own radial axis (see :meth:`ProtractorRingBase._label_rotation`)
whenever the camera is looking at this ring from its back side, so the
numbers never render mirrored. What differs between the two protractor
rings (whether the angle tracks the selected object or stays fixed, and
what a click/hover/drag on the ring actually does) is left entirely to
the two subclasses -- this class only builds and draws the shared
geometry.
"""

import math
from typing import TYPE_CHECKING

import build123d
import numpy as np
from OpenGL import GL

from ...shapes import disc_ring as _disc_ring
from ...shapes import cylinder as _cylinder
from ...shapes import text as _text
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl import materials as _materials
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ...gl import shaders as _shaders
    from ...gl.canvas_base import camera_base as _camera_base


# One tick (and one numeric label) every 10 degrees.
TICK_STEP_DEGREES = 10.0
TICK_COUNT = int(360.0 / TICK_STEP_DEGREES)


@_check_types.do
def _tick_world_basis(theta: float, ring_angle: "_angle.Angle") -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return (world_position_offset, tangential_world, radial_world,
    normal_world) for the tick at local angle *theta* (radians), given
    the protractor ring's own world orientation.

    The three returned direction vectors are an orthonormal world-space
    basis for that tick -- tangential (local X), radial (local Y), ring
    normal (local Z) -- built by rotating the ring-local basis by
    *ring_angle*, then assembled into a rotation matrix for
    :meth:`Angle.from_matrix` (columns = where local X/Y/Z map to in
    world space -- the standard convention this class's own
    ``as_matrix_numpy``/``from_matrix`` already use elsewhere in this
    codebase).
    """
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    radial_local = np.array([cos_t, sin_t, 0.0], dtype=np.float32)
    tangential_local = np.array([-sin_t, cos_t, 0.0], dtype=np.float32)
    normal_local = np.array([0.0, 0.0, 1.0], dtype=np.float32)

    radial_world = ring_angle @ radial_local
    tangential_world = ring_angle @ tangential_local
    normal_world = ring_angle @ normal_local

    return radial_world, tangential_world, radial_world, normal_world


class _Tick:
    """One tick mark + its numeric label. Position/orientation are set
    once at build time by the owning ring (see ``_build_ticks``) and
    refreshed via :meth:`reposition` whenever the ring's own angle
    changes (the inner ring, tracking the object) or the camera moves
    (the outer ring, billboarding its labels).
    """

    __slots__ = (
        'degrees', 'local_theta', 'position', 'rotation', 'mesh_rotation',
        'flipped_rotation', 'normal', 'label', 'label_position')

    def __init__(self, degrees: float, local_theta: float,
                position: _point.Point, rotation: _angle.Angle, label: "_text.Text"):
        self.degrees = degrees
        self.local_theta = local_theta
        self.position = position
        self.rotation = rotation
        self.mesh_rotation = rotation
        self.flipped_rotation = rotation
        self.normal = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        self.label = label
        self.label_position = position


class ProtractorRingBase:
    """Shared washer + ticks + labels for one axis's protractor display.

    :param center: World-space center -- shared reference (not copied),
        same as every other piece of this gizmo.
    :param radius: Outer radius of the tick band (the washer itself is
        drawn slightly narrower, see :data:`_BAND_INSET`).
    :param depth: World-space thickness along the ring's normal axis.
    :param material: Material the translucent washer renders with.
    :param label_size: Font size passed to each tick's :class:`Text`.
    """

    _BAND_INSET = 0.85  # washer outer radius as a fraction of the tick radius
    _BAND_WIDTH = 0.9   # washer inner radius as a fraction of its own outer radius
    _TICK_LENGTH = 0.06  # tick length, as a fraction of radius
    _TICK_DIAMETER = 0.006  # tick diameter, as a fraction of radius
    _LABEL_RADIUS_SCALE = 1.12  # label distance from center, as a fraction of radius

    @_check_types.do
    def __init__(self, center: _point.Point, radius: float, depth: float,
                material: _materials.GLMaterial, label_size: float, context,
                camera: "_camera_base.CameraBase" = None):

        self.center = center
        self.radius = radius
        self.depth = depth
        self.material = material
        self.is_visible = False
        self._camera = camera

        self._disc_vbo = _disc_ring.create_vbo()
        self._tick_vbo = _cylinder.create_vbo()

        self._ticks: list[_Tick] = []

        with context:
            for i in range(TICK_COUNT):
                degrees = i * TICK_STEP_DEGREES
                theta = math.radians(degrees)

                label = _text.Text(str(int(degrees)), label_size, build123d.FontStyle.REGULAR)

                self._ticks.append(_Tick(
                    degrees=degrees, local_theta=theta,
                    position=_point.Point(0.0, 0.0, 0.0),
                    rotation=_angle.Angle.from_euler(0.0, 0.0, 0.0),
                    label=label))

        # subclasses must call reposition_all() once their own ring
        # angle is established (after their own __init__ finishes)

    @_check_types.do
    def reposition_all(self, ring_angle: "_angle.Angle") -> None:
        """Recompute every tick's/label's world position+orientation from
        the current *ring_angle*. Cheap -- plain vector math on
        :data:`TICK_COUNT` (36) ticks, not a per-frame cost unless the
        caller actually invokes it every frame.
        """
        for tick in self._ticks:
            _, tangential_world, radial_world, normal_world = _tick_world_basis(
                tick.local_theta, ring_angle)

            tick_world_pos = np.array(
                [float(self.center.x), float(self.center.y), float(self.center.z)],
                dtype=np.float64) + radial_world * self.radius

            tick.position = _point.Point(*[float(v) for v in tick_world_pos])

            matrix = np.column_stack([tangential_world, radial_world, normal_world])
            tick.rotation = _angle.Angle.from_matrix(matrix)
            tick.normal = normal_world

            # Cylinder tick: rotationally symmetric about its own length
            # axis, so it only needs that axis (+Z in the unit mesh, see
            # shapes/cylinder.py) pointed radially outward -- no in-plane
            # orientation to get right the way the label needs.
            tick.mesh_rotation = _angle.Angle.from_direction(radial_world)

            # Label, viewed from this ring's back side: negating both the
            # tangential and normal columns (keeping radial fixed) is
            # exactly a 180-degree rotation about the radial axis -- the
            # numbers read left-to-right correctly from that side too,
            # instead of mirrored.
            flipped_matrix = np.column_stack([-tangential_world, radial_world, -normal_world])
            tick.flipped_rotation = _angle.Angle.from_matrix(flipped_matrix)

            label_world_pos = np.array(
                [float(self.center.x), float(self.center.y), float(self.center.z)],
                dtype=np.float64) + radial_world * (self.radius * self._LABEL_RADIUS_SCALE)

            tick.label_position = _point.Point(*[float(v) for v in label_world_pos])

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram") -> None:
        if not self.is_visible:
            return

        # Translucent washer -- alpha blending scoped to just this draw,
        # matching gl/canvas_schematic/floor.py's own established
        # enable-around-the-call/restore pattern.
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        faces_program = shaders.faces

        with faces_program:
            self.material.set(faces_program)

            band_outer = self.radius * self._BAND_INSET
            band_inner = band_outer * self._BAND_WIDTH

            # disc_ring's own create_vbo() bakes outer=0.5/inner=0.4/depth=1.0
            # -- scale X/Y to reach band_outer*2 (diameter), Z to self.depth;
            # the ring's own inner/outer ratio (0.4/0.5=0.8) is close enough
            # to _BAND_WIDTH that no per-instance mesh rebuild is needed.
            self._disc_vbo.render(
                faces_program,
                self.center, self._disc_rotation(),
                _point.Point(band_outer * 2.0, band_outer * 2.0, self.depth), None)

            overridden = False

            # cylinder's own unit mesh (shapes/cylinder.py) uses
            # scale.x/scale.y as diameter and scale.z as length -- see
            # e.g. Base3D._render_debug_box_edges' own cylinder_scale.
            tick_diameter = self.radius * self._TICK_DIAMETER
            tick_scale = _point.Point(
                tick_diameter, tick_diameter, self.radius * self._TICK_LENGTH)

            for tick in self._ticks:
                override = self._tick_override_color(tick.degrees)

                if override is not None:
                    faces_program.material_diffuse = [override[0], override[1], override[2], 1.0]
                    faces_program.material_emissive = [override[0], override[1], override[2], 1.0]
                    overridden = True
                elif overridden:
                    # A previous tick overrode the shared uniform state --
                    # restore this material's own values before drawing a
                    # normal tick again.
                    self.material.set(faces_program)
                    overridden = False

                self._tick_vbo.render(
                    faces_program,
                    tick.position, tick.mesh_rotation, tick_scale, True)

            if overridden:
                self.material.set(faces_program)

            GL.glDisable(GL.GL_BLEND)

            label_scale = _point.Point(1.0, 1.0, 1.0)

            for tick in self._ticks:
                tick.label.render(
                    faces_program,
                    tick.label_position, self._label_rotation(tick), label_scale, False)

    @_check_types.do
    def _label_rotation(self, tick: _Tick) -> "_angle.Angle":
        """Return whichever of *tick*'s two precomputed label
        orientations currently reads correctly -- ``rotation`` from the
        front, ``flipped_rotation`` (180 degrees about the radial axis)
        from the back. No camera means always front-facing (never flip)
        rather than guessing.
        """
        if self._camera is None:
            return tick.rotation

        to_camera = self._camera.position.as_numpy - np.array(
            [float(tick.position.x), float(tick.position.y), float(tick.position.z)],
            dtype=np.float32)

        if float(np.dot(tick.normal, to_camera)) < 0.0:
            return tick.flipped_rotation

        return tick.rotation

    @_check_types.do
    def _disc_rotation(self) -> "_angle.Angle":
        """Subclasses provide whatever orientation the washer itself
        should render with -- the inner ring's tracks the object, the
        outer ring's stays fixed. Ticks/labels get their own
        orientation from :meth:`reposition_all` regardless.
        """
        raise NotImplementedError

    @_check_types.do
    def _tick_override_color(self, degrees: float) -> "tuple[float, float, float] | None":
        """Per-tick color override for the current frame, or ``None`` for
        the ring's own material color. Base implementation never
        overrides -- :class:`.outer_ring.OuterRing` overrides this to
        highlight the currently-hovered tick red.
        """
        return None

    @_check_types.do
    def tick_at_angle(self, degrees: float) -> "_Tick | None":
        """Return the tick nearest *degrees* (wrapped to 0-360), or
        ``None`` if there are no ticks (shouldn't happen -- present for
        the hover/click code in the subclasses to use defensively).
        """
        if not self._ticks:
            return None

        target = degrees % 360.0
        return min(self._ticks, key=lambda t: min(
            abs(t.degrees - target), 360.0 - abs(t.degrees - target)))
