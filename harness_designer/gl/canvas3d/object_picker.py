from typing import TYPE_CHECKING

import numpy as np
from math import inf

from ... import debug as _debug

if TYPE_CHECKING:
    from . import camera as _camera


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


# Ray vs AABB (slab method)
def _ray_intersect_aabb(orig, direc, aabb_min, aabb_max, t0=0.0, t1=inf):
    tmin_vals = np.full(3, -inf, dtype=np.float64)
    tmax_vals = np.full(3, inf, dtype=np.float64)

    for i in range(3):
        if np.abs(direc[i]) > 1e-8:  # not parallel to this slab
            inv_d = 1.0 / direc[i]
            t_near = (aabb_min[i] - orig[i]) * inv_d
            t_far = (aabb_max[i] - orig[i]) * inv_d

            tmin_vals[i] = min(t_near, t_far)
            tmax_vals[i] = max(t_near, t_far)
        else:
            # Ray is parallel to this slab
            if orig[i] < aabb_min[i] or orig[i] > aabb_max[i]:
                # Ray origin is outside the slab, no intersection
                return False, None

    t_enter = max(t0, np.max(tmin_vals))
    t_exit = min(t1, np.min(tmax_vals))

    if t_enter <= t_exit and t_exit >= 0.0:
        return True, t_enter

    return False, None


def _aabb_screen_bbox_and_depth(bboxes, camera: "_camera.Camera"):
    """
    Build a 2D screen bbox from projecting ALL 8 AABB corners.
    This is necessary for stability across camera yaw/pitch.
    """
    screen_pts = []
    depths = []
    any_in_front = False

    mv = camera.modelview
    pj = camera.projection
    viewport = camera.viewport

    for corner in bboxes:

        v = np.array([corner[0], corner[1], corner[2], 1.0], dtype=np.float64)
        eye = mv.dot(v)
        clip = pj.dot(eye)

        w = clip[3]
        if np.isclose(w, 0.0):
            continue

        ndc = clip[:3] / w
        vx, vy, vw, vh = viewport

        winx = vx + (ndc[0] + 1.0) * vw * 0.5
        winy = vy + (ndc[1] + 1.0) * vh * 0.5
        winz = (ndc[2] + 1.0) * 0.5

        winy = viewport[3] - winy

        screen_pts.append((winx, winy, winz))

        eye_z = eye[2]
        if eye_z < 0:
            any_in_front = True
            depths.append(-eye_z)
        else:
            depths.append(inf)

        xs = [p[0] for p in screen_pts]
        ys = [p[1] for p in screen_pts]

        bbox2d = (min(xs), min(ys), max(xs), max(ys))

        # depth metric: closest in-front corner if possible
        if any_in_front:
            depth_metric = float(min(d for d in depths if d != inf))
        else:
            depth_metric = float(min(depths))

        yield bbox2d, depth_metric


@_debug.logfunc
def _pick_candidates_at_mouse(mx, my, scene_objects,
                              camera: "_camera.Camera", tol_pixels=3.0):  # NOQA
    """
    scene_objects: iterable of objects with attributes:
        - aabb_min (3-tuple), aabb_max (3-tuple)
        - optional .id or reference returned in candidate tuple
    Returns list of (depth_metric, object, bbox2d) sorted by depth (closest first)
    """

    mx_screen = mx
    my_screen = my

    candidates = []
    for obj in scene_objects:
        for (minx, miny, maxx, maxy), depth in (
            _aabb_screen_bbox_and_depth(obj.obj3d.obb, camera)
        ):

            if (
                minx - tol_pixels <= mx_screen <= maxx + tol_pixels and
                miny - tol_pixels <= my_screen <= maxy + tol_pixels
            ):

                candidates.append((depth, obj))

    candidates.sort(key=lambda k: k[0])

    return candidates


@_debug.logfunc
def find_object(mouse_pos, scene_objects, camera: "_camera.Camera"):
    mx, my = mouse_pos.as_float[:-1]

    pj = camera.projection
    mv = camera.modelview
    viewport = camera.viewport

    # refresh candidate list if mouse moved significantly

    candidates = _pick_candidates_at_mouse(mx, my, scene_objects, camera)

    if not candidates:
        return None

    # compute inv(P * MV)
    mvp = pj.dot(mv)  # row-major
    inv_mvp = np.linalg.inv(mvp)
    vx, vy, vw, vh = viewport

    # convert mouse to GL bottom-left origin:
    wx = mx
    wy = (vh - my)

    # map to NDC
    ndc_x = (2.0 * (wx - vx) / vw) - 1.0
    ndc_y = (2.0 * (wy - vy) / vh) - 1.0

    # near: z = -1 (OpenGL NDC), far z = +1
    near_world = _unproject_from_ndc((ndc_x, ndc_y, -1.0), inv_mvp)
    far_world = _unproject_from_ndc((ndc_x, ndc_y, 1.0), inv_mvp)
    if near_world is None or far_world is None:
        origin = direc = None
    else:
        origin = np.array(near_world, dtype=np.float64)
        direc = np.array(far_world, dtype=np.float64) - origin
        direc /= np.linalg.norm(direc)

    # Build ray once
    if origin is None:
        # fallback: just pick first candidate
        return candidates[0][1]

    # Evaluate ray hit for ALL candidates; pick closest t
    best_obj = None
    best_t = inf

    for _, obj in candidates:
        # world AABB
        wmin, wmax = obj.obj3d.aabb

        hit, t_hit = _ray_intersect_aabb(origin, direc, wmin, wmax)
        if hit and t_hit < best_t:
            best_t = t_hit
            best_obj = obj

    return best_obj
