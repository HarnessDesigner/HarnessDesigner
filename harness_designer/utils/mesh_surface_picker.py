# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Unified mesh surface picker for any 3D object.

Design
------
Keeps raw VBO vertices in model-local space and NEVER maintains a
world-space copy of the mesh.  When an object is placed at an arbitrary
position/rotation/scale in the scene the picking ray is transformed into
local space instead, using the inverse of the object's current TRS
(translate-rotate-scale) transform.

Transform order (matching Base3D._compute_aabb / _compute_obb):

    world = (local * scale) @ rotation_matrix + position

Inverse (world → local):

    local = ((world - position) @ rotation_matrix.T) / scale

Because the rotation matrix is orthogonal, R^{-1} = R^T.

Surfaces (coplanar groups) are computed once from local vertices and only
rebuilt when the VBO changes (model loaded / replaced).  Position, angle
and scale changes do NOT require a surface rebuild – they only update the
three cached numpy arrays used by the ray transform.

Usage
-----
Instantiate MeshSurfacePicker with the obj3d (must expose .position,
.angle, .scale, ._vbo) and the raw QOpenGLWidget that drives the scene.

    picker = MeshSurfacePicker(obj3d, gl_widget)
    surf_idx, world_hit = picker.pick_surface_at(mouse_x, mouse_y)

Call picker.cleanup() when the object is deleted.
"""

from typing import Iterable as _Iterable, TYPE_CHECKING

from collections import defaultdict
from dataclasses import dataclass
import numpy as np


if TYPE_CHECKING:
    from ..gl.canvas3d import Canvas3D as _Canvas3D
    from ..geometry import angle as _angle
    from ..geometry import point as _point


@dataclass
class Surface:
    tri_indices: list   # 0-based indices into triangle soup
    normal: np.ndarray  # unit normal, float32, canonical direction
    plane_dist: float   # dot(centroid, normal) — signed dist from origin


def _points_in_triangles(p: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Vectorized point-in-triangle test.

    ``a``, ``b``, ``c`` are (T, 3) arrays of triangle vertices; ``p`` is a
    single point broadcast against every triangle. Returns a (T,) boolean
    mask — same barycentric test as the scalar version this replaces, just
    evaluated for every triangle in one shot instead of a Python loop.
    """
    v0 = c - a
    v1 = b - a
    v2 = p - a

    d00 = np.einsum('ij,ij->i', v0, v0)
    d01 = np.einsum('ij,ij->i', v0, v1)
    d02 = np.einsum('ij,ij->i', v0, v2)
    d11 = np.einsum('ij,ij->i', v1, v1)
    d12 = np.einsum('ij,ij->i', v1, v2)

    denom = d00 * d11 - d01 * d01
    valid = np.abs(denom) >= 1e-12

    inv = np.zeros_like(denom)
    inv[valid] = 1.0 / denom[valid]

    u = (d11 * d02 - d01 * d12) * inv
    v = (d00 * d12 - d01 * d02) * inv

    return valid & (u >= -1e-4) & (v >= -1e-4) & ((u + v) <= 1.0 + 1e-4)


# ---------------------------------------------------------------------------
# Main picker
# ---------------------------------------------------------------------------

