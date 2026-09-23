# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Schematic-editor rotation gizmo -- a single Y-axis
:class:`~..rotation_ring.RotationRing` (protractor only, no torus --
see below), reusing that exact same class (it only ever needed a GL
context and a camera, never anything 3D-view-specific) built around a
selected object. Same visual/interaction design as the 3D editor's own
3-axis gizmo (see :mod:`~..rotation_rings`'s own module docstring) --
just one axis, since the schematic view is permanently locked top-down
and only a rotation about world Y is ever meaningful here. Mirrors
:mod:`~..editor_3d.generic`'s own ``Rings3D`` almost exactly; see that
module for the fuller commentary this one deliberately doesn't repeat.

No torus ring (``has_torus=False``, see :class:`~..rotation_ring.
RotationRing`'s own docstring): the 3D gizmo's always-on torus exists so
the user can pick which of 3 axes to rotate about -- with only one axis
here, there is nothing to pick between, so the protractor is simply
already active the moment this gizmo is built (see :meth:`__init__`'s
own ``self.activate('y')`` call) instead of waiting for a click on a
ring that would otherwise be the only thing ever shown. Confirmed
2026-09-22 (Kevin) as the fix for both the pointless extra click and this
gizmo taking a visible moment to appear.
"""

from typing import TYPE_CHECKING

import numpy as np

from .. import rotation_ring
from ...objects.objects_schematic import base_schematic as _base_schematic
from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import color as _color
from ... import config as _config
from ... import check_types as _check_types
from .. import rotation_mesh as _rotation_mesh
from ...shapes import text as _text
from ...gl import materials as _materials
from ...wire_routing import reroute as _wire_reroute


Config = _config.Config.editor_schematic

AXES = ('y',)

LABEL_SIZE_SCALE = 0.045


if TYPE_CHECKING:
    from ... import ui as _ui
    from ... import objects as _objects
    from ...gl import shaders as _shaders


class Rings2D(_base_schematic.BaseSchematic):
    """Own a single Y-axis :class:`~..rotation_ring.
    RotationRing` gizmo (torus + protractor) built around a selected
    object -- see the module docstring.
    """

    @_check_types.do
    def __init__(self, parent, selected: "_objects.ObjectBase",
                 mainframe: "_ui.MainFrame"):
        """Initialise the :class:`Rings2D` instance.

        :param parent: Parent :class:`~..rotation_rings.RotationRings` wrapper.
        :param selected: The object being rotated.
        :param mainframe: MainFrame reference.
        """
        objschematic = selected.objschematic

        self._axes = AXES
        self._active_axis = None

        self._build_colors()

        self._obj_view = objschematic
        self._selected = selected
        self._radius, self._object_radius = self._compute_radius_values()

        # Resolved once, here, not per angle change -- what's attached
        # doesn't change while this gizmo is up, same discipline
        # drag_handlers.editor_schematic.generic.Generic's own
        # self._attached uses (and the same sort: junction wires first,
        # then shortest-crow-flies-distance first -- see that class's
        # own docstring for why). Used by apply_drag_angle to re-route
        # every attached wire whenever the rotation actually changes.
        self._attached_wires = sorted(
            _wire_reroute.wires_attached_to(selected),
            key=lambda w: (not _wire_reroute.is_junction_wire(w), _wire_reroute.crow_flies_distance(w)))

        self._config_sig = self._current_config_sig()

        obj_angle = objschematic.angle
        obj_scale = objschematic.scale

        obj_angle.bind(self._on_obj_angle)
        self._obj_angle = obj_angle

        obj_scale.bind(self._on_obj_scale)
        self._obj_scale = obj_scale

        # The ring's own drawn geometry is centered on a COPY of
        # objschematic.position, its Y bumped up by
        # Config.rotation_handler.ring_height, so it renders above the
        # housing rectangle/cavity/terminal labels instead of coplanar
        # with (and blending/depth-fighting against) them -- this copy
        # marks only where the ring itself is drawn, it plays no part in
        # the actual rotation being performed on the tracked object.
        # Computed once, here -- see _update_position's own comment for
        # why this never needs to track the object afterward.
        self._ring_center = objschematic.position.copy()
        self._ring_center.y += float(Config.rotation_handler.ring_height)

        scale = _point.Point(1.0, 1.0, 1.0)
        angle = _angle.Angle.from_euler(0, 0, 0)

        with mainframe.editor2d.context:
            self._rings = {
                axis: rotation_ring.RotationRing(
                    axis, self._ring_center, obj_angle, self._radius, self._object_radius,
                    float(Config.rotation_handler.tube_diameter_scale),
                    self._colors[axis], self._outer_color, self._radius * LABEL_SIZE_SCALE,
                    mainframe.editor2d.context, mainframe, _base_schematic.BaseSchematic,
                    # No camera -- same reasoning as editor_pegboard.
                    # generic's own identical change: this view's camera
                    # is permanently locked top-down, the exact
                    # gimbal-lock orientation ProtractorRingBase's
                    # billboard math degenerates at. camera=None falls
                    # every tick label through to its raw, non-tracking
                    # mesh_rotation instead (see ProtractorRingBase's own
                    # "no camera at all" fallback) -- confirmed
                    # 2026-09-07 (Kevin) as the fix.
                    None, local_tilt=_text.TOP_DOWN_TILT, has_torus=False)
                for axis in self._axes
            }

            # No torus to reuse a material from (has_torus=False, see the
            # module docstring) -- render() never uses this material
            # either way (see Rings3D's own identical comment), so any
            # valid material satisfies BaseSchematic.__init__'s own type
            # check; this axis's own ring color is as good as any.
            material = _materials.Generic(self._colors[self._axes[-1]])
            super().__init__(parent, None, None,
                             angle, objschematic.position, scale, material)

            # Only one axis, nothing to pick between -- skip the torus'
            # click-to-activate step and come up with the protractor
            # already active (see the module docstring). Still inside
            # the context manager above: unlike the 3D/pegboard gizmos'
            # own activate() (called later, from mouse handling, once
            # the canvas's own context is already current), this one
            # builds the protractor's GL objects during __init__ itself.
            self.activate('y')

        self._is_visible = True

        self._compute_obb()
        self._compute_aabb()

    @_check_types.do
    def _build_colors(self):
        """(Re)build the per-axis colors from config -- only ``y`` here."""
        ring_config = Config.rotation_handler
        self._colors = {axis: _color.Color(*ring_config.y_color) for axis in self._axes}
        self._outer_color = _color.Color(*ring_config.outer_ring_color)

    @staticmethod
    @_check_types.do
    def _current_config_sig() -> tuple:
        """Return a comparable snapshot of the gizmo-affecting config."""
        ring_config = Config.rotation_handler
        return (
            float(ring_config.diameter_scale),
            float(ring_config.tube_diameter_scale),
            tuple(ring_config.y_color),
            tuple(ring_config.outer_ring_color),
        )

    @_check_types.do
    def _refresh_from_config(self):
        """Re-apply config-driven properties after a config change."""
        old_sig = self._config_sig
        self._config_sig = self._current_config_sig()

        # No torus to rebuild here (has_torus=False, see the module
        # docstring) -- tube_diameter_scale only ever affected the torus
        # tube's own cross-section, so a config change to it is a no-op
        # for this view; only re-derive the protractor sizing below.
        self._compute_size()

    @property
    @_check_types.do
    def _context(self):
        return self.editor2d.context

    @_check_types.do
    def _update_position(self, position: _point.Point):
        """Track gizmo position changes -- see Rings3D's own version;
        this view has no floor lock to defeat.

        Doesn't touch :attr:`_ring_center` (the ring's own, separately
        lifted, drawn position -- see ``__init__``'s own comment) -- the
        tracked object never actually moves while its own rotation gizmo
        is up (drag and rotate are mutually-exclusive armed handlers on
        the same object), so the offset computed once at construction
        stays correct for this gizmo's whole lifetime.
        """
        self._o_position = position.copy()
        self.numpy_position[:] = position.as_numpy

        self._compute_obb()
        self._compute_aabb()

    @_check_types.do
    def _compute_aabb(self):
        """Mirror the tracked object's AABB (culling linked to the object)."""
        obj_aabb = self._obj_view.aabb

        for i in range(2):
            for j in range(3):
                self._aabb[i][j] = obj_aabb[i][j]

    @_check_types.do
    def _compute_obb(self):
        """Mirror the tracked object's OBB (culling linked to the object)."""
        self._obb = np.array(self._obj_view.obb, dtype=np.float32, copy=True)

    @_check_types.do
    def detach(self):
        """Unbind from the tracked object and free the GL buffers.

        Also sweeps for any OTHER wire in the project -- one not
        attached to the object just rotated, so never touched by
        apply_drag_angle's own _route_attached_wires -- that the new
        footprint left too close to (mirrors
        drag_handlers.editor_schematic.generic.Generic.delete's own
        identical call, made once on drag release; this is rotation's
        equivalent "the interaction is over" point).
        """
        project = self.mainframe.project
        _wire_reroute.sweep_for_overlaps(project, self._selected, self._attached_wires)

        self._position.unbind(self._update_position)
        self._obj_angle.unbind(self._on_obj_angle)
        self._obj_scale.unbind(self._on_obj_scale)

        try:
            with self.editor2d.context:
                for ring in self._rings.values():
                    ring.delete(self.editor2d.context)
        except Exception:  # NOQA
            pass

    @_check_types.do
    def _compute_radius_values(self) -> tuple[float, float]:
        """Derive (radius, object_radius) from the object's own AABB
        space diagonal -- a pure computation, no side effects, safe to
        call before ``self._radius``/``self._object_radius`` or
        ``self._rings`` exist (see ``__init__``). No attached-parts
        sizing here -- schematic doesn't overlay those the way the 3D
        editor does.
        """
        aabb = self._obj_view.aabb

        ring_config = Config.rotation_handler

        diagonal = float(np.linalg.norm(
            np.asarray(aabb[1], dtype=np.float64) -
            np.asarray(aabb[0], dtype=np.float64)))
        diameter = diagonal * float(ring_config.diameter_scale)

        radius = max(diameter / 2.0, 1e-3)
        object_radius = max(diagonal / 2.0, 1e-3)

        return radius, object_radius

    @_check_types.do
    def _compute_size(self):
        """Recompute size and propagate it to every already-built ring --
        call whenever the tracked object's own scale/AABB changes.
        """
        self._radius, self._object_radius = self._compute_radius_values()

        rings = getattr(self, '_rings', None)
        if rings is not None:
            for ring in rings.values():
                ring.on_object_scale_changed(self._radius, self._object_radius)

    @_check_types.do
    def apply_drag_angle(self, axis: str, value: float):
        """Write a drag-driven Euler value without re-triggering ourselves.

        Rounded to the nearest ``Config.rotation_handler.snap_angle``
        (90 degrees) first -- schematic housings are locked to cardinal
        orientations (see that config value's own comment), so both the
        free-drag inner ring and the click-a-tick outer ring only ever
        land the object on 0/90/180/270, never anything in between. A
        no-op if that rounded value matches what's already stored (the
        common case mid-drag, between two 90-degree boundaries) -- skips
        the DB write and the wire re-route below for a value that
        wouldn't actually change anything.
        """
        snap_angle = float(Config.rotation_handler.snap_angle)
        value = _rotation_mesh.wrap_angle(round(value / snap_angle) * snap_angle)

        if value == float(getattr(self._obj_angle, axis)):
            return

        self._obj_angle.unbind(self._on_obj_angle)
        try:
            setattr(self._obj_angle, axis, value)
        finally:
            self._obj_angle.bind(self._on_obj_angle)

        self._on_obj_angle(None)

        self._route_attached_wires()

    @_check_types.do
    def _route_attached_wires(self) -> None:
        """Re-route every wire attached to the object being rotated.

        Unlike a plain drag (drag_handlers.editor_schematic.generic.
        Generic._event's own ``follow_moved`` step), there is no cheap
        "does the existing path still work" shortcut to try first -- a
        rotation swings each attached terminal's own exit point AND
        direction by a different amount depending on its offset from
        the pivot, so every attached wire is always fully re-routed
        here, as one batch (shared ``RoutingFrame``, same
        ``build_frame``/``skip_wires`` pattern
        ``drag_handlers.editor_schematic.generic.Generic._route``
        already uses) so they resettle around each other instead of
        routing straight through one another.
        """
        if not self._attached_wires:
            return

        project = self.mainframe.project
        frame = _wire_reroute.build_frame(project, self._attached_wires)

        unsettled = set(self._attached_wires)
        for wire in self._attached_wires:
            unsettled.discard(wire)
            _wire_reroute.reroute_wire(project, wire, skip_wires=unsettled, frame=frame)

    @_check_types.do
    def pick(self, mouse_pos: _point.Point, camera) -> str | None:
        """Return the axis whose torus ring is under the mouse, if any."""
        for axis in self._axes:
            if self._rings[axis].hit_test_torus(mouse_pos, camera):
                return axis
        return None

    @_check_types.do
    def activate(self, axis: str):
        """Show *axis*'s protractor."""
        for a, ring in self._rings.items():
            if a == axis:
                ring.set_dimmed(False)
                ring.activate()
            else:
                ring.set_dimmed(True)

        self._active_axis = axis

    @_check_types.do
    def deactivate(self):
        """Hide the active protractor and restore normal torus picking."""
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
        if self._active_axis is None:
            return False

        return self._rings[self._active_axis].inner.is_dragging

    @_check_types.do
    def begin_inner_drag(self, mouse_pos: _point.Point, camera) -> bool:
        if self._active_axis is None:
            return False

        ring = self._rings[self._active_axis]
        if not ring.hit_test_inner(mouse_pos, camera):
            return False

        ring.inner.begin_drag(mouse_pos, camera)
        return True

    @_check_types.do
    def update_inner_drag(self, mouse_pos: _point.Point):
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
        if self._active_axis is None:
            return

        self._rings[self._active_axis].outer.update_hover(mouse_pos, camera)

    @_check_types.do
    def click_outer_snap(self) -> bool:
        """Snap the active axis's Euler value to the currently-hovered
        outer-ring tick, if any.

        :returns: Whether a tick was actually hovered (and so a snap
            happened) -- lets the caller tell a real gizmo interaction
            apart from a click that missed it entirely.
        """
        if self._active_axis is None:
            return False

        value = self._rings[self._active_axis].outer.click_hovered()
        if value is None:
            return False

        self.apply_drag_angle(self._active_axis, value)
        return True

    @_check_types.do
    def _on_obj_angle(self, _):
        """Update every ring's orientation when the tracked object rotates.

        The rings' own sizes/offsets are fixed for this gizmo's whole
        lifetime, but this wrapper's own culling bounds (_aabb/_obb,
        mirrored from the tracked object) genuinely are angle-dependent,
        so those still need refreshing here, every time.
        """
        for ring in self._rings.values():
            ring.on_object_angle_changed()

        self._compute_obb()
        self._compute_aabb()

    @_check_types.do
    def _on_obj_scale(self, _):
        self._compute_size()

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram"):
        """Render the single-axis gizmo."""
        if self._config_sig != self._current_config_sig():
            self._refresh_from_config()

        faces_program = shaders.faces

        with faces_program:
            faces_program.normal_mode = 0
            faces_program.has_reflection = 0
            faces_program.stripe_clip_start = 0.0
            faces_program.stripe_clip_stop = 0.0

            for ring in self._rings.values():
                ring.render(shaders)

            faces_program.has_reflection = 0
