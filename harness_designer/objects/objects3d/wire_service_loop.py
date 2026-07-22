# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math
import numpy as np
from PySide6.QtWidgets import QMenu

from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base3d as _base3d
from . import menu_ops as _menu_ops
from ...gl import materials as _materials
from ... import config as _config
from ...shapes import cylinder_helix as _cylinder_helix


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire_service_loop as _pjt_wire_service_loop
    from .. import wire_service_loop as _wire_service_loop
    from .. import wire as _wire
    from .. import wire_marker as _wire_marker


Config = _config.Config.editor3d


# ---------------------------------------------------------------------------
# Mesh-vs-mesh collision helpers
#
# Wires and loops are tested against each other using their actual VBO
# triangle data transformed into world space -- a straight-line-plus-radius
# capsule is a fine stand-in for a wire (which really is a cylinder) but a
# poor one for the loop itself, which bulges out sideways. No clearance
# margin is added on top of raw intersection: these loops are packed tight
# into a boot with no gap by design, any remaining space gets filled with
# epoxy resin afterward.
# ---------------------------------------------------------------------------

def _quat_mul(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """Hamilton product of two [w, x, y, z] quaternions."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ], dtype=np.float64)


def _mesh_world_triangles(
    vbo, position: np.ndarray, angle: "_angle.Angle", scale: np.ndarray
) -> "np.ndarray | None":
    """(N, 3, 3) world-space triangles for a mesh at the given pose -- same
    transform the faces shader applies (scale, then rotate, then
    translate). None if the object has no mesh.
    """
    if vbo is None:
        return None

    verts = vbo.vertices.reshape(-1, 3)
    if len(verts) % 3:
        return None

    verts = (verts * scale) @ angle
    verts = verts + position
    return verts.reshape(-1, 3, 3)


def _triangle_edges(tris: np.ndarray) -> np.ndarray:
    """(N*3, 2, 3) start/end pairs for every edge of every triangle --
    shared edges get tested twice, which is harmless."""
    v0, v1, v2 = tris[:, 0], tris[:, 1], tris[:, 2]
    edges = np.stack([
        np.stack([v0, v1], axis=1),
        np.stack([v1, v2], axis=1),
        np.stack([v2, v0], axis=1),
    ], axis=1)
    return edges.reshape(-1, 2, 3)


# Corner 0 = (x1,y1,z1), 1 toggles x, 3 toggles y, 4 toggles z (see
# gl.canvas3d.object_picker's comment on the same convention) -- these are
# the same 6 quad faces Base3D._render_obb draws, each split into 2
# triangles.
_OBB_TRIANGLE_INDICES = np.array([
    (0, 1, 2), (0, 2, 3),  # front
    (5, 4, 7), (5, 7, 6),  # back
    (4, 0, 3), (4, 3, 7),  # left
    (1, 5, 6), (1, 6, 2),  # right
    (3, 2, 6), (3, 6, 7),  # top
    (4, 5, 1), (4, 1, 0),  # bottom
], dtype=np.int32)


def _candidate_obb(vbo, position: np.ndarray, angle: "_angle.Angle", scale: np.ndarray
                   ) -> "np.ndarray | None":
    """(8, 3) world-space OBB corners for a hypothetical (not-yet-applied)
    pose -- same formula Base3D._compute_obb uses for its own (always
    current) .obb, just evaluated against a candidate instead of self.
    Tiny array, cheap to build -- this is the broad-phase test, run for
    every roll/slide candidate, before ever touching per-triangle mesh
    data (see _is_clear).
    """
    if vbo is None or vbo.local_obb is None:
        return None
    obb = vbo.local_obb * scale
    obb = obb @ angle
    obb = obb + position
    return obb


def _obb_triangles(obb: np.ndarray) -> np.ndarray:
    """(12, 3, 3) triangles for an OBB's own 8 corners."""
    return obb[_OBB_TRIANGLE_INDICES]


def _rays_vs_triangles_batched(
    ray_origins: np.ndarray, ray_dirs: np.ndarray, tris: np.ndarray, max_t: "float | None" = None
) -> np.ndarray:
    """Möller-Trumbore ray-triangle intersection, batched over *both* M
    rays and N triangles at once via numpy broadcasting -- returns an
    (M, N) boolean hit matrix in a single call.

    Same algebra as Base3D._ray_triangles_intersect_vectorized (which
    only batches over triangles, one ray at a time -- that shape is kept
    as-is for the picker, which only ever needs one ray), just with a
    leading ray axis threaded through every intermediate array so numpy
    computes every ray-triangle pair in one pass instead of one Python
    call per ray.

    Args:
        ray_origins: (M, 3)
        ray_dirs: (M, 3) -- unnormalized; t=1 reaches ray_origin + ray_dirs
        tris: (N, 3, 3)
        max_t: optional upper bound on t, for a finite segment (edge) test
    """
    v0, v1, v2 = tris[:, 0], tris[:, 1], tris[:, 2]  # each (N, 3)
    edge1 = v1 - v0  # (N, 3)
    edge2 = v2 - v0  # (N, 3)

    ro = ray_origins[:, None, :]  # (M, 1, 3)
    rd = ray_dirs[:, None, :]  # (M, 1, 3)
    e1 = edge1[None, :, :]  # (1, N, 3)
    e2 = edge2[None, :, :]  # (1, N, 3)
    v0b = v0[None, :, :]  # (1, N, 3)

    h = np.cross(rd, e2)  # (M, N, 3)
    det = np.sum(e1 * h, axis=-1)  # (M, N)

    valid_det = np.abs(det) > 1e-6
    inv_det = np.zeros_like(det)
    inv_det[valid_det] = 1.0 / det[valid_det]

    s = ro - v0b  # (M, N, 3)
    u = inv_det * np.sum(s * h, axis=-1)  # (M, N)
    valid_u = valid_det & (u >= 0.0) & (u <= 1.0)

    q = np.cross(s, e1)  # (M, N, 3)
    v = inv_det * np.sum(rd * q, axis=-1)  # (M, N)
    valid_v = valid_u & (v >= 0.0) & (u + v <= 1.0)

    t = inv_det * np.sum(e2 * q, axis=-1)  # (M, N)

    hit = valid_v & (t > 1e-6)
    if max_t is not None:
        hit = hit & (t <= max_t)

    return hit


def _meshes_intersect(tris_a: "np.ndarray | None", tris_b: "np.ndarray | None") -> bool:
    """True if any edge of one mesh crosses a face of the other -- both
    directions batched in one call each via _rays_vs_triangles_batched,
    not a Python loop over edges.

    Rather than a full triangle-triangle SAT test (11 separating axes,
    easy to get subtly wrong with no test suite to check it against), this
    reuses the same Möller-Trumbore math Base3D already has for picking,
    bounded to a finite segment via max_t=1.0 (ray_dir passed as the
    unnormalized edge vector, so t=1 reaches the far endpoint). Misses
    only the case of one mesh fully nested inside the other with no
    surface crossing at all, which doesn't happen here -- wires and loops
    are always comparable in scale, never one wholly swallowing the other.
    """
    if tris_a is None or tris_b is None or len(tris_a) == 0 or len(tris_b) == 0:
        return False

    for tris_x, tris_y in ((tris_a, tris_b), (tris_b, tris_a)):
        edges = _triangle_edges(tris_x)
        hits = _rays_vs_triangles_batched(edges[:, 0], edges[:, 1] - edges[:, 0], tris_y, max_t=1.0)
        if np.any(hits):
            return True

    return False


def _obb_hit_owners(my_obb_tris: np.ndarray, session: "_MoveSession") -> np.ndarray:
    """Indices into session.candidates whose OBB overlaps my_obb_tris --
    the broad-phase for _is_clear, entirely batched against the whole
    session-cached candidate set in two calls (one per direction) instead
    of looping candidate-by-candidate.

    session.candidate_obb_tris/candidate_obb_edge_* are every candidate's
    OBB stacked into one array up front by begin_move_session, along with
    an owner-index array mapping each triangle/edge back to which
    candidate it came from -- built once for the whole move/rotate
    operation, since none of it changes for the duration of one.
    """
    owners = []

    if len(session.candidate_obb_tris):
        my_edges = _triangle_edges(my_obb_tris)
        hits = _rays_vs_triangles_batched(
            my_edges[:, 0], my_edges[:, 1] - my_edges[:, 0], session.candidate_obb_tris, max_t=1.0)
        hit_tris = np.any(hits, axis=0)
        if np.any(hit_tris):
            owners.append(session.candidate_tri_owner[hit_tris])

    if len(session.candidate_obb_edge_owner):
        hits = _rays_vs_triangles_batched(
            session.candidate_obb_edge_origins, session.candidate_obb_edge_dirs,
            my_obb_tris, max_t=1.0)
        hit_edges = np.any(hits, axis=1)
        if np.any(hit_edges):
            owners.append(session.candidate_obb_edge_owner[hit_edges])

    if not owners:
        return np.empty(0, dtype=np.int64)

    return np.unique(np.concatenate(owners))


def _is_clear(
    vbo, position: np.ndarray, angle: "_angle.Angle", scale: np.ndarray,
    my_obb: "np.ndarray | None", session: "_MoveSession",
) -> bool:
    """True if a candidate pose (my_obb, plus vbo/position/angle/scale to
    build real mesh data from if needed) doesn't intersect any candidate's
    own geometry.

    OBB-vs-OBB first, batched against the whole session-cached candidate
    set at once (see _obb_hit_owners) -- full per-triangle mesh data for
    *this* object, and for whichever candidates actually overlapped at
    the OBB level, is only ever transformed into world space for those
    candidates (there are typically zero or one), never eagerly for the
    whole candidate set.
    """
    if my_obb is None:
        return True

    hit_owners = _obb_hit_owners(_obb_triangles(my_obb), session)
    if len(hit_owners) == 0:
        return True

    my_tris = _mesh_world_triangles(vbo, position, angle, scale)
    if my_tris is None:
        return True

    for owner in hit_owners:
        obj3d = session.candidates[owner].obj3d
        other_tris = _mesh_world_triangles(
            obj3d._vbo, obj3d._position.as_numpy, obj3d._angle, obj3d._scale.as_numpy)  # NOQA

        if _meshes_intersect(my_tris, other_tris):
            return False

    return True


class _MoveSession:
    """Cached collision-candidate state for one whole interactive move or
    rotate operation -- see WireServiceLoop.begin_move_session. None of
    this changes for the duration of a single continuous drag, so it's
    computed once at the start of one instead of on every intermediate
    _update_position/_update_angle call.

    candidate_obb_tris/candidate_obb_edge_* are every entry in
    `candidates`' own OBB stacked into one array apiece, with an
    owner-index array mapping each triangle/edge back to its position in
    `candidates` -- what lets _obb_hit_owners test against the whole
    candidate set in two batched numpy calls instead of looping
    candidate-by-candidate.
    """
    attached: list = None
    markers: list = None
    candidates: list = None
    candidate_obb_tris: "np.ndarray | None" = None
    candidate_tri_owner: "np.ndarray | None" = None
    candidate_obb_edge_origins: "np.ndarray | None" = None
    candidate_obb_edge_dirs: "np.ndarray | None" = None
    candidate_obb_edge_owner: "np.ndarray | None" = None


class WireServiceLoop(_base3d.Base3D):
    """A wire service loop: a helix-shaped part connecting a start point to
    a derived stop point (see _sync_stop_position) offset from it by the
    loop's own geometry.

    Base3D only knows about one Point (the start -- passed to Base3D.__init__
    as *position*, so it's what the render pivot/OBB/AABB/floor-lock all key
    off). The stop point is this class's own concern: _update_position and
    _update_angle are overridden so that whenever the start point moves or
    the loop rotates, the derived stop point is recomputed to match -- a
    caller only ever needs to move the start point (see
    handlers.wire_service_loop_handler) and everything else -- the stop
    point, and rotation pivoting around the loop's own centroid rather than
    its start point -- is handled here.
    """
    parent: "_wire_service_loop.WireServiceLoop" = None
    db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop" = None

    def __init__(self, parent: "_wire_service_loop.WireServiceLoop",
                 db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop"):
        """Initialise the :class:`WireServiceLoop` instance.

        :param parent: Parent object.
        :type parent: :class:`_wire_service_loop.WireServiceLoop`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_service_loop.PJTWireServiceLoop`
        """

        parent.mainframe.editor3d.context.acquire()

        self._part = db_obj.part
        color = self._part.color.ui
        material = _materials.Plastic(color)

        position = db_obj.start_position3d
        position2 = db_obj.stop_position3d

        vbo = _cylinder_helix.create_vbo()
        diameter = self._part.od_mm
        scale = _point.Point(diameter, diameter, diameter)
        angle = db_obj.angle3d

        self._last_centroid: "np.ndarray | None" = None
        # Last pose _resolve_collision actually verified as clear -- the
        # fallback to revert to if a later resolve attempt can't find any
        # clear spot at all (see _resolve_collision).
        self._last_resolved_position: "np.ndarray | None" = None
        self._last_resolved_quat: "np.ndarray | None" = None
        # Set by begin_move_session/cleared by end_move_session -- see
        # both, and _resolve_collision.
        self._move_session: "_MoveSession | None" = None

        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, position, scale, material)

        self._p1 = position
        self._p2 = position2

        # Always derive the stop point fresh from the start point/angle/
        # scale rather than trusting whatever was last persisted -- keeps
        # this the single source of truth regardless of how the row got
        # here (self-heals any stale data from before this existed).
        self._last_centroid = self._world_centroid()
        self._sync_stop_position()

        # Collision avoidance runs "anytime a service loop is being moved"
        # (see _resolve_collision) -- that includes the very first
        # placement, not just later interactive moves.
        self._resolve_collision()
        self._sync_stop_position()
        self._last_centroid = self._world_centroid()

        parent.mainframe.editor3d.context.release()

    def _world_centroid(self) -> np.ndarray:
        """World-space centroid of the loop's own OBB -- the rotation pivot
        (see _update_angle), not the start/stop connection points.
        """
        centroid = self._vbo.local_obb.mean(axis=0)
        centroid = centroid * self._scale.as_numpy
        centroid = centroid @ self._angle
        centroid = centroid + self._position.as_numpy
        return centroid

    def _sync_stop_position(self) -> None:
        """Recompute the derived stop point from the current start
        position, angle and scale -- the same scale/rotate/translate of
        the VBO's own endpoint that _mesh_world_triangles applies to the
        full mesh.
        """
        tmp = self._vbo.endpoint.copy()
        tmp *= self._scale
        tmp @= self._angle
        tmp += self._position

        self._p2 += tmp - self._p2

    def _update_position(self, position: "_point.Point"):
        """Base3D recomputes OBB/AABB/floor-lock off the start point alone
        -- also keep the derived stop point in step with it, resolve any
        collision the move introduced (see _resolve_collision), and keep
        the centroid rotation pivot baseline used by _update_angle current.
        """
        super()._update_position(position)
        self._resolve_collision()
        self._sync_stop_position()
        self._last_centroid = self._world_centroid()

    def _update_angle(self, angle: "_angle.Angle"):
        """Rotate the loop around its own centroid, not its start point.

        Base3D's rendering pivot is always objectPosition (the start
        point), so pivoting around the centroid instead means compensating
        the start position by however far the centroid would otherwise
        move under the new angle -- computed and applied *before* Base3D's
        own bookkeeping (OBB/AABB, floor lock) runs against the corrected
        position. Only this object's own _update_position listener is
        unbound for that one write (the same unbind -> write -> rebind
        idiom used throughout this codebase, e.g.
        gl.canvas3d.rotation_rings.Rings3D.apply_drag_angle) so it isn't
        re-entered; any other object sharing this same Point (e.g. an
        attached wire's endpoint, see
        handlers.wire_service_loop_handler._split_wire_for_loop) still
        sees the move normally.

        Not used for one-shot authoritative placement (finalizing
        interactive placement) -- see set_placement, which bypasses this.
        """
        if self._last_centroid is not None:
            # Where the centroid would land if the position stayed put,
            # under the angle that was just applied.
            unshifted_centroid = self._world_centroid()
            delta = self._last_centroid - unshifted_centroid

            if not np.allclose(delta, 0.0, atol=1e-9):
                self._position.unbind(self._update_position)
                try:
                    self._position += _point.Point(*[float(v) for v in delta])
                finally:
                    self._position.bind(self._update_position)

        super()._update_angle(angle)

        self._resolve_collision()
        self._sync_stop_position()
        self._last_centroid = self._world_centroid()

    def _write_angle(self, target_angle: "_angle.Angle") -> None:
        """Write target_angle's exact rotation into self._angle, bypassing
        its normal Euler-driven derivation. Caller is responsible for
        unbind/rebind of _update_angle around this if needed -- this
        method only performs the write.

        Per the codebase-wide rule that any angle change must be made via
        Euler, never the raw quaternion (quaternion -> Euler conversion is
        ambiguous under gimbal lock), this mirrors HandlerBase.reset_angle/
        set_angle_from_housing: mutate the Euler fields inside the angle's
        own write-context, then correct _q/_matrix to the exact target
        rotation and manually re-fire callbacks.
        """
        euler = target_angle.as_euler_float
        with self._angle:
            self._angle.x = euler[0]
            self._angle.y = euler[1]
            self._angle.z = euler[2]
            self._angle._matrix[:] = target_angle.as_matrix_numpy  # NOQA
        self._angle._q.w = target_angle._q.w  # NOQA
        self._angle._q.x = target_angle._q.x  # NOQA
        self._angle._q.y = target_angle._q.y  # NOQA
        self._angle._q.z = target_angle._q.z  # NOQA
        self._angle._process_callbacks()  # NOQA

    def _roll_axis(self) -> "np.ndarray | None":
        """Direction from the loop's own current start to stop point -- the
        axis _resolve_collision twists candidate orientations around.

        Per the user's direction, this is derived from the loop's own
        connection points, not by asking any wire for its direction --
        snapshotted once per resolve attempt (see _resolve_collision), since
        _p2 is itself angle-dependent (see _sync_stop_position) and would be
        circular if re-derived from an in-progress candidate.
        """
        direction = self._p2.as_numpy - self._p1.as_numpy
        length = np.linalg.norm(direction)
        if length < 1e-6:
            return None
        return direction / length

    def _attached_wires(self) -> "list[_wire.Wire]":
        """Wires directly touching this loop's own start/stop points --
        found by the object itself (via the shared Point db_id, see
        handlers.wire_service_loop_handler._split_wire_for_loop) rather
        than being told by a handler. Adjacent by construction, never a
        real collision -- excluded from _resolve_collision's candidates.
        """
        ids = {self._p1.db_id, self._p2.db_id}
        return [
            w for w in self.mainframe.project.wires
            if w.obj3d.start_position.db_id in ids or w.obj3d.stop_position.db_id in ids
        ]

    def _markers_on_attached_wires(self) -> "list[_wire_marker.WireMarker]":
        """Wire markers sitting on either of this loop's attached wires --
        both a collision obstacle and a hard slide boundary (see
        _resolve_collision): sliding must never cross a marker to reach
        clear space on its far side.
        """
        wire_ids = {w.db_obj.db_id for w in self._attached_wires()}
        if not wire_ids:
            return []
        return [m for m in self.mainframe.project.wire_markers if m.db_obj.wire_id in wire_ids]

    def _apply_resolved(self, position_np: np.ndarray, q_arr: np.ndarray) -> None:
        """Commit a (position, quaternion) pair found by _resolve_collision
        without re-entering _update_position/_update_angle -- the search
        that produced them already accounts for their combined effect
        (roll candidates are tested at a fixed position; see
        _resolve_collision), so re-deriving via the normal callbacks
        (which would, e.g., re-apply centroid-pivot compensation on top)
        would invalidate the very placement just verified as clear.
        """
        current_pos = self._position.as_numpy
        if not np.allclose(position_np, current_pos, atol=1e-9):
            self._position.unbind(self._update_position)
            try:
                self._position += _point.Point(*[float(v) for v in (position_np - current_pos)])
            finally:
                self._position.bind(self._update_position)

        current_q = np.array(self._angle.as_quat_float, dtype=np.float64)
        if not np.allclose(q_arr, current_q, atol=1e-9):
            self._angle.unbind(self._update_angle)
            try:
                self._write_angle(_angle.Angle.from_quat(q_arr.tolist()))
            finally:
                self._angle.bind(self._update_angle)

        self._compute_obb()
        self._compute_aabb()

    def _viewport_candidates(self) -> list:
        """Wires and other loops currently visible in the viewport -- the
        filter tier for begin_move_session.

        This is a rendering-frustum concept, not a spatial-locality one:
        an obstacle just outside the frustum while genuinely close in world
        space would be missed. Accepted -- the user is necessarily looking
        at the wire they just clicked on to start this placement, and a
        fresh move/rotate session rebuilds this list from scratch, so
        releasing the mouse and moving/clicking again picks up anything a
        gap here let through.

        No further distance cull on top of this: once the OBB test itself
        is batched across the whole candidate set in one numpy call (see
        _obb_hit_owners), an extra candidate costs a few more rows in an
        array numpy was already broadcasting over, not a fresh Python-level
        loop iteration -- the per-candidate cost distance culling existed
        to avoid mostly disappears once nothing loops candidate-by-candidate
        in Python anymore.
        """
        return [
            obj for obj in self.editor3d.camera.objects_in_view
            if obj is not self.parent
            and (obj.is_wire or obj.is_wire_service_loop)
        ]

    def begin_move_session(self) -> None:
        """Start caching the collision-candidate list -- and every
        candidate's OBB, pre-stacked into one array apiece -- for a whole
        interactive move or rotate operation, instead of rebuilding any of
        it on every single intermediate _update_position/_update_angle
        call during one continuous drag.

        Called once when a drag/rotate begins:
        gl.canvas3d.dragging.DragObject and gl.canvas3d.rotation_rings.
        DragRotate call this (duck-typed -- only when the dragged/rotated
        object actually defines it) from their own __init__; handlers.
        wire_service_loop_handler.AddWireServiceLoopHandler calls it right
        after constructing the preview object, treating its whole
        interactive placement as one such operation. Pair with
        end_move_session.
        """
        session = _MoveSession()
        session.attached = self._attached_wires()
        attached_wire_ids = {w.db_obj.db_id for w in session.attached}
        session.markers = self._markers_on_attached_wires()

        session.candidates = [
            obj for obj in self._viewport_candidates()
            if not (obj.is_wire and obj.db_obj.db_id in attached_wire_ids)
        ] + session.markers

        # Every candidate's OBB, stacked into one array apiece, with an
        # owner-index array mapping each triangle/edge back to its
        # position in session.candidates -- built once here so
        # _obb_hit_owners can test against the whole set in two batched
        # numpy calls (one per direction) instead of looping
        # candidate-by-candidate on every roll/slide step.
        obbs = [c.obj3d.obb for c in session.candidates]
        obb_tris = [_obb_triangles(obb) for obb in obbs if obb is not None]
        tri_owners = [i for i, obb in enumerate(obbs) if obb is not None]

        if obb_tris:
            session.candidate_obb_tris = np.concatenate(obb_tris, axis=0)
            session.candidate_tri_owner = np.repeat(
                np.array(tri_owners, dtype=np.int64), 12)
        else:
            session.candidate_obb_tris = np.empty((0, 3, 3))
            session.candidate_tri_owner = np.empty(0, dtype=np.int64)

        obb_edges = [_triangle_edges(t) for t in obb_tris]
        if obb_edges:
            edges = np.concatenate(obb_edges, axis=0)
            session.candidate_obb_edge_origins = edges[:, 0]
            session.candidate_obb_edge_dirs = edges[:, 1] - edges[:, 0]
            session.candidate_obb_edge_owner = np.repeat(
                np.array(tri_owners, dtype=np.int64), 36)
        else:
            session.candidate_obb_edge_origins = np.empty((0, 3))
            session.candidate_obb_edge_dirs = np.empty((0, 3))
            session.candidate_obb_edge_owner = np.empty(0, dtype=np.int64)

        self._move_session = session

    def end_move_session(self) -> None:
        """Stop caching -- the next call to _resolve_collision without an
        active session builds and uses a throwaway one-shot list instead
        (see _resolve_collision), and the next begin_move_session call
        starts a fresh cache. Pair with begin_move_session.
        """
        self._move_session = None

    def _resolve_collision(self) -> None:
        """Roll then slide until the current pose is clear of nearby wires,
        other loops, and wire markers on the attached wires -- mutates
        self._position/self._angle as needed (see _apply_resolved).

        1. Try all 16 roll orientations (22.5 degree steps, one full
           clockwise revolution) around _roll_axis() at the current
           position. First clear one wins.
        2. If none clear, slide along that axis in both directions,
           re-trying the full roll search at each step, each direction
           capped at whichever is closer: the attached wire's own outer
           endpoint, or the nearest wire marker on that side -- sliding
           never crosses either.
        3. Keep whichever direction reaches a clear spot in fewer steps.
        4. If neither direction ever clears within its bound, the pose is
           left unchanged -- "the placement should not be allowed" past
           that point; canceling and re-placing on the other side of
           whatever's blocking it is the way out, not an automatic
           slide-through.

        Runs from _update_position/_update_angle (and once at the end of
        __init__), so this fires for any move regardless of what triggered
        it -- this handler's own preview drag today, or anything else that
        moves this loop's shared start point or rotates it in the future.

        Candidate gathering (viewport filter, distance cull, attached-wire/
        marker lookups) is cached for the whole operation by
        begin_move_session, not redone on every one of these calls -- see
        there. If no session is active (this was reached outside a
        begin/end_move_session bracket), a throwaway one-shot list is
        built here instead of skipping collision avoidance entirely.
        """
        axis = self._roll_axis()
        if axis is None:
            return

        session = self._move_session
        if session is None:
            self.begin_move_session()
            session = self._move_session
            self._move_session = None  # one-shot -- nothing to keep cached

        attached = session.attached
        markers = session.markers

        p1_np = self._p1.as_numpy
        q_base = np.array(self._angle.as_quat_float, dtype=np.float64)
        scale_np = self._scale.as_numpy
        t0 = float(np.dot(self._position.as_numpy - p1_np, axis))

        def _roll_search(t: float) -> "np.ndarray | None":
            pos_np = p1_np + t * axis
            for step in range(16):
                theta = step * (2.0 * math.pi / 16.0)
                hw = math.cos(theta / 2.0)
                hs = math.sin(theta / 2.0)
                q_twist = np.array(
                    [hw, axis[0] * hs, axis[1] * hs, axis[2] * hs], dtype=np.float64)
                q_cand = _quat_mul(q_base, q_twist)
                cand_angle = _angle.Angle.from_quat(q_cand.tolist())

                cand_obb = _candidate_obb(self._vbo, pos_np, cand_angle, scale_np)
                if _is_clear(self._vbo, pos_np, cand_angle, scale_np, cand_obb, session):
                    return q_cand

            return None

        q_result = _roll_search(t0)
        if q_result is not None:
            self._commit_resolved(p1_np + t0 * axis, q_result)
            return

        # Bound each slide direction by the nearest obstacle point (the
        # attached wire's own outer endpoint, or a marker) projected onto
        # the axis -- whichever is closer.
        boundary_ts = []
        my_ids = (self._p1.db_id, self._p2.db_id)
        for w in attached:
            for p in (w.obj3d.start_position, w.obj3d.stop_position):
                if p.db_id in my_ids:
                    continue
                boundary_ts.append(float(np.dot(p.as_numpy - p1_np, axis)))
        for m in markers:
            boundary_ts.append(float(np.dot(m.obj3d.position.as_numpy - p1_np, axis)))

        pos_limit = min([bt for bt in boundary_ts if bt > t0], default=t0)
        neg_limit = max([bt for bt in boundary_ts if bt < t0], default=t0)

        step = max(float(scale_np[0]) * 0.5, 0.5)
        best: "tuple[float, float, np.ndarray] | None" = None

        for limit, sign in ((pos_limit, 1.0), (neg_limit, -1.0)):
            t = t0
            while True:
                t_next = t + sign * step
                t_next = min(t_next, limit) if sign > 0 else max(t_next, limit)
                reached_limit = t_next == t
                t = t_next

                q_cand = _roll_search(t)
                if q_cand is not None:
                    distance = abs(t - t0)
                    if best is None or distance < best[0]:
                        best = (distance, t, q_cand)
                    break

                if reached_limit:
                    # Reached the wire's own endpoint or a marker without
                    # clearing -- the limit of how far this direction can
                    # slide.
                    break

        if best is not None:
            _, t_final, q_final = best
            self._commit_resolved(p1_np + t_final * axis, q_final)
            return

        # Nothing clears anywhere within bounds -- revert to the last pose
        # actually verified clear, instead of leaving the loop sitting
        # wherever the move that triggered this attempt landed it (which
        # may itself be colliding). "The placement should not be allowed"
        # past this point; canceling and re-placing elsewhere is the way
        # out, not an automatic slide-through or a silently-accepted
        # collision.
        if self._last_resolved_position is not None:
            self._apply_resolved(self._last_resolved_position, self._last_resolved_quat)

    def _commit_resolved(self, position_np: np.ndarray, q_arr: np.ndarray) -> None:
        """Apply a pose _resolve_collision just verified as clear, and
        remember it as the fallback for a future resolve attempt that
        can't find anything clear at all (see _resolve_collision)."""
        self._apply_resolved(position_np, q_arr)
        self._last_resolved_position = self._position.as_numpy.copy()
        self._last_resolved_quat = np.array(self._angle.as_quat_float, dtype=np.float64)

    def set_placement(self, position: "_point.Point", quat: np.ndarray) -> None:
        """Snap the loop to an exact start position + rotation (a
        [w, x, y, z] quaternion) in one atomic step, bypassing the
        rotate-around-centroid compensation _update_angle normally applies.

        Used to finalize interactive placement, where the handler (or
        _resolve_collision, via a live drag) has already arrived at an
        exact, already-resolved target position/orientation and wants it
        applied as-is -- not for incremental interactive rotation, which is
        what _update_angle's centroid pivoting is for, and not re-run
        through collision avoidance again (it's already been resolved
        continuously throughout the drag that led here -- see
        _resolve_collision).
        """
        target_angle = _angle.Angle.from_quat(quat.tolist())

        self._position.unbind(self._update_position)
        self._angle.unbind(self._update_angle)
        try:
            self._position += position - self._position
            self._write_angle(target_angle)
        finally:
            self._position.bind(self._update_position)
            self._angle.bind(self._update_angle)

        self._compute_obb()
        self._compute_aabb()
        self._sync_stop_position()
        self._last_centroid = self._world_centroid()
        self.editor3d.Refresh(False)

    def get_context_menu(self):
        """Return the context menu.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return WireServiceLoopMenu(self.mainframe.editor3d.editor, self)

    @property
    def start_position(self):
        """Wire start position (Point instance)"""
        return self._p1

    @property
    def stop_position(self):
        """Wire stop position (Point instance)"""
        return self._p2


class WireServiceLoopMenu(QMenu):
    """Represent a wire service loop menu in :mod:`harness_designer.objects.objects3d.wire_service_loop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, selected):
        """Initialise the :class:`WireServiceLoopMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Wire')
        action.triggered.connect(self.on_add_wire)

        self.addSeparator()
        action = self.addAction('Trace Circuit')
        action.triggered.connect(self.on_trace_circuit)

        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        action = self.addAction('Clone')
        action.triggered.connect(self.on_clone)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    def on_add_wire(self):
        """Start placing a wire using this service loop's part type."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe
        part_id = self.selected.db_obj.part_id

        _menu_ops.start_handler(
            mainframe, lambda: _handlers.AddWireHandler(mainframe, part_id))

    def on_trace_circuit(self):
        """Highlight every object on this service loop's circuit."""
        _menu_ops.trace_circuit(self.selected)

    def on_select(self):
        """Make this wire service loop the active selection."""
        _menu_ops.select_object(self.selected)

    def on_clone(self):
        """Arm clone mode using this wire service loop as the template."""
        _menu_ops.clone_object(self.selected)

    def on_delete(self):
        """Delete this wire service loop from the project."""
        _menu_ops.delete_object(
            self.selected,
            self.selected.mainframe.project.delete_wire_service_loop)

    def on_properties(self):
        """Show this wire service loop's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
