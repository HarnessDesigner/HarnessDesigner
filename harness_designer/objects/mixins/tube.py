# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""How a wire, a cable or a bundle is drawn, in every view: as tubes handed to the frame's batch.

A path (start, waypoints, stop) is cut into pieces (the straights, and the short chords of a rounded corner; a corner is rounded to a
bend of ``shapes.twisted_wire.BEND_RADIUS_DIAMETERS`` diameters), written as rows into ``gl/wire_pool.py`` when it changes, and
each frame the object hands ``gl/wire_batch.py`` one entry per conductor (its place in the pool, twist rate, circle, material and
stripe). The canvas draws everything handed in with one call per pool arena, so a frame costs the same however many objects it has
(TWISTED_WIRE_DESIGN.md, WAYPOINT_REWORK_DESIGN.md).

The class using this mixin supplies: ``_segment_transforms()`` (one ``(position, angle, scale, length)`` per straight section of the
path), ``_part`` (for a twisted look), ``_material``, ``_selected_material``, ``_stripe_material`` (the stripe's material or ``None``), ``_twist`` (the cable's own
look or ``None``), ``_trunk_size(part)``, and the BaseVar bounds (``is_visible``, ``is_selected``, ``_vbo``, the AABB / OBB
managers). Call :meth:`_init_tubes` once from ``__init__``.
"""

from typing import TYPE_CHECKING, Iterator
from typing import NamedTuple as _NamedTuple
from typing import Union as _Union

import weakref

import numpy as np

from ...shapes import helix as _helix
from ...shapes import twisted_path as _twisted_path
from ...shapes import twisted_wire as _twisted_wire
from ...gl import floor_outline as _floor_outline
from ...gl import materials as _materials
from ...gl import wire_batch as _wire_batch
from ...gl import wire_pool as _wire_pool
from ...ray_tracing import tube_mesh as _tube_mesh
from ... import color as _color
from ... import config as _config
from ... import check_types as _check_types
from ... import logger as _logger
from OpenGL import GL


if TYPE_CHECKING:
    from ...gl import shaders as _shaders


_debug_config = _config.Config.debug.rendering3d
_floor_config = _config.Config.editor_3d.floor

# The floor outline's material (made again when the colour in the config changes)
_outline_material = None
_outline_color = None

# Two path segments whose ends are closer than this are one continuous wire (a stretch hidden inside a bundle leaves a far
# bigger gap); the twist carries on across such a joint.
_TWIST_JOIN_GAP_MM = 0.01

# objects.terminal.Terminal, imported the first time a wire asks whether its end crimps into one (a cycle at import time)
_TERMINAL = None


# Pool keys of the wires already reported as having no length (see TubeMixin._render_tubes).
_reported_empty: set[str] = set()


class TwistLook(_NamedTuple):
    """How a tube is drawn (see ``TubeMixin._build_twist``); the same for every segment of the path."""

    rate: float
    """Twist rate, radians per mm."""

    outer_radius: float
    """Radius of the circle that holds the whole cable, mm."""

    circles: list[tuple[float, float, float]]
    """Where each conductor sits: centre x, centre y, radius (mm), conductor 0 first."""

    materials: list[_materials.GLMaterial]
    """Each conductor's insulation material."""

    stripes: list[_Union[_materials.GLMaterial, None]]
    """Each conductor's stripe material, ``None`` where it has no stripe."""

    rounded: bool = True
    """Whether a corner of the path is rounded to a bend of ``shapes.twisted_wire.BEND_RADIUS_DIAMETERS`` diameters: every look but
    a ribbon cable's (a flat cable does not bend round its own width)."""


class TwistSegment(_NamedTuple):
    """One piece of the path, with what a cable's conductor leads need to meet it."""

    position: tuple[float, float, float]
    rotation: list[float, float, float, float]
    matrix: np.ndarray
    length: float
    twist: _twisted_wire.SegmentTwist
    rings: int


