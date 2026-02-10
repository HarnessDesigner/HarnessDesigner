"""
End-to-end CPU picking pipeline:
 - Frustum culling (AABB vs frustum planes)
 - Screen-space AABB projection + 2D mouse containment (cheap filter)
 - Depth metric (eye-space z or ray-AABB t) and sorting
 - Ray-AABB refinement (slab test)
 - Optional ray-triangle Möller–Trumbore intersection for exact mesh hit

This file provides:
 - build frustum from camera params or from view/projection matrices
 - fast filters and precise refinements
 - example pick-on-click handler that cycles candidates on repeated clicks
"""

import numpy as np
from OpenGL.GL import *
from math import inf

from . import debug as _debug


@_debug.logfunc
def _gl_get_matrices():
    """
    Return
    modelview (mv), projection (pj) as row-major 4x4 numpy arrays and
    viewport tuple.
    """
    mv_raw = glGetDoublev(GL_MODELVIEW_MATRIX)
    pj_raw = glGetDoublev(GL_PROJECTION_MATRIX)
    vp = glGetIntegerv(GL_VIEWPORT)

    mv = np.array(mv_raw, dtype=np.float64).reshape((4, 4)).T
    pj = np.array(pj_raw, dtype=np.float64).reshape((4, 4)).T
    return mv, pj, tuple(vp)


@_debug.logfunc
def _project_point_world(point, mv, pj, viewport):
    """
    Project world point to window coords. mv, pj are row-major 4x4 numpy arrays.
    """

    v = np.array([point[0], point[1], point[2], 1.0], dtype=np.float64)
    eye = mv.dot(v)
    clip = pj.dot(eye)

    w = clip[3]
    if np.isclose(w, 0.0):
        return None

    ndc = clip[:3] / w
    vx, vy, vw, vh = viewport

    winx = vx + (ndc[0] + 1.0) * vw * 0.5
    winy = vy + (ndc[1] + 1.0) * vh * 0.5
    winz = (ndc[2] + 1.0) * 0.5

    return winx, winy, winz, eye


@_debug.logfunc
def _unproject_from_ndc(ndc, inv_mvp):
    """
    ndc: (x,y,z) in [-1,1]
    inv_mvp: inverse of P*MV (row-major)
    """

    clip = np.array([ndc[0], ndc[1], ndc[2], 1.0], dtype=np.float64)

    world = inv_mvp.dot(clip)
    if np.isclose(world[3], 0.0):
        return None

    world /= world[3]

    return world[:3]


@_debug.logfunc
def _mouse_ray_from_screen(mx, my, mv=None, pj=None,
                           viewport=None, mouse_is_top_left=True):
    """
    Return (origin, dir) in world space. Uses manual unproject via inverse(P * MV).
    mx,my should be in framebuffer pixel coordinates
    (origin top-left if mouse_is_top_left True).
    """

    if mv is None or pj is None or viewport is None:
        mv, pj, viewport = _gl_get_matrices()

    # compute inv(P * MV)
    mvp = pj.dot(mv)  # row-major
    inv_mvp = np.linalg.inv(mvp)
    vx, vy, vw, vh = viewport

    # convert mouse to GL bottom-left origin:
    if mouse_is_top_left:
        wx = mx
        wy = (vh - my)
    else:
        wx = mx
        wy = my

    # map to NDC
    ndc_x = (2.0 * (wx - vx) / vw) - 1.0
    ndc_y = (2.0 * (wy - vy) / vh) - 1.0

    # near: z = -1 (OpenGL NDC), far z = +1
    near_world = _unproject_from_ndc((ndc_x, ndc_y, -1.0), inv_mvp)
    far_world = _unproject_from_ndc((ndc_x, ndc_y,  1.0), inv_mvp)
    if near_world is None or far_world is None:
        return None, None

    origin = np.array(near_world, dtype=np.float64)
    direc = np.array(far_world, dtype=np.float64) - origin
    direc /= np.linalg.norm(direc)

    return origin, direc


# Ray vs AABB (slab method)
@_debug.logfunc
def _ray_intersect_aabb(orig, direc, aabb_min, aabb_max, t0=0.0, t1=inf):
    aabb_min = np.array(aabb_min, dtype=np.float64)
    aabb_max = np.array(aabb_max, dtype=np.float64)

    inv_dir = 1.0 / direc

    tmin_all = (aabb_min - orig) * inv_dir
    tmax_all = (aabb_max - orig) * inv_dir

    tmin = np.minimum(tmin_all, tmax_all)
    tmax = np.maximum(tmin_all, tmax_all)

    t_enter = max(t0, np.max(tmin))
    t_exit = min(t1, np.min(tmax))

    if t_enter <= t_exit and t_exit >= 0.0:
        return True, t_enter

    return False, None


# Ray-triangle Möller–Trumbore
@_debug.logfunc
def _ray_triangle_intersect(orig, dir, v0, v1, v2, eps=1e-9):  # NOQA
    edge1 = v1 - v0  # NOQA
    edge2 = v2 - v0

    h = np.cross(dir, edge2)  # NOQA
    a = np.dot(edge1, h)

    if -eps < a < eps:
        return False, None  # parallel

    f = 1.0 / a
    s = orig - v0

    u = f * np.dot(s, h)
    if u < 0.0 or u > 1.0:
        return False, None

    q = np.cross(s, edge1)  # NOQA
    v = f * np.dot(dir, q)
    if v < 0.0 or u + v > 1.0:
        return False, None

    t = f * np.dot(edge2, q)
    if t > eps:
        return True, t

    return False, None


