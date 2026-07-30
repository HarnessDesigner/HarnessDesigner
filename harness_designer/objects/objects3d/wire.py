# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu
from PySide6.QtCore import QTimer
from OpenGL import GL
import numpy as np
import math

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry import line as _line
from . import base3d as _base3d
from . import menu_ops as _menu_ops
from ...shapes import cylinder as _cylinder
from ...shapes import helix as _helix
from ...gl import materials as _materials
from ... import color as _color
from ... import config as _config
from ... import utils as _utils
from . import mixins as _mixins

if TYPE_CHECKING:
    from ...database.project_db import pjt_wire as _pjt_wire
    from .. import wire as _wire


Config = _config.Config.editor3d

# Real-world mm of extra headroom built into the shared stripe helix mesh
# beyond whatever's currently required (see WireStripe._ensure_stripe_capacity).
# A live drag/preview can then grow a wire's own total length without
# forcing a GPU buffer reallocation on every frame -- only once the
# overshoot itself is exhausted does the mesh actually need to regrow.
_HELIX_OVERSHOOT_MM = 1000.0


class Wire(_base3d.Base3D, _mixins.WireTypeMixin):
    """Represent a wire in :mod:`harness_designer.objects.objects3d.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_wire.Wire" = None
    db_obj: "_pjt_wire.PJTWire" = None

    def __init__(self, parent: "_wire.Wire", db_obj: "_pjt_wire.PJTWire"):
        """Initialise the :class:`Wire` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_wire.Wire`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire.PJTWire`
        """
        with parent.mainframe.editor3d.context:
            self._stripe = None

            self._part = db_obj.part
            color = self._part.color.ui
            stripe_color = self._part.stripe_color
            diameter = self._part.od_mm

            # Wires hold strong references to bundles as a sanity check
            self._bundle = None

            material = _materials.Plastic(color)

            # Bare-conductor look for whichever end segment(s) crimp into a
            # terminal (see render()) -- conductor_dia_mm already falls back
            # to an AWG-derived estimate when the wire_size_dia column is
            # NULL; od_mm * 2/3 is the final fallback for a part missing both,
            # per the same ratio a stranded conductor's copper core typically
            # is of its own fully-insulated OD.
            conductor_dia = self._part.conductor_dia_mm
            if not conductor_dia:
                conductor_dia = diameter * (2.0 / 3.0)

            self._conductor_dia = conductor_dia
            self._conductor_material = _materials.Polished(self._part.core_material.color.ui)

            self._p1 = db_obj.start_position3d
            self._p2 = db_obj.stop_position3d

            # Live Point objects for every interior waypoint (idx order),
            # kept in sync with the DB via refresh_waypoints() -- called by
            # whichever handler adds/removes/reorders this wire's own
            # waypoints (handlers.wire_layout_handler, handlers.wire_handler,
            # objects.terminal.Terminal.add_wire).
            self._waypoint_points: list[_point.Point] = []

            self._length = self._calc_length()

            position = self._p1

            scale = _point.Point(diameter, diameter, self._length)

            # Track wires in this bundle using weak references
            # Wires hold strong references to bundles; bundles use weak refs to wires
            self._wires = []  # List of weak references to Wire objects

            self._p2.bind(self._update_position)

            vbo = _cylinder.create_vbo()
            angle = _angle.Angle()

            # Built before the stripe -- WireStripe's own OBB/AABB are copied
            # from this wire's, so the wire must already have real _obb/_aabb
            # attributes (set by Base3D.__init__) before WireStripe.__init__
            # (itself calling Base3D.__init__, which calls _compute_obb/_aabb)
            # can safely read them. Binding position/angle/scale here first also
            # means this wire's own _update_* callbacks (which recompute its
            # _obb/_aabb) fire before the stripe's on any later shared change.
            _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, position, scale, material)

            if stripe_color is not None:
                self._stripe = WireStripe(parent, self, stripe_color.ui, scale, angle, position)
                # WireStripe's db_obj is always None (it's not its own DB row --
                # see WireStripe.__init__), so Base3D.__init__ hits the
                # `except AttributeError: self._is_visible = False` branch and
                # the stripe is built permanently invisible. Sync it to the
                # wire's own just-computed visibility here.
                self._stripe.is_visible = self._is_visible

                self.editor3d.Refresh()

            # _update_angle just calls _update_position(None) — redundant since
            # both endpoints already drive recalculation via their point bindings.
            self._angle.unbind(self._update_angle)

            # self.db_obj is only valid from here on (set by Base3D.__init__
            # above) -- this is the first point waypoints3d/for_wire can be
            # queried, so the initial waypoint bind and the real (possibly
            # multi-segment) geometry recompute both happen here, not earlier.
            self._bind_waypoints()
            self._recalculate_geometry()

    @property
    def length(self) -> float:
        return self._length

    def _calc_length(self):
        """Straight-line seed length used only to size this wire's
        initial scale before Base3D.__init__ runs (self.db_obj isn't
        valid yet, so this can't query waypoints3d) -- a brand new wire
        row never has any waypoints yet anyway. _recalculate_geometry
        (called at the end of __init__, and on every subsequent endpoint/
        waypoint move) replaces this with the true, possibly multi-segment
        polyline length via WireTypeMixin._segments().
        """
        x1, y1, z1 = self._p1.as_numpy.tolist()
        x2, y2, z2 = self._p2.as_numpy.tolist()

        dx = x2 - x1
        dy = y2 - y1
        dz = z2 - z1

        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def _bind_waypoints(self) -> None:
        """(Re-)bind this wire's own _update_position callback to every
        current interior waypoint's live Point, unbinding it from whatever
        set was bound before.

        Called once at construction and again (as refresh_waypoints) by
        any handler that adds/removes/reorders this wire's own waypoints,
        so live position-change callbacks always match the current set.
        """
        for point in self._waypoint_points:
            point.unbind(self._update_position)

        self._waypoint_points = [wp.point for wp in self.db_obj.waypoints3d]

        for point in self._waypoint_points:
            point.bind(self._update_position)

    def refresh_waypoints(self) -> None:
        """Public entry point for handlers: call after this wire's own
        waypoint rows change (added, removed, or reordered) so live
        callbacks, cached length, and geometry all catch up."""
        self._bind_waypoints()
        self._recalculate_geometry()
        self.editor3d.Refresh()

    @property
    def start_position(self):
        """Wire start position (Point instance)"""
        return self._p1

    @property
    def stop_position(self):
        """Wire stop position (Point instance)"""
        return self._p2

    def is_housing_attached(self) -> bool:
        """True if either endpoint shares a db_id with any cavity's or
        terminal's housing-derived wire-routing point (cavity.wire_position3d,
        terminal.wire_position3d, terminal.attach_position3d) anywhere in
        the project. Such a wire's position is derived from its housing --
        it must not be independently draggable; the user has to move the
        housing or drag the wire's own layout instead.

        Checks the *_raw properties (no lazy point creation) so this never
        forces a wire-routing point into existence for a cavity/terminal
        that has never had one, just by asking.
        """
        start_id = int(self._p1.db_id[:-2])
        stop_id = int(self._p2.db_id[:-2])
        ids = {start_id, stop_id}

        project = self.mainframe.project

        for cavity in project.cavities:
            if cavity.db_obj.wire_point3d_id_raw in ids:
                return True

        for terminal in project.terminals:
            if terminal.db_obj.wire_point3d_id_raw in ids:
                return True
            if terminal.db_obj.attach_point3d_id_raw in ids:
                return True

        return False

    def set_start_position(self, point: _point.Point) -> None:
        """Repoint this wire's own start end to *point* entirely.

        Not a merge/delegation (see Point.attach for that) -- the old
        start point is left alone as an independent point (e.g. becoming
        a permanent interior waypoint the instant before this is called;
        see handlers.wire_handler.AddWireHandler._commit_waypoint, the
        only caller today), and *point* must already be exactly where
        this wire's start should be -- nothing here moves it.
        """
        self._p1.unbind(self._update_position)
        self._p1 = point
        self._p1.bind(self._update_position)
        self._recalculate_geometry()

    def set_stop_position(self, point: _point.Point) -> None:
        """See set_start_position."""
        self._p2.unbind(self._update_position)
        self._p2 = point
        self._p2.bind(self._update_position)
        self._recalculate_geometry()

    def _update_angle(self, angle: _angle.Angle):
        """Update the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        self._update_position(None)

    def _recalculate_geometry(self):
        """Compute total length, an aggregate angle, and OBB/AABB from
        the wire's current start/interior-waypoints/stop path.

        Per-segment position/angle/scale for actual drawing and hit-
        testing are computed fresh in render()/hit_test_step3 from
        WireTypeMixin._segments() -- this only maintains the aggregate
        values anything outside this class still reads (.length, .scale,
        .angle, .obb, .aabb).
        """
        segments = self._segments()

        total_length = 0.0
        for seg_p1, seg_p2 in segments:
            total_length += float(np.linalg.norm(seg_p2 - seg_p1))

        if total_length < 0.001:
            return

        self._length = total_length
        self._scale.z = total_length

        if self._stripe is not None:
            self._stripe._ensure_stripe_capacity(self.mainframe, total_length)  # NOQA

        # Aggregate angle: the overall start->stop chord direction. Not
        # used for drawing (each segment computes its own), kept only for
        # any other code reading .angle on a wire.
        a = self._p1.as_numpy
        b = self._p2.as_numpy
        chord = b - a
        chord_length = float(np.linalg.norm(chord))
        if chord_length >= 0.001:
            angle = self._rotation_from_direction(chord / chord_length)
            self._angle._q = angle._q  # NOQA

        self._compute_obb()
        self._compute_aabb()

    def _update_position(self, _: _point.Point):
        """Recompute geometry immediately, not deferred to the next
        render pass -- bound to the start/stop endpoints and every
        interior waypoint (see _bind_waypoints), so any of them moving
        keeps the wire's aggregate length/OBB/AABB and the stripe's
        mesh capacity current before the next repaint.
        """

        self._recalculate_geometry()

    def _segment_transforms(self):
        """Yield (position, angle, scale, length) for every sub-segment
        of this wire's current path -- the values render()/hit_test_step3
        both draw/test against, computed fresh each call since a wire's
        waypoints can change at any time."""
        diameter = self._scale.x

        for seg_p1, seg_p2 in self._segments():
            seg_vec = seg_p2 - seg_p1
            seg_len = float(np.linalg.norm(seg_vec))
            if seg_len < 1e-6:
                continue

            direction = seg_vec / seg_len
            seg_angle = self._rotation_from_direction(direction)
            seg_position = _point.Point(*seg_p1)
            seg_scale = _point.Point(diameter, diameter, seg_len)

            yield seg_position, seg_angle, seg_scale, seg_len

    def _compute_obb(self):
        """Union AABB across every sub-segment, expressed as an 8-corner
        box (same shape find_object/_ray_intersect_obb expects) -- a
        single rigid OBB has no meaningful orientation for a wire with
        more than one bend, so this degenerates to the same envelope as
        _compute_aabb rather than a tight rotated box. Conservative (a
        click near an elbow but off the actual tube can still register a
        hit) but always correct; see hit_test_step3 for the precise,
        per-segment mesh test."""
        if self._vbo is None:
            return

        corners = self._segment_world_corners()
        if corners is None:
            return

        mins = corners.min(axis=0)
        maxs = corners.max(axis=0)

        self._obb = np.array([
            [mins[0], mins[1], mins[2]], [mins[0], mins[1], maxs[2]],
            [mins[0], maxs[1], mins[2]], [mins[0], maxs[1], maxs[2]],
            [maxs[0], mins[1], mins[2]], [maxs[0], mins[1], maxs[2]],
            [maxs[0], maxs[1], mins[2]], [maxs[0], maxs[1], maxs[2]],
        ], dtype=np.float32)

    def _compute_aabb(self):
        """See _compute_obb -- same union-of-segments envelope."""
        if self._vbo is None:
            return

        corners = self._segment_world_corners()
        if corners is None:
            return

        aabb = _utils.adjust_aabb(corners)

        for i in range(2):
            for j in range(3):
                self._aabb[i][j] = aabb[i][j]

    def _segment_world_corners(self):
        """World-space AABB corners (8 per segment) for every sub-segment,
        stacked into one array -- the shared building block for both
        _compute_obb and _compute_aabb's union-of-segments envelope."""
        local_min = self._vbo.local_aabb[0]
        local_max = self._vbo.local_aabb[1]
        x1, y1, z1 = local_min
        x2, y2, z2 = local_max

        local_corners = np.array([
            [x1, y1, z1], [x1, y1, z2],
            [x1, y2, z1], [x1, y2, z2],
            [x2, y1, z1], [x2, y1, z2],
            [x2, y2, z1], [x2, y2, z2]
        ], dtype=np.float32)

        all_corners = []
        for seg_position, seg_angle, seg_scale, _seg_len in self._segment_transforms():
            corners = local_corners * seg_scale.as_numpy
            corners = corners @ seg_angle
            corners = corners + seg_position.as_numpy
            all_corners.append(corners)

        if not all_corners:
            # Every sub-segment is degenerate (start and stop, and any
            # waypoints between them, all coincide) -- a real state a
            # wire can transiently be in (e.g. a wire service loop's own
            # placeholder "gap" wire, deleted a moment after construction
            # -- see handlers.wire_service_loop_handler._split_wire_for_
            # loop). A point-sized box at the wire's own position is
            # still a valid, if trivial, bound -- returning None left obb/
            # aabb permanently unset (None) instead.
            point = self._p1.as_numpy
            return np.tile(point, (8, 1)).astype(np.float32)

        return np.concatenate(all_corners, axis=0)

    def hit_test_step3(self, ray_origin, ray_dir):
        """Precise per-segment mesh hit test (see BaseVar.hit_test_step3):
        tests every sub-segment's own transformed triangles individually
        instead of assuming one rigid transform for the whole wire."""
        if self._vbo is None:
            return False

        vertices_local = self._vbo.vertices.reshape(-1, 3)
        if len(vertices_local) % 3:
            return False

        for seg_position, seg_angle, seg_scale, _seg_len in self._segment_transforms():
            ray_object = ray_origin - seg_position.as_numpy

            vertices = (vertices_local * seg_scale.as_numpy) @ seg_angle
            verts = vertices.reshape(-1, 3, 3)

            if self._ray_triangles_intersect_vectorized(ray_object, ray_dir, verts):
                return True

        return False

    def _conductor_segment_ends(self) -> tuple[bool, bool]:
        """Return (start_is_conductor, stop_is_conductor) -- whether the
        first/last sub-segment crimps directly into a Terminal and should
        render bare-conductor-sized/colored instead of at the wire's own
        insulation diameter/material (see render()).

        Checked via the sibling graph (parent.start_sibling/stop_sibling,
        a cheap weakref lookup already maintained by Terminal.add_wire/
        AddWireHandler) rather than the raw db_obj point ids -- a splice
        or wire-service-loop sibling never gets the conductor treatment,
        only an actual Terminal.
        """
        from .. import terminal as _terminal

        return (isinstance(self.parent.start_sibling, _terminal.Terminal),
                isinstance(self.parent.stop_sibling, _terminal.Terminal))

    def render(self, faces_program, edges_program, vertices_program):
        """Render every sub-segment of the wire's current path.

        Geometry is always current by the time this runs --
        _update_position recomputes it synchronously the moment any
        endpoint or waypoint moves, so there is nothing to catch up on
        here. Each sub-segment is drawn as its own straight cylinder by
        temporarily pointing this object's (and the stripe's) position/
        angle/scale at that segment before delegating to Base3D.render()
        -- reuses its existing faces/edges/normals/vertices debug-config
        gating and material handling unchanged, once per segment.

        The one segment nearest each end that crimps into a Terminal
        (see _conductor_segment_ends) renders at the conductor's own
        diameter/material instead -- a short bare-conductor look at the
        crimp, matching real hardware, rather than full insulation OD
        running straight into the terminal. Suppressed while selected,
        same as the stripe overlay below, so the selection highlight
        stays a single uniform color across the whole wire.
        """
        real_position, real_angle, real_scale, real_material = (
            self._position, self._angle, self._scale, self._material)

        draw_stripe = self._stripe is not None and not self.is_selected

        if self.is_selected:
            conductor_start = conductor_stop = False
        else:
            conductor_start, conductor_stop = self._conductor_segment_ends()

        if draw_stripe:
            stripe_position = self._stripe._position  # NOQA
            stripe_angle = self._stripe._angle  # NOQA

        stripe_offset = 0.0
        segments = list(self._segment_transforms())
        last_idx = len(segments) - 1

        for i, (seg_position, seg_angle, seg_scale, seg_len) in enumerate(segments):
            is_conductor = (
                (i == 0 and conductor_start) or
                (i == last_idx and conductor_stop))

            self._position, self._angle = seg_position, seg_angle

            if is_conductor:
                self._scale = _point.Point(self._conductor_dia, self._conductor_dia, seg_len)
                self._material = self._conductor_material
            else:
                self._scale = seg_scale
                self._material = real_material

            super().render(faces_program, edges_program, vertices_program)

            if draw_stripe and not is_conductor:
                # Stripe geometry ignores scale.z entirely (see
                # gl.shaders.faces' vertex shader) -- only x/y (bumped past
                # the wire's own radius) matter, so its own scale.z value
                # is irrelevant; position/angle must match this segment.
                self._stripe._position = seg_position  # NOQA
                self._stripe._angle = seg_angle  # NOQA
                self._stripe.render_segment(
                    faces_program, edges_program, vertices_program,
                    stripe_offset, stripe_offset + seg_len)

            stripe_offset += seg_len

        self._position, self._angle, self._scale, self._material = (
            real_position, real_angle, real_scale, real_material)
        if draw_stripe:
            self._stripe._position = stripe_position  # NOQA
            self._stripe._angle = stripe_angle  # NOQA

    def set_selected(self, flag: bool):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        super().set_selected(flag)
        if self._stripe is not None:
            self._stripe.set_selected(flag)

    @staticmethod
    def _rotation_from_direction(direction):
        """Create quaternion to rotate +Z axis to align with direction"""
        # Unit cylinder points along +Z, rotate it to point along 'direction'
        z_axis = np.array([0.0, 0.0, 1.0], dtype=np.float32)

        # Handle special case: direction already aligned with Z (tight
        # epsilon -- this only exists to dodge the near-zero-length cross
        # product below, not to treat "close to vertical" as "vertical")
        dot = np.dot(z_axis, direction)
        if abs(dot - 1.0) < 1e-6:
            return _angle.Angle.from_quat([1.0, 0.0, 0.0, 0.0])  # Identity

        if abs(dot + 1.0) < 1e-6:
            # 180 degree rotation around X axis
            return _angle.Angle.from_quat([0.0, 1.0, 0.0, 0.0])

        # Calculate rotation axis and angle
        axis = np.cross(z_axis, direction)  # NOQA
        axis = axis / np.linalg.norm(axis)

        angle = math.acos(np.clip(dot, -1.0, 1.0))

        return _angle.Angle.from_axis_angle(axis, angle)

    @property
    def bundle(self):
        """Return the bundle this wire belongs to, if any."""
        return self._bundle

    @bundle.setter
    def bundle(self, value):
        """Set the bundle this wire belongs to.

        Wires hold strong references to bundles as a sanity check.
        """
        self._bundle = value

    @property
    def is_visible(self) -> bool:
        """Return the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self._is_visible

    @is_visible.setter
    def is_visible(self, value: bool) -> None:
        """Set the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._is_visible = value
        self.db_obj.is_visible = value

        if self._stripe is not None:
            self._stripe.is_visible = value

    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return WireMenu(self.mainframe.editor3d.editor, self)


