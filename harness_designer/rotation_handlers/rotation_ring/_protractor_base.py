# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
The washer, the 360 tick marks and the 36 degree labels of one protractor
ring -- the part of the rotation gizmo that :mod:`.inner_ring` and
:mod:`.outer_ring` share. How the gizmo as a whole fits together is in
:mod:`harness_designer.rotation_handlers.rotation_ring`; this module is how a
ring is built, stored and drawn so that turning it costs almost nothing.

THE IDEA: BUILD ONCE IN THE RING'S OWN FRAME, MOVE WITH ONE ROTATION
====================================================================
A protractor ring is a rigid object. Its ticks never move relative to each
other or to the washer; what changes is where the whole ring sits and how it
is turned, and that is one centre and one rotation. So everything about the
ring that does not depend on that is computed ONCE, in the ring's own frame
(centre at the origin, ring plane = XY, +Z = the ring's normal, tick *i* at
``i`` degrees counter-clockwise from +X), and kept as arrays and GPU buffers:

* the washer: one VBO (``_disc_vbo``), as it always was;
* all 360 ticks: ONE VBO (``_ticks_vbo``), a single mesh that holds every tick
  already placed, sized and aimed in the ring's frame (see TICK MESH);
* the 360 pick boxes of the outer ring: three NumPy arrays (see PICKING);
* the label offsets and the glyph meshes of the 36 labels.

