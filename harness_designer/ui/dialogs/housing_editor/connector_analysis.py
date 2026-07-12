"""
connector_analysis.py
Pure-numpy geometry analysis for connector housing inspection.
No Qt or OpenGL dependencies.
"""
from __future__ import annotations

import math
import numpy as np
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Surface:
    tri_indices: List[int]   # 0-based indices into triangle soup
    normal: np.ndarray  # unit normal, float32, canonical direction
    plane_dist:  float       # dot(centroid, normal) — signed dist from origin


# ── 1.  Surface grouping ──────────────────────────────────────────────────────

def compute_surfaces(
    vertices: np.ndarray,   # (3N, 3) float32 — triangle-soup positions
    face_normals: np.ndarray,   # (3N, 3) float32 — face normal repeated per vertex
    normal_tol: float = 0.02,
    dist_tol: float = 0.5,
) -> List[Surface]:

    """Group triangle indices into coplanar surface groups."""
    n_tris = len(vertices) // 3
    normals = face_normals[::3].astype(np.float64)      # one per triangle

    mag = np.linalg.norm(normals, axis=1, keepdims=True)
    mag = np.where(mag < 1e-10, 1.0, mag)
    normals /= mag

    # Canonicalize so n and -n hash identically
    for i in range(n_tris):
        for c in normals[i]:
            if abs(c) > 1e-6:
                if c < 0:
                    normals[i] *= -1
                break

    centroids = vertices.reshape(-1, 3, 3).astype(np.float64).mean(axis=1)
    dists = np.einsum('ij,ij->i', centroids, normals)

    qn = np.round(normals / normal_tol).astype(np.int64)
    qd = np.round(dists / dist_tol).astype(np.int64)

    groups: Dict[tuple, List[int]] = defaultdict(list)
    for i in range(n_tris):
        groups[(tuple(qn[i]), int(qd[i]))].append(i)

    return [
        Surface(lst, normals[lst[0]].astype(np.float32), float(dists[lst[0]]))
        for lst in groups.values()
    ]


def split_into_components(surface: Surface, vertices: np.ndarray) -> List[Surface]:
    """
    Split a surface group into topologically connected triangle islands.
    Two triangles are neighbours if they share an edge (two matching vertex positions).
    Returns a list of one Surface per island; returns [surface] if already one island.
    """

    verts = vertices.reshape(-1, 3)
    tri_list = list(surface.tri_indices)

    # Build edge → [triangle, ...] map
    edge_tris: Dict[tuple, List[int]] = defaultdict(list)
    for ti in tri_list:
        pvs = [_pos_key(verts[3*ti + j]) for j in range(3)]
        for j in range(3):
            edge = (min(pvs[j], pvs[(j + 1) % 3]),
                    max(pvs[j], pvs[(j + 1) % 3]))

            edge_tris[edge].append(ti)

    # Triangle adjacency (shared edge)
    adj: Dict[int, List[int]] = defaultdict(list)
    for tris in edge_tris.values():
        for i in range(len(tris)):
            for k in range(i + 1, len(tris)):
                adj[tris[i]].append(tris[k])
                adj[tris[k]].append(tris[i])

    # BFS flood-fill
    visited = set()
    components: List[List[int]] = []
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


# ── 2.  Boundary loop extraction ──────────────────────────────────────────────

def _pos_key(v: np.ndarray) -> tuple:
    return tuple(np.round(v.astype(np.float64), 4))


def extract_boundary_loops(
    tri_indices: List[int],
    vertices: np.ndarray,   # (3N, 3) float32
) -> List[np.ndarray]:
    """
    Return closed boundary loops (hole outlines) as list of (M, 3) float32 arrays.
    """

    verts = vertices.reshape(-1, 3)

    edge_use: Dict[tuple, int] = defaultdict(int)
    edge_fwd: Dict[tuple, Tuple[tuple, tuple]] = {}

    for ti in tri_indices:
        for j in range(3):
            a, b = 3 * ti + j, 3 * ti + (j + 1) % 3
            pa, pb = _pos_key(verts[a]), _pos_key(verts[b])
            key = (min(pa, pb), max(pa, pb))
            edge_use[key] += 1
            edge_fwd[key] = (pa, pb)

    # boundary = edges belonging to exactly one triangle
    adj: Dict[tuple, List[tuple]] = defaultdict(list)
    for key, cnt in edge_use.items():
        if cnt == 1:
            pa, pb = edge_fwd[key]
            adj[pa].append(pb)

    visited = set()
    loops: List[np.ndarray] = []

    for start in list(adj):
        if start in visited:
            continue

        loop = [start]
        visited.add(start)
        cur = start
        while True:
            nxts = [n for n in adj.get(cur, []) if n not in visited]
            if not nxts:
                break

            nxt = nxts[0]
            visited.add(nxt)
            loop.append(nxt)
            cur = nxt

        if len(loop) >= 6:  # skip degenerate tiny loops
            loops.append(np.array(loop, dtype=np.float32))

    return loops


