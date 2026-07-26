# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math

from OpenGL import GL
from PySide6.QtWidgets import QMenu

from . import base2d as _base2d
from ...geometry import angle as _angle
from ...geometry import point as _point
from ... import config as _config
from ...gl import materials as _materials
from ...shapes import cylinder as _cylinder
from ...shapes import helix as _helix


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire as _pjt_wire
    from .. import wire as _wire


Config = _config.Config.editor2d


class Wire(_base2d.Base2D):
    """
    2D representation of a wire for schematic view

    Renders as a cylinder between its two endpoints -- the *same* shared
    ``shapes/cylinder.py`` mesh ``objects3d/wire.py``'s ``Wire`` uses,
    positioned at the start point and scaled/rotated to reach the stop
    point, plus (if the part has a stripe color) the *same* shared
    growable helix stripe mesh (``shapes/helix.py``) that wire uses too
    -- rendered as an extra (see :meth:`render_extras`), clipped to this
    segment via the ``stripeClipStart``/``stripeClipStop`` uniforms
    ported into ``gl/shaders/schematic2d.py`` for this purpose (mirrors
    ``gl/shaders/faces.py``'s mechanism exactly, minus the geometry-
    shader floor-reflection step that shader has and this one doesn't
    need). The ``schematic2d`` vertex shader already does the full
    3D transform (quaternion rotation, scale, translation) before
    projecting down to 2D -- there's no need for a flat-only mesh here
    the way ``objects2d/housing.py``'s rectangle/``objects2d/cavity.py``'s
    text are, since a cylinder viewed edge-on from directly above already
    reads as a plain rectangle.

    Unlike the 3D editor's real ``od_mm``, every wire renders at the same
    fixed width (``Config.editor2d.wire.diameter``); unlike 3D's
    ``stripe_clip_start``/``stripe_clip_stop`` (calibrated to real 3D
    routing length and chained across split segments so the phase never
    jumps at a splice), each 2D segment's stripe starts fresh at its own
    beginning -- the 2D schematic's endpoint distances are laid out
    positions, not physical lengths, so there's no meaningful shared
    phase to preserve across a chain here.

    Wire Connection Rules:
    - Wire endpoints can ONLY attach to: Terminals, Splices, or WireLayouts (handles)
    - WireLayouts (handles) can be added along the wire for positioning
    """
    _parent: "_wire.Wire" = None
    db_obj: "_pjt_wire.PJTWire"

    def __init__(self, parent: "_wire.Wire", db_obj: "_pjt_wire.PJTWire"):
        """Initialise the :class:`Wire` instance.

        :param parent: Parent object.
        :type parent: :class:`_wire.Wire`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire.PJTWire`
        """
        self._part = db_obj.part

        self._p1 = db_obj.start_position2d
        self._p2 = db_obj.stop_position2d

        material = _materials.Generic(self._part.color.ui)

        stripe_color = self._part.stripe_color
        self._stripe_material = (
            _materials.Generic(stripe_color.ui) if stripe_color is not None else None)

        diameter = Config.wire.diameter
        self._length = self._calc_length()
        scale = _point.Point(diameter, diameter, self._length)

        # No angle2d column on PJTWire -- rotation is fully derived from
        # the two endpoints (see _recalculate_geometry), same reason
        # objects2d/splice.py's Splice/objects2d/wire_layout.py's
        # WireLayout use a static, unbound identity Angle.
        angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)

        parent.mainframe.editor2d.editor.context.acquire()
        vbo = _cylinder.create_vbo()

        if self._stripe_material is not None:
            _helix.create_vbo(self._length)

        # Base2D.__init__ (below) already binds self._p1 (passed as
        # position) to _update_position -- this covers the other
        # endpoint, so either one moving recomputes geometry.
        self._p2.bind(self._update_position)

        super().__init__(parent, db_obj, vbo, angle, self._p1, scale, material)

        self._recalculate_geometry()
        parent.mainframe.editor2d.editor.context.release()

    def _calc_length(self) -> float:
        a = self._p1.as_numpy
        b = self._p2.as_numpy
        dx = b[0] - a[0]
        dz = b[2] - a[2]
        return math.sqrt(dx * dx + dz * dz)

    def _recalculate_geometry(self):
        """Recompute this wire's length, angle, and OBB/AABB from its
        current endpoints -- called (via :meth:`_update_position`)
        whenever either endpoint moves.
        """
        a = self._p1.as_numpy
        b = self._p2.as_numpy

        dx = b[0] - a[0]
        dz = b[2] - a[2]
        length = math.sqrt(dx * dx + dz * dz)

        if length < 0.001:
            return

        self._length = length
        self._scale.z = length

        if self._stripe_material is not None:
            _helix.create_vbo(self._length)

        # Rotate local +Z (the cylinder's own length axis when
        # unrotated) to align with (dx, dz) -- angle sign verified
        # empirically against _rotate_about_y (objects2d/base2d.py):
        # local +Z (0,0,1) rotates to (sin(deg), 0, cos(deg)), so
        # aligning with an arbitrary (dx, dz) needs atan2(dx, dz).
        self._angle.y = math.degrees(math.atan2(dx, dz))

        self._compute_obb()
        self._compute_aabb()

    def _update_position(self, _position: _point.Point):
        """Recompute geometry immediately whenever either endpoint
        moves -- mirrors ``objects3d/wire.py``'s ``Wire._update_position``
        exactly (this wire's own ``numpy_position`` cache is never read;
        ``_p1``/``_p2`` are read fresh from the live Point objects every
        time, so there's nothing for the inherited ``BaseVar``
        implementation to usefully update here).
        """
        self._recalculate_geometry()

    def render_extras(self, program, pos_loc, rot_loc, scale_loc, normal_loc):
        """Render this wire's stripe (if its part has a stripe color) as
        a clipped window into the shared helix mesh -- see the class
        docstring. Piggybacks on this wire's own render pass, same as
        ``objects3d/wire.py``'s ``WireStripe`` (not a separately-
        registered scene object; nothing else ever calls this for it).
        """
        if self._stripe_material is None or self._position is None:
            return

        stripe_vbo = _helix.create_vbo(self._length)

        start_loc = GL.glGetUniformLocation(program, 'stripeClipStart')
        stop_loc = GL.glGetUniformLocation(program, 'stripeClipStop')

        self._stripe_material.set(program)
        GL.glUniform1i(normal_loc, 0)
        GL.glUniform4f(rot_loc, *[float(str(v)) for v in self._angle.as_quat_numpy.tolist()])
        GL.glUniform3f(scale_loc, *self._scale.as_float)
        GL.glUniform3f(pos_loc, self._position.x, 0.0, self._position.z)

        GL.glUniform1f(start_loc, 0.0)
        GL.glUniform1f(stop_loc, self._length)

        stripe_vbo.render()

        GL.glUniform1f(start_loc, 0.0)
        GL.glUniform1f(stop_loc, 0.0)


class WireMenu(QMenu):
    """Represent a wire menu in :mod:`harness_designer.objects.objects2d.wire`.

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

    def on_add_handle(self):
        """Handle the add handle event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_marker(self):
        """Handle the add marker event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_splice(self):
        """Handle the add splice event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_wire(self):
        """Handle the add wire event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_wire_service_loop(self):
        """Handle the add wire service loop event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_to_bundle(self):
        """Handle the add to bundle event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_trace_circuit(self):
        """Handle the trace circuit event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_select(self):
        """Handle the select event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_delete(self):
        """Handle the delete event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_properties(self):
        """Handle the properties event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass
