# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared disc + tick-marks + numeric-label construction/rendering for
:mod:`.inner_ring`/:mod:`.outer_ring`.

Each protractor is a flat washer (:mod:`~harness_designer.shapes.disc_ring`)
spanning an explicit inner radius (ID) to outer radius (OD) -- not a thin
band at a single nominal radius -- with a ring of radial tick marks
(:mod:`~harness_designer.shapes.cylinder`) hanging inward from the OD: a
short one every degree, a longer one with a numeric
:class:`~harness_designer.shapes.text.Text` label every 10 degrees. A
cylinder needs only one radius/length pair (vs. a box's three independent
scale components) and, being rotationally symmetric about its own length
axis, has no front/back face to worry about -- unlike the flat text
label, which does, but which never needs a front/back flip at all: each
major tick's own label keeps a live camera-facing billboard angle instead
(see :meth:`ProtractorRingBase._update_label_angles`, computed directly
against ``shapes.text``'s own free ``_billboard_matrices`` function --
not through that module's shared ``_CameraTrackingArena``, which exists
for OBB/AABB-tracked owners like notes; a protractor label has neither),
always turned to face the camera directly rather than sitting at a fixed
orientation that would need flipping depending on viewing side. What
differs between the two
protractor rings (whether the angle tracks the selected object or stays
fixed, and what a click/hover/drag on the ring actually does) is left
entirely to the two subclasses -- this class only builds and draws the
shared geometry.
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
from ...gl import vbo as _vbo_handler
from ... import utils as _utils
from ... import check_types as _check_types
from .. import rotation_mesh as _rotation_mesh
from ... import color as _color


if TYPE_CHECKING:
    from ...gl import shaders as _shaders
    from ...gl.canvas_base import camera_base as _camera_base


# One minor (unlabeled) tick every degree; every 10th is a longer, labeled
# major tick -- 360 total, 36 of them major.
TICK_STEP_DEGREES = 1.0
MAJOR_TICK_STEP_DEGREES = 10.0
TICK_COUNT = int(360.0 / TICK_STEP_DEGREES)
_MAX_TRACKED_LABELS = int(360.0 / MAJOR_TICK_STEP_DEGREES)

# Shared, pre-allocated once at import time and reused by whichever
# protractor ring's own reposition_all()/camera-move callback is
# currently running (see ProtractorRingBase._update_label_angles) --
# safe because only a single axis's ring pair is ever visible at a time
# (RotationRing._ensure_protractor's own docstring: other axes stay
# built but hidden), and this all runs synchronously on the Qt UI
# thread, never concurrently, so there's no risk of two calls racing
# over the same buffer. Sized for exactly one ring's own major-tick
# count -- inner and outer are never updated in the same call, so this
# never needs to hold both at once.
_label_positions_scratch = np.zeros((_MAX_TRACKED_LABELS, 3), dtype=np.float64)

# Fixed tick color -- deliberately independent of the washer's own
# (axis- or outer-tinted) material so the ticks always read clearly
# against it, regardless of which ring or axis this is.
_TICK_COLOR = (0.0, 0.0, 0.0)


class _Tick:
    """One tick mark (+ numeric label, major ticks only).

    Holds only genuinely per-tick state -- ``degrees``/``is_major`` are
    fixed for its whole lifetime; ``tick_len`` is fixed for as long as
    the ring's ID/OD/label size don't change; ``position``/
    ``mesh_rotation``/``label_position`` are the only dynamic fields,
    refreshed every :meth:`~ProtractorRingBase.reposition_all` call.

    Its LOCAL geometry (the fixed, pre-``ring_angle`` direction and
    offset vectors :meth:`~ProtractorRingBase._recompute_local_geometry`
    derives) deliberately does NOT live here -- see that method's own
    docstring for why it's kept as bulk arrays on
    :class:`ProtractorRingBase` instead of per-tick attributes: rotating
    all :data:`TICK_COUNT` (360) of them through the ring's current
    orientation happens on every angle change (continuously, during a
    free-rotation drag), and one batched matrix multiply over a whole
    array is far cheaper than 360 individual ones.

    The label's own rotation is a live camera-facing billboard, kept
    live directly by :meth:`ProtractorRingBase._update_label_angles`
    (writing straight into this tick's own ``label._tracking_angle``)
    rather than recomputed by this class itself --
    ``ProtractorRingBase.render()`` just asks the label's own
    ``render_angle()`` for whichever angle to actually draw with.
    """

    __slots__ = (
        'degrees', 'is_major', 'tick_len', 'scale',
        'position', 'mesh_rotation', 'label', 'label_position')

    def __init__(self, degrees: float, is_major: bool, label: "_text.Text | None"):
        self.degrees = degrees
        self.is_major = is_major
        self.tick_len = 0.0

        # Cached alongside tick_len in _recompute_local_geometry -- like
        # tick_len, this depends only on the ring's radii/tick-diameter
        # fraction, never on ring_angle, so render() would otherwise be
        # rebuilding an identical Point every one of TICK_COUNT (360)
        # ticks on every single frame regardless of whether anything is
        # actually rotating.
        self.scale = _point.Point(0.0, 0.0, 0.0)

        self.position = _point.Point(0.0, 0.0, 0.0)
        self.mesh_rotation = _angle.Angle.from_euler(0.0, 0.0, 0.0)
        self.label = label
        self.label_position = self.position