# ── 3.  Hole classification ───────────────────────────────────────────────────

def plane_frame(n: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    n = np.asarray(n, np.float64)
    n /= np.linalg.norm(n) + 1e-12

    if abs(n[0]) < 0.9:
        ref = np.array([1., 0., 0.])
    else:
        ref = np.array([0., 1., 0.])

    u = np.cross(n, ref)
    u /= np.linalg.norm(u) + 1e-12

    return u, np.cross(n, u)


def classify_loop(
    pts: np.ndarray,   # (M, 3)
    normal: np.ndarray,
) -> Tuple[str, Dict[str, Any]]:
    """
    Classify a 2-D shape as 'circle' or 'rect' by area comparison.

    1. Project unique vertices onto the plane.
    2. Compute actual shape area  — shoelace on points sorted by angle (convex hull).
    3. Compute bounding-rectangle area  — OBB via PCA.
    4. Compute circumscribed-circle area — smallest circle enclosing all points,
       centred on the point-cloud centroid.
    5. Whichever area (rect or circle) is closer to the actual shape area wins.
    """

    c = pts.mean(axis=0).astype(np.float64)
    n = np.asarray(normal, np.float64)
    n /= np.linalg.norm(n) + 1e-12
    u, v = plane_frame(n)

    rel = pts.astype(np.float64) - c
    pts2d = np.column_stack([rel @ u, rel @ v])
    unique2d = np.unique(np.round(pts2d, 4), axis=0)

    # ── OBB via PCA ──────────────────────────────────────────────────────────
    cov = np.cov(unique2d.T) if len(unique2d) > 2 else np.eye(2)
    if cov.ndim < 2:
        ax1 = np.array([1.0, 0.0])
        ax2 = np.array([0.0, 1.0])
    else:
        _, ev = np.linalg.eigh(cov)
        ax1 = ev[:, 1]
        ax2 = ev[:, 0]

    p1, p2 = unique2d @ ax1, unique2d @ ax2
    half_w = (p1.max() - p1.min()) / 2
    half_h = (p2.max() - p2.min()) / 2
    off2d = np.array([(p1.max() + p1.min()) / 2, (p2.max() + p2.min()) / 2])

    # 3-D OBB centre and axes (used in both return branches)
    obb_c3d = (c + off2d[0] *
               (ax1[0] * u + ax1[1] * v) + off2d[1] *
               (ax2[0] * u + ax2[1] * v))

    u3 = (ax1[0] * u + ax1[1] * v).astype(np.float32)
    v3 = (ax2[0] * u + ax2[1] * v).astype(np.float32)

    # ── Actual shape area: shoelace on angle-sorted unique points ─────────────
    centroid2d = unique2d.mean(axis=0)
    angles = np.arctan2(unique2d[:, 1] - centroid2d[1],
                        unique2d[:, 0] - centroid2d[0])

    ring = unique2d[np.argsort(angles)]
    x = ring[:, 0]
    y = ring[:, 1]

    shape_area = abs(float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))) * 0.5

    # ── Bounding-rectangle area ───────────────────────────────────────────────
    rect_area = 4.0 * half_w * half_h

    # ── Circumscribed-circle area (centred on point-cloud centroid) ───────────
    r_circum = float(np.linalg.norm(unique2d - centroid2d, axis=1).max())
    circle_area = math.pi * r_circum ** 2

    # ── Decision: whichever enclosing area is closer to the actual shape wins ───
    # Both rect_area and circle_area can be larger OR smaller than shape_area
    # (e.g. a chamfered rect has shape_area < rect_area), so we use abs() on both
    # sides and pick the smaller difference.
    auto_kind = ('circle'
                 if abs(circle_area - shape_area) < abs(rect_area - shape_area)
                 else 'rect')

    # Always return ALL params so the caller can override kind without recomputing.
    return auto_kind, dict(normal=n.astype(np.float32), u=u3, v=v3,
                           center=obb_c3d.astype(np.float32), radius=r_circum,
                           half_w=float(half_w), half_h=float(half_h))


