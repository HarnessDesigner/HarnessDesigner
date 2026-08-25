# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""3D rotation gizmo -- the actual per-axis torus/protractor rings and
their pick/activate/drag/snap interaction, built around a selected
object. See :mod:`~..rotation_rings`'s own module docstring for the
gizmo's full visual/interaction design; this is the piece
``rotation_rings.RotationRings`` (the facade constructed by
``Base3D.handle_interaction``) holds as its own ``obj3d``.
"""

from typing import TYPE_CHECKING

import numpy as np

from . import rotation_ring
from ...objects.objects_3d import base_3d as _base_3d
from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import color as _color
from ... import config as _config
from ... import check_types as _check_types
from ...gl.canvas_base import rotation_mesh as _rotation_mesh


Config = _config.Config.editor_3d

AXES = _rotation_mesh.AXES

# Tick-number font size, as a fraction of the gizmo radius -- kept
# proportional rather than a fixed world size so labels stay legible
# whether the gizmo is wrapped around a terminal or a whole housing.
LABEL_SIZE_SCALE = 0.045


if TYPE_CHECKING:
    from ... import ui as _ui
    from ... import objects as _objects
    from ...gl import shaders as _shaders


class Rings3D(_base_3d.Base3D):
    """Own three per-axis :class:`~.rotation_ring.RotationRing` gizmos
    (torus + protractor) built around a selected object.
    """

    @_check_types.do
    def __init__(self, parent, selected: "_objects.ObjectBase",
                 mainframe: "_ui.MainFrame"):
        """Initialise the :class:`Rings3D` instance.

        :param parent: Parent :class:`~..rotation_rings.RotationRings` wrapper.
        :param selected: The object being rotated.
        :param mainframe: MainFrame reference.
        """
        obj3d = selected.obj3d

        self._axes = AXES
        self._active_axis = None

        self._build_colors()

        self._obj3d = obj3d
        self._selected = selected
        self._radius = 1e-3
        self._compute_size()

        # Signature of the config values baked into materials/meshes —
        # render() dirty-checks this each frame so config edits made from
        # UI controls apply live (no dependency on ConfigDB.bind)
        self._config_sig = self._current_config_sig()

        # Track angle and scale changes made from UI controls while the
        # rings are visible. The position is NOT copied — every sub-ring
        # shares the object's own Point instance directly, so they are
        # always exactly centered on the object with no follow-the-leader
        # callback needed.
        obj_angle = obj3d.angle
        obj_scale = obj3d.scale

        obj_angle.bind(self._on_obj_angle)
        self._obj_angle = obj_angle

        obj_scale.bind(self._on_obj_scale)
        self._obj_scale = obj_scale

        scale = _point.Point(1.0, 1.0, 1.0)
        angle = _angle.Angle.from_euler(0, 0, 0)

        # _floor_guard defeats Base3D.__init__'s inline floor-lock check —
        # with a shared position instance a bump would move the actual
        # object (and write it to the database)
        self._floor_guard = True

        with mainframe.editor3d.context:
            self._rings = {
                axis: rotation_ring.RotationRing(
                    axis, obj3d.position, obj_angle, self._radius,
                    float(Config.rotation_handler.tube_diameter_scale),
                    self._colors[axis], self._radius * LABEL_SIZE_SCALE,
                    mainframe.editor3d.context, mainframe.editor3d.camera)
                for axis in self._axes
            }

            # vbo=None: Rings3D overrides render()/_compute_aabb()/_compute_obb().
            # material is otherwise unused (render() never calls the base
            # implementation) -- reuse one axis's torus material rather
            # than plumb an Optional through Base3D's own type checks.
            material = self._rings[self._axes[-1]].torus.material
            super().__init__(parent, None, None,
                             angle, obj3d.position, scale, material)

        self._floor_guard = False
        self._is_visible = True

        self._compute_obb()
        self._compute_aabb()

    @_check_types.do
    def _build_colors(self):
        """(Re)build the per-axis colors from config."""
        ring_config = Config.rotation_handler
        self._colors = {
            axis: _color.Color(*getattr(ring_config, f'{axis}_color'))
            for axis in self._axes
        }

    @staticmethod
    @_check_types.do
    def _current_config_sig() -> tuple:
        """Return a comparable snapshot of the gizmo-affecting config."""
        ring_config = Config.rotation_handler
        return (
            float(ring_config.diameter_scale),
            float(ring_config.tube_diameter_scale),
            tuple(ring_config.x_color),
            tuple(ring_config.y_color),
            tuple(ring_config.z_color),
        )

    @_check_types.do
    def _refresh_from_config(self):
        """Re-apply config-driven properties after a config change."""
        old_sig = self._config_sig
        self._config_sig = self._current_config_sig()

        if old_sig[1] != self._config_sig[1]:
            for ring in self._rings.values():
                ring.torus.rebuild(
                    float(Config.rotation_handler.tube_diameter_scale),
                    self._context)

        self._compute_size()

    @property
    @_check_types.do
    def _context(self):
        return self.editor3d.context

    @_check_types.do
    def _update_position(self, position: _point.Point):
        """Track gizmo position changes WITHOUT Base3D's world-space logic.

        The base implementation re-applies the floor lock (which would bump
        the gizmo off-center — its local mesh always dips below ground) and
        shifts ``_data`` by the position delta (the legacy world-space
        client-array semantics). The gizmo's mesh is local space with the
        transform done in uniforms, so neither applies. The sub-rings need
        no update here — they all hold the same shared Point instance.
        """
        self._o_position = position.copy()
        self.numpy_position[:] = position.as_numpy

        self._compute_obb()
        self._compute_aabb()

    @_check_types.do
    def _compute_aabb(self):
        """Mirror the tracked object's AABB.

        The culling rows hold live views of ``self._aabb``, so keeping it
        identical to the object's box links the gizmo's view culling to the
        object: the rings are culled if and only if the object is.
        """
        obj_aabb = self._obj3d.aabb

        for i in range(2):
            for j in range(3):
                self._aabb[i][j] = obj_aabb[i][j]

        if self._floor_guard:
            # During Base3D.__init__ only: report the bottom at/above the
            # ground plane so the inline floor-lock check can never fire
            # and move the shared object position
            ground = float(Config.floor.ground_height)
            if self._aabb[0][1] < ground:
                self._aabb[0][1] = ground

    @_check_types.do
    def _compute_obb(self):
        """Mirror the tracked object's OBB (culling linked to the object)."""
        self._obb = np.array(self._obj3d.obb, dtype=np.float32, copy=True)

    @_check_types.do
    def detach(self):
        """Unbind from the tracked object and free the GL buffers."""
        # the position is the object's own Point instance — Base3D bound our
        # _update_position to it, so it must be released explicitly
        self._position.unbind(self._update_position)
        self._obj_angle.unbind(self._on_obj_angle)
        self._obj_scale.unbind(self._on_obj_scale)

        try:
            with self.editor3d.context:
                for ring in self._rings.values():
                    ring.delete(self.editor3d.context)
        except Exception:  # NOQA
            # Context may be unavailable during shutdown — the buffers die
            # with the context in that case
            pass

    @_check_types.do
    def _compute_size(self):
        """Derive the gizmo radius from the object's AABB space diagonal.

        All gizmo sizing derives from the AABB space diagonal (the largest
        distance between two points of the box) so the rings always clear
        the object regardless of its proportions.

        For housings the sizing additionally encompasses all attached parts
        (cover, seal, boot, TPA/CPA locks) so the rings wrap the full
        assembly rather than just the housing body.
        """
        aabb = self._obj3d.aabb

        ring_config = Config.rotation_handler

        if self._selected.is_housing:
            db_obj = self._selected.db_obj
            attached = [db_obj.cover, db_obj.seal, db_obj.boot,
                        db_obj.tpa_lock1, db_obj.tpa_lock2, db_obj.cpa_lock]

            # Rings are centered at the housing position, so the radius must
            # be the maximum distance from that center to any bounding corner
            # of any part — not half the combined AABB diagonal, which would
            # be wrong whenever parts are offset from the housing origin.
            pos = self._obj3d.position
            housing_pos = np.array(
                [float(pos.x), float(pos.y), float(pos.z)], dtype=np.float64)

            # Housing's own AABB: pick the farthest corner per axis without
            # needing to enumerate all 8 combinations.
            mn = np.asarray(aabb[0], dtype=np.float64)
            mx = np.asarray(aabb[1], dtype=np.float64)
            far = np.maximum(np.abs(mn - housing_pos), np.abs(mx - housing_pos))
            max_reach = float(np.linalg.norm(far))

            for part_db in attached:
                if part_db is None:
                    continue
                part_obj = part_db.get_object()
                if part_obj is None:
                    continue
                obb = part_obj.obj3d.obb
                if obb is not None:
                    dists = np.linalg.norm(
                        np.asarray(obb, dtype=np.float64) - housing_pos, axis=1)
                    max_reach = max(max_reach, float(dists.max()))

            diameter = max_reach * 2.0 * float(ring_config.diameter_scale)
        else:
            diagonal = float(np.linalg.norm(
                np.asarray(aabb[1], dtype=np.float64) -
                np.asarray(aabb[0], dtype=np.float64)))
            diameter = diagonal * float(ring_config.diameter_scale)

        self._radius = max(diameter / 2.0, 1e-3)

        # Guard for the __init__-time call, made before self._rings exists
        # (the rings are constructed with this initial radius directly);
        # every later call (config/scale changes) propagates to them.
        rings = getattr(self, '_rings', None)
        if rings is not None:
            for ring in rings.values():
                ring.on_object_scale_changed(self._radius)

    @_check_types.do
    def apply_drag_angle(self, axis: str, value: float):
        """Write a drag-driven Euler value without re-triggering ourselves.

        The angle callback is unbound around the write (the same pattern the
        UI property controls use) so the rings do not respond to their own
        updates; the ring geometry is refreshed explicitly afterwards.

        :param axis: ``'x'``, ``'y'`` or ``'z'``.
        :param value: New Euler value in degrees.
        """
        self._obj_angle.unbind(self._on_obj_angle)
        try:
            setattr(self._obj_angle, axis, value)
        finally:
            self._obj_angle.bind(self._on_obj_angle)

        self._on_obj_angle(None)

    @_check_types.do
    def pick(self, mouse_pos: _point.Point, camera) -> str | None:
        """Return the axis whose torus ring is under the mouse, if any.

        Only currently-pickable torus rings are considered — a dimmed
        sibling (a protractor is active on another axis) or the active
        axis's own torus (superseded by its protractor bands while
        shown) never hit.

        :param mouse_pos: Mouse position in screen coordinates.
        :type mouse_pos: :class:`_point.Point`
        :param camera: Canvas camera used for projection.
        :returns: ``'x'``, ``'y'`` or ``'z'`` when a ring is hit, else ``None``.
        :rtype: str | None
        """
        for axis in self._axes:
            if self._rings[axis].hit_test_torus(mouse_pos, camera):
                return axis
        return None

    @_check_types.do
    def activate(self, axis: str):
        """Show *axis*'s protractor and dim the other two torus rings."""
        for a, ring in self._rings.items():
            if a == axis:
                # Un-dim first in case this axis was left dimmed by a
                # previous activation of a different axis without an
                # intervening deactivate().
                ring.set_dimmed(False)
                ring.activate()
            else:
                ring.set_dimmed(True)

        self._active_axis = axis

    @_check_types.do
    def deactivate(self):
        """Hide any active protractor and restore normal torus picking."""
        for ring in self._rings.values():
            ring.deactivate()
            ring.set_dimmed(False)

        self._active_axis = None

    @property
    @_check_types.do
    def active_axis(self) -> str | None:
        return self._active_axis

    @property
    @_check_types.do
    def is_inner_dragging(self) -> bool:
        """Whether the active axis's inner (free-rotation) band currently
        has a drag in progress -- lets a caller distinguish "advance the
        free-rotation drag" (:meth:`update_inner_drag`) from "just update
        the outer ring's nearest-tick hover" (:meth:`update_outer_hover`)
        on the same mouse-move event.
        """
        if self._active_axis is None:
            return False

        return self._rings[self._active_axis].inner.is_dragging

    @_check_types.do
    def begin_inner_drag(self, mouse_pos: _point.Point, camera) -> bool:
        """Start a free-rotation drag if *mouse_pos* is on the active
        axis's inner (object-space) protractor band.

        :returns: Whether a drag was started.
        """
        if self._active_axis is None:
            return False

        ring = self._rings[self._active_axis]
        if not ring.hit_test_inner(mouse_pos, camera):
            return False

        ring.inner.begin_drag(mouse_pos, camera)
        return True

    @_check_types.do
    def update_inner_drag(self, mouse_pos: _point.Point):
        """Advance the active axis's free-rotation drag, if any."""
        if self._active_axis is None:
            return

        value = self._rings[self._active_axis].inner.update_drag(mouse_pos)
        if value is not None:
            self.apply_drag_angle(self._active_axis, value)

    @_check_types.do
    def end_inner_drag(self):
        if self._active_axis is None:
            return

        self._rings[self._active_axis].inner.end_drag()

    @_check_types.do
    def update_outer_hover(self, mouse_pos: _point.Point, camera):
        """Update the active axis's nearest-tick hover highlight."""
        if self._active_axis is None:
            return

        self._rings[self._active_axis].outer.update_hover(mouse_pos, camera)

    @_check_types.do
    def click_outer_snap(self):
        """Snap the active axis's Euler value to the currently-hovered
        outer-ring tick, if any.
        """
        if self._active_axis is None:
            return

        value = self._rings[self._active_axis].outer.click_hovered()
        if value is not None:
            self.apply_drag_angle(self._active_axis, value)

    @_check_types.do
    def _on_obj_angle(self, _):
        """Update every ring's orientation when the tracked object rotates."""
        for ring in self._rings.values():
            ring.on_object_angle_changed()

    @_check_types.do
    def _on_obj_scale(self, _):
        """Resize the gizmo when the tracked object's scale changes.

        Base3D's own scale callback was bound first, so the object's AABB
        has already been recomputed by the time this runs.
        """
        self._compute_size()

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram"):
        """Render all three axis gizmos."""
        # Live config tracking: rebuild sizing/mesh/colors when any of the
        # gizmo settings changed since the last frame
        if self._config_sig != self._current_config_sig():
            self._refresh_from_config()

        faces_program = shaders.faces

        with faces_program:
            # Smooth normals so the tube/washer cross-sections shade round
            faces_program.normal_mode = 0

            # The gizmo is a UI element, not part of the scene — suppress the
            # floor reflection for it, then restore the global config value so
            # objects rendered after the rings keep theirs.
            faces_program.has_reflection = 0

            # This program's uniform state persists across draw calls, so a
            # WireStripe drawn earlier in the same frame can leave
            # stripeClipStart/stripeClipStop set to a real window -- without
            # resetting it, that leftover value clips this gizmo's own
            # geometry too (spheres flattening to discs, rings flattening),
            # varying frame to frame with whatever last set it.
            faces_program.stripe_clip_start = 0.0
            faces_program.stripe_clip_stop = 0.0

            for ring in self._rings.values():
                ring.render(shaders)

            config = self.editor3d.config
            faces_program.has_reflection = int(
                config.floor.reflections.enable and
                config.floor.enable_floor_lock)