class ProtractorRingBase:
    """Shared washer + ticks + labels for one axis's protractor display.

    :param center: World-space center -- shared reference (not copied),
        same as every other piece of this gizmo.
    :param inner_radius: Washer/tick-band inner radius (ID).
    :param outer_radius: Washer/tick-band outer radius (OD). Tick marks
        hang inward from this edge.
    :param depth: World-space thickness along the ring's normal axis.
    :param material: Material the translucent washer renders with.
    :param label_size: Font size passed to each major tick's :class:`Text`.
    :param labels_outward: Which side of this washer has open space for
        labels to sit in, clear of the disc's own face -- ``True`` places
        them just beyond the OD, ``False`` just inside the ID. The torus
        ring sits exactly at the inner protractor's OD / outer
        protractor's ID (see :mod:`~.rotation_ring`'s own docstring), so
        :class:`.inner_ring.InnerRing` passes ``False`` (the object-ward
        side, at its ID, is the only side clear of the torus) and
        :class:`.outer_ring.OuterRing` passes ``True`` (the outward side,
        at its OD, is the only side clear of the torus).
    """

    # Tick length, as a fraction of the band width (outer_radius -
    # inner_radius) -- major (10-degree, labeled) ticks reach 3/4 of the
    # way across the band, minor (1-degree) ones half way, both anchored
    # at the same edge labels_outward points away from (see reposition_all).
    _MAJOR_TICK_LENGTH_FRAC = 0.75
    _MINOR_TICK_LENGTH_FRAC = 0.5
    _TICK_DIAMETER_FRAC = 0.006  # tick diameter, as a fraction of outer_radius
    _LABEL_GAP_FRAC = 0.12       # label standoff beyond the washer's own free edge, as a fraction of band width

    @_check_types.do
    def __init__(self, axis: str, center: _point.Point, inner_radius: float, outer_radius: float,
                depth: float, material: _materials.GLMaterial, label_size: float, context,
                camera: "_camera_base.CameraBase" = None, labels_outward: bool = True):

        self.axis = axis
        self.center = center
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius
        self._labels_outward = labels_outward
        self.depth = depth
        self.material = material
        self.is_visible = False
        self._camera = camera
        self._label_size = label_size

        self._tick_vbo = _cylinder.create_vbo()

        # Set by reposition_all -- lets it skip its own (otherwise
        # unconditional) work when the ring's orientation hasn't
        # actually changed since last time. Genuinely common: the
        # gyroscope nesting (see rotation_mesh.py) means most rings
        # DON'T move on most angle changes -- e.g. dragging one axis's
        # inner ring changes that axis's own value only, which leaves
        # every other built ring (any axis previously activated stays
        # built -- see RotationRing._ensure_protractor) computing the
        # exact same ring_angle it already had, every single frame of
        # that drag, for no visible effect.
        self._last_ring_angle_quat: np.ndarray | None = None

        self._ticks: list[_Tick] = []

        # Bulk, vectorized per-tick LOCAL geometry -- row i corresponds
        # to self._ticks[i]. Lives here (not per-tick attributes) purely
        # for speed -- see _recompute_local_geometry's and
        # reposition_all's own docstrings for why batching a single
        # matrix multiply over all TICK_COUNT (360) rows matters (this
        # runs on every angle change, continuously during a
        # free-rotation drag).
        self._local_radials = np.zeros((TICK_COUNT, 3), dtype=np.float32)
        self._is_major_mask = np.zeros(TICK_COUNT, dtype=bool)
        self._local_offsets = np.zeros((TICK_COUNT, 3), dtype=np.float32)
        self._label_local_offsets = np.zeros((TICK_COUNT, 3), dtype=np.float32)
        self._tick_lens = np.zeros(TICK_COUNT, dtype=np.float32)

        self._label_material = _materials.Polished(_color.Color(*self._get_label_color()))

        with context:
            self._disc_vbo = self._build_disc_vbo(inner_radius, outer_radius, depth)
            self._disc_vbo.acquire()

            for i in range(TICK_COUNT):
                degrees = i * TICK_STEP_DEGREES
                theta = math.radians(degrees)
                is_major = (degrees % MAJOR_TICK_STEP_DEGREES) == 0.0

                # Fixed for this tick's whole lifetime -- its angular slot
                # around the ring never changes, only the ring's own world
                # orientation does (see reposition_all).
                self._local_radials[i] = (math.cos(theta), math.sin(theta), 0.0)
                self._is_major_mask[i] = is_major

                label = None
                if is_major:
                    # Displayed as -180..180 (matching the toolbar's own
                    # Euler display convention -- see rotation_mesh.
                    # wrap_angle, also what a snapped/dragged value gets
                    # wrapped to before being written back), not the raw
                    # 0..350 this tick's own position is still built
                    # from -- tick.degrees stays the unwrapped value
                    # (angle-to-tick lookups elsewhere assume 0..360).
                    label_degrees = _rotation_mesh.wrap_angle(degrees)
                    label = _text.Text(
                        str(int(round(label_degrees))), label_size, build123d.FontStyle.ITALIC,
                        center_anchor=True)

                self._ticks.append(_Tick(degrees=degrees, is_major=is_major, label=label))

        # Fixed for the ring's whole lifetime (which ticks are major
        # never changes) -- cached once so render()'s label pass doesn't
        # re-filter all 360 ticks every frame.
        self._major_ticks = [t for t in self._ticks if t.label is not None]

        self._recompute_local_geometry()

        # subclasses must call reposition_all() once their own ring
        # angle is established (after their own __init__ finishes), then
        # start_camera_tracking() -- see that method's own docstring for
        # why the ordering matters.

    @staticmethod
    @_check_types.do
    def _build_disc_vbo(inner_radius: float, outer_radius: float,
                       depth: float) -> "_vbo_handler.NonPooledVBOHandler":
        """Build a washer mesh baked directly to these exact real-world
        dimensions -- rendered with scale (1, 1, 1) (see render()), no
        render-time scaling involved at all. Unlike the fixed-ratio mesh
        :func:`~harness_designer.shapes.disc_ring.create_vbo` caches and
        shares globally (which needs a render-time scale to reach
        whatever final size a caller wants), every protractor ring here
        needs its own real ID/OD/depth (the inner protractor spans from
        just outside the object out to the torus ring; the outer spans
        from the torus ring outward by the same band width -- see
        :mod:`~.rotation_ring`'s own docstring for the derivation), so
        this builds a dedicated, non-shared VBO instead (same reasoning
        as :class:`~.torus_ring.TorusRing`'s own per-instance mesh).
        """
        vertices, faces = _disc_ring.create(outer_radius, inner_radius, depth)
        packed, count = _utils.compute_normals(vertices, faces)

        unpacked_verts = packed[:count * 3].reshape(-1, 3)
        aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
        aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
        obb = _utils.compute_obb(aabb1, aabb2)

        return _vbo_handler.NonPooledVBOHandler(packed, count, aabb=aabb, obb=obb)

    @_check_types.do
    def set_radii(self, inner_radius: float, outer_radius: float, depth: float, context) -> None:
        """Update this ring's ID/OD/depth -- called whenever the tracked
        object's size changes (see
        :meth:`~.rotation_ring.RotationRing.on_object_scale_changed`).
        Rebuilds the washer mesh directly to the new dimensions (no
        ratio/scale indirection -- see :meth:`_build_disc_vbo`) whenever
        any of them actually differ from the current mesh.
        """
        if (inner_radius, outer_radius, depth) != (self.inner_radius, self.outer_radius, self.depth):
            with context:
                try:
                    self._disc_vbo.release()
                except Exception:  # NOQA
                    pass

                self._disc_vbo = self._build_disc_vbo(inner_radius, outer_radius, depth)
                self._disc_vbo.acquire()

        self.inner_radius = inner_radius
        self.outer_radius = outer_radius
        self.depth = depth
        self._recompute_local_geometry()

        # A radii change alone (no angle change) still moves every
        # tick's world position/length -- reposition_all's own dirty
        # check only compares ring_angle, so it needs to be told
        # explicitly that the LOCAL geometry just changed underneath it,
        # or it would wrongly skip the next call as a no-op.
        self._last_ring_angle_quat = None

    @_check_types.do
    def delete(self, context) -> None:
        # Not strictly required (Point.bind() only ever holds a
        # WeakMethod, so this callback goes inert on its own once this
        # ring is collected) but explicit is cheap and avoids a stale
        # callback firing spurious work while something else might still
        # be keeping this instance alive a moment longer -- see
        # Point.unbind's own docstring.
        if self._camera is not None:
            self._camera.position.unbind(self._on_camera_moved)

        for tick in self._major_ticks:
            tick.label._tracking_angle = None  # NOQA

        try:
            with context:
                self._disc_vbo.release()
        except Exception:  # NOQA
            # Context may be unavailable during shutdown -- the buffer
            # dies with the context in that case.
            pass

    @_check_types.do
    def _recompute_local_geometry(self) -> None:
        """(Re)derive every tick's fixed LOCAL geometry -- length, and
        the local-space (pre-``ring_angle``) offset vectors for both the
        tick mesh and its label -- from the current ID/OD/label size.

        None of this depends on the ring's current world orientation --
        a tick's size and its position *within the ring's own plane* are
        as fixed as the ring's radii are; only the ring's orientation in
        world space changes (when the tracked object rotates), which
        :meth:`reposition_all` alone accounts for. So this only needs to
        run here and from :meth:`set_radii` (whenever the radii actually
        change), never on every angle-driven reposition.
        """
        band_width = self.outer_radius - self.inner_radius
        major_len = band_width * self._MAJOR_TICK_LENGTH_FRAC
        minor_len = band_width * self._MINOR_TICK_LENGTH_FRAC

        # A label is center-anchored (see the Text(..., center_anchor=True)
        # call above), so its own near edge reaches roughly _label_size/2
        # back toward the ring past its anchor point -- a gap that's only
        # a fraction of the (possibly much smaller) band width isn't
        # enough clearance once the text is actually that size. Take
        # whichever of the two is bigger.
        label_gap = max(band_width * self._LABEL_GAP_FRAC, self._label_size * 1.5)

        # Off the washer's own face entirely, on whichever side is clear
        # of the torus ring (see this class's own __init__ docstring) --
        # never on top of the disc.
        if self._labels_outward:
            label_radius = self.outer_radius + label_gap
        else:
            label_radius = max(self.inner_radius - label_gap, 0.0)

        # Ticks anchor at the same edge the labels sit beyond (see
        # __init__'s own docstring) and grow toward the other edge --
        # every tick's mesh is base-anchored, not centered (see
        # shapes/cylinder.py's own module docstring: local Z=0 is the
        # cylinder's start end, local Z=length is its tip -- kept that
        # way because the wire-preview mesh relies on exactly this
        # convention, only ever changing scale.z/angle from a fixed
        # start point), so the START radius below is this tick's
        # *local offset* directly, not a midpoint. Outer protractor:
        # starts at the ID, grows out toward the OD. Inner protractor:
        # starts at the OD, grows in toward the ID -- same start-radius
        # rule, just the opposite growth direction (see reposition_all's
        # own use of self._labels_outward for that half of it).
        if self._labels_outward:
            start_radius = self.inner_radius
        else:
            start_radius = self.outer_radius

        # Whole-array scalar multiplies -- every tick shares the same
        # start_radius/label_radius, so this is the batched equivalent of
        # the old per-tick ``tick.local_radial * start_radius`` loop.
        self._tick_lens = np.where(
            self._is_major_mask, major_len, minor_len).astype(np.float32)
        self._local_offsets = (self._local_radials * start_radius).astype(np.float32)
        self._label_local_offsets = (self._local_radials * label_radius).astype(np.float32)

        # cylinder's own unit mesh (shapes/cylinder.py) uses scale.x/
        # scale.y as diameter and scale.z as length -- see e.g.
        # Base3D._render_debug_box_edges' own cylinder_scale. Cached
        # here (not per render() call) since it depends only on
        # outer_radius/tick_len, never on ring_angle or the camera --
        # render() would otherwise rebuild an identical Point 360 times
        # every single frame regardless of whether anything is rotating.
        tick_diameter = self.outer_radius * self._TICK_DIAMETER_FRAC

        for i, tick in enumerate(self._ticks):
            tick.tick_len = float(self._tick_lens[i])
            tick.scale = _point.Point(tick_diameter, tick_diameter, tick.tick_len)

    @_check_types.do
    def reposition_all(self, ring_angle: "_angle.Angle") -> bool:
        """Place every tick/label in world space by rotating their
        already-fixed LOCAL geometry (see :meth:`_recompute_local_geometry`)
        through the ring's current *ring_angle* -- the only thing that
        ever changes here is the object's rotation, never a tick's own
        size or its position within the ring's own plane.

        Batched: one 3x3 matrix multiply over all :data:`TICK_COUNT`
        (360) rows at once (``self._local_offsets``/``self._local_radials``/
        ``self._label_local_offsets``), not 360 individual ``Angle``
        rotations -- this runs on every angle change, continuously while
        a free-rotation drag is in progress, so the per-call cost matters
        far more than it would for a one-shot call. The remaining
        per-tick loop below only wraps already-computed rows into the
        ``Point``/``Angle`` objects render() and the outer ring's pick
        objects need -- no further trig or matrix math left to do there.

        Skips everything below (including the matrix multiplies) when
        *ring_angle* is identical to the last call's -- see
        :attr:`_last_ring_angle_quat`'s own docstring for why this is a
        common, not a rare, case.

        :returns: Whether this call actually repositioned anything --
            :class:`.outer_ring.OuterRing` uses this to also skip its own
            pick-object resync when nothing here changed either.
        """
        new_quat = ring_angle.as_quat_numpy
        if (
            self._last_ring_angle_quat is not None and
            np.array_equal(new_quat, self._last_ring_angle_quat)
        ):
            return False

        self._last_ring_angle_quat = new_quat

        center_np = np.array(
            [float(self.center.x), float(self.center.y), float(self.center.z)],
            dtype=np.float64)

        ring_matrix = ring_angle.as_matrix_numpy

        world_offsets = self._local_offsets @ ring_matrix.T
        positions = center_np + world_offsets

        # Cylinder tick: rotationally symmetric about its own length
        # axis, so it only needs that axis (+Z in the unit mesh, see
        # shapes/cylinder.py) pointed along this tick's own growth
        # direction -- no in-plane orientation to get right the way a
        # label needs (labels get their own live camera-facing billboard
        # instead, kept live by shapes.text's own shared tracking system
        # -- not a rotation cached here). The mesh's local Z=0 (its base
        # -- see shapes/cylinder.py's own docstring) sits at
        # tick.position (this tick's start radius, from
        # _recompute_local_geometry), so growth has to point AWAY from
        # center for the outer protractor (ID -> OD) but TOWARD center
        # for the inner one (OD -> ID) -- the opposite of the outward
        # radial direction.
        radial_world = self._local_radials @ ring_matrix.T
        growth_world = radial_world if self._labels_outward else -radial_world

        world_label_offsets = self._label_local_offsets @ ring_matrix.T
        label_positions = center_np + world_label_offsets

        for i, tick in enumerate(self._ticks):
            tick.position = _point.Point(*[float(v) for v in positions[i]])
            tick.mesh_rotation = _angle.Angle.from_direction(growth_world[i])

            if tick.label is not None:
                tick.label_position = _point.Point(*[float(v) for v in label_positions[i]])

        # Every label's own camera-facing angle is computed from its
        # *position*, which every tick's label_position write above just
        # changed -- without this, a label keeps whatever billboard angle
        # it had from the last real camera move, which is now wrong for
        # its new position, and stays wrong until the camera happens to
        # move again (the only other thing that refreshes it). See
        # _update_label_angles's own docstring -- it's the "no camera at
        # all" gate itself, so nothing needed here.
        self._update_label_angles()

        return True

    @_check_types.do
    def start_camera_tracking(self) -> None:
        """Prime every major tick's label with a real (identity) angle,
        bind this ring's own camera-move callback, then immediately
        compute a real angle for each of them -- must be called AFTER
        this ring's own first :meth:`reposition_all` (see each
        subclass's own ``__init__``, where both calls happen back to
        back), not from this class's own ``__init__``: a label's
        tracking position comes from ``tick.label_position``, which only
        holds its real, ring-relative value once ``reposition_all`` has
        actually run -- computing any earlier would track the
        ``_Tick.__init__`` placeholder position (0, 0, 0) instead.

        ``render_angle()`` (see :class:`~harness_designer.shapes.text.Text`)
        falls through to a label's raw, non-tracking angle whenever
        ``_tracking_angle`` is ``None`` -- the priming write here (a real
        identity ``Angle``, not ``None``) must happen before
        :meth:`_update_label_angles` gets its first real chance to run,
        or every label would render at its raw ``mesh_rotation`` fallback
        (flat in the ring's own plane, not camera-facing) until whichever
        of a ring drag or a real camera move happens to come first -- the
        same gap notes have at the instant they're first placed (see
        add_handlers.editor_3d.note.Note's own explicit priming call,
        right after placement, for the identical reasoning).

        No camera at all (the schematic/pegboard views' own protractor
        -- a locked top-down projection has nothing to billboard toward)
        leaves every label's ``render_angle()`` falling through to its
        own ``tick.mesh_rotation`` instead, same as always.
        """
        if self._camera is None:
            return

        for tick in self._major_ticks:
            tick.label._tracking_angle = _angle.Angle()  # NOQA

        self._camera.position.bind(self._on_camera_moved)
        self._update_label_angles()

    @_check_types.do
    def _update_label_angles(self) -> None:
        """Recompute every major tick's own camera-facing billboard
        angle directly, writing straight into each tick's own label --
        no ``shapes.text._CameraTrackingArena`` involvement at all: that
        class exists for OBB/AABB-tracked owners (notes), and computing
        (then discarding) its 8-corner contraction for labels that have
        neither was real, measured wasted work on exactly this hot path
        (see this method's own call sites).

        Called from :meth:`reposition_all` (so a ring drag only ever
        recomputes THIS ring's own up-to-36 labels, not the whole
        scene's worth of tracked notes too) and from
        :meth:`_on_camera_moved` (so labels whose *position* didn't just
        change still get their facing angle refreshed for the camera's
        new position) -- the same two triggers routing labels through
        ``shapes.text.update_camera_tracking`` used to cover, just
        without that class's shared arena at all now.

        Uses the shared, module-level :data:`_label_positions_scratch`
        instead of allocating a fresh positions array on every call --
        see that buffer's own comment for why reusing it here is safe.
        A no-op with no camera at all (the schematic/pegboard views'
        own protractor), or before this ring has any major ticks with
        labels yet.
        """
        if self._camera is None:
            return

        count = len(self._major_ticks)
        if count == 0:
            return

        positions = _label_positions_scratch[:count]
        for i, tick in enumerate(self._major_ticks):
            p = tick.label_position
            positions[i, 0] = p.x
            positions[i, 1] = p.y
            positions[i, 2] = p.z

        camera_pos = self._camera.position.as_numpy.astype(np.float64)
        matrices, safe = _text._billboard_matrices(positions, camera_pos)  # NOQA

        for i, tick in enumerate(self._major_ticks):
            if not safe[i]:
                continue

            tick.label._tracking_angle = _angle.Angle.from_matrix(matrices[i])  # NOQA

    @_check_types.do
    def _on_camera_moved(self, *_args) -> None:
        """Bound to ``self._camera.position`` in
        :meth:`start_camera_tracking` -- must be a real bound method
        (not a lambda/free function): ``Point.bind()`` stores it as a
        ``weakref.WeakMethod``, which only works against an actual bound
        method's own ``__self__`` (see ``gl.canvas_3d.canvas.Canvas.
        _on_camera_moved_for_notes`` for the identical constraint on the
        equivalent per-note callback).
        """
        self._update_label_angles()

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram") -> None:
        if not self.is_visible:
            return

        # Translucent washer -- alpha blending scoped to just this draw,
        # matching gl/canvas_schematic/floor.py's own established
        # enable-around-the-call/restore pattern. Depth-mask handling for
        # this handler's whole render is the caller's responsibility now
        # (canvas_base.py's _draw_scene renders the handler before the
        # tracked object itself, rather than this method reasoning about
        # what renders after it -- see that method's own docstring) --
        # this draw just uses whatever depth-mask state it's called with.
        # GL.glEnable(GL.GL_BLEND)
        # GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        faces_program = shaders.faces

        with faces_program:
            self.material.set(faces_program)

            # self._disc_vbo is baked directly to this ring's real
            # ID/OD/depth (see _build_disc_vbo) -- no render-time scale
            # needed at all.
            self._disc_vbo.render(
                faces_program,
                self.center, self._disc_rotation(),
                _point.Point(1.0, 1.0, 1.0), None)

            # Ticks always render in a fixed color (black), independent of
            # the washer's own material -- inheriting the washer's own
            # translucent, axis-tinted color (the old behavior) made them
            # hard to pick out against it. OuterRing's hover highlight
            # still overrides this per-tick, in bright red.
            self._set_solid_color(faces_program, _TICK_COLOR)
            overridden = False

            for tick in self._ticks:
                override = self._tick_override_color(tick.degrees)

                if override is not None:
                    self._set_solid_color(faces_program, override)
                    overridden = True
                elif overridden:
                    # A previous tick overrode the shared uniform state --
                    # restore the default tick color before drawing a
                    # normal tick again.
                    self._set_solid_color(faces_program, _TICK_COLOR)
                    overridden = False

                self._tick_vbo.render(
                    faces_program,
                    tick.position, tick.mesh_rotation, tick.scale, True)

            # GL.glDisable(GL.GL_BLEND)

            # Labels get their own fixed, light color -- previously this
            # restored the washer's own material here (meant to leave
            # the shared uniform state clean for whatever renders next),
            # but the labels render immediately after this and inherited
            # that (translucent, axis-tinted, often dark/blue-ish) color
            # instead of a dedicated one -- making them nearly disappear
            # against the dark scene background. Every render() call
            # already sets its own material first thing (see the top of
            # this method, and TorusRing.render()'s identical pattern),
            # so nothing downstream actually depends on this state being
            # restored -- it only ever affected these labels.
            self._label_material.set(faces_program)

            label_scale = _point.Point(1.0, 1.0, 1.0)

            for tick in self._major_ticks:
                # render_angle() returns the label's own live camera-
                # facing billboard while tracking is enabled (see
                # __init__'s own enable_camera_tracking call), or falls
                # straight through to tick.mesh_rotation (lying flat in
                # the ring's own plane) when there's no camera to
                # billboard toward at all (schematic/pegboard).
                rotation = tick.label.render_angle(tick.mesh_rotation)
                tick.label.render(
                    faces_program,
                    tick.label_position, rotation, label_scale, False)

    @_check_types.do
    def _disc_rotation(self) -> "_angle.Angle":
        """Subclasses provide whatever orientation the washer itself
        should render with -- the inner ring's tracks the object, the
        outer ring's stays fixed. Ticks/labels get their own
        orientation from :meth:`reposition_all` regardless.
        """
        raise NotImplementedError

    def _get_label_color(self):
        raise NotImplementedError

    @staticmethod
    @_check_types.do
    def _set_solid_color(faces_program, color: "tuple[float, float, float]") -> None:
        faces_program.material_diffuse = [color[0], color[1], color[2], 1.0]
        faces_program.material_emissive = [color[0], color[1], color[2], 1.0]

    @_check_types.do
    def _tick_override_color(self, degrees: float) -> "tuple[float, float, float] | None":
        """Per-tick color override for the current frame, or ``None`` for
        the default fixed tick color (:data:`_TICK_COLOR`). Base
        implementation never overrides -- :class:`.outer_ring.OuterRing`
        overrides this to highlight the currently-hovered tick red.
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