# ── 4.  Hole alignment ────────────────────────────────────────────────────────

def align_holes(
    pin_holes: List[dict],
    wire_holes: List[dict],
    normal: np.ndarray,
    pos_tol: float = 2.0,
) -> List[Tuple[dict, dict]]:
    """
    Greedy nearest-neighbor match of pin→wire
    holes projected onto the shared plane.
    """

    u, v = plane_frame(np.asarray(normal, np.float64))

    def proj(c):
        c = np.asarray(c, np.float64)
        return np.array([float(c @ u), float(c @ v)])

    used, matched = set(), []
    for ph in pin_holes:
        pc = proj(ph['params']['center'])

        bd = pos_tol
        bi = -1

        for wi, wh in enumerate(wire_holes):
            if wi in used:
                continue

            d = float(np.linalg.norm(pc - proj(wh['params']['center'])))
            if d < bd:
                bd = d
                bi = wi

        if bi >= 0:
            matched.append((ph, wire_holes[bi]))
            used.add(bi)

    return matched


# ── 5.  Geometry generation ───────────────────────────────────────────────────

def _project_to_plane(c: np.ndarray, n: np.ndarray, d: float) -> np.ndarray:
    """Project point c onto plane (n, d)."""
    return c - (float(c @ n) - d) * n


def _cylinder_mesh(c: np.ndarray, r: float, u: np.ndarray,
                   v: np.ndarray, n: np.ndarray, d0: float,
                   d1: float, seg: int = 32) -> Tuple[np.ndarray, np.ndarray]:

    ang = np.linspace(0, 2 * math.pi, seg, endpoint=False)

    # (S,3) outward unit
    ring = np.cos(ang)[:, None] * u + np.sin(ang)[:, None] * v
    c0 = _project_to_plane(c, n, d0)
    c1 = _project_to_plane(c, n, d1)

    # (S,3)
    r0 = c0 + r * ring
    r1 = c1 + r * ring

    verts, norms = [], []
    for i in range(seg):
        j = (i + 1) % seg

        for tri, ns in (
            ([r0[i], r1[i], r1[j]], [ring[i], ring[i], ring[j]]),
            ([r0[i], r1[j], r0[j]], [ring[i], ring[j], ring[j]]),
        ):
            verts.extend(tri)
            norms.extend(ns)

    return np.array(verts, np.float32), np.array(norms, np.float32)


def _box_mesh(c: np.ndarray, hw: float, hh: float, u: np.ndarray, v: np.ndarray,
              n: np.ndarray, d0: float, d1: float) -> Tuple[np.ndarray, np.ndarray]:

    offs = np.array([-hw * u - hh * v,
                     hw * u - hh * v,
                     hw * u + hh * v,
                     -hw * u + hh * v])

    c0 = _project_to_plane(c, n, d0)
    c1 = _project_to_plane(c, n, d1)

    s = c0 + offs
    e = c1 + offs      # (4,3) each

    sn = [-v, u, v, -u]

    verts, norms = [], []
    for i in range(4):
        j = (i + 1) % 4
        for tri in ([s[i], e[i], e[j]], [s[i], e[j], s[j]]):
            verts.extend(tri)
            norms.extend([sn[i], sn[i], sn[i]])

    return np.array(verts, np.float32), np.array(norms, np.float32)


