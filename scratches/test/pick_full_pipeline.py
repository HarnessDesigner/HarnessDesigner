
# pick_full_pipeline.py
# Unmodified from the original file you provided earlier.

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


def _aabb_screen_bbox_and_depth(aabb_min, aabb_max, mv, pj,
                                viewport, flip_y_for_ui=True):

    corners = [aabb_min.as_float, aabb_max.as_float]
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
        return None

    xs = [p[0] for p in screen_pts]
    ys = [p[1] for p in screen_pts]

    bbox2d = (min(xs), min(ys), max(xs), max(ys))

    depth_metric = float(min([d for d in depths if d != inf])
                         if any_in_front else min(depths))

    if depth_metric == inf:
        # fallback: distance to center
        center = 0.5 * (aabb_min.as_numpy + aabb_max.as_numpy)
        v = np.array([center[0], center[1], center[2], 1.0], dtype=np.float64)
        eye_center = mv.dot(v)

        if eye_center[2] < 0:
            depth_metric = float(-eye_center[2])
        else:
            depth_metric = float(np.linalg.norm(center))

    return bbox2d, depth_metric


# Candidate picking + cycling
last_pick_state = {
    'mouse_pos': None,
    'candidates': [],
    'index': 0
}


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
        res = _aabb_screen_bbox_and_depth(obj.hit_test_rect[0], obj.hit_test_rect[1],
                                          mv, pj, viewport, flip_y_for_ui=True)

        if res is None:
            continue

        (minx, miny, maxx, maxy), depth = res

        if (
            minx - tol_pixels <= mx_screen <= maxx + tol_pixels and
            miny - tol_pixels <= my_screen <= maxy + tol_pixels
        ):

            candidates.append((depth, obj))

    candidates.sort(key=lambda k: k[0])

    return candidates[:max_candidates]


def handle_click_cycle(mx, my, scene_objects):
    """
    On click: select next candidate under pixel.
              Recomputes candidate list if mouse moved > threshold.

    Returns selected object or None.
    """

    mv, pj, vp = _gl_get_matrices()
    move_thresh = 4.0

    if last_pick_state['mouse_pos'] is None:
        last_pick_state['candidates'] = _pick_candidates_at_mouse(
            mx, my, scene_objects, mv, pj, vp)

        last_pick_state['index'] = 0
        last_pick_state['mouse_pos'] = (mx, my)
    else:
        move = np.hypot(mx - last_pick_state['mouse_pos'][0],  # NOQA
                        my - last_pick_state['mouse_pos'][1])  # NOQA

        if move > move_thresh:
            last_pick_state['candidates'] = _pick_candidates_at_mouse(
                mx, my, scene_objects, mv, pj, vp)

            last_pick_state['index'] = 0
            last_pick_state['mouse_pos'] = (mx, my)

    cands = last_pick_state['candidates']
    if not cands:
        return None

    # choose candidate at current index, optionally refine
    # with ray-AABB (fast) and ray-triangle (expensive)
    depth, obj = cands[last_pick_state['index']]

    # refine with ray-AABB
    o, d = _mouse_ray_from_screen(mx, my, mv, pj, vp)
    if o is None:
        selected = obj
    else:
        hit, t = _ray_intersect_aabb(
            o, d, obj.hit_test_rect[0].as_float, obj.hit_test_rect[1].as_float)

        if hit:
            nearest_t = inf
            nearest_hit = False
            for tri in obj.get_triangles():
                v0, v1, v2 = np.array(tri[0]), np.array(tri[1]), np.array(tri[2])

                h, tt = _ray_triangle_intersect(o, d, v0, v1, v2)
                if h and tt < nearest_t:
                    nearest_t = tt
                    nearest_hit = True

            if nearest_hit:
                selected = obj
            else:
                selected = obj
        else:
            selected = obj

    last_pick_state['index'] = (last_pick_state['index'] + 1) % len(cands)
    return selected
