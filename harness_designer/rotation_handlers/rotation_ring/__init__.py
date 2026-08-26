# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Assembles one axis's :class:`~.torus_ring.TorusRing` +
:class:`~.inner_ring.InnerRing` + :class:`~.outer_ring.OuterRing` into a
single :class:`RotationRing`, and owns the show/hide/pickability state
machine between them.

Initial state: only the torus ring is visible and pickable (the
"always-on" activation ring for this axis). Clicking it (see
:meth:`RotationRing.try_activate`) shows this axis's protractor (inner
+ outer rings) and dims/depickables the torus; the sibling axes' torus
rings get dimmed too, via :meth:`RotationRing.set_dimmed` -- called by
whatever owns all three instances (``rotation_handlers/rotation_rings.py``)
since dimming a sibling is inherently a cross-axis decision this class
can't make on its own.
"""

from typing import TYPE_CHECKING

from .torus_ring import TorusRing
from .inner_ring import InnerRing
from .outer_ring import OuterRing
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl import materials as _materials
from .. import rotation_mesh as _rotation_mesh
from ... import color as _color
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ... import ui as _ui
    from ...objects.objectsvar import base_var as _base_var
    from ...gl.canvas_base import camera_base as _camera_base
    from ...gl import shaders as _shaders


# Torus opacity while a sibling axis's protractor is active -- "the
# other 2 rings would becomes more transparent."
_DIMMED_ALPHA = 0.25
_NORMAL_ALPHA = 1.0


class RotationRing:
    """One axis's full protractor gizmo (torus + inner + outer rings).

    Radial layout, object outward to screen edge::

        object -> gap -> INNER protractor band -> torus ring -> OUTER protractor band

    The inner protractor is the "free rotate" ring: it spins with the
    object (see :class:`.inner_ring.InnerRing`), its ID sits just outside
    the object's own corner-to-corner reach, and its OD meets the torus
    ring exactly -- so the torus (the always-on, click-to-activate ring)
    sits right on the seam between the two protractors, not radially
    between two separate thin bands the way an earlier version of this
    gizmo had it. The outer protractor is fixed to world space (see
    :class:`.outer_ring.OuterRing`): its ID meets the torus from the
    other side, its OD is set so its own band width matches the inner
    protractor's exactly, and its ticks are what you click to snap the
    inner protractor's (the object's) angle to an exact value. Both
    protractors' ``0`` ticks line up whenever the object's own Euler
    value for this axis is ``0`` -- the outer ring never moves, so that
    alignment is also where "the torus ring, at rest" visually sits.

    :param axis: ``'x'``, ``'y'`` or ``'z'``.
    :param center: World-space center -- shared with the tracked
        object's position (not copied), same as every other piece of
        this gizmo.
    :param obj_angle: The tracked object's own :class:`Angle` (shared
        reference) -- every sub-ring reads this directly rather than
        keeping its own synced copy.
    :param radius: Torus ring radius -- already includes whatever
        clearance ``Config.rotation_handler.diameter_scale`` adds beyond
        the object (see :meth:`~..generic.Rings3D._compute_size`).
    :param object_radius: The tracked object's own raw corner-to-corner
        reach (radius, i.e. half the full diagonal) -- *not*
        clearance-scaled -- used only to size the inner protractor's ID.
    :param tube_diameter_scale: Torus tube thickness, as a fraction of
        *radius* -- ``Config.rotation_handler.tube_diameter_scale``.
    :param color: Base RGB for this axis (muted, not the old gizmo's
        saturated primaries -- see the docstring on
        ``rotation_handlers/rotation_rings.py`` for the config knobs).
    :param label_size: Font size for tick numbers.
    :param mainframe: Passed straight through to every outer-ring tick's
        :class:`.tick_pick_object.TickPickObject` -- see that module's
        docstring for why it's never actually registered with it.
    :param base_cls: Whichever of ``Base3D``/``BaseSchematic``/
        ``BasePegboard`` matches the view this ring belongs to -- see
        :class:`.outer_ring.OuterRing`'s own docstring.
    """

    # How far outside the object's own corner-to-corner reach the inner
    # protractor's ID sits, as a multiple of that reach. Needs enough
    # clearance for more than just avoiding the object visually -- the
    # inner protractor's own tick labels render just inside this ID (see
    # ProtractorRingBase's labels_outward=False), so this gap has to fit
    # real label text, not just a hairline. Only takes effect if
    # Config.rotation_handler.diameter_scale gives the torus enough of
    # its own headroom above this margin -- otherwise _MIN_BAND_WIDTH_SCALE
    # clamps the band down regardless (see _compute_radii).
    _INNER_ID_MARGIN = 1.25

    # Floor for the protractor band width, as a fraction of the torus
    # radius -- guards against a degenerate (zero/negative) band if
    # config ever puts the object's margin-padded reach at or beyond the
    # torus radius (e.g. diameter_scale set too small).
    _MIN_BAND_WIDTH_SCALE = 0.05

    # Kept smaller than ProtractorRingBase._TICK_DIAMETER_FRAC (as a
    # fraction of the same, roughly comparable torus/outer_radius
    # reference) so the washer's own flat faces never fully enclose the
    # tick cylinders -- a tick only reads as a visible raised mark if it
    # pokes out past the washer's own thickness on both sides.
    _PROTRACTOR_DEPTH_SCALE = 0.003

    @_check_types.do
    def __init__(self, axis: str, center: _point.Point,
                obj_angle: _angle.Angle, radius: float, object_radius: float,
                tube_diameter_scale: float, color: "_color.Color",
                outer_color: "_color.Color", label_size: float, context,
                mainframe: "_ui.MainFrame", base_cls: "type[_base_var.BaseVar]", camera=None):

        self.axis = axis
        self.center = center
        self.obj_angle = obj_angle
        self.radius = radius
        self.object_radius = object_radius
        self._tube_diameter_scale = tube_diameter_scale
        self._context = context
        self._camera = camera
        self._label_size = label_size
        self._mainframe = mainframe
        self._base_cls = base_cls

        self.is_active = False
        self._dimmed = False

        cr, cg, cb = color.rgb
        torus_material = _materials.Plastic(color)

        # Inner protractor matches this axis's own ring color (it IS this
        # axis, dragged directly); the outer protractor is deliberately a
        # separate, neutral color (see outer_color) so it never reads as
        # "belonging to" any one axis -- it's the world-fixed snap ring.
        self._inner_material = _materials.Glowing(_color.Color(cr, cg, cb, 40))

        ocr, ocg, ocb = outer_color.rgb
        self._outer_material = _materials.Glowing(_color.Color(ocr, ocg, ocb, 40))

        torus_angle = _rotation_mesh.slot_ring_angle(axis, obj_angle.as_euler_float)
        self.torus = TorusRing(
            center, torus_angle, radius, tube_diameter_scale, torus_material, context)

        # Every protractor position/offset this axis will ever need is
        # derived here, up front, from the same (radius, object_radius)
        # the torus above was just built from -- the tracked object's
        # size cannot change while these rings are being shown (nothing
        # resizes an object mid-rotation), so there is no reason to defer
        # this math to activation time the way building the actual
        # InnerRing/OuterRing GL objects still is (see below).
        (self._inner_id, self._inner_od,
         self._outer_id, self._outer_od) = self._compute_radii(radius, object_radius, tube_diameter_scale)
        self._protractor_depth = radius * self._PROTRACTOR_DEPTH_SCALE

        # The protractor (inner + outer rings, each owning its own
        # per-axis disc-ring VBO -- see _protractor_base.py) is only
        # ever needed once this axis is actually activated, which for
        # any given right-click-to-rotate happens on at most one axis in
        # one view -- built lazily in _ensure_protractor (called from
        # activate()) instead of unconditionally here, so arming the
        # gizmo across all 3 views doesn't pay for up to 3x2 (3D) + 1x2
        # (schematic) + 1x2 (pegboard) = 10 protractor rings nobody may
        # ever look at. Only the GL objects themselves are deferred --
        # the sizes/offsets above are already known.
        self.inner: "InnerRing | None" = None
        self.outer: "OuterRing | None" = None

    @_check_types.do
    def _ensure_protractor(self) -> None:
        """Build :attr:`inner`/:attr:`outer` on first use, from the
        positions/offsets already computed in :meth:`__init__` -- a
        no-op on every activation after the first.
        """
        if self.inner is not None:
            return

        self.inner = InnerRing(
            self.axis, self.center, self._inner_id, self._inner_od, self._protractor_depth,
            self._inner_material, self._label_size, self.obj_angle, self._context, self._camera)

        self.outer = OuterRing(
            self.axis, self.center, self._outer_id, self._outer_od, self._protractor_depth,
            self._outer_material, self._label_size, self.obj_angle, self._context,
            self._mainframe, self._base_cls, self._camera)

    # Gap between the torus ring and the OUTER protractor, as a multiple
    # of the torus *tube's* own diameter (its cross-section -- radius *
    # tube_diameter_scale -- not the major circle it sweeps around the
    # object) -- keeps the outer protractor visibly clear of the torus
    # now that the torus itself stays visible while a protractor is
    # shown (see RotationRing.activate()). The inner protractor's own
    # position is left alone -- only the outer one gets pushed out.
    _OUTER_GAP_SCALE = 1.0

    @classmethod
    @_check_types.do
    def _compute_radii(cls, radius: float, object_radius: float,
                       tube_diameter_scale: float) -> tuple[float, float, float, float]:
        """Derive (inner_id, inner_od, outer_id, outer_od) from the torus
        radius and the object's own raw corner-to-corner reach -- see
        this class's own docstring for the radial layout these implement.

        The torus ring has real thickness of its own (a round tube, not
        an infinitely-thin line) -- ``tube_diameter_scale * radius`` is
        its full diameter (see :class:`.torus_ring.TorusRing`), so each
        protractor's near edge is pulled back from the bare centerline
        *radius* by the tube's own half-thickness, on whichever side that
        protractor sits, so neither one intersects the torus at all.
        """
        tube_radius = radius * tube_diameter_scale / 2.0

        inner_od = radius - tube_radius
        inner_id = object_radius * cls._INNER_ID_MARGIN

        band_width = inner_od - inner_id
        min_band_width = radius * cls._MIN_BAND_WIDTH_SCALE
        if band_width < min_band_width:
            band_width = min_band_width
            inner_id = inner_od - band_width

        # See _OUTER_GAP_SCALE above -- tube diameter (its cross-section),
        # not the major-circle diameter.
        tube_diameter = radius * tube_diameter_scale
        outer_gap = cls._OUTER_GAP_SCALE * tube_diameter

        outer_id = radius + tube_radius + outer_gap
        outer_od = outer_id + band_width

        return inner_id, inner_od, outer_id, outer_od

    @_check_types.do
    def on_object_angle_changed(self) -> None:
        """Refresh every sub-ring's orientation -- call whenever
        ``obj_angle``'s callback fires. Runs for all three axes'
        instances regardless of which is active, since the gyroscope
        nesting means any axis's change can move any ring's plane.
        """
        self.torus.angle = _rotation_mesh.slot_ring_angle(
            self.axis, self.obj_angle.as_euler_float)

        if self.inner is not None:
            self.inner.on_object_angle_changed()
            self.outer.on_object_angle_changed()

    @_check_types.do
    def on_object_scale_changed(self, radius: float, object_radius: float) -> None:
        """Resize when the tracked object's scale changes -- the caller
        (the owning ``RotationRings3D``-equivalent) recomputes *radius*/
        *object_radius* the same way ``Rings3D._compute_size`` always
        did; this method just re-derives everything downstream of it.
        """
        self.radius = radius
        self.object_radius = object_radius

        self.torus.radius = radius

        (self._inner_id, self._inner_od,
         self._outer_id, self._outer_od) = self._compute_radii(radius, object_radius, self._tube_diameter_scale)
        self._protractor_depth = radius * self._PROTRACTOR_DEPTH_SCALE

        if self.inner is None:
            # Not yet activated -- _ensure_protractor will build from the
            # freshly-cached values above whenever this axis's protractor
            # eventually gets built, so there's nothing further to do here.
            return

        self.inner.set_radii(self._inner_id, self._inner_od, self._protractor_depth, self._context)
        self.outer.set_radii(self._outer_id, self._outer_od, self._protractor_depth, self._context)

        if self.is_active:
            self.inner.reposition_all(self.inner._disc_rotation())  # NOQA
            self.outer.reposition_all(self.outer._disc_rotation())  # NOQA

    @_check_types.do
    def set_dimmed(self, flag: bool) -> None:
        """Dim/undim this axis's torus ring -- called on the two axes
        that are NOT the one just activated.

        A dimmed torus stays pickable -- clicking it is exactly how the
        gizmo switches directly to that axis's own protractor (see
        ``Rings3D.activate``'s own re-entrant handling and
        ``_handle_rotation_interaction``'s LEFT_DOWN branch) -- only the
        currently ACTIVE axis's own torus is excluded, since its
        protractor bands take over the click surface while it's shown.
        """
        self._dimmed = flag
        self.torus.material.diffuse[3] = _DIMMED_ALPHA if flag else _NORMAL_ALPHA
        self.torus.is_pickable = not self.is_active

    @_check_types.do
    def activate(self) -> None:
        """Show this axis's protractor (the torus itself stays visible --
        it's still the seam the two protractor bands meet at) and stop
        the torus from being pickable (dragging now happens on the
        protractor bands instead).
        """
        self._ensure_protractor()

        self.is_active = True
        self.torus.is_pickable = False
        self.inner.is_visible = True
        self.outer.is_visible = True
        self.inner.reposition_all(self.inner._disc_rotation())  # NOQA
        self.outer.reposition_all(self.outer._disc_rotation())  # NOQA

    @_check_types.do
    def deactivate(self) -> None:
        """Hide this axis's protractor and restore normal torus
        visibility/picking."""
        self.is_active = False
        self.torus.is_visible = True
        self.torus.is_pickable = not self._dimmed

        if self.inner is None:
            return

        self.inner.is_visible = False
        self.outer.is_visible = False
        self.inner.end_drag()
        self.outer.clear_hover()

    @_check_types.do
    def hit_test_torus(self, mouse_pos: _point.Point,
                       camera: "_camera_base.CameraBase") -> bool:
        return self.torus.hit_test(mouse_pos, camera)

    @_check_types.do
    def hit_test_inner(self, mouse_pos: _point.Point,
                       camera: "_camera_base.CameraBase") -> bool:
        return self.is_active and self.inner.hit_test(mouse_pos, camera)

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram") -> None:
        self.torus.render(shaders)

        if self.is_active:
            self.inner.render(shaders)
            self.outer.render(shaders)

    @_check_types.do
    def delete(self, context) -> None:
        self.torus.delete(context)

        if self.inner is not None:
            self.inner.delete(context)
            self.outer.delete(context)