def generate_hole_geometry(
    kind: str,
    params: dict,
    d_pin: float,
    d_wire: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Triangle-soup cylinder or box spanning pin→wire planes.
    Returns (verts, norms) float32.
    """

    n = params['normal'].astype(np.float64)
    n /= np.linalg.norm(n) + 1e-12

    c = params['center'].astype(np.float64)
    u = params['u'].astype(np.float64)
    v = params['v'].astype(np.float64)

    if kind == 'circle':
        return _cylinder_mesh(c, params['radius'], u, v, n, d_pin, d_wire)

    return _box_mesh(
        c, params['half_w'], params['half_h'], u, v, n, d_pin, d_wire)


# ── 6.  Inner-hole filtering ─────────────────────────────────────────────────

def _loop_area_2d(loop: np.ndarray, u: np.ndarray, v: np.ndarray) -> float:
    """Absolute 2-D area of a loop via the shoelace formula."""
    pts = loop.astype(np.float64)
    x = pts @ u
    y = pts @ v

    return abs(0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)))


def inner_loops_only(
    loops: List[np.ndarray],
    normal: np.ndarray
) -> List[np.ndarray]:
    """
    Given all boundary loops of a flat face, discard the outer perimeter(s) and
    return only the inner hole loops.

    Strategy: the outer perimeter is always the loop with the largest 2-D area.
    Everything smaller is a hole cavity.  We drop any loop whose area is within
    50 % of the maximum — this handles cases where two large outer-boundary
    segments exist while still keeping distinctly smaller cavities.
    """

    if not loops:
        return []

    u, v = plane_frame(np.asarray(normal, np.float64))
    areas = [_loop_area_2d(i, u, v) for i in loops]
    max_area = max(areas)

    # Keep loops that are clearly smaller than the outer boundary
    return [i for i, a in zip(loops, areas) if a < max_area * 0.5]


# ── 7.  Size-consensus filtering ─────────────────────────────────────────────

def filter_by_size_consensus(
    holes: List[dict],
    size_tol: float = 0.5,
) -> List[dict]:
    """
    Keep only holes whose size matches at least one other hole within `size_tol`.
    This enforces the requirement that valid cavities appear in groups of ≥ 2.

    Circle match : |r_a − r_b| < size_tol
    Rect match   : both normalised half-sides (short, long) within size_tol
                   (orientation-invariant so a portrait and landscape rect still match)
    """

    if len(holes) < 2:
        return []

    def _matches(a: dict, b: dict) -> bool:
        if a['type'] != b['type']:
            return False

        if a['type'] == 'circle':
            return abs(a['params']['radius'] - b['params']['radius']) < size_tol

        # rect — compare (shorter, longer) half-side pairs
        wa = a['params']['half_w']
        ha = a['params']['half_h']

        wb = b['params']['half_w']
        hb = b['params']['half_h']

        sa = min(wa, ha)
        la = max(wa, ha)

        sb = min(wb, hb)
        lb = max(wb, hb)

        return abs(sa - sb) < size_tol and abs(la - lb) < size_tol

    return [h for i, h in enumerate(holes)
            if any(_matches(h, holes[j])
                   for j in range(len(holes)) if j != i)]


def _coplanar(s: Surface, ref: Surface, normal_tol: float, dist_tol: float) -> bool:
    return (float(np.dot(s.normal, ref.normal)) > 1.0 - normal_tol and
            abs(s.plane_dist - ref.plane_dist) < dist_tol)


# ── 8.  Coplanar-surface lookup ──────────────────────────────────────────────

def find_coplanar_surfaces(
    reference: Surface,
    all_surfaces: List[Surface],
    normal_tol: float = 0.02,
    dist_tol: float = 0.5,
) -> List[Surface]:
    """
    Return every surface in all_surfaces that lies on the same world plane as
    reference (same normal direction within normal_tol, same plane distance
    within dist_tol).  The reference surface itself is included.
    """
    return [s for s in all_surfaces
            if _coplanar(s, reference, normal_tol, dist_tol)]


# ── 9.  Direct terminal-plane approach ───────────────────────────────────────

def get_surface_shape(
    surface: Surface,
    vertices: np.ndarray,   # (3N, 3) float32
) -> Tuple[str, dict]:
    """
    Classify the 2-D footprint of a surface as 'circle' or 'rect'.
    Projects all vertex positions of the surface onto its plane and runs the
    same circularity / OBB logic used for boundary loops.
    """

    verts = vertices.reshape(-1, 3)
    idxs = [3 * ti + j for ti in surface.tri_indices for j in range(3)]
    pts = verts[idxs].astype(np.float32)

    return classify_loop(pts, surface.normal)


def surface_centroid(surface: Surface, vertices: np.ndarray) -> np.ndarray:
    verts = vertices.reshape(-1, 3)
    idxs = [3 * ti + j for ti in surface.tri_indices for j in range(3)]

    return verts[idxs].astype(np.float64).mean(axis=0)


def generate_terminal_geometry(
    terminal: Surface,
    wire: Surface,
    vertices: np.ndarray,
    kind_override: Optional[str] = None,
    length_factor: float = 1.0,
) -> Tuple[str, dict, np.ndarray, np.ndarray]:
    """
    Build a box or cylinder for one terminal cavity, spanning from the terminal
    recess plane toward the wire-side plane.

    The extrusion axis is the terminal surface's own normal.  The wire-side
    distance is the wire centroid projected onto that axis, so this works
    regardless of whether the two normals are parallel or antiparallel.

    kind_override: 'circle' or 'rect' — forces shape, ignoring auto-detection.
    length_factor: 0.0–1.0 — scales the extrusion length; the terminal floor
                   (d_start) is the fixed anchor; the wire end moves toward it.
    """

    auto_kind, params = get_surface_shape(terminal, vertices)
    kind = kind_override if kind_override in ('circle', 'rect') else auto_kind

    n = terminal.normal.astype(np.float64)
    n /= np.linalg.norm(n) + 1e-12

    d_start = terminal.plane_dist
    d_full = float(surface_centroid(wire, vertices) @ n)

    d_end = (d_start + (d_full - d_start) *
             float(np.clip(length_factor, 0.01, 1.0)))

    v, nm = generate_hole_geometry(kind, params, d_start, d_end)

    return kind, params, v, nm


# ── 9.  Full pipeline ─────────────────────────────────────────────────────────

def run_analysis(
    vertices: np.ndarray,
    face_normals: np.ndarray,  # NOQA
    pin_surface: Surface,
    wire_surface: Surface,
    all_surfaces: List[Surface],
    normal_tol: float = 0.02,
    dist_tol: float = 0.5,
    pos_tol: float = 2.0,
    size_tol: float = 0.5,
) -> List[Tuple[str, dict, np.ndarray, np.ndarray]]:
    """
    Full pipeline:
      1. Collect all triangles coplanar with pin_surface / wire_surface.
      2. Extract boundary loops (= hole outlines) from each plane.
      3. Strip outer perimeter; keep only inner cavity loops.
      4. Classify each loop as circle or rect.
      5. Drop any hole whose size doesn't match at least one other (≥ 2 required).
      6. Match aligned hole pairs by projected 2-D center.
      7. Generate mesh geometry for every matched hole.

    Returns list of (kind, params, verts_f32, norms_f32).
    """

    pin_tris = [ti for s in all_surfaces
                if _coplanar(s, pin_surface, normal_tol, dist_tol)
                for ti in s.tri_indices]

    wire_tris = [ti for s in all_surfaces
                 if _coplanar(s, wire_surface, normal_tol, dist_tol)
                 for ti in s.tri_indices]

    pin_loops = inner_loops_only(
        extract_boundary_loops(pin_tris,  vertices), pin_surface.normal)

    wire_loops = inner_loops_only(
        extract_boundary_loops(wire_tris, vertices), wire_surface.normal)

    pin_holes = [{'type': t, 'params': p}
                 for t, p in (classify_loop(i, pin_surface.normal)
                              for i in pin_loops)]

    wire_holes = [{'type': t, 'params': p}
                  for t, p in (classify_loop(i, wire_surface.normal)
                               for i in wire_loops)]

    # Require each surviving hole to have at least one size-matching partner
    pin_holes = filter_by_size_consensus(pin_holes, size_tol)
    wire_holes = filter_by_size_consensus(wire_holes, size_tol)

    matched = align_holes(pin_holes, wire_holes, pin_surface.normal, pos_tol)

    results = []
    for ph, _wh in matched:
        v, n = generate_hole_geometry(
            ph['type'], ph['params'],
            pin_surface.plane_dist, wire_surface.plane_dist)

        results.append((ph['type'], ph['params'], v, n))

    return results