class TubeMixin:
    """Draw the object's path as tubes through the frame's batch. See the module docstring."""

    # True for a wire: its first / last piece is drawn as the bare conductor where it crimps into a terminal. A cable (its
    # siblings are always None) and a bundle never are.
    _has_bare_ends: bool = False

    @_check_types.do
    def _init_tubes(self) -> None:
        """Set up the state the drawing keeps: the plan, the pool rows and the batch entries. Call from ``__init__``."""
        # _twist_plan is the per-segment bookkeeping, thrown away by _recalculate_geometry and rebuilt when the object is next
        # drawn; _gpu_look is the look of a plain tube (one conductor on the axis), built the first time it is wanted (see
        # _active_look), and _twist_plan_look is the look _twist_plan was worked out for
        self._twist_plan = None
        self._gpu_look = None
        self._twist_plan_look = None

        # the input segment each piece of the plan is cut from (-1: a chord of a rounded corner), for the bare conductor ends, and
        # the bare conductor (radius, material), built the first time it is wanted
        self._pool_sources = None
        self._bare = None

        # The path as rows of gl/wire_pool.py: packed together with the plan, written into the pool when the object is next
        # drawn after a change (_pool_dirty), and freed in the pool when the object is garbage collected
        self._pool_key = _wire_pool.new_key()
        self._pool_rows = None
        self._pool_vertices = 0
        self._pool_dirty = False
        weakref.finalize(self, _wire_pool.WirePool.release, self._pool_key)

        # What the object hands the frame's batch: its entries, and what they were made for (the pool stamp, the look, whether
        # it was selected, the selection material)
        self._batch_entries = None
        self._batch_stamp = 0
        self._batch_look = None
        self._batch_selected = False
        self._batch_material = None
        self._batch_bare = (0, 0)

    @_check_types.do
    def _build_twist(self, outer_diameter: float) -> TwistLook:
        """The look of this wire as a twisted pair / triple: the twist rate, where each conductor sits in the cable and
        each conductor's materials. Only called for a wire whose part ``is_twisted``.

        :param outer_diameter: The cable's diameter, mm.
        """
        part = self._part
        materials, stripes = self._conductor_materials()

        return TwistLook(
            _twisted_wire.rate_for(part.tpi, outer_diameter), outer_diameter * 0.5,
            _twisted_wire.profile(len(materials), outer_diameter), materials, stripes)

    @_check_types.do
    def _make_look(self, diameter: float) -> _Union[TwistLook, None]:
        """The look of the wire's conductors, ``None`` for a plain tube: a twisted pair / triple for a part that ``is_twisted``.
        A cable view overrides it for a ribbon.

        :param diameter: The cable's diameter, mm.
        """
        if self._part.is_twisted:
            return self._build_twist(diameter)

        return None

    def _single_radius(self) -> float:
        """The radius of a plain tube, mm: half the trunk's width. A bundle says otherwise (its diameter can change).

        Called a few times per object per frame, so not wrapped in ``check_types.do``.
        """
        return self._trunk_size(self._part)[0] * 0.5

    @_check_types.do
    def _build_single(self) -> TwistLook:
        """The look of a plain wire: one conductor centred on the axis, in the wire's own colour.

        A wire with a stripe twists at the pitch of the stripe's helix mesh (``shapes.helix.PITCH_MM``), so the stripe winds
        round the wire as the mesh does. A wire without one does not twist: a centred circle turning on its own centre looks
        the same at any rate, so it gets the fewest rings. (``shapes.twisted_wire.profile`` is for 2 or more conductors; for 1
        it is degenerate, hence the circle here.)
        """
        radius = self._single_radius()
        stripe = None
        rate = 0.0

        if self._stripe_material is not None:
            stripe = self._stripe_material
            rate = _twisted_wire.rate_from_tpi(_twisted_wire.MM_PER_INCH / _helix.PITCH_MM)

        return TwistLook(rate, radius, [(0.0, 0.0, radius)], [self._material], [stripe])

    def _active_look(self) -> TwistLook:
        """The look this wire is drawn with right now: its twist look, else the single-wire look (rebuilt when the wire's
        material has changed).

        Called a few times per wire per frame, so not wrapped in ``check_types.do``.
        """
        if self._twist is not None:
            return self._twist

        look = self._gpu_look

        if look is None or look.materials[0] is not self._material or look.outer_radius != self._single_radius():
            look = self._build_single()
            self._gpu_look = look

        return look

    @_check_types.do
    def _conductor_materials(self) -> tuple[list[_materials.GLMaterial], list[_Union[_materials.GLMaterial, None]]]:
        """Each conductor's insulation material and stripe material (``None`` for no stripe), from the part's conductor rows
        (``wire_conductors``), conductor 0 first."""
        materials = []
        stripes = []

        for color, stripe_color in self._part.conductor_colors:
            materials.append(_materials.Plastic(color.ui))

            if stripe_color is None:
                stripes.append(None)
            else:
                stripes.append(_materials.Plastic(stripe_color.ui))

        return materials, stripes

    @staticmethod
    @_check_types.do
    def _segment_joins(segments: list[tuple]) -> list[bool]:
        """For each path segment, whether it starts where the one before it ends (the first never reads as joined): a stretch
        hidden inside a bundle breaks the chain. *segments* are ``(position, angle, scale, length)`` as
        ``_segment_transforms`` yields them."""
        joined = [False]

        for i in range(1, len(segments)):
            rotation = segments[i - 1][1].as_matrix_numpy
            end_of_previous = segments[i - 1][0].as_numpy + rotation[:, 2] * segments[i - 1][3]
            gap = float(np.linalg.norm(segments[i][0].as_numpy - end_of_previous))
            joined.append(gap < _TWIST_JOIN_GAP_MM)

        return joined

    @_check_types.do
    def _twist_segments(self) -> list[TwistSegment]:
        """The path segments with their twist phase, mitres and ring counts, worked out once per change of the path
        (``_recalculate_geometry`` clears it) rather than every frame."""
        look = self._active_look()

        if self._twist_plan is not None and self._twist_plan_look is look:
            return self._twist_plan

        segments = list(self._segment_transforms())
        joined = np.array(self._segment_joins(segments), dtype=np.uint8)

        count = len(segments)
        starts = np.empty((count, 3))
        rotations = np.empty((count, 3, 3))
        quats = np.empty((count, 4))
        lengths = np.empty(count)

        for i, (position, angle, _scale, length) in enumerate(segments):
            starts[i] = position.as_numpy
            rotations[i] = angle.as_matrix_numpy
            quats[i] = angle.as_quat_numpy
            lengths[i] = length

        # Rounding the corners, the frame of every chord, the twist phase and mitres and the ring counts are all worked out in
        # one compiled call on plain arrays (shapes/twisted_path.pyx); no Point or Angle is made per piece.
        positions, piece_quats, piece_lengths, phases, start_mitres, end_mitres, rings, sources, matrices = (
            _twisted_path.build_path(
                starts, rotations, quats, lengths, joined, _twisted_wire.BEND_RADIUS_DIAMETERS * 2.0 * look.outer_radius,
                look.rounded, look.rate, look.outer_radius, 0.0, _twisted_wire.BEND_STEP, _twisted_wire.SAMPLES_PER_TURN,
                _twisted_wire.MAX_RINGS))

        position_rows = positions.tolist()
        quat_rows = piece_quats.tolist()
        length_rows = piece_lengths.tolist()
        phase_rows = phases.tolist()
        start_rows = start_mitres.tolist()
        end_rows = end_mitres.tolist()
        ring_rows = rings.tolist()

        plan = []

        for i in range(len(position_rows)):
            twist = _twisted_wire.SegmentTwist(phase_rows[i], tuple(start_rows[i]), tuple(end_rows[i]))
            plan.append(TwistSegment(tuple(position_rows[i]), quat_rows[i], matrices[i], length_rows[i], twist, ring_rows[i]))

        self._twist_plan = plan
        self._twist_plan_look = look

        self._pool_sources = sources
        self._pool_rows, self._pool_vertices = _wire_pool.WirePool.pack(
            positions, piece_quats, piece_lengths, phases, start_mitres, end_mitres, rings, _twisted_wire.SIDES * 6)
        self._pool_dirty = True

        return plan

    @_check_types.do
    def _curve_chords(self) -> list[tuple[np.ndarray, np.ndarray]]:
        """The path as drawn, as ``(start, end)`` of each short straight piece (a rounded corner is several), in world space.
        A stretch hidden inside a bundle is not there."""
        chords = []

        for piece in self._twist_segments():
            start = np.asarray(piece.position, dtype=np.float64)
            chords.append((start, start + piece.matrix[:, 2] * piece.length))

        return chords

    @_check_types.do
    def _render_floor_outline(self, shaders: "_shaders.ShaderProgram") -> None:
        """Cast the outline of the path as seen from above onto the floor, in the floor-projection colour and width of the config (``Config.debug.rendering3d``):
        the path as drawn (rounded corners), a tube wide, flattened along Y. Replaces the rectangle per section the selected
        overlay used to project. Needs the GL context; draws only while the object is selected and visible."""
        global _outline_material, _outline_color

        if not self.is_selected or not self.is_visible:
            return

        chords = self._curve_chords()

        if not chords:
            return

        radius = self._active_look().outer_radius
        loops = _floor_outline.silhouette_loops(chords, radius)

        # a fixed width (Config.debug.rendering3d.floor_projection_width), just above the floor mesh, which would otherwise z-fight
        vertices = _floor_outline.outline_vertices(loops, float(_debug_config.floor_projection_width),
                                                   _floor_config.ground_height + 0.03)

        color = tuple(_debug_config.floor_projection_color)

        if _outline_color != color:
            _outline_material = _materials.Glowing(_color.Color(*color))
            _outline_color = color

        GL.glDepthMask(GL.GL_FALSE)

        try:
            _floor_outline.FLOOR_OUTLINE.draw(shaders.faces, _outline_material, vertices)
        finally:
            GL.glDepthMask(GL.GL_TRUE)

    @_check_types.do
    def _render_tubes(self) -> None:
        """Hand the wire to the frame's batch (``gl/wire_batch.py``), which draws every wire of the frame with one call when
        the canvas has drawn its objects. Selected, every conductor takes the selection colour, so the highlight stays one
        uniform colour.

        Only the faces pass is drawn: the debug edge / normal / vertex passes have no twist mode (TWISTED_WIRE_DESIGN.md,
        section 5), and a crimp end is not drawn at the conductor's own diameter.
        """
        if not self.is_visible:
            return

        if self._vbo.is_dirty:
            self._compute_aabb()
            self._compute_obb()

        self._aabb_manager.mark_visible(self._aabb_index)
        self._obb_manager.mark_visible(self._obb_index)

        if not _debug_config.draw_faces:
            return

        self._twist_segments()

        # A path with no length (both ends on one spot) packs to no rows, and asking the pool for none raised on every frame (a render
        # failure report each time). There is nothing to draw; say so once, with which wire it is.
        if len(self._pool_rows) == 0:
            if self._pool_key not in _reported_empty:
                _reported_empty.add(self._pool_key)
                _logger.warning(f'{type(self).__name__} {self.db_obj.db_id.hex()} has no length (its ends are on one spot): not drawn')

            return

        self._batch_wire(self._active_look(), self.is_selected)

    @_check_types.do
    def _write_pool_rows(self) -> None:
        """Make sure the pool holds the rows of the current path (writing them when the path has changed since the wire was
        last drawn). Needs the GL context."""
        self._twist_segments()

        if self._pool_dirty:
            _wire_pool.WirePool.set_rows(self._pool_key, self._pool_rows, self._pool_vertices)
            self._pool_dirty = False

    def _batch_wire(self, look: TwistLook, selected: bool) -> None:
        """Hand the wire to this frame's batch (``gl/wire_batch.py``): one entry per conductor, with the wire's material, stripe,
        rate and size in it, drawn with every other wire of the frame in one call. A one-conductor wire whose end crimps into a
        terminal gets an entry of its own for the bare conductor there (the conductor's diameter and the core's material), as it
        always had. The entries are made again only when what they were made for has changed (the wire's place in the pool, its
        look, the selection, which ends are bare); a frame in which nothing about the wire changed costs a few comparisons and a
        list append per conductor. Selected, every conductor takes the selection colour and has no stripe, and no end is bare, so
        the highlight is one uniform colour.

        Called once per wire per frame, so not wrapped in ``check_types.do``.
        """
        self._write_pool_rows()

        stamp = _wire_pool.WirePool.stamp(self._pool_key)
        bare_start, bare_stop = self._bare_ends(look, selected)

        if (self._batch_entries is None or self._batch_stamp != stamp or self._batch_look is not look or
                self._batch_selected != selected or self._batch_material is not self._selected_material or
                self._batch_bare != (bare_start, bare_stop)):
            count = len(look.circles)
            ends = None

            if selected:
                materials = [self._selected_material] * count
                stripes = [None] * count
            else:
                materials = look.materials
                stripes = look.stripes

            if bare_start or bare_stop:
                radius, material = self._bare_conductor()
                ends = (bare_start, bare_stop, (0.0, 0.0, radius), material)

            self._batch_entries = _wire_batch.entries_for(self._pool_key, look.rate, look.circles, materials, stripes,
                                                          _twisted_wire.STRIPE_HALF_ANGLE, self._pool_rows, ends)
            self._batch_stamp = stamp
            self._batch_look = look
            self._batch_selected = selected
            self._batch_material = self._selected_material
            self._batch_bare = (bare_start, bare_stop)

        texture, entries, counts = self._batch_entries

        for entry, vertices in zip(entries, counts):
            _wire_batch.BATCH.add(texture, entry, vertices)

    @_check_types.do
    def ray_trace_meshes(self) -> Iterator[tuple[np.ndarray, np.ndarray, _materials.GLMaterial]]:
        """The triangles the ray tracer renders for this object (``ray_tracing.scene.Scene.add_object``): the tubes the viewport
        draws, made on the CPU by ``ray_tracing/tube_mesh.py`` from the same pieces, so the corners are as rounded, the conductors
        as twisted and the joints as smooth. Yields ``(vertices, normals, material)`` (world space, three corners per triangle)
        for each conductor, and for its stripe. Selected, every conductor takes the selection material and has no stripe, and no
        end is bare, as in the viewport; a wire that crimps into a terminal has its bare conductor drawn there.
        """
        look = self._active_look()
        pieces = self._twist_segments()
        selected = self.is_selected

        if selected:
            materials = [self._selected_material] * len(look.circles)
            stripes = [None] * len(look.circles)
        else:
            materials = look.materials
            stripes = look.stripes

        bare_start, bare_stop = self._bare_ends(look, selected)
        first = bare_start
        last = len(pieces) - bare_stop

        if bare_start or bare_stop:
            radius, material = self._bare_conductor()
            ends = pieces[:first] + pieces[last:]

            body, _stripe = _tube_mesh.conductor_mesh(ends, 0.0, (0.0, 0.0, radius), 0.0)

            if body is not None:
                yield body[0], body[1], material

        pieces = pieces[first:last]

        for circle, material, stripe_material in zip(look.circles, materials, stripes):
            if stripe_material is None:
                half = 0.0
            else:
                half = _twisted_wire.STRIPE_HALF_ANGLE

            body, stripe = _tube_mesh.conductor_mesh(pieces, look.rate, circle, half)

            if body is not None:
                yield body[0], body[1], material

            if stripe is not None:
                yield stripe[0], stripe[1], stripe_material

    def _bare_ends(self, look: TwistLook, selected: bool) -> tuple[int, int]:
        """How many pieces at the start and at the end of the path are drawn as the bare conductor: the straight piece cut from
        the first (last) input segment when this is a one-conductor wire that crimps into a terminal there, not selected. A wire of
        a single piece is bare throughout when either end crimps. Not wrapped in ``check_types.do`` (per wire per frame)."""
        if selected or not self._has_bare_ends or len(look.circles) != 1 or self._twist is not None:
            return 0, 0

        start_bare, stop_bare = self._conductor_segment_ends()

        if not start_bare and not stop_bare:
            return 0, 0

        sources = self._pool_sources

        if len(sources) == 1:
            return 1, 0

        last = int(sources.max())
        start_pieces = 0
        stop_pieces = 0

        if start_bare and sources[0] == 0:
            start_pieces = 1

        if stop_bare and sources[-1] == last:
            stop_pieces = 1

        return start_pieces, stop_pieces

    def _conductor_segment_ends(self) -> tuple[bool, bool]:
        """(start_is_conductor, stop_is_conductor): whether the first / last sub-segment crimps directly into a Terminal and is
        drawn bare-conductor-sized and coloured instead of at the wire's insulation diameter and material.

        Checked via the sibling graph (``parent.start_sibling`` / ``stop_sibling``, a cheap weakref lookup maintained by
        ``Terminal.add_wire``) rather than the raw point ids: a splice or wire service loop sibling never gets the conductor
        treatment, only an actual Terminal. (False, False) for anything that is not a wire."""
        if not self._has_bare_ends:
            return False, False

        global _TERMINAL

        if _TERMINAL is None:
            from .. import terminal as _terminal  # NOQA -- avoid a cycle at import time

            _TERMINAL = _terminal.Terminal

        return (isinstance(self.parent.start_sibling, _TERMINAL),
                isinstance(self.parent.stop_sibling, _TERMINAL))

    @_check_types.do
    def _bare_conductor(self) -> tuple[float, object]:
        """The bare conductor's radius and material: ``conductor_dia_mm`` (which already falls back to an AWG-derived estimate when
        the wire_size_dia column is NULL; two thirds of the outside diameter is the last resort for a part missing both, the ratio a
        stranded copper core typically is of its insulated OD) and the core's polished metal."""
        if self._bare is None:
            conductor_dia = self._part.conductor_dia_mm

            if not conductor_dia:
                conductor_dia = self._trunk_size(self._part)[0] * (2.0 / 3.0)

            self._bare = (conductor_dia * 0.5, _materials.Polished(self._part.core_material.color.ui))

        return self._bare