class MeshSurfacePicker:
    """
    Mesh surface picker that works entirely in model-local space.

    Parameters
    ----------
    obj3d:
        The 3-D scene object.  Must expose:
            .position  – Point (x, y, z) with .bind() / .unbind()
            .angle     – Angle with .as_matrix_numpy, .bind(), .unbind()
            .scale     – Point (x, y, z) with .bind() / .unbind()
            ._vbo      – VBO with .vertices and .face_normals flat arrays
    canvas3d:
        The Canvas3D wrapper for the scene.  The inner ``._canvas``
        (QOpenGLWidget) is extracted and used for camera access,
        DPR queries, and the frameSwapped signal.

    Attributes
    ----------
    vertices : np.ndarray  shape (N, 3) float64
        Raw VBO vertices in model-local space.  Read-only after __init__;
        replaced wholesale by update_vbo().

    normals : np.ndarray  shape (N, 3) float64
        Per-vertex face normals, same indexing as vertices.

    selected_surf_idx : int | None
        Index into _surfaces of the currently highlighted surface, or None.

    overlay_color : tuple[int, int, int, int]
        RGBA (0-255) for the overlay highlight.  Default: blue 110/255 alpha.
    """

    # Only one picker may have an active highlight at a time across all
    # objects in the scene.  Selecting a surface on one object auto-clears
    # any highlight from every other picker.
    _active: "MeshSurfacePicker" = None

    @property
    def camera(self):
        return self._camera

    @property
    def rot_mat(self) -> np.ndarray:
        return self._rot_mat

    @property
    def inv_rot(self) -> np.ndarray:
        return self._inv_rot

    @property
    def scale_arr(self) -> np.ndarray:
        return self._scale_arr

    @property
    def pos_arr(self) -> np.ndarray:
        return self._pos_arr

    def __init__(self, obj3d, canvas3d: "_Canvas3D"):
        self._obj3d = obj3d
        self._gl_widget = canvas3d._canvas  # NOQA
        self._camera = self._gl_widget.camera

        self.selected_surf_idx: int = None
        self.overlay_color = (100, 180, 255, 110)

        # Live references to the object's transform attributes.
        self._position = obj3d.position
        self._angle = obj3d.angle
        self._scale = obj3d.scale

        # Cached numpy representations (rebuilt on each transform change).
        self._rot_mat: np.ndarray = np.eye(3, dtype=np.float64)
        self._inv_rot: np.ndarray = np.eye(3, dtype=np.float64)
        self._scale_arr: np.ndarray = np.ones(3, dtype=np.float64)
        self._pos_arr: np.ndarray = np.zeros(3, dtype=np.float64)
        self._refresh_transform_cache()

        # Bind change notifications.
        self._position.bind(self._on_position)
        self._angle.bind(self._on_angle)
        self._scale.bind(self._on_scale)

        # Model-local vertices and normals – never transformed in place.
        vbo = obj3d._vbo  # NOQA

        self.vertices = vbo.vertices.reshape(-1, 3).copy().astype(np.float64)

        self.normals = vbo.face_normals.reshape(-1, 3).copy().astype(np.float64)

        self._verticesf32 = self.vertices.astype(np.float32)
        self._normalsf32 = self.normals.astype(np.float32)

        self._surfaces: list[Surface] = []
        self._build_surfaces()

    def _refresh_transform_cache(self) -> None:
        """
        Snapshot angle/position/scale into plain numpy arrays.

        Called once at init and again whenever any of the three change.
        Hot paths (ray transform, overlay projection) read the cached
        arrays directly – no Angle/Point overhead per pick or per frame.
        """

        rot = self._angle.as_matrix_numpy.astype(np.float64)
        # as_matrix_numpy is the column-vector matrix R where R@v rotates v.
        # numpy @ uses row-vector convention, so the forward transform is
        # world = (local*S) @ R.T + P, and the inverse is @ R (not R.T).
        self._rot_mat = rot.T
        self._inv_rot = rot
        self._scale_arr = self._scale.as_numpy.astype(np.float64)
        self._pos_arr = self._position.as_numpy.astype(np.float64)

    def _on_position(self, position: "_point.Point") -> None:
        self._pos_arr = position.as_numpy.astype(np.float64)

    def _on_angle(self, angle: "_angle.Angle") -> None:
        rot = angle.as_matrix_numpy.astype(np.float64)
        self._rot_mat = rot.T
        self._inv_rot = rot

    def _on_scale(self, scale: "_point.Point") -> None:
        self._scale_arr = scale.as_numpy.astype(np.float64)

    def update_vbo(self, surfaces: list | None = None) -> None:
        """
        Reload local vertices from the object's current VBO.

        Call this after the object's mesh has been replaced (e.g. after the
        real 3-D model finishes loading over the placeholder box).  Rebinds
        transform callbacks in case position / angle / scale objects changed.

        :param surfaces: Already-computed surface list to install directly,
            skipping :meth:`_build_surfaces`'s coplanar-grouping + connected-
            components work entirely. Vertex/normal arrays are still
            refreshed as usual (every placement needs its own local copy
            for ray-casting), only the surface computation is skipped. For
            callers that reuse the same mesh across many placements of the
            same catalog part -- see ``objects.objects3d.housing.Housing.
            match_cavity_surfaces``, which caches this on the shared global
            part object since the surface list is purely a function of
            mesh geometry, identical for every placement.
        :type surfaces: list | None
        """

        # Unbind old callbacks.
        for attr, cb in (
            (self._position, self._on_position),
            (self._angle, self._on_angle),
            (self._scale, self._on_scale),
        ):
            try:
                attr.unbind(cb)
            except Exception:  # NOQA
                pass

        # Refresh references (they may have been replaced on the obj3d).
        self._position = self._obj3d.position
        self._angle = self._obj3d.angle
        self._scale = self._obj3d.scale
        self._refresh_transform_cache()

        # Rebind.
        self._position.bind(self._on_position)
        self._angle.bind(self._on_angle)
        self._scale.bind(self._on_scale)

        # Pull new local vertices.
        vbo = self._obj3d._vbo  # NOQA
        self.vertices = vbo.vertices.reshape(-1, 3).copy().astype(np.float64)
        self.normals = vbo.face_normals.reshape(-1, 3).copy().astype(np.float64)

        self._verticesf32 = self.vertices.astype(np.float32)
        self._normalsf32 = self.normals.astype(np.float32)

        if surfaces is not None:
            self._set_surfaces(surfaces)
        else:
            self._build_surfaces()

    # ------------------------------------------------------------------
    # Surface geometry (static — no self needed)
    # ------------------------------------------------------------------

    def _weld_vertices(self) -> np.ndarray:
        """Assign an integer id to every triangle corner in the whole mesh
        (shape ``(3*n_tris,)``) such that two corners share an id iff
        they're at the same position after rounding to 4 decimals --
        vectorized equivalent of the old per-corner ``_pos_key`` position
        hash, computed once per VBO update instead of once per corner per
        surface group. This is what actually costs real time (a Python
        ``tuple(np.round(...))`` call per triangle corner, over the whole
        mesh) -- everything downstream of it is cheap by comparison, so
        there's no need to reach for numpy/scipy per surface group (that
        was tried and made things *worse*: real housing meshes apparently
        have many small coplanar surface groups, and scipy's per-call
        overhead -- sparse matrix construction, Python-level dispatch --
        dominated when paid once per small group instead of once overall).
        """
        verts = self._verticesf32.reshape(-1, 3).astype(np.float64)
        rounded = np.round(verts, 4)
        _, welded = np.unique(rounded, axis=0, return_inverse=True)
        return welded.ravel()

    def compute_surfaces(self, normal_tol: float = 0.02, dist_tol: float = 0.5) -> list:
        """
        Group triangle indices into coplanar surface groups.
        """

        verts = self._verticesf32
        norms = self._normalsf32

        n_tris = len(verts) // 3
        if n_tris == 0:
            return []

        normals = norms[::3].astype(np.float64)

        mag = np.linalg.norm(normals, axis=1, keepdims=True)
        mag = np.where(mag < 1e-10, 1.0, mag)
        normals /= mag

        mask = np.abs(normals) > 1e-6
        first_sig_vals = normals[np.arange(n_tris), np.argmax(mask, axis=1)]
        flip = np.where(mask.any(axis=1) & (first_sig_vals < 0), -1.0, 1.0)
        normals *= flip[:, np.newaxis]

        centroids = verts.reshape(-1, 3, 3).astype(np.float64).mean(axis=1)
        dists = np.einsum('ij,ij->i', centroids, normals)

        qn = np.round(normals / normal_tol).astype(np.int64)
        qd = np.round(dists / dist_tol).astype(np.int64)

        keys = np.concatenate([qn, qd[:, np.newaxis]], axis=1)

        # Vectorized replacement for the old per-triangle Python dict-build
        # loop -- this is a single call over the whole mesh (unlike
        # split_into_components, which runs once per raw group), so there's
        # no per-call-overhead-times-many-groups risk here. np.unique's
        # groups come back sorted by key, so first-occurrence order
        # (matching the old defaultdict's insertion order) is re-derived
        # from return_index. That matters: group order becomes each
        # surface's index into self._surfaces, which is what gets
        # persisted as terminal_surf_indices/wire_surf_indices from the
        # housing editor -- silently reordering groups would repoint
        # existing saved indices at the wrong surface.
        _, first_idx, inverse, counts = np.unique(
            keys, axis=0, return_index=True, return_inverse=True, return_counts=True)
        inverse = inverse.ravel()

        order_of_groups = np.argsort(first_idx)
        rank_of_group = np.empty_like(order_of_groups)
        rank_of_group[order_of_groups] = np.arange(len(order_of_groups))
        remapped_group_id = rank_of_group[inverse]
        sorted_counts = counts[order_of_groups]

        tri_order = np.argsort(remapped_group_id, kind='stable')
        tri_groups = np.split(tri_order, np.cumsum(sorted_counts)[:-1])

        return [Surface(grp.tolist(), normals[grp[0]].astype(np.float32), float(dists[grp[0]]))
                for grp in tri_groups]

    def split_into_components(self, surface: Surface) -> list:
        """
        Split a surface into topologically connected triangle islands.

        Deliberately plain Python (dict/set/BFS), same structure as the
        original -- this runs once per raw coplanar group, and a real
        housing can have many small groups, so anything with meaningful
        per-call setup cost (numpy array construction, scipy sparse
        matrices) ends up slower here than doing simple work in native
        Python. The only change from the original is using the
        pre-welded integer vertex ids (see _weld_vertices) as edge keys
        instead of rebuilding a rounded-position tuple per corner --
        that per-corner hashing was the actual bottleneck.
        """

        welded = self._welded_vertex_ids
        tri_list = list(surface.tri_indices)
        if len(tri_list) <= 1:
            return [surface]

        edge_tris = defaultdict(list)
        for ti in tri_list:
            c0 = int(welded[3 * ti])
            c1 = int(welded[3 * ti + 1])
            c2 = int(welded[3 * ti + 2])

            for a, b in ((c0, c1), (c1, c2), (c2, c0)):
                edge = (a, b) if a < b else (b, a)
                edge_tris[edge].append(ti)

        adj = defaultdict(list)
        for tris in edge_tris.values():
            for i in range(len(tris)):
                for k in range(i + 1, len(tris)):
                    adj[tris[i]].append(tris[k])
                    adj[tris[k]].append(tris[i])

        visited = set()
        components: list = []
        for start in tri_list:
            if start in visited:
                continue

            comp = []
            queue = [start]
            visited.add(start)

            while queue:
                ti = queue.pop()
                comp.append(ti)
                for nb in adj[ti]:
                    if nb not in visited:
                        visited.add(nb)
                        queue.append(nb)

            components.append(comp)

        if len(components) == 1:
            return [surface]

        return [Surface(comp, surface.normal.copy(), surface.plane_dist)
                for comp in components]

    @staticmethod
    def _coplanar(s: "Surface", ref: "Surface", normal_tol: float, dist_tol: float) -> bool:
        return (float(np.dot(s.normal, ref.normal)) > 1.0 - normal_tol and
                abs(s.plane_dist - ref.plane_dist) < dist_tol)

    @staticmethod
    def find_coplanar_surfaces(
        reference: "Surface",
        all_surfaces: list,
        normal_tol: float = 0.02,
        dist_tol: float = 0.5,
    ) -> list:
        """
        Return every surface in all_surfaces on the same plane as reference.
        """

        return [s for s in all_surfaces
                if MeshSurfacePicker._coplanar(s, reference, normal_tol, dist_tol)]

    def surface_centroid(self, surface: "Surface") -> np.ndarray:
        """
        Return the mean world-space position of all vertices belonging to surface.
        """

        verts = self.vertices.reshape(-1, 3)
        idxs = [3 * ti + j for ti in surface.tri_indices for j in range(3)]
        local_c = verts[idxs].mean(axis=0)

        return (local_c * self._scale_arr) @ self._rot_mat + self._pos_arr

    def _build_surfaces(self) -> None:
        """
        Group local vertices into coplanar surface islands.

        Uses the same analysis used by the housing editor dialog, so the
        groupings are consistent between the two contexts.

        This only needs to run when the VBO changes, not on every
        position/angle/scale update.
        """

        self._welded_vertex_ids = self._weld_vertices()

        raw = self.compute_surfaces()

        self._set_surfaces([s for grp in raw for s in self.split_into_components(grp)])

    def _set_surfaces(self, surfaces: list) -> None:
        """Install an already-computed surface list (either just built by
        :meth:`_build_surfaces`, or a cached one reused from elsewhere --
        see :meth:`update_vbo`'s ``surfaces`` parameter).
        """

        self._surfaces = surfaces

        if self._surfaces:
            self._surf_normals = np.array(
                [s.normal for s in self._surfaces], dtype=np.float64)
            self._surf_dists = np.array(
                [s.plane_dist for s in self._surfaces], dtype=np.float64)
        else:
            self._surf_normals = np.zeros((0, 3), dtype=np.float64)
            self._surf_dists = np.zeros((0,), dtype=np.float64)

    @property
    def surfaces(self) -> list[Surface]:
        """
        Read-only view of the computed surface list.
        """

        return self._surfaces

    def compute_ray_world(
        self, px: int, py: int
    ) -> tuple[np.ndarray, np.ndarray] | tuple[None, None]:
        """
        Compute a world-space ray from pixel (px, py).

        Returns (origin, unit_direction) in world space, or (None, None)
        if the camera matrices are not yet available.
        """

        camera = self._camera

        if camera.inv_clip is None or camera.viewport is None:
            return None, None

        vx, vy, vw, vh = camera.viewport
        if vw < 1 or vh < 1:
            return None, None

        # Mouse position is in logical pixels; GL viewport is in physical
        # pixels.  Scale by DPR to put both in the same unit before computing
        # normalised device coordinates.
        dpr = camera.devicePixelRatio
        wx = float(px) * dpr
        wy = float(vh - py * dpr)

        ndc_x = (2.0 * (wx - vx) / vw) - 1.0
        ndc_y = (2.0 * (wy - vy) / vh) - 1.0

        near = camera.unproject_from_ndc(ndc_x, ndc_y, -1.0)
        far = camera.unproject_from_ndc(ndc_x, ndc_y,  1.0)

        if near is None or far is None:
            return None, None

        d = far - near
        mag = float(np.linalg.norm(d))
        if mag < 1e-10:
            return None, None

        return near, d / mag

    def transform_ray_to_local(
        self,
        origin_world: np.ndarray,
        direction_world: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray] | tuple[None, None]:
        """
        Transform a world-space ray into model-local space.

        The forward transform is:   world = (local * S) @ R + P
        The inverse is therefore:   local = ((world - P) @ R^T) / S

        Both origin and direction are transformed.  Direction does not
        include the translation step (vectors are not affected by
        translations).  After the inverse scale, the direction is
        renormalised so that the parametric t returned from intersection
        tests is in local-space units.

        Returns (origin_local, direction_local) or (None, None) if the
        scale has a near-zero component.
        """

        scale = self._scale_arr
        if np.any(np.abs(scale) < 1e-10):
            return None, None

        # Inverse translate, inverse rotate, inverse scale – in that order.
        o = ((origin_world - self._pos_arr) @ self._inv_rot) / scale
        d = (direction_world @ self._inv_rot) / scale

        d_mag = float(np.linalg.norm(d))
        if d_mag < 1e-10:
            return None, None

        return o, d / d_mag

    def pick_surface_at(
        self, px: int, py: int, candidate_indices: _Iterable[int] | None = None
    ) -> tuple[int, np.ndarray | None]:
        """
        Ray-cast at pixel (px, py).

        ``candidate_indices``, if given, restricts the test to that subset
        of surface indices (into ``self.surfaces``) instead of every surface
        in the mesh — e.g. only the surfaces a caller has already matched to
        a cavity, rather than the whole housing shell.

        Returns (surf_idx, world_hit_point) where surf_idx is the index
        into self.surfaces of the closest intersected surface, or -1 on
        miss.  world_hit_point is the 3-D intersection in world space.
        """

        origin_w, direction_w = self.compute_ray_world(px, py)
        if origin_w is None:
            return -1, None

        return self.pick_surface_at_ray(
            origin_w, direction_w, candidate_indices=candidate_indices)

    def pick_surface_at_ray(
        self,
        origin_world: np.ndarray,
        direction_world: np.ndarray,
        candidate_indices: _Iterable[int] | None = None,
    ) -> tuple[int, np.ndarray | None]:
        """
        Ray-cast with a pre-computed world-space ray.

        Useful when the caller already has the ray (e.g. from another
        picker or from a cached value).

        ``candidate_indices``, if given, restricts the test to that subset
        of surface indices instead of every surface in the mesh.

        Returns (surf_idx, world_hit_point) or (-1, None) on miss.
        """

        if not self._surfaces or self.vertices is None:
            return -1, None

        origin_l, direction_l = self.transform_ray_to_local(
            origin_world, direction_world)

        if origin_l is None:
            return -1, None

        verts = self.vertices  # (N*3, 3) float64, local space

        if candidate_indices is None:
            idxs = np.arange(len(self._surfaces))
        else:
            idxs = np.asarray(list(candidate_indices), dtype=np.int64)
            if idxs.size == 0:
                return -1, None

        surf_normals = self._surf_normals[idxs]
        surf_dists = self._surf_dists[idxs]

        # Ray-vs-plane test for every candidate surface at once (cheap: one
        # array op per call, not per triangle). Invalid/behind-camera
        # surfaces are marked +inf so they sort last and are never visited
        # below.
        denom = surf_normals @ direction_l  # (len(idxs),)
        t = np.full(len(idxs), np.inf, dtype=np.float64)
        valid = np.abs(denom) >= 1e-8
        t[valid] = (surf_dists[valid] - surf_normals[valid] @ origin_l) / denom[valid]
        t[t < 0.0] = np.inf

        # Visit surfaces nearest-plane-first. The first one whose actual
        # triangles (not just its infinite plane) contain the hit point is
        # necessarily the closest valid hit — every surface with a smaller t
        # was already tried and missed, and nothing further can beat it.
        best_t = float('inf')
        best_idx = -1

        for k in np.argsort(t):
            tk = float(t[k])
            if not np.isfinite(tk):
                break

            i = int(idxs[k])
            surf = self._surfaces[i]
            hit_l = origin_l + tk * direction_l

            tri_idx = np.asarray(surf.tri_indices)
            a = verts[3 * tri_idx]
            b = verts[3 * tri_idx + 1]
            c = verts[3 * tri_idx + 2]
            p = np.broadcast_to(hit_l, a.shape)

            if _points_in_triangles(p, a, b, c).any():
                best_t = tk
                best_idx = i
                break

        if best_idx < 0:
            return -1, None

        # Convert local hit back to world space.
        hit_l = origin_l + best_t * direction_l
        hit_w = (hit_l * self._scale_arr) @ self._rot_mat + self._pos_arr

        return best_idx, hit_w

    def _set_active(self) -> None:
        """
        Make this picker the scene-wide active one, clearing any other.
        """

        if (
            MeshSurfacePicker._active is not None and
            MeshSurfacePicker._active is not self
        ):
            MeshSurfacePicker._active.clear_selection()

        MeshSurfacePicker._active = self

    def select(self, surf_idx: int) -> None:
        """
        Highlight surface surf_idx.
        """

        self._set_active()
        self.selected_surf_idx = surf_idx

    def clear_selection(self) -> None:
        """
        Remove the highlight.
        """

        self.selected_surf_idx = None

        if MeshSurfacePicker._active is self:
            MeshSurfacePicker._active = None

    def cleanup(self) -> None:
        """
        Unbind transform callbacks.
        """

        if MeshSurfacePicker._active is self:
            MeshSurfacePicker._active = None

        for attr, cb in (
            (self._position, self._on_position),
            (self._angle, self._on_angle),
            (self._scale, self._on_scale),
        ):
            try:
                attr.unbind(cb)
            except Exception:  # NOQA
                pass