class WireStripe(_base3d.Base3D):
    """Represent a wire stripe in :mod:`harness_designer.objects.objects3d.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent: "_wire.Wire", wire: Wire, color: _color.Color, scale: _point.Point,
                 angle: _angle.Angle, position: _point.Point):
        """Initialise the :class:`WireStripe` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_wire.Wire`
        :param wire: Value for ``wire``.
        :type wire: :class:`Wire`
        :param color: Value for ``color``.
        :type color: :class:`_color.Color`
        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        :param position: Position value.
        :type position: :class:`_point.Point`
        """

        # wire.length isn't trustworthy yet at this point in Wire.__init__
        # -- it's still the plain straight-line p1/p2 seed from
        # Wire._calc_length, computed before _recalculate_geometry ever
        # runs (see Wire.__init__'s ordering). wire.db_obj/start_position/
        # stop_position are already valid by now though (set by
        # Base3D.__init__, just above), so the true, possibly multi-
        # segment polyline length -- what this stripe actually needs
        # capacity for, e.g. reloading an already-bent wire -- can be
        # computed directly here via the same WireTypeMixin._segments()
        # walk Wire itself uses.
        required = sum(
            float(np.linalg.norm(seg_p2 - seg_p1))
            for seg_p1, seg_p2 in wire._segments())  # NOQA
        self._ensure_stripe_capacity(parent.mainframe, required)

        # Already big enough after _ensure_stripe_capacity -- this just
        # fetches the resulting handle (a cheap no-op fast path, see
        # create_vbo).
        vbo = _helix.create_vbo(required)
        material = _materials.Plastic(color)
        self._wire = wire

        # Deliberately NOT the same scale Point instance the wire uses (only
        # position/angle are shared -- the stripe has no independent extent
        # of its own there; see the _obb/_aabb properties below). The
        # stripe's x/y are bumped past the wire's own radius so it always
        # renders genuinely outside the wire's surface instead of coincident
        # with it -- two coincident opaque surfaces z-fight per-pixel no
        # matter how that's biased, so the fix is to not be coincident in
        # the first place. z is irrelevant here: faces.py's vertex shader
        # skips z-scaling entirely for stripe geometry (stripeClipStop >
        # 0), so it doesn't need to track any segment's live length -- see
        # the clip_start/clip_stop args Wire.render() passes into
        # render_segment below, computed fresh per segment as it walks
        # the wire's own waypoints.
        stripe_scale = _point.Point(scale.x + 0.1, scale.y + 0.1, scale.z)
        _base3d.Base3D.__init__(self, parent, None, vbo, angle, position, stripe_scale, material)

    @staticmethod
    def _ensure_stripe_capacity(mainframe, required: float) -> None:
        """Grow the shared wire-stripe helix mesh -- and persist the new
        true-required max back onto the project row -- if `required`
        (a wire's own total length, the furthest any of its segments'
        clip windows will ever reach into the shared mesh) exceeds what's
        currently stored.

        Takes `mainframe` explicitly rather than reading self.mainframe:
        called from __init__ before Base3D.__init__ has set it (the vbo
        it builds here is itself an argument to that call), and later
        from Wire._recalculate_geometry against the *wire's* mainframe,
        not this stripe's own (identical, but the wire is what changed).

        The actual VBO build is padded by _HELIX_OVERSHOOT_MM so a live
        drag/preview has headroom to grow without forcing a GPU
        reallocation on every frame -- the persisted max itself stays
        the true, unpadded requirement. No-op (no create_vbo call at
        all) in the common case where the stored max already covers
        this wire.
        """
        project_db_obj = mainframe.project.db_obj

        if required > project_db_obj.wire_stripe_max_length:
            project_db_obj.wire_stripe_max_length = required
            _helix.create_vbo(required + _HELIX_OVERSHOOT_MM)

    @property
    def smooth(self) -> bool:
        """Always smooth-shaded -- the helix is a swept curved surface with
        no flat faces, so there's no reason for this to ever be flat (see
        Base3D._render_geometry, which defaults to flat shading when a
        subclass doesn't define this)."""
        return True

    def render_segment(self, faces_program, edges_program, vertices_program,
                        clip_start: float, clip_stop: float):
        """Draw this stripe windowed to [clip_start, clip_stop] -- one
        call per wire sub-segment, made by Wire.render() with this
        stripe's own _position/_angle already pointed at that segment.

        clip_start/clip_stop are now computed fresh by the caller (a
        running total of preceding segment lengths) rather than read from
        a persisted, cross-row-cascaded value -- see gl.shaders.faces'
        stripeClipStart/stripeClipStop uniforms for what they mean to the
        shader; nothing else about the windowing mechanism changes.

        Resets the uniforms to 0.0 right after, same as the single-shot
        render() this replaces -- only WireStripe ever touches them, and
        GL uniform state persists on the program across draw calls, so a
        nonzero value left behind would otherwise leak into whatever
        renders next on the same faces_program.
        """
        if not self.is_visible:
            return

        start_loc = GL.glGetUniformLocation(faces_program, "stripeClipStart")
        stop_loc = GL.glGetUniformLocation(faces_program, "stripeClipStop")

        GL.glUseProgram(faces_program)
        GL.glUniform1f(start_loc, clip_start)
        GL.glUniform1f(stop_loc, clip_stop)

        super().render(faces_program, edges_program, vertices_program)

        GL.glUseProgram(faces_program)
        GL.glUniform1f(start_loc, 0.0)
        GL.glUniform1f(stop_loc, 0.0)

    def _compute_obb(self):
        """No-op: the stripe has no independent geometry of its own. See
        the _obb property below."""

    def _compute_aabb(self):
        """See _compute_obb."""

    @property
    def _obb(self):
        """Always the wire's current OBB array -- read-only everywhere
        obb/aabb are used (hit-testing, debug overlay boxes), so there's
        never a need for the stripe to hold its own copy."""
        return self._wire._obb

    @_obb.setter
    def _obb(self, value):
        # Base3D.__init__ assigns this once before calling _compute_obb();
        # the wire is the source of truth, so the write is discarded.
        pass

    @property
    def _aabb(self):
        """See _obb."""
        return self._wire._aabb

    @_aabb.setter
    def _aabb(self, value):
        pass

    def _update_position(self, position: _point.Point):
        """Recompute (copy) OBB/AABB from the wire; the wire's own
        _update_position already triggers a repaint, so this doesn't need
        its own Refresh() call.

        :param position: Position value.
        :type position: :class:`_point.Point`
        """
        # self._compute_obb()
        # self._compute_aabb()

        pass

    def _update_angle(self, angle: _angle.Angle):
        """See _update_position.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        # self._compute_obb()
        # self._compute_aabb()

        pass

    def _update_scale(self, scale: _point.Point):
        """See _update_position.

        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        """
        # self._compute_obb()
        # self._compute_aabb()

        pass

    @property
    def is_visible(self) -> bool:
        """Return the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self._is_visible

    @is_visible.setter
    def is_visible(self, value: bool):
        """Set the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._is_visible = value


class WireMenu(QMenu):
    """Represent a wire menu in :mod:`harness_designer.objects.objects3d.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, selected):
        """Initialise the :class:`WireMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Handle')
        action.triggered.connect(self.on_add_handle)

        action = self.addAction('Add Marker')
        action.triggered.connect(self.on_add_marker)

        action = self.addAction('Add Splice')
        action.triggered.connect(self.on_add_splice)

        action = self.addAction('Add Wire')
        action.triggered.connect(self.on_add_wire)

        action = self.addAction('Add Wire Service Loop')
        action.triggered.connect(self.on_add_wire_service_loop)

        self.addSeparator()
        action = self.addAction('Add to Bundle')
        action.triggered.connect(self.on_add_to_bundle)

        self.addSeparator()
        action = self.addAction('Trace Circuit')
        action.triggered.connect(self.on_trace_circuit)

        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    def _midpoint(self) -> _point.Point:
        """Return the world space midpoint of the wire."""
        line = _line.Line(self.selected.start_position,
                          self.selected.stop_position)

        return line.point_from_start(line.length() / 2.0)

    def on_add_handle(self):
        """Insert a wire layout (drag handle) at the point on the wire
        that was right-clicked to open this menu (falls back to the
        wire's midpoint if no click point was captured -- e.g. the menu
        was opened some other way).

        No row split any more -- the new waypoint is inserted into the
        wire's own ordered path at whichever position the click actually
        projects onto (see _create_wire_layout_on_wire), same as
        on_add_marker's own click-position handling below.
        """
        from ...handlers import wire_layout_handler as _wire_layout_handler

        wire = self.selected.parent
        project = self.selected.mainframe.project

        click_pos = self.selected._context_menu_click_pos  # NOQA
        position = insert_idx = None
        if click_pos is not None:
            position, _angle, insert_idx = self.selected.get_closest_point(click_pos)

        if position is None:
            # No click captured -- fall back to the wire's own midpoint;
            # _create_wire_layout_on_wire works out the insertion index
            # itself in that case (see its insert_idx=None default).
            position = self._midpoint()

        _wire_layout_handler._create_wire_layout_on_wire(  # NOQA
            project, wire, position, insert_idx)

        self.selected.editor3d.Refresh()

    def on_add_marker(self):
        """Add a wire marker at the point on the wire that was
        right-clicked to open this menu (falls back to the wire's
        midpoint if no click point was captured -- e.g. the menu was
        opened some other way)."""
        def _do():
            from .. import wire_marker as _wire_marker_obj

            mainframe = self.selected.mainframe

            part_id = _menu_ops.get_part_id(
                mainframe, 'wire_markers',
                mainframe.global_db.wire_markers_table, 'Add Wire Marker')

            if part_id is None:
                return

            click_pos = self.selected._context_menu_click_pos  # NOQA
            position = None
            if click_pos is not None:
                position, _angle, _idx = self.selected.get_closest_point(click_pos)

            if position is None:
                position = self._midpoint()

            ptables = mainframe.project.ptables
            p3d = ptables.pjt_points3d_table.insert(*position.as_float)

            db_obj = ptables.pjt_wire_markers_table.insert(
                None, p3d.db_id, self.selected.db_obj.db_id, part_id, '')

            marker = _wire_marker_obj.WireMarker(mainframe, db_obj)
            mainframe.project.add_wire_marker(marker)

        QTimer.singleShot(0, _do)

    def on_add_splice(self):
        """Start the interactive splice placement flow on this wire."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe
        wire = self.selected.parent

        _menu_ops.start_handler(
            mainframe, lambda: _handlers.AddSpliceHandler(mainframe, wire))

    def on_add_wire(self):
        """Start placing another wire of the same part type."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe
        part_id = self.selected.db_obj.part_id

        _menu_ops.start_handler(
            mainframe, lambda: _handlers.AddWireHandler(mainframe, part_id))

    def on_add_wire_service_loop(self):
        """Start placing a service loop on this wire, anchored at the point
        that was right-clicked to open this menu."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe
        wire = self.selected.parent
        click_pos = self.selected._context_menu_click_pos  # NOQA

        _menu_ops.start_handler(
            mainframe,
            lambda: _handlers.AddWireServiceLoopHandler(mainframe, wire, click_pos))

    def on_add_to_bundle(self):
        """Add this wire to the closest bundle in the project."""
        mainframe = self.selected.mainframe
        midpoint = self._midpoint()

        closest = None
        closest_distance = None

        for bundle in mainframe.project.bundles:
            b_line = _line.Line(bundle.obj3d.start_position,
                                bundle.obj3d.stop_position)
            b_mid = b_line.point_from_start(b_line.length() / 2.0)

            distance = _line.Line(midpoint, b_mid).length()

            if closest_distance is None or distance < closest_distance:
                closest_distance = distance
                closest = bundle

        if closest is None:
            return

        closest.obj3d.add_wire(self.selected)
        self.selected.bundle = closest.obj3d

        mainframe.editor3d.Refresh()

    def on_trace_circuit(self):
        """Highlight every object on this wire's circuit."""
        _menu_ops.trace_circuit(self.selected)

    def on_select(self):
        """Make this wire the active selection."""
        _menu_ops.select_object(self.selected)

    def on_delete(self):
        """Delete this wire from the project."""
        _menu_ops.delete_object(self.selected)

    def on_properties(self):
        """Show this wire's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