@_debug.logfunc
def _aabb_screen_bbox_and_depth(bboxes, mv, pj,
                                viewport, flip_y_for_ui=True):
    """
    Build a 2D screen bbox from projecting ALL 8 AABB corners.
    This is necessary for stability across camera yaw/pitch.
    """
    for corners in bboxes:
        screen_pts = []
        depths = []
        any_in_front = False

        for c in corners:
            proj = _project_point_world(c, mv, pj, viewport)
            if proj is None:
                continue

            wx, wy, wz, eye_coords = proj
            if flip_y_for_ui:
                wy = viewport[3] - wy

            screen_pts.append((wx, wy, wz))

            eye_z = eye_coords[2]
            if eye_z < 0:
                any_in_front = True
                depths.append(-eye_z)
            else:
                depths.append(inf)

        if not screen_pts:
            continue

        xs = [p[0] for p in screen_pts]
        ys = [p[1] for p in screen_pts]

        bbox2d = (min(xs), min(ys), max(xs), max(ys))

        # depth metric: closest in-front corner if possible
        if any_in_front:
            depth_metric = float(min(d for d in depths if d != inf))
        else:
            depth_metric = float(min(depths))

        yield bbox2d, depth_metric


def _get_obj_rotation_matrix_3x3(obj) -> np.ndarray | None:
    """
    Try to obtain a stable 3x3 rotation matrix for the object.

    Expected possibilities (adjust to your real object API):
    - obj.angle.as_matrix (your Angle class property)
    - obj.rotation_matrix
    - obj.rotation (already a 3x3)
    """
    return obj.angle.as_matrix


def _get_obj_translation_3(obj) -> np.ndarray | None:
    """
    Try to obtain object translation as a 3-vector.
    Likely candidates: obj.position (Point), obj.center, obj.pos
    """

    return obj.position.as_float


@_debug.logfunc
def _ray_to_local_space(orig_world, dir_world, R_obj, t_obj):
    """
    Transform a world-space ray into object-local space.

    We must match your convention.
    If your object points are transformed as row-vectors: p_world = p_local @ R + t,
    then inverse is: p_local = (p_world - t) @ R.T   (since pure rotation)

    We'll assume pure rotation (orthonormal R). If you add scale/shear later,
    you need a full inverse matrix.
    """
    R = np.asarray(R_obj, dtype=np.float64)
    t = np.asarray(t_obj, dtype=np.float64)

    # row-vector inverse: multiply by R.T on the right
    o_local = (orig_world - t) @ R.T
    d_local = dir_world @ R.T

    dn = np.linalg.norm(d_local)
    if dn > 1e-12:
        d_local = d_local / dn

    return o_local, d_local


@_debug.logfunc
def _ray_intersect_obb_via_local_aabb(orig_world, dir_world, local_min,
                                      local_max, R_obj, t_obj):
    """
    Ray vs OBB: transform ray into local space, then slab test vs local AABB.
    """

    o_local, d_local = _ray_to_local_space(orig_world, dir_world, R_obj, t_obj)
    return _ray_intersect_aabb(o_local, d_local, local_min, local_max)


# Candidate picking + cycling
last_pick_state = {
    'mouse_pos': None,
    'candidates': [],
    'index': 0
}


@_debug.logfunc
def _pick_candidates_at_mouse(mx, my, scene_objects, mv=None, pj=None, viewport=None,
                             mouse_is_top_left=True, tol_pixels=3.0, max_candidates=128):  # NOQA
    """
    scene_objects: iterable of objects with attributes:
        - aabb_min (3-tuple), aabb_max (3-tuple)
        - optional .id or reference returned in candidate tuple
    Returns list of (depth_metric, object, bbox2d) sorted by depth (closest first)
    """

    if mv is None or pj is None or viewport is None:
        mv, pj, viewport = _gl_get_matrices()

    mx_screen = mx
    my_screen = my

    candidates = []
    for obj in scene_objects:
        for (minx, miny, maxx, maxy), depth in (
            _aabb_screen_bbox_and_depth(obj.bb, mv, pj, viewport, flip_y_for_ui=True)
        ):

            if (
                minx - tol_pixels <= mx_screen <= maxx + tol_pixels and
                miny - tol_pixels <= my_screen <= maxy + tol_pixels
            ):

                candidates.append((depth, obj))

    candidates.sort(key=lambda k: k[0])

    return candidates[:max_candidates]


@_debug.logfunc
def find_object(mouse_pos, scene_objects):
    mx, my = mouse_pos.as_float[:-1]

    mv, pj, vp = _gl_get_matrices()
    move_thresh = 4.0

    # refresh candidate list if mouse moved significantly
    if last_pick_state['mouse_pos'] is None:
        moved = True
    else:
        moved = np.hypot(mx - last_pick_state['mouse_pos'][0],
                         my - last_pick_state['mouse_pos'][1]) > move_thresh

    if moved:
        last_pick_state['candidates'] = _pick_candidates_at_mouse(mx, my, scene_objects, mv, pj, vp)
        last_pick_state['mouse_pos'] = (mx, my)
        last_pick_state['index'] = 0

    cands = last_pick_state['candidates']
    if not cands:
        return None

    # Build ray once
    o, d = _mouse_ray_from_screen(mx, my, mv, pj, vp)
    if o is None:
        # fallback: just pick first candidate
        return cands[0][1]

    # Evaluate ray hit for ALL candidates; pick closest t
    best_obj = None
    best_t = inf

    for _, obj in cands:
        # world AABB
        for wmin, wmax in obj.rect:

            hit, t_hit = _ray_intersect_aabb(o, d, wmin.as_float, wmax.as_float)
            if hit and t_hit < best_t:
                best_t = t_hit
                best_obj = obj

    return best_obj
