# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import weakref
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
from . import mixins as _mixins

if TYPE_CHECKING:
    from ...database.project_db import pjt_wire as _pjt_wire
    from .. import wire as _wire


Config = _config.Config.editor3d

# Real-world mm of extra headroom built into the shared stripe helix mesh
# beyond whatever's currently required (see WireStripe._ensure_stripe_capacity).
# A live drag/preview can then grow a wire's stripe_clip_stop without
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
        parent.mainframe.editor3d.context.acquire()
        self._stripe = None

        self._part = db_obj.part
        color = self._part.color.ui
        stripe_color = self._part.stripe_color
        diameter = self._part.od_mm

        # Wires hold strong references to bundles as a sanity check
        self._bundle = None

        material = _materials.Plastic(color)

        self._p1 = db_obj.start_position3d
        self._p2 = db_obj.stop_position3d

        self._length = self._calc_length()

        position = self._p1

        scale = _point.Point(diameter, diameter, self._length)

        # Track wires in this bundle using weak references
        # Wires hold strong references to bundles; bundles use weak refs to wires
        self._wires = []  # List of weak references to Wire objects

        self._p2.bind(self._update_position)

        # Weakref to whichever wire's start point is this wire's own stop
        # point (the next segment in a split chain) -- see the sibling
        # property. Set by whichever handler creates that continuation
        # (handlers.wire_layout_handler._split_wire_at_point,
        # handlers.wire_handler.AddWireHandler).
        self._sibling_ref = None

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

        self._recalculate_geometry()

        parent.mainframe.editor3d.context.release()

    @property
    def length(self) -> float:
        return self._length

    def _calc_length(self):
        x1, y1, z1 = self._p1.as_numpy.tolist()
        x2, y2, z2 = self._p2.as_numpy.tolist()

        dx = x2 - x1
        dy = y2 - y1
        dz = z2 - z1

        return math.sqrt(dx * dx + dy * dy + dz * dz)

    @property
    def stripe_clip_start(self) -> float:
        if self._stripe is None:
            return 0.0

        return self.db_obj.stripe_clip_start

    @stripe_clip_start.setter
    def stripe_clip_start(self, value: float) -> None:
        """Set this wire's own offset into the shared stripe helix mesh.

        Persists the new value and, if it actually changed, cascades
        the same shift onward: whichever wire continues from this
        one's stop point (see sibling) gets its own stripe_clip_start
        set to this wire's new stripe_clip_stop -- which triggers this
        exact same check in its own setter, one hop at a time, only as
        far as an actual change reaches.
        """
        if abs(value - self.db_obj.stripe_clip_start) < 1e-6:
            return

        self.db_obj.stripe_clip_start = value

        next_obj = self.sibling
        if next_obj is not None:
            next_obj.stripe_clip_start = self.stripe_clip_stop

        self.editor3d.Refresh()

    @property
    def stripe_clip_stop(self):
        if self._stripe is None:
            return 0.0

        return self._length + self.stripe_clip_start

    @property
    def sibling(self) -> "Wire | None":
        """The wire whose start point is this wire's own stop point --
        i.e. the next segment in a chain split by a wire layout point.
        Set at creation time by whichever handler creates that
        continuation (see _split_wire_at_point, AddWireHandler). Backed
        by a plain weakref (see the setter) so a deleted sibling just
        reads back as None -- nothing to clean up.
        """
        if self._sibling_ref is None:
            return None

        return self._sibling_ref()

    @sibling.setter
    def sibling(self, wire_obj: "Wire | None") -> None:
        self._sibling_ref = None if wire_obj is None else weakref.ref(wire_obj)

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

    def _update_angle(self, angle: _angle.Angle):
        """Update the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        self._update_position(None)

    def _recalculate_geometry(self):
        """Compute wire direction, length, angle, OBB and AABB from current endpoints."""
        a = self._p1.as_numpy
        b = self._p2.as_numpy

        wire_vector = b - a
        length = math.sqrt(wire_vector[0] * wire_vector[0] +
                           wire_vector[1] * wire_vector[1] +
                           wire_vector[2] * wire_vector[2])

        if length < 0.001:
            return

        self._length = length
        self._scale.z = length

        if self._stripe is not None:
            self._stripe._ensure_stripe_capacity(self.mainframe, self.stripe_clip_start + length)  # NOQA

            # Push this wire's new stripe_clip_stop onto whichever wire
            # continues from it (see sibling) -- the stripe_clip_start
            # setter itself no-ops if the value didn't actually change,
            # and cascades onward through its own sibling otherwise.
            next_obj = self.sibling
            if next_obj is not None:
                next_obj.stripe_clip_start = self.stripe_clip_stop

        direction = wire_vector / length

        # Rotation: align +Z axis with wire direction
        angle = self._rotation_from_direction(direction)
        self._angle._q = angle._q  # NOQA

        self._compute_obb()
        self._compute_aabb()

    def _update_position(self, _: _point.Point):
        """Recompute geometry immediately, not deferred to the next
        render pass.

        The stripe_clip_start cascade to sibling (see
        _recalculate_geometry/the stripe_clip_start setter) has to
        happen synchronously and deterministically: render order across
        wires isn't guaranteed to follow chain order, so deferring this
        would let a downstream wire render with a stale stripe_clip_start
        for a frame -- or worse, depending on which wire's render()
        happens to run first that frame.
        """

        self._recalculate_geometry()

    def render(self, faces_program, edges_program, vertices_program):
        """Render the wire. Geometry is always current by the time this
        runs -- _update_position/_update_angle recompute it synchronously
        the moment an endpoint moves, so there is nothing to catch up on
        here."""
        super().render(faces_program, edges_program, vertices_program)

        # The stripe is a plain attribute, not a separately-registered scene
        # object (canvas.add_object is never called for it), so nothing else
        # ever calls its render() -- piggyback on the wire's own render pass.
        # Suppressed while selected: the wire body above already switched to
        # the selected material/color (Base3D.material), and the stripe
        # can't be independently clicked (it's never in objects_in_view) so
        # there's no selection state of its own to visually represent.
        if self._stripe is not None and not self.is_selected:
            self._stripe.render(faces_program, edges_program, vertices_program)

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

    def __init__(self, parent: "_wire.Wire", wire: "Wire", color: _color.Color, scale: _point.Point,
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

        # Read db_obj.stripe_clip_start directly rather than through the
        # stripe_clip_stop property: wire._stripe is still None until
        # Wire.__init__'s `self._stripe = WireStripe(...)` assignment
        # completes, so the property would read back 0.0 right now.
        required = wire.db_obj.stripe_clip_start + wire.length
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
        # 0), so it doesn't need to track the wire's live length -- see
        # stripe_clip_start/stripe_clip_stop on Wire, read directly by
        # this class's own render() override below.
        stripe_scale = _point.Point(scale.x + 0.1, scale.y + 0.1, scale.z)
        _base3d.Base3D.__init__(self, parent, None, vbo, angle, position, stripe_scale, material)

    @staticmethod
    def _ensure_stripe_capacity(mainframe, required: float) -> None:
        """Grow the shared wire-stripe helix mesh -- and persist the new
        true-required max back onto the project row -- if `required`
        (a wire's own end position in the shared mesh, i.e. its
        stripe_clip_stop) exceeds what's currently stored.

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

    def render(self, faces_program, edges_program, vertices_program):
        """Set stripeStartLength for this stripe's own draw, then reset
        it to zero right after.

        Unlike stripeClipLength (which every object explicitly sets on
        every draw call -- see Base3D._render_geometry), only WireStripe
        ever touches this uniform, so it has to clean up after itself:
        GL uniform state persists on the program across draw calls, and
        a nonzero value left behind would otherwise leak into whatever
        renders next on the same faces_program.
        """
        if not self.is_visible:
            return

        start_loc = GL.glGetUniformLocation(faces_program, "stripeClipStart")
        stop_loc = GL.glGetUniformLocation(faces_program, "stripeClipStop")

        GL.glUseProgram(faces_program)
        GL.glUniform1f(start_loc, self._wire.stripe_clip_start)
        GL.glUniform1f(stop_loc, self._wire.stripe_clip_stop)

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
        """Insert a wire layout (drag handle) at the middle of the wire.

        The wire is split into two segments that share the layout point.
        """
        from ...handlers import wire_layout_handler as _wire_layout_handler

        wire = self.selected.parent
        project = self.selected.mainframe.project
        midpoint = self._midpoint()

        _wire_layout_handler._create_wire_layout_on_wire(  # NOQA
            project, wire, midpoint)

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
                position, _ = self.selected.get_closest_point(click_pos)

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
        """Start placing a service loop using this wire's part type."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe
        part_id = self.selected.db_obj.part_id

        _menu_ops.start_handler(
            mainframe,
            lambda: _handlers.AddWireServiceLoopHandler(mainframe, part_id))

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
        _menu_ops.delete_object(
            self.selected, self.selected.mainframe.project.delete_wire)

    def on_properties(self):
        """Show this wire's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
