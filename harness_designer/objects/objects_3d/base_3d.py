# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np
from OpenGL import GL

from ... import color as _color
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry.decimal import Decimal as _d
from ... import config as _config
from ... import utils as _utils
from ...gl import materials as _materials
from ...gl import vbo as _vbo
from ...shapes import text as _text
from ...shapes import box as _box
from ...shapes import cylinder as _cylinder
from ...shapes import sphere as _sphere
from ...shapes import square_outline as _square_outline
from .. import objectsvar as _objectsvar
from ...gl.canvas_base import interaction as _interaction

from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database import project_db as _project_db
    from ...database.global_db import model3d as _model3d
    from .. import ObjectBase as _ObjectBase
    from ... import ui as _ui
    from ...gl import shaders as _shaders


Config = _config.Config.editor_3d
_debug_config = _config.Config.debug.rendering3d


class Base3D(_objectsvar.BaseVar):
    """Represent a base 3D in :mod:`harness_designer.objects.objects_3d.base_3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    db_obj: "_project_db.PJTEntryBase"

    # Floor lock keeps a freely-placed object (a Housing dragged into the
    # scene) from clipping below the ground plane. Subclasses whose
    # position is always derived from a parent object (Terminal from its
    # cavity, etc.) rather than placed directly by the user should set this
    # True -- otherwise the one-time snap in __init__ silently overwrites a
    # correctly-computed position (and persists the overwrite to the DB).
    _floor_lock_exempt: bool = False

    # Object-picking priority (see gl.object_picker.find_object).
    # Wins outright over lower-priority objects hit by the same click ray,
    # regardless of which is nearer -- needed for handle-type objects
    # (WireMarker, WireLayout, BundleLayout) that legitimately sit inside
    # their parent wire/bundle's own OBB, sometimes with zero radial
    # offset, where the parent's tube surface is genuinely the nearer
    # ray hit and pure nearest-hit picking could never select the handle.
    _pick_priority: int = 0

    # Local-canvas mouse position that opened this object's context menu,
    # stashed by mainframe.py's _on_obj_right_click_3d right before it
    # calls get_context_menu() -- a plain instance attribute rather than a
    # get_context_menu() parameter so every other Base3D subclass's
    # get_context_menu(self) override keeps working unchanged. Only
    # Wire.get_context_menu/WireMenu currently reads this (to place a new
    # marker at the actual click point instead of the wire's midpoint).
    _context_menu_click_pos: _point.Point | None = None

    @_check_types.do
    def __init__(self, parent: "_ObjectBase", db_obj: "_project_db.PJTEntryBase",
                 vbo: _vbo.VBOHandlerBase | _text.Text | None, angle: _angle.Angle | None,
                 position: _point.Point | None, scale: _point.Point | None,
                 material: _materials.GLMaterial | None):

        self.editor3d = parent.mainframe.editor3d

        super().__init__(parent, db_obj, vbo, angle, position, scale, material)

        self.parent: "_ObjectBase" = parent
        self.mainframe: "_ui.MainFrame" = parent.mainframe

        try:
            self._is_visible = db_obj.is_visible3d  # NOQA
            self.db_obj.bind(self._is_visible_callback, 'is_visible3d')
        except AttributeError:
            self._is_visible = False

        # Inert placeholder construction (no position/angle/scale of its
        # own -- e.g. a note not placed in this view, see
        # objects_3d/note.py's own __init__) passes all three as None;
        # BaseVar.__init__ above already tolerates that, but the
        # floor-lock logic below is 3D-only and has nothing to bind/
        # unbind/snap in that case.
        if position is not None and angle is not None and scale is not None:
            position.unbind(self._update_position)
            angle.unbind(self._update_angle)
            scale.unbind(self._update_scale)

            if (
                not self._floor_lock_exempt and
                self.editor3d.config.floor.enable_floor_lock and
                self._aabb[0][1] < Config.floor.ground_height
            ):
                y = _d(position.y)
                y += _d(Config.floor.ground_height) - _d(float(self._aabb[0][1]))

                position.y = float(y)

            position.bind(self._update_position)
            angle.bind(self._update_angle)
            scale.bind(self._update_scale)

    @property
    @_check_types.do
    def _selected_color(self) -> _color.Color:
        return _color.Color(*Config.selected_color)

    @property
    @_check_types.do
    def editor(self):
        return self.editor3d

    @_check_types.do
    def _is_visible_callback(self, *_, **__):
        self._is_visible = self.db_obj.is_visible3d  # NOQA
        self.mainframe.editor3d.Refresh()

    @_debug.logfunc
    @_check_types.do
    def _set_model(self, model: "_model3d.Model3D"):
        with self.parent.mainframe.editor3d.context:
            uuid = model.uuid

            try:
                # this checks the stored part size against the actual calculated
                # size of the part using the models obb. This is done with the angle
                # of the part set beforehand.
                o_size = self.db_obj.part.size  # NOQA
                size = model.size
                if size != o_size:
                    self.db_obj.part.size = size  # NOQA
            except AttributeError:
                pass

            if uuid in _vbo.PooledVBOHandler:
                vbo = _vbo.PooledVBOHandler(uuid)
            else:
                packed = np.load(model.data_path).reshape(-1, 3)

                angle = model.angle3d
                position = model.position3d
                count = model.vertex_count

                obb = model.obb
                aabb = model.aabb

                obb @= angle
                aabb @= angle

                obb += position
                aabb += position

                packed @= angle
                packed[:count] += position

                packed = packed.reshape(-1)

                vbo = _vbo.PooledVBOHandler(uuid, packed, count, aabb=aabb, obb=obb)
            vbo.acquire()

            self._vbo = vbo
            try:
                scale = self.db_obj.scale3d  # NOQA
                self._scale.unbind(self._update_scale)
                self._scale = scale
                self._o_scale = self._scale.copy()
                self._scale.bind(self._update_scale)

            except AttributeError:
                pass

            self.position.unbind(self._update_position)
            self.angle.unbind(self._update_angle)

            self._compute_obb()
            self._compute_aabb()

            if (
                not self._floor_lock_exempt and
                self.editor3d.config.floor.enable_floor_lock and
                self._aabb[0][1] < Config.floor.ground_height
            ):
                y = _d(self.position.y)
                y += _d(Config.floor.ground_height) - _d(float(self._aabb[0][1]))

                self.position.y = float(y)

            self.position.bind(self._update_position)
            self.angle.bind(self._update_angle)

        self.editor3d.Refresh()

    @_check_types.do
    def _update_position(self, position: _point.Point):
        """Update the position.

        UNKNOWN details are inferred from the callable name and signature.

        :param position: Position value.
        :type position: :class:`_point.Point`
        """

        super()._update_position(position)

        if (
            not self._floor_lock_exempt and
            self.editor3d.config.floor.enable_floor_lock and
            self._aabb[0][1] < Config.floor.ground_height
        ):
            with self.editor3d.context:
                y = _d(position.y)
                y += _d(Config.floor.ground_height) - _d(float(self._aabb[0][1]))

                position.unbind(self._update_position)
                position.y = float(y)
                position.bind(self._update_position)

                self._o_position = position.copy()
                self.numpy_position[:] = position.as_numpy

                self._compute_obb()
                self._compute_aabb()

            self.editor3d.Refresh(False)

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle):
        """Update the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        super()._update_angle(angle)

        if (
            not self._floor_lock_exempt and
            self.editor3d.config.floor.enable_floor_lock and
            self._aabb[0][1] < Config.floor.ground_height
        ):
            with self.editor3d.context:
                y = _d(self._position.y)
                y += _d(Config.floor.ground_height) - _d(float(self._aabb[0][1]))

                self._position.unbind(self._update_position)
                self._position.y = float(y)
                self._position.bind(self._update_position)

    @_check_types.do
    def _update_scale(self, scale: _point.Point):
        """Update the scale.

        UNKNOWN details are inferred from the callable name and signature.

        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        """

        super()._update_scale(scale)

        if (
            not self._floor_lock_exempt and
            self.editor3d.config.floor.enable_floor_lock and
            self._aabb[0][1] < Config.floor.ground_height
        ):
            with self.editor3d.context:
                y = _d(self._position.y)
                y += _d(Config.floor.ground_height) - _d(float(self._aabb[0][1]))

                self._position.unbind(self._update_position)
                self._position.y = float(y)
                self._position.bind(self._update_position)

    @_check_types.do
    def delete(self):
        """Execute the delete operation.

        Row deletion and canvas de-registration are handled once, centrally,
        by :meth:`ObjectBase.delete`. Subclasses override this as their hook
        for view-local teardown (see :meth:`objects_3d.housing.Housing.delete`).
        """
        self.parent.delete()

    @_check_types.do
    def _delete(self):
        """
        Any object specific taredown should occur in this function
        """
        self._is_deleted = True
        self.editor3d.Refresh()

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        """Generic single-position drag arming/dispatch, plus rotation-
        gizmo arming/dispatch (see rotation_handlers.rotation_rings.
        RotationRings) -- applies to any 3D object type that doesn't need
        bespoke drag behavior (see drag_handlers.editor_3d.generic.
        Generic's own docstring for the full list). Object types whose
        drag isn't a plain translation (Wire, Bundle, WireMarker) override
        this outright with their own drag arm/forward logic instead of
        this generic one -- and get no rotation support at all as a
        result, which is correct: none of the three has an independently
        user-set orientation (a wire/bundle's shape comes from its path,
        a marker's from the wire it rides), so there's nothing meaningful
        for a rotation gizmo to adjust.
        """
        from ...rotation_handlers import rotation_rings as _rotation_rings

        if isinstance(self._active_handler, _rotation_rings.RotationRings):
            return self._handle_rotation_interaction(
                current_pos, had_motion, interaction_type, clicked_object)

        if self._active_handler is not None:
            if interaction_type is _interaction.MouseInteraction.MOVE:
                self._active_handler(current_pos - last_pos, current_pos)
                return True

            if interaction_type is _interaction.MouseInteraction.LEFT_UP:
                self._active_handler.delete()
                self._active_handler = None
                # No real drag happened -- a plain click-release on an
                # already-selected object arms this handler (selection is
                # required to arm), but a click with no motion should still
                # fall through to the default select/deselect toggle below,
                # not get eaten here.
                return had_motion

            return False

        if (
            interaction_type is _interaction.MouseInteraction.RIGHT_DOWN and
            clicked_object is self.parent and
            self.mainframe.get_selected() is self.parent and
            self.can_rotate()
        ):
            self._active_handler = _rotation_rings.RotationRings(self.editor3d.editor, self.parent)
            self._rotation_just_armed = True
            return True

        if (
            interaction_type is _interaction.MouseInteraction.LEFT_DOWN and
            clicked_object is self.parent and
            self.mainframe.get_selected() is self.parent and
            self.can_drag()
        ):
            from ...drag_handlers.editor_3d import generic as _drag_generic  # NOQA -- avoid a cycle at import time (drag_handlers.editor_3d -> move_arrows -> this module)

            self._active_handler = _drag_generic.Generic(self.editor3d.editor, self.parent)
            return True

        return False

    @_check_types.do
    def _handle_rotation_interaction(
        self, current_pos: _point.Point, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        """Forward one mouse event to the already-armed rotation gizmo
        (:attr:`_active_handler`, a RotationRings) -- see that class's
        own docstring for the full torus-pick -> protractor-activate ->
        inner-drag/outer-snap flow this drives.

        A plain right-click (no motion between RIGHT_DOWN and RIGHT_UP)
        toggles the gizmo off, decided on RIGHT_UP rather than RIGHT_DOWN
        so a right-drag (the default binding for truck/pedestal-ing the
        camera) is never mistaken for the toggle-off click -- RIGHT_DOWN
        itself always leaves the event unconsumed, letting the camera's
        own right-button-drag handling arm normally; if that drag never
        materializes, RIGHT_UP still closes the gizmo. Clicking somewhere
        that hits neither a torus ring nor (while an axis is active) the
        inner/outer protractor closes the gizmo too, but leaves the event
        unconsumed so normal selection handling still runs for that click.

        Every branch below only ever consumes (returns True for) an event
        that actually did something to the gizmo -- everything else
        (a plain hover, a miss on the protractor, a drag on a button not
        bound to a ring) returns False so the camera's own mouse controls
        (e.g. the default pan/tilt-on-left-drag, truck/pedestal-on-right-
        drag bindings) still work while the rings/protractor are on
        screen, letting the camera be repositioned without having to
        close the gizmo first.
        """
        rings = self._active_handler
        camera = self.editor3d.editor.camera

        if interaction_type is _interaction.MouseInteraction.RIGHT_DOWN:
            return False

        if interaction_type is _interaction.MouseInteraction.RIGHT_UP:
            if self._rotation_just_armed:
                # This release belongs to the same click that just armed
                # the gizmo on RIGHT_DOWN, not a later toggle-off click --
                # both look identical here (had_motion False), so only
                # the very first RIGHT_UP after arming is exempt.
                self._rotation_just_armed = False
                return True

            if had_motion:
                # A right-drag happened -- that was the camera's own
                # truck/pedestal control, not a toggle-off click.
                return False

            rings.delete()
            self._active_handler = None
            return True

        if interaction_type is _interaction.MouseInteraction.MOVE:
            if rings.obj3d.is_inner_dragging:
                rings.obj3d.update_inner_drag(current_pos)
                return True

            if rings.obj3d.active_axis is not None:
                rings.obj3d.update_outer_hover(current_pos, camera)

            return False

        if interaction_type is _interaction.MouseInteraction.LEFT_UP:
            if rings.obj3d.is_inner_dragging:
                rings.obj3d.end_inner_drag()
                return True

            return False

        if interaction_type is _interaction.MouseInteraction.LEFT_DOWN:
            if rings.obj3d.active_axis is not None:
                if rings.obj3d.begin_inner_drag(current_pos, camera):
                    return True

                if rings.obj3d.click_outer_snap():
                    return True

                # Missed both protractor bands -- a click on a SIBLING
                # torus ring (still pickable while dimmed -- see
                # RotationRing.set_dimmed) switches directly to that
                # axis instead of requiring a miss-click first to close
                # the current one.
                axis = rings.obj3d.pick(current_pos, camera)
                if axis is not None and axis != rings.obj3d.active_axis:
                    rings.obj3d.activate(axis)
                    return True

                # Missed everything -- leave the gizmo exactly as it is
                # (still active on this axis) and let the default
                # click/drag behavior run.
                return False

            axis = rings.obj3d.pick(current_pos, camera)
            if axis is not None:
                rings.obj3d.activate(axis)
                return True

            rings.delete()
            self._active_handler = None
            return False

        return False

    @property
    @_check_types.do
    def is_visible(self) -> bool:
        """Return the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self._is_visible

    @is_visible.setter
    @_check_types.do
    def is_visible(self, value: bool):
        """Set the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._is_visible = value
        try:
            self.db_obj.is_visible3d = value
        except AttributeError:
            pass

    @_check_types.do
    def render_selected_overlay(self, shaders: "_shaders.ShaderProgram") -> None:
        """Debug/selection overlays for the currently-selected object --
        AABB/OBB wireframe-ish boxes (each gated by its own debug toggle)
        plus a floor projection of the OBB's footprint (always on, not a
        debug setting) -- every check lives *inside* the respective
        ``render_*`` method below rather than here, so any other caller
        (see ``objects_3d/wire.py``'s own ``render_selected_overlay``
        override, which draws the identical overlays per segment plus for
        each waypoint layout marker along a bent path) gets the same
        gating for free without needing to duplicate the checks.

        Called directly by ``canvas_base.py::_render_selected_overlay``
        once per frame, as the last thing drawn (see that method's own
        docstring, and ``objectsvar/base_var.py::render_selected_overlay``'s,
        for why this isn't an automatic ``render()`` tail call) -- the
        explicit ``is_selected`` guard below is this method's own
        responsibility now rather than the caller's.

        The 3 methods below take only *shaders* -- they read
        ``self._vbo``/``self._position``/``self._angle``/``self._scale``
        directly, the same way ``_render_geometry`` already does. A caller
        that wants these overlays for something other than this object's
        own current transform (a Wire/Bundle waypoint marker, not the
        wire/bundle itself) temporarily swaps those 4 attributes first --
        the same swap-call-restore idiom ``Wire.render()``'s own per-segment
        loop already uses -- rather than these methods taking extra
        parameters for a shape/transform that isn't ``self``'s own.
        """
        if not self.is_selected:
            return

        if not self.is_visible:
            return

        if (
            self._vbo is None or
            self._position is None or
            self._scale is None or
            self._angle is None
        ):
            return

        self._render_overlay_group(shaders)

    @_check_types.do
    def render_handler(self, shaders: "_shaders.ShaderProgram") -> None:
        """Render whatever's currently armed on :attr:`_active_handler`
        (a drag or rotation handler) -- e.g. the move-arrows axis-lock
        gizmo, or the rotation-rings protractor.

        Called directly by ``canvas_base.py``'s own selected-object
        rendering, at the same point (and under the same depth/blend
        handling) as ``render_selected_overlay`` above -- NOT an
        automatic ``render()`` tail call, and the handler itself is
        deliberately never registered as its own scene object via
        ``mainframe.add_object`` (see ``drag_handlers/move_arrows.py``'s
        and ``rotation_handlers/rotation_rings.py``'s own docstrings).
        Rendering it mixed into the ordinary per-object pipeline instead
        of alongside the selected object's own special handling is what
        broke both the object's and the gizmo's own depth compositing in
        the first place.

        Same 4-attribute guard as ``render_selected_overlay`` -- an
        armed handler that's tracking this object's own now-gone
        transform has nothing valid to render relative to.
        """
        if self._active_handler is None:
            return

        if (
            self._vbo is None or
            self._position is None or
            self._scale is None or
            self._angle is None
        ):
            return

        # Rotation handlers are a single facade shared across all 3
        # views (obj3d/objschematic/objpegboard) -- see RotationRings'
        # own docstring for why (the gizmo has to show correctly in
        # whichever view the user is looking at, not just the one that
        # armed it), so this view's own render() is reached through its
        # own obj3d. Every other _active_handler is already a 3D-only
        # drag handler (DragHandlerBase, see its own render() -- always
        # defined, defaulting to a no-op for drags with nothing to draw)
        # -- called directly, the same instance either way.

        self._active_handler.obj3d.render(shaders)

    @_check_types.do
    def _render_overlay_group(self, shaders: "_shaders.ShaderProgram") -> None:
        """DO NOT remove the ``GL.glDepthMask(GL.GL_FALSE)`` below or draw
        the AABB/OBB/floor-projection calls outside of it -- this method
        and ``canvas_base.py::_render_selected_overlay`` (which controls
        WHEN this whole group runs, relative to the floor) are a matched
        pair; changing either one without the other reintroduces one of
        two bugs this pairing exists to prevent: with a depth write here
        but the group still running after the floor (current call order),
        nothing is broken by writing depth per se, but it's also entirely
        pointless -- there's nothing left downstream in the frame for it
        to protect, so it only adds a way for the AABB/OBB to needlessly
        occlude each other again (see below); with depth writes removed
        from here AND the group moved back to running before the floor
        (undoing the canvas_base.py change), the floor punches straight
        through the boxes again, exactly as before that fix.

        Draw the AABB box, OBB box, and floor projection as one group
        with depth writes disabled, so none of the 3 can hide another of
        the 3 behind it via the depth test -- the AABB always encloses
        the OBB (same object, AABB is just the OBB's own axis-aligned
        bound), so with both debug toggles on and normal depth writes,
        drawing the AABB first would leave its nearer front face's depth
        in the buffer and the OBB drawn right after would fail the depth
        test against it everywhere the two overlap, making the OBB
        disappear entirely rather than show through the AABB's own
        translucent fill.

        Depth TESTING stays on (each of the 3 is still correctly hidden
        behind any genuine geometry actually in front of it), only
        writing is off. This used to also need a second, color-masked
        pass to write depth anyway, for the floor's sake -- see
        ``canvas_base.py::_render_selected_overlay``'s own docstring for
        why that's no longer necessary now that the overlay is the very
        last thing drawn each frame, after the floor, instead of before
        it: with nothing left to draw afterward, there's nothing left
        that needs this group's depth written for it to respect.

        Called both from ``render_selected_overlay`` itself (this
        object's own current transform) and from ``Wire``/``Bundle``'s
        own ``_render_waypoint_layouts`` (each waypoint's temporarily
        swapped-in sphere transform) -- either way it just draws whatever
        ``render_aabb_overlay``/``render_obb_overlay``/
        ``render_floor_projection`` would currently produce for ``self``.
        """
        GL.glDepthMask(GL.GL_FALSE)
        try:
            self.render_aabb_overlay(shaders)
            self.render_obb_overlay(shaders)
            self.render_floor_projection(shaders)
        finally:
            GL.glDepthMask(GL.GL_TRUE)

    @_check_types.do
    def render_aabb_overlay(self, shaders: "_shaders.ShaderProgram") -> None:
        """Draw a translucent AABB box for this object's current
        ``self._vbo``/``self._position``/``self._angle``/``self._scale``
        -- no-op unless ``_debug_config.draw_aabb`` is set.

        Computed fresh every call (re-fit to a true world-space
        axis-aligned box from all 8 rotated/scaled/translated local
        corners) rather than read back from the cached ``self.aabb``
        property -- that only refreshes via the Point/Angle callback
        system (``_update_position``/``_update_angle``/``_update_scale``),
        which a per-segment position swap (Wire/Bundle's own ``render()``
        loop, a bare reassignment rather than a bound-Point mutation) never
        triggers, so the cached value would otherwise go stale mid-loop.
        """
        if not _debug_config.draw_aabb:
            return

        if not self.is_visible:
            return

        if (
            self._vbo is None or
            self._position is None or
            self._angle is None or
            self._scale is None
        ):
            return

        local_min, local_max = self._vbo.local_aabb
        local_center = (local_min + local_max) / 2.0
        local_extents = local_max - local_min
        scale_np = self._scale.as_numpy

        half = local_extents / 2.0
        local_corners = local_center + np.array([
            [sx * half[0], sy * half[1], sz * half[2]]
            for sx in (-1.0, 1.0) for sy in (-1.0, 1.0) for sz in (-1.0, 1.0)
        ], dtype=np.float32)

        world_corners = (local_corners * scale_np) @ self._angle + self._position.as_numpy
        aabb = _utils.adjust_aabb(world_corners)

        center = _point.Point(*[float(v) for v in ((aabb[0] + aabb[1]) / 2.0).tolist()])
        extents = _point.Point(*[float(v) for v in (aabb[1] - aabb[0]).tolist()])
        self._render_debug_box(shaders, center, _angle.Angle(), extents, _debug_config.aabb_color)

    @_check_types.do
    def render_obb_overlay(self, shaders: "_shaders.ShaderProgram") -> None:
        """Draw a translucent OBB box for this object's current
        ``self._vbo``/``self._position``/``self._angle``/``self._scale``
        -- no-op unless ``_debug_config.draw_obb`` is set.
        """
        if not _debug_config.draw_obb:
            return

        if not self.is_visible:
            return

        if (
            self._vbo is None or
            self._position is None or
            self._angle is None or
            self._scale is None
        ):
            return

        local_min, local_max = self._vbo.local_aabb
        local_center = (local_min + local_max) / 2.0
        local_extents = local_max - local_min
        scale_np = self._scale.as_numpy

        center_np = (local_center * scale_np) @ self._angle + self._position.as_numpy
        center = _point.Point(*[float(v) for v in center_np.tolist()])
        extents = _point.Point(*[float(v) for v in (local_extents * scale_np).tolist()])

        self._render_debug_box(shaders, center, self._angle, extents, _debug_config.obb_color)

    # Index pairs (into _debug_box_corners' 8-corner array) forming the
    # box's 12 real edges -- corner i and corner i^bit differ in exactly
    # one axis for bit in (1, 2, 4), which is exactly an edge of a cube;
    # the "j > i" filter keeps each of the 12 edges once instead of twice.
    _BOX_EDGE_INDICES = [
        (i, i ^ bit) for i in range(8) for bit in (1, 2, 4) if (i ^ bit) > i]

    @staticmethod
    @_check_types.do
    def _debug_box_corners(position: _point.Point, angle: "_angle.Angle", scale: _point.Point) -> np.ndarray:
        """Return the box's 8 world-space corners.

        *scale* is the box's full (not half) size along each local axis,
        matching what ``_render_debug_box``'s own caller already passes to
        ``box_vbo.render`` -- ``shapes/box.py``'s unit box spans -0.5..0.5
        locally, so half of *scale* is the local corner offset.
        """
        half = scale.as_numpy / 2.0
        local_corners = np.array([
            [sx * half[0], sy * half[1], sz * half[2]]
            for sx in (-1.0, 1.0) for sy in (-1.0, 1.0) for sz in (-1.0, 1.0)
        ], dtype=np.float32)

        return local_corners @ angle + position.as_numpy

    @_check_types.do
    def _render_debug_box(self, shaders: "_shaders.ShaderProgram", position: _point.Point,
                          angle: "_angle.Angle", scale: _point.Point, color) -> None:

        material = _materials.Generic(_color.Color(*color))
        box_vbo = _box.create_vbo()

        # Depth mask is deliberately left alone here (whatever the caller
        # already has active) rather than forced off -- this geometry
        # needs to write depth normally like any other solid mesh so that
        # anything drawn afterward in the same frame (the floor, in
        # particular) correctly tests against it and doesn't draw straight
        # through the parts of the box that extend past the selected
        # object's own real surface. The one context where writing this
        # box's depth would be wrong -- canvas_base.py's selected-object
        # supplemental depth-only pass, which exists specifically to
        # (re)establish the real mesh's own depth and would have that
        # undone by this enclosing box's nearer depth winning instead --
        # is handled at the source in canvas_base.py's own _draw_scene,
        # by skipping this whole overlay for that one call rather than by
        # this method guessing its caller's intent from GL state.
        with shaders.faces:
            material.set(shaders.faces)
            # smooth=False -> face (flat) normals (see gl/vbo.py's own
            # render(), which maps smooth -> normalMode as
            # int(not smooth) -- normalMode=0 is smooth, anything else
            # is face). A box needs its 6 faces sharply distinct, not
            # blended across edges the way the segment/waypoint
            # geometry drawn just before it in the same frame might
            # have left normalMode set for (whatever self.smooth was
            # for that real geometry) -- always pass this explicitly,
            # every call, rather than assuming state.
            box_vbo.render(shaders.faces, position, angle, scale, False)

        self._render_debug_box_edges(shaders, position, angle, scale, color)

    @_check_types.do
    def _render_debug_box_edges(self, shaders: "_shaders.ShaderProgram", position: _point.Point,
                                angle: "_angle.Angle", scale: _point.Point, color) -> None:
        
        """Trace the box's real 12 edges (plus a sphere at each of its 8
        corners) on top of the translucent fill -- a thin cylinder run
        corner-to-corner along each edge, using the box's own known
        corner points directly, with a matching sphere at each corner to
        cleanly join the cylinders where 3 edges meet rather than leaving
        a gap or a hard-edged cylinder cap showing. Both render with
        ``smooth=True`` -- rounded cylinders/spheres read cleanly at this
        thinness, unlike a triangulated wireframe-box mesh, which would
        need flat shading and would draw each face's diagonal along with
        its edges (2 triangles per face, no way to suppress just the
        diagonal).
        """
        edge_color = self._debug_box_edge_color(color)
        edge_material = _materials.Generic(_color.Color(*edge_color))
        diameter = _debug_config.box_edge_diameter
        edge_scale = _point.Point(diameter, diameter, diameter)

        corners = self._debug_box_corners(position, angle, scale)

        cylinder_vbo = _cylinder.create_vbo()
        sphere_vbo = _sphere.create_vbo()

        with shaders.faces:
            edge_material.set(shaders.faces)

            for i, j in self._BOX_EDGE_INDICES:
                start = corners[i]
                end = corners[j]
                delta = end - start

                length = float(np.linalg.norm(delta))
                if length < 1e-6:
                    continue

                direction = delta / length
                edge_angle = _angle.Angle.from_direction(direction)
                edge_position = _point.Point(*[float(v) for v in start.tolist()])
                cylinder_scale = _point.Point(diameter, diameter, length)

                cylinder_vbo.render(shaders.faces, edge_position, edge_angle, cylinder_scale, True)

            for corner in corners:
                corner_position = _point.Point(*[float(v) for v in corner.tolist()])
                sphere_vbo.render(shaders.faces, corner_position, _angle.Angle(), edge_scale, True)

    @staticmethod
    @_check_types.do
    def _debug_box_edge_color(color) -> list:
        """Derive a more-opaque, lighter-or-darker edge color from *color*
        (a debug box's own translucent fill) -- lighten a dark fill,
        darken a light one, so the edges read clearly against the fill
        either way, using the same perceived-luminance formula
        BaseVar.render()'s own debug edges pass already uses to pick
        light-vs-dark.
        """
        r, g, b, a = color
        luminance = 0.299 * r + 0.587 * g + 0.114 * b

        shift = 0.35
        if luminance < 0.5:
            r += (1.0 - r) * shift
            g += (1.0 - g) * shift
            b += (1.0 - b) * shift
        else:
            r *= 1.0 - shift
            g *= 1.0 - shift
            b *= 1.0 - shift

        return [r, g, b, min(a + 0.4, 1.0)]

    @_check_types.do
    def render_floor_projection(self, shaders: "_shaders.ShaderProgram") -> None:
        """Draw an outline of the OBB's footprint (for this object's
        current ``self._vbo``/``self._position``/``self._angle``/
        ``self._scale``) flattened onto the floor.

        Unlike the AABB/OBB boxes, this is not a debug toggle -- it always
        renders for the selected object (3D view only; nothing calls this
        from the schematic/pegboard object hierarchies).

        The OBB's own bottom-face corners (local Y = ``local_min[1]``) are
        transformed into world space here (carrying the real rotation/tilt
        with them), so flattening just their Y to floor height gives the
        true footprint as seen from directly above -- not merely an
        axis-aligned footprint. Rather than 4 separate draw calls (one thin
        box per edge), this uses the cached unit
        ``shapes/square_outline.py`` frame mesh -- one draw call, scaled
        non-uniformly to (footprint length, floor thickness, footprint
        width) and rotated to the footprint's own heading.
        """
        if not self.is_visible:
            return

        if (
            self._vbo is None or
            self._position is None or
            self._angle is None or
            self._scale is None
        ):
            return

        local_min, local_max = self._vbo.local_aabb
        x1, _y1, z1 = local_min
        x2, _y2, z2 = local_max
        scale_np = self._scale.as_numpy

        local_bottom = np.array([[x1, local_min[1], z1],
                                 [x2, local_min[1], z1],
                                 [x1, local_min[1], z2],
                                 [x2, local_min[1], z2]], dtype=np.float32)

        world_bottom = (local_bottom * scale_np) @ self._angle + self._position.as_numpy

        floor_y = Config.floor.ground_height + 0.01  # avoid z-fighting with the floor mesh
        p0 = _point.Point(float(world_bottom[0][0]), floor_y, float(world_bottom[0][2]))
        p1 = _point.Point(float(world_bottom[1][0]), floor_y, float(world_bottom[1][2]))
        p4 = _point.Point(float(world_bottom[2][0]), floor_y, float(world_bottom[2][2]))
        p5 = _point.Point(float(world_bottom[3][0]), floor_y, float(world_bottom[3][2]))

        center = (p0 + p5) * 0.5
        length = float(np.linalg.norm((p1 - p0).as_numpy))
        width = float(np.linalg.norm((p4 - p0).as_numpy))
        heading = _angle.Angle.from_points(p0, p1)

        outline_vbo = _square_outline.create_vbo()
        material = _materials.Generic(_color.Color(*_debug_config.floor_projection_color))
        outline_scale = _point.Point(width, 0.012, length)

        # Depth mask deliberately left alone (see _render_debug_box's own
        # comment on this) -- this outline sits just 0.01 above the floor
        # mesh itself, so it particularly needs to write its own (nearer)
        # depth normally: the floor renders after every object in the
        # frame (canvas_base.py's own _draw_scene -> _render_floor_after
        # ordering), and without a depth write here the floor's opaque
        # pass would have nothing of this outline's to test against and
        # would draw straight over it.
        with shaders.faces:
            material.set(shaders.faces)
            # smooth=False -> face (flat) normals -- see
            # _render_debug_box's own comment for the normalMode mapping.
            outline_vbo.render(shaders.faces, center, heading, outline_scale, False)