A frame, and an angle change, then only have to carry that frame to the world::

    world point = center + R @ local point        (R: the ring's 3x3 rotation)

which is ``objectPosition = center`` and ``objectRotation = the ring's
quaternion`` on the draw -- the same two uniforms every mesh in the program
already has. Nothing about a tick is a ``Point`` or an ``Angle`` any more: an
earlier version kept one ``Point`` and one ``Angle`` per tick (360 of each, per
ring, two rings per axis) and rebuilt every one of them on every angle change
(90 ms, 95% of it in ``Angle.from_direction``) and drew each with its own
call (397 draws, 11.8 ms of Python per ring). Those numbers are why this module
is the way it is; the current ones are in COST below.

WHAT CAN CHANGE, AND WHAT EACH THING COSTS
==========================================
============================  ===================================================
Event                          Work
============================  ===================================================
the ring turns                 :meth:`reposition_all`: the ring's quaternion and
(object angle changed)         matrix are stored (two small calls), the labels'
                               positions and orientations are recomputed with a
                               handful of array operations over 36 rows. The
                               ticks and pick boxes need NOTHING: they are in the
                               ring's frame and move with the draw's rotation.
the centre moves               The washer and ticks follow the shared ``center``
                               ``Point`` on the very next frame (it is read live
                               for the draw). The labels are re-oriented by
                               :meth:`reposition_all`, which whoever moves the
                               centre must call (``Rings3D._update_position`` does).
the camera moves               :meth:`_on_camera_moved` re-aims the 36 labels (3D
                               view only; the 2D views have no camera): one
                               vectorised billboard + one quaternion conversion.
the radii change               :meth:`set_radii` rebuilds the washer VBO and the
(object resized)               tick VBO and the arrays derived from the radii.
                               Rare; not per frame.
a tick is hovered              Nothing is rebuilt. The tick VBO is drawn in up to
(outer ring)                   three ranges, the hovered tick's in red (RENDER).
the mouse moves                The outer ring tests the ray against all 360 boxes
(outer ring)                   in one array pass (PICKING).
============================  ===================================================

TICK MESH
=========
:meth:`_build_ticks_vbo` makes the single mesh. A tick is a thin prism
(``_TICK_SIDES`` = 8 sides) with its base at the tick's start radius and its
tip ``tick_len`` further along its growth direction: outward from the inner
radius for the outer ring, inward from the outer radius for the inner ring
(``labels_outward`` says which). The prototype prism (the unit cylinder of
:mod:`harness_designer.shapes.cylinder`, base-anchored: ``z`` from 0 to 1) is
scaled by ``(d, d, tick_len)`` and carried by the tick's own frame::

    x axis = tangent  (-sin t, cos t, 0)
    y axis = grow * normal  (0, 0, grow)
    z axis = grow * radial  (cos t, sin t, 0)        grow = +1 outward, -1 inward

a right-handed frame for either ``grow`` (so the triangle winding is
untouched). A prism has no front or back, so which way ``x`` and ``y`` point
around ``z`` does not show. Normals go through the same frame (divided by the
scale first, as the vertex shader does, then normalised). All 360 are done in
three ``einsum`` calls and concatenated into one buffer: tick ``i`` owns the
vertices ``[i * V, (i + 1) * V)`` where ``V`` is one prism's vertex count
(``_ticks_per_vertex``). That layout is what lets the hovered tick be drawn on
its own. 8 sides, not the 360 of the shared cylinder the ticks used to be
drawn with: a tick is 0.6% of the outer radius wide, a few pixels at most, and
360 ticks of 360 sides would be about 28 MB of vertices per ring (against about
0.6 MB).

LABELS
======
Each label is a :class:`~harness_designer.shapes.text.Text` of one word (a
number between -180 and 170), whose word mesh is a pooled VBO. The ring does not
call ``Text.render`` (which builds ``Point`` and ``Angle`` objects and compares
them every frame); it asks the ``Text`` for its word meshes and offsets once
(``Text.word_draw_data``) and places them itself:

    word position = label position + rotate(label rotation, word offset)
    draw scale    = (label_size, label_size, 1)

exactly what ``Text.render`` computes. The label position is
``center + R @ (radial * label_radius)`` (outside the washer's outer edge for
the outer ring, inside the inner edge for the inner ring; see
:meth:`_recompute_local_geometry`). Its rotation depends on the view:

* 3D (a camera was given): a CYLINDRICAL BILLBOARD, the label turns about
  world Y to face the camera and never rolls with it (``Y`` is swapped for
  ``Z`` within 2.5 degrees of straight up/down, where the cross product
  degenerates). That is ``shapes.text._billboard_matrices``, converted to
  quaternions in one call (:func:`~harness_designer.geometry.batch.quaternions_from_matrices`).
  A row whose position coincides with the camera keeps its previous rotation.
* 2D views (no camera; the schematic and peg board are locked top-down, which
  is the billboard's degenerate case): the label lies in the ring plane with the
  rotation of the tick it belongs to (``Angle.from_direction`` of the tick's
  growth direction, in one call: :func:`~harness_designer.geometry.batch.quaternions_from_directions`).
* if the ring was given a ``local_tilt`` (the 2D views' ``TOP_DOWN_TILT``) it is
  composed in front, ``tilt + rotation``, as ``Text.render`` did.

A label whose rotation or the ring's centre changes is re-placed by
:meth:`_update_labels`, which does all 36 at once; at draw time the 36 meshes are
the only per-object draws left (one call each, :meth:`VBOHandlerBase.render_raw`).

RENDER
======
One frame of a ring is: the washer (one draw), the ticks (ONE draw, or three
while one is hovered: the ticks before it, the ticks after it, and it, in
:data:`_HOVER_COLOR`), then the 36 labels. Draws go through
:meth:`~harness_designer.gl.vbo.VBOHandlerBase.render_raw`, which takes plain
floats. The washer and the ticks use the ring's cached quaternion (computed in
:meth:`reposition_all`, not per frame) and the live ``center``.

PICKING
=======
The outer ring's ticks are picked with a real ray against each tick's own
oriented box (the box of the prism: ``tick_len`` along the growth direction,
``tick_diameter`` across). The 360 boxes are stored once in the ring's frame:
``_box_centre_l`` ``(360, 3)``, ``_box_axes_l`` ``(360, 3, 3)`` (the three unit
axes of each box) and ``_box_half`` ``(360, 3)`` (half extents), 34 KB in all.
:meth:`.outer_ring.OuterRing.pick_tick_index` carries them to the world with the
ring's matrix (``centre_l @ R.T + center``; ``axes_l @ R.T``: one matmul each)
and tests the ray against every box in one vectorised slab test (the same
test as ``gl.object_picker._ray_intersect_obb``, over arrays). Nothing about a
box is stored in world space, so there is nothing to keep in sync and nothing
that can be stale.

INVARIANTS (what the rest of the gizmo relies on)
=================================================
* :meth:`reposition_all` must be called whenever the ring's orientation or the
  centre changes; it is cheap, and it skips itself when neither changed. A
  subclass's ``__init__`` calls it once (with its ring angle) and then
  :meth:`start_camera_tracking`, in that order.
* The ring's world transform is only ever ``center`` + ``R``; no tick, box or
  label holds a world position of its own except the 36 label positions
  (``_label_rel`` + the live centre), refreshed by the calls above.
* The GPU buffers belong to the GL context given to the constructor; every
  place that builds or releases them does so inside ``with context``.
* Everything per-tick is array data indexed by tick number ``0..359`` (degrees
  of ``TICK_STEP_DEGREES``); the labels are the ticks at multiples of
  ``MAJOR_TICK_STEP_DEGREES``, ``_major_index`` lists them.
* A moved or resized object calls :meth:`set_radii`; nothing else rebuilds a mesh.

COST
====
Measured with the real classes on interpreted Python 3.11 in an offscreen GL
context (the compiled build is faster in absolute terms), one inner ring (360
ticks, 36 labels, washer), before -> after. The inner and the outer ring are
both drawn while an axis is active, so a frame with the gizmo open pays the
render figure twice.

=============================================  ===========  ==========
What                                            Before       After
=============================================  ===========  ==========
draw one ring, 3D view (CPU submit)             11.99 ms     0.70 ms
draw one ring, 2D views (no camera, tilt)       25.27 ms     0.58 ms
the object turns (``reposition_all``), 3D       91.4 ms      1.9 ms
the object turns, 2D views                      84.2 ms      1.8 ms
camera moves (3 coordinate writes), 3D          22.2 ms      0.94 ms
build a ring                                    269 ms       35 ms
pick the tick under the mouse (outer ring)      16 ms (a)    0.15 ms
=============================================  ===========  ==========

(a) the per-box ray test alone over 360 boxes; the screen-bounds pass that ran
before it projected 8 corners per tick in Python and was not timed.

The pixels are the same: five rendered frames (3D with the object turned, the
centre moved and the camera moved; the 2D top-down view with the tilt) were
compared pixel by pixel with the old code's, and no pixel differs by more than
32 levels, though the ticks are now 8-sided prisms instead of 360-sided
cylinders. The slab test agrees with ``gl.object_picker._ray_intersect_obb``
on every box tried, and the helpers in :mod:`harness_designer.geometry.batch`
agree with ``Angle.from_matrix``, ``Angle.from_direction`` and ``Point @ Angle``
to better than 1e-6 (checked on random rotations and the half-turn cases).

What a frame still costs is 38 draws per ring (the washer, the tick mesh, 36
labels) at about 18 us of Python each; what an angle change still costs is
mostly ``_disc_rotation()`` (a ``Decimal`` quaternion built from the object's
Euler angles, 0.7 ms) and the matrix and quaternion read off it.
"""

from typing import TYPE_CHECKING

import build123d
import numpy as np

from ...shapes import disc_ring as _disc_ring
from ...shapes import cylinder as _cylinder
from ...shapes import text as _text
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry import batch as _batch
from ...gl import materials as _materials
from ...gl import vbo as _vbo_handler
from ... import utils as _utils
from ... import check_types as _check_types
from .. import rotation_mesh as _rotation_mesh
from ... import color as _color
from ...gl import shaders as _shaders
from ...gl.canvas_base import camera_base as _camera_base


if TYPE_CHECKING:
    from ...gl import context as _gl_context
    from ...gl.materials import material as _material
    from ...gl.shaders import program as _shader_program


# One minor (unlabeled) tick every degree; every 10th is a longer, labeled
# major tick -- 360 total, 36 of them major.
TICK_STEP_DEGREES = 1.0
MAJOR_TICK_STEP_DEGREES = 10.0
TICK_COUNT = int(360.0 / TICK_STEP_DEGREES)

# Sides of the prism one tick is made of (see this module's TICK MESH).
_TICK_SIDES = 8

# Fixed tick color -- deliberately independent of the washer's own
# (axis- or outer-tinted) material so the ticks always read clearly
# against it, regardless of which ring or axis this is.
_TICK_COLOR = (0.0, 0.0, 0.0)

_UNIT_SCALE = (1.0, 1.0, 1.0)

# (vertices, smooth normals, face normals) of one tick prism, each (V, 3),
# built on first use (the same for every ring).
_tick_prototype_cache: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None


@_check_types.do
def _tick_prototype() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The unit tick prism: ``_TICK_SIDES`` sides, radius 0.5, base at z = 0,
    tip at z = 1 (the unit cylinder of ``shapes.cylinder``, at a low side
    count), as (vertices, smooth normals, face normals), float64."""

    global _tick_prototype_cache

    if _tick_prototype_cache is None:
        vertices, faces = _cylinder.create(0.5, 1.0, _TICK_SIDES, 1)
        packed, count = _utils.compute_normals(vertices, faces)

        _tick_prototype_cache = (
            packed[:count * 3].reshape(-1, 3).astype(np.float64),
            packed[count * 3:count * 6].reshape(-1, 3).astype(np.float64),
            packed[count * 6:count * 9].reshape(-1, 3).astype(np.float64))

    return _tick_prototype_cache


class ProtractorRingBase:
    """
    Shared washer + ticks + labels for one axis's protractor display.

    How it works -- the single tick mesh, the label placement, the pick
    arrays and what each event costs -- is in this module's docstring; read
    that first.

    :param center: World-space center -- shared reference (not copied),
        same as every other piece of this gizmo.

    :param inner_radius: Washer/tick-band inner radius (ID).

    :param outer_radius: Washer/tick-band outer radius (OD). Tick marks
                         hang inward from this edge.

    :param depth: World-space thickness along the ring's normal axis.

    :param material: Material the translucent washer renders with.

    :param label_size: Font size passed to each major tick's :class:`Text`.

    :param camera: The 3D camera the labels turn to face, or ``None`` (the
                   2D views) for labels that lie in the ring plane.

    :param labels_outward: Which side of this washer has open space for
                           labels to sit in, clear of the disc's own face
                           -- ``True`` places them just beyond the OD,
                           ``False`` just inside the ID. The torus ring sits
                           exactly at the inner protractor's OD / outer
                           protractor's ID (see :mod:`~.rotation_ring`'s own
                           docstring), so :class:`.inner_ring.InnerRing` passes
                           ``False`` (the object-ward side, at its ID, is the
                           only side clear of the torus) and
                           :class:`.outer_ring.OuterRing` passes ``True``
                           (the outward side, at its OD, is the only side clear
                           of the torus). It also decides which way the ticks
                           grow (away from the edge the labels are on).

    :param local_tilt: A fixed rotation composed in front of every label's
                       rotation (the 2D views' top-down tilt), or ``None``.
    """

    # Tick length, as a fraction of the band width (outer_radius -
    # inner_radius) -- major (10-degree, labeled) ticks reach 3/4 of the
    # way across the band, minor (1-degree) ones half way, both anchored
    # at the same edge labels_outward points away from.
    _MAJOR_TICK_LENGTH_FRAC = 0.75
    _MINOR_TICK_LENGTH_FRAC = 0.5

    # tick diameter, as a fraction of outer_radius
    _TICK_DIAMETER_FRAC = 0.006

    # label standoff beyond the washer's own free edge, as a fraction of band width
    _LABEL_GAP_FRAC = 0.12

    # The tick drawn in this colour while it is hovered (the outer ring
    # overrides this and sets _hovered_index; the inner ring never hovers).
    _HOVER_COLOR = _TICK_COLOR

    # Index (0..359, degrees / TICK_STEP_DEGREES) of the tick to draw in
    # _HOVER_COLOR, or None.
    _hovered_index: int | None = None

    @_check_types.do
    def __init__(self, axis: str, center: _point.Point, inner_radius: float,
                 outer_radius: float, depth: float, material: _materials.GLMaterial,
                 label_size: float, context: "_gl_context.GLContext", camera: _camera_base.CameraBase | None = None,
                 labels_outward: bool = True, local_tilt: _angle.Angle | None = None):

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

        if local_tilt is None:
            self._tilt_quat: np.ndarray | None = None
        else:
            self._tilt_quat = np.asarray(local_tilt.as_quat_numpy, dtype=np.float64)

        # Set by reposition_all -- lets it skip its own work when neither the
        # ring's orientation nor the centre changed since last time.
        # Genuinely common: the gyroscope nesting (see rotation_mesh.py)
        # means most rings DON'T move on most angle changes.
        self._last_ring_angle_quat: np.ndarray | None = None
        self._last_center: np.ndarray | None = None

        # The ring's current world transform (see this module's docstring):
        # the quaternion (w, x, y, z) as the list the draw takes, and the
        # matching column-vector rotation matrix.
        self._ring_quat: list[float] = [1.0, 0.0, 0.0, 0.0]
        self._ring_matrix = np.eye(3, dtype=np.float64)

        # ---- per-tick geometry in the ring's own frame, row i = tick i
        theta = np.radians(np.arange(TICK_COUNT, dtype=np.float64) * TICK_STEP_DEGREES)

        self._local_radials = np.stack(
            [np.cos(theta), np.sin(theta), np.zeros(TICK_COUNT)], axis=1)

        self._local_tangents = np.stack(
            [-np.sin(theta), np.cos(theta), np.zeros(TICK_COUNT)], axis=1)

        degrees = np.arange(TICK_COUNT, dtype=np.float64) * TICK_STEP_DEGREES
        self._is_major_mask = (degrees % MAJOR_TICK_STEP_DEGREES) == 0.0

        # Which ticks are labeled -- fixed for the ring's whole lifetime.
        self._major_index = np.flatnonzero(self._is_major_mask)

        # Filled by _recompute_local_geometry (from the radii), below.
        self._tick_lens = np.zeros(TICK_COUNT, dtype=np.float64)
        self._tick_diameter = 0.0
        self._tick_start_radius = 0.0
        self._tick_grow = 1.0
        self._label_local_offsets = np.zeros((len(self._major_index), 3), dtype=np.float64)

        # The pick boxes (see PICKING): centre, the three unit axes and the half
        # extents of every tick's box in the ring's frame.
        self._box_centre_l = np.zeros((TICK_COUNT, 3), dtype=np.float64)
        self._box_axes_l = np.zeros((TICK_COUNT, 3, 3), dtype=np.float64)
        self._box_half = np.zeros((TICK_COUNT, 3), dtype=np.float64)

        self._ticks_per_vertex = 0

        self._label_material = _materials.Polished(
            _color.Color(*self._get_label_color()))

        with context:
            self._disc_vbo = self._build_disc_vbo(
                inner_radius, outer_radius, depth)

            self._disc_vbo.acquire()

            self._labels: list[_text.Text] = []
            words = []
            owners = []
            offsets = []

            for label_number, tick_index in enumerate(self._major_index):
                # Displayed as -180..180 (matching the toolbar's own
                # Euler display convention -- see rotation_mesh.
                # wrap_angle, also what a snapped/dragged value gets
                # wrapped to before being written back), not the raw
                # 0..350 this tick's own position is still built from.
                label_degrees = _rotation_mesh.wrap_angle(float(degrees[tick_index]))

                label = _text.Text(str(int(round(label_degrees))),
                                   label_size, build123d.FontStyle.ITALIC,
                                   center_anchor=True, local_tilt=local_tilt)

                self._labels.append(label)

                word_vbos, word_offsets = label.word_draw_data()

                for word_vbo, word_offset in zip(word_vbos, word_offsets):
                    words.append(word_vbo)
                    owners.append(label_number)
                    offsets.append(word_offset)

            # one entry per drawn word mesh (a label is one word, so one each):
            # the mesh, which label it belongs to, its offset in that label's frame
            self._label_word_vbos = words
            self._label_word_owner = np.array(owners, dtype=np.int64)
            self._label_word_offsets = np.array(offsets, dtype=np.float64).reshape(-1, 3)

            self._recompute_local_geometry()

            self._ticks_vbo = self._build_ticks_vbo()
            self._ticks_vbo.acquire()

        label_count = len(self._labels)
        word_count = len(self._label_word_vbos)

        # Per label: position relative to the centre (ring-rotated offset),
        # the world growth direction of its tick (the 2D views' rotation),
        # its current base rotation (billboard or tick direction); per word
        # mesh: its position relative to the centre and its final rotation.
        self._label_rel = np.zeros((label_count, 3), dtype=np.float64)
        self._label_growth = np.zeros((label_count, 3), dtype=np.float64)
        self._label_base_quats = np.tile(
            np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64), (label_count, 1))
        self._word_pos_rel = np.zeros((word_count, 3), dtype=np.float64)
        self._word_quats: list[list[float]] = [[1.0, 0.0, 0.0, 0.0]] * word_count

        # subclasses must call reposition_all() once their own ring
        # angle is established (after their own __init__ finishes), then
        # start_camera_tracking() -- see that method's own docstring for
        # why the ordering matters.

    @staticmethod
    @_check_types.do
    def _build_disc_vbo(inner_radius: float, outer_radius: float,
                        depth: float) -> _vbo_handler.NonPooledVBOHandler:
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
    def _build_ticks_vbo(self) -> _vbo_handler.NonPooledVBOHandler:
        """
        Build the ONE mesh that holds all 360 ticks, each already scaled to
        its length and diameter and carried into the ring's frame (see this
        module's TICK MESH). Tick ``i`` owns vertices ``[i * V, (i + 1) * V)``
        (``V`` = :attr:`_ticks_per_vertex`). Built from the arrays
        :meth:`_recompute_local_geometry` fills, so it is rebuilt whenever
        the radii change and at no other time. Needs the GL context current.
        """

        verts, smooth, face = _tick_prototype()

        scale = np.stack([np.full(TICK_COUNT, self._tick_diameter),
                          np.full(TICK_COUNT, self._tick_diameter),
                          self._tick_lens], axis=1)

        grow = self._tick_grow
        normal = np.tile(np.array([0.0, 0.0, 1.0]), (TICK_COUNT, 1))

        # row k of frame[i] is the k-th axis of tick i (x, y, z of the prism)
        frame = np.stack([self._local_tangents, grow * normal, grow * self._local_radials], axis=1)
        start = self._local_radials * self._tick_start_radius

        world_verts = np.einsum('nvk,nkj->nvj', verts[None] * scale[:, None, :], frame) + start[:, None, :]

        def carried(normals: np.ndarray) -> np.ndarray:
            carried_normals = np.einsum('nvk,nkj->nvj', normals[None] / scale[:, None, :], frame)
            carried_normals /= np.linalg.norm(carried_normals, axis=2, keepdims=True)
            return carried_normals

        self._ticks_per_vertex = int(verts.shape[0])
        count = TICK_COUNT * self._ticks_per_vertex

        packed = np.concatenate((world_verts.reshape(-1, 3).ravel(),
                                 carried(smooth).reshape(-1, 3).ravel(),
                                 carried(face).reshape(-1, 3).ravel())).astype(np.float32)

        unpacked_verts = packed[:count * 3].reshape(-1, 3)
        aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
        aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
        obb = _utils.compute_obb(aabb1, aabb2)

        return _vbo_handler.NonPooledVBOHandler(packed, count, aabb=aabb, obb=obb)

    @_check_types.do
    def set_radii(self, inner_radius: float, outer_radius: float,
                  depth: float, context: "_gl_context.GLContext") -> None:

        """
        Update this ring's ID/OD/depth -- called whenever the tracked
        object's size changes (see
        :meth:`~.rotation_ring.RotationRing.on_object_scale_changed`).
        Rebuilds the washer mesh and the tick mesh directly to the new
        dimensions (no ratio/scale indirection -- see :meth:`_build_disc_vbo`,
        :meth:`_build_ticks_vbo`) whenever any of them actually differ from
        the current ones.
        """

        if (
            (inner_radius, outer_radius, depth) !=
            (self.inner_radius, self.outer_radius, self.depth)
        ):
            self.inner_radius = inner_radius
            self.outer_radius = outer_radius
            self.depth = depth

            self._recompute_local_geometry()

            with context:
                try:
                    self._disc_vbo.release()
                    self._ticks_vbo.release()
                except Exception:  # NOQA
                    pass

                self._disc_vbo = self._build_disc_vbo(
                    inner_radius, outer_radius, depth)

                self._disc_vbo.acquire()

                self._ticks_vbo = self._build_ticks_vbo()
                self._ticks_vbo.acquire()

        # A radii change alone (no angle change) still moves every label --
        # reposition_all's own dirty check only compares the ring's
        # orientation and centre, so it has to be told explicitly that the
        # LOCAL geometry just changed underneath it, or it would wrongly
        # skip the next call as a no-op.
        self._last_ring_angle_quat = None

    @_check_types.do
    def delete(self, context: "_gl_context.GLContext") -> None:
        # Not strictly required (Point.bind() only ever holds a
        # WeakMethod, so this callback goes inert on its own once this
        # ring is collected) but explicit is cheap and avoids a stale
        # callback firing spurious work while something else might still
        # be keeping this instance alive a moment longer -- see
        # Point.unbind's own docstring.
        if self._camera is not None:
            self._camera.position.unbind(self._on_camera_moved)

        try:
            with context:
                self._disc_vbo.release()
                self._ticks_vbo.release()
        except Exception:  # NOQA
            # Context may be unavailable during shutdown -- the buffers
            # die with the context in that case.
            pass

    @_check_types.do
    def _recompute_local_geometry(self) -> None:
        """
        (Re)derive everything that depends only on the radii and the label
        size, all in the ring's own frame: every tick's length, diameter,
        start radius and growth direction, the label offsets, and the 360
        pick boxes.

        None of this depends on the ring's world orientation -- a tick's
        size and its position *within the ring's own plane* are as fixed as
        the ring's radii are -- so it only runs from ``__init__`` and
        :meth:`set_radii`, never on an angle change.
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
        #
        # Ticks anchor at the edge the labels are NOT on and grow toward
        # the labels' edge: the outer protractor starts at the ID and grows
        # out toward the OD, the inner starts at the OD and grows in toward
        # the ID. A tick's mesh is base-anchored (local z = 0 is its base,
        # see shapes/cylinder.py), so the start radius is where the base sits.
        if self._labels_outward:
            label_radius = self.outer_radius + label_gap
            self._tick_start_radius = self.inner_radius
            self._tick_grow = 1.0
        else:
            label_radius = max(self.inner_radius - label_gap, 0.0)
            self._tick_start_radius = self.outer_radius
            self._tick_grow = -1.0

        self._tick_lens = np.where(self._is_major_mask, major_len, minor_len).astype(np.float64)
        self._tick_diameter = self.outer_radius * self._TICK_DIAMETER_FRAC

        self._label_local_offsets = self._local_radials[self._major_index] * label_radius

        # The pick boxes: along the growth direction for tick_len, one
        # tick_diameter across in the other two (tangent and ring normal).
        grow = self._tick_grow
        normal = np.tile(np.array([0.0, 0.0, 1.0]), (TICK_COUNT, 1))

        self._box_centre_l = self._local_radials * (
            self._tick_start_radius + grow * self._tick_lens / 2.0)[:, None]

        self._box_axes_l = np.stack(
            [grow * self._local_radials, self._local_tangents, normal], axis=1)

        self._box_half = np.stack(
            [self._tick_lens / 2.0,
             np.full(TICK_COUNT, self._tick_diameter / 2.0),
             np.full(TICK_COUNT, self._tick_diameter / 2.0)], axis=1)

    @_check_types.do
    def _center_array(self) -> np.ndarray:
        return np.array(
            [float(self.center.x), float(self.center.y), float(self.center.z)],
            dtype=np.float64)

    @_check_types.do
    def reposition_all(self, ring_angle: _angle.Angle) -> None:
        """
        Make the ring's current orientation (*ring_angle*) and centre the
        ones it draws and picks with. Only the LABELS depend on either:
        the washer and the ticks follow through the draw's rotation and the
        live centre, and the pick boxes are carried by the stored matrix when
        a pick happens (see this module's docstring). So this stores the
        ring's quaternion and matrix, then re-places the 36 labels
        (:meth:`_update_labels`).

        Skips everything when *ring_angle* and the centre are identical to
        the last call's -- see :attr:`_last_ring_angle_quat`'s own comment
        for why that is common, not rare.
        """

        new_quat = ring_angle.as_quat_numpy
        center_np = self._center_array()

        # The labels are placed in world space from the center, while the
        # washer and ticks read the shared center Point live every frame --
        # so a center that moved with the orientation unchanged has to
        # re-place the labels too (a wire service loop's gizmo does this).
        if (
            self._last_ring_angle_quat is not None and
            self._last_center is not None and
            np.array_equal(new_quat, self._last_ring_angle_quat) and
            np.array_equal(center_np, self._last_center)
        ):
            return

        self._last_ring_angle_quat = new_quat
        self._last_center = center_np

        self._ring_quat = [float(v) for v in new_quat]
        self._ring_matrix = np.asarray(ring_angle.as_matrix_numpy, dtype=np.float64)

        matrix_t = self._ring_matrix.T

        self._label_rel = self._label_local_offsets @ matrix_t

        # The growth direction of each labeled tick, in the world: the 2D
        # views turn a label to lie along it (see LABELS in the module
        # docstring); outward for the outer ring, inward for the inner.
        self._label_growth = self._tick_grow * (self._local_radials[self._major_index] @ matrix_t)

        self._update_labels()

    @_check_types.do
    def start_camera_tracking(self) -> None:
        """
        Bind this ring's own camera-move callback, then immediately aim
        the labels at the camera -- must be called AFTER this ring's own
        first :meth:`reposition_all` (see each subclass's own ``__init__``,
        where both calls happen back to back): the label positions the
        billboard is computed from only hold their real, ring-relative
        value once ``reposition_all`` has run.

        No camera at all (the schematic/pegboard views' own protractor
        -- a locked top-down projection has nothing to billboard toward)
        leaves every label lying in the ring plane along its tick, as
        :meth:`_update_labels` places it.
        """

        if self._camera is None:
            return

        self._camera.position.bind(self._on_camera_moved)
        self._update_labels()

    @_check_types.do
    def _update_labels(self) -> None:
        """
        Place all 36 labels: each one's rotation (a camera-facing billboard
        in 3D, along its tick in the 2D views, composed after the ring's
        ``local_tilt`` if any) and each word mesh's position, from the
        ring's current transform, centre and camera. Array operations over
        the 36 rows; nothing per label in Python.

        Called from :meth:`reposition_all` (orientation or centre changed)
        and :meth:`_on_camera_moved` (the camera moved: positions did not,
        but the facing did). See LABELS in this module's docstring.
        """

        positions = self._center_array() + self._label_rel

        if self._camera is None:
            self._label_base_quats = _batch.quaternions_from_directions(self._label_growth)
        else:
            camera_pos = self._camera.position.as_numpy.astype(np.float64)
            matrices, safe = _text._billboard_matrices(positions, camera_pos)  # NOQA

            # a label exactly at the camera has no direction to face: it
            # keeps the rotation it had
            self._label_base_quats[safe] = _batch.quaternions_from_matrices(matrices)[safe]

        if self._tilt_quat is None:
            final = self._label_base_quats
        else:
            final = _batch.compose(self._tilt_quat, self._label_base_quats)

        word_quats = final[self._label_word_owner]

        self._word_pos_rel = (self._label_rel[self._label_word_owner] +
                              _batch.rotate_vectors(word_quats, self._label_word_offsets))

        self._word_quats = word_quats.tolist()

    @_check_types.do
    def _on_camera_moved(self, *_args) -> None:
        """
        Bound to ``self._camera.position`` in
        :meth:`start_camera_tracking` -- must be a real bound method
        (not a lambda/free function): ``Point.bind()`` stores it as a
        ``weakref.WeakMethod``, which only works against an actual bound
        method's own ``__self__``.
        """

        self._update_labels()

    @_check_types.do
    def render(self, shaders: _shaders.ShaderProgram) -> None:
        """
        Draw the washer (one call), the ticks (one call, three while one is
        hovered) and the 36 labels -- see RENDER in this module's
        docstring. The washer's and ticks' transform is the live centre and
        the quaternion :meth:`reposition_all` stored.

        Depth-mask handling for this handler's whole render is the caller's
        responsibility (canvas_base.py's _draw_scene renders the handler
        before the tracked object itself -- see that method's own
        docstring); every draw here just uses whatever depth-mask state it
        is called with.
        """
        if not self.is_visible:
            return

        faces_program = shaders.faces

        center = self._center_array()
        center_t = (float(center[0]), float(center[1]), float(center[2]))
        quat = self._ring_quat

        with faces_program:
            self.material.set(faces_program)

            # self._disc_vbo is baked directly to this ring's real
            # ID/OD/depth (see _build_disc_vbo) -- no render-time scale
            # needed at all.
            self._disc_vbo.render_raw(faces_program, center_t, quat, _UNIT_SCALE, None)

            # Ticks always render in a fixed color (black), independent of
            # the washer's own material -- inheriting the washer's own
            # translucent, axis-tinted color (the old behavior) made them
            # hard to pick out against it. The hovered tick (outer ring)
            # is drawn on its own, last, in _HOVER_COLOR.
            self._set_solid_color(faces_program, _TICK_COLOR)

            per_tick = self._ticks_per_vertex
            total = TICK_COUNT * per_tick
            hovered = self._hovered_index

            if hovered is None:
                self._ticks_vbo.render_raw(faces_program, center_t, quat, _UNIT_SCALE, True)
            else:
                first = hovered * per_tick
                after = first + per_tick

                if first > 0:
                    self._ticks_vbo.render_raw(faces_program, center_t, quat, _UNIT_SCALE, True, 0, first)

                if after < total:
                    self._ticks_vbo.render_raw(faces_program, center_t, quat, _UNIT_SCALE, True, after, total - after)

                self._set_solid_color(faces_program, self._HOVER_COLOR)
                self._ticks_vbo.render_raw(faces_program, center_t, quat, _UNIT_SCALE, True, first, per_tick)

            # Labels get their own fixed, light color. Every render() call
            # sets its own material first thing (see the top of this
            # method, and TorusRing.render()'s identical pattern), so
            # nothing downstream depends on this state being restored.
            self._label_material.set(faces_program)

            label_scale = (self._label_size, self._label_size, 1.0)
            positions = (self._word_pos_rel + center).tolist()

            for word_vbo, position, rotation in zip(self._label_word_vbos, positions, self._word_quats):
                word_vbo.render_raw(faces_program, (position[0], position[1], position[2]),
                                    rotation, label_scale, False)

    @_check_types.do
    def _disc_rotation(self) -> _angle.Angle:
        """
        Subclasses provide whatever orientation the washer itself
        should render with -- the inner ring's tracks the object, the
        outer ring's stays fixed. Passed to :meth:`reposition_all` (which
        stores what is drawn from it) whenever the object's angle changes;
        it is not read per frame.
        """

        raise NotImplementedError

    @_check_types.do
    def _get_label_color(self) -> tuple[float, float, float, float]:
        raise NotImplementedError

    @staticmethod
    @_check_types.do
    def _set_solid_color(faces_program: "_shader_program.FacesProgram",
                         color: tuple[float, float, float]) -> None:

        faces_program.material_diffuse = [color[0], color[1], color[2], 1.0]
        faces_program.material_emissive = [color[0], color[1], color[2], 1.0]
