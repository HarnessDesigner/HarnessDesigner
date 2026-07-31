# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np
from math import inf

from .. import debug as _debug
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .canvas3d import camera as _camera3d
    from .canvas2d import camera as _camera2d


@_check_types.do
def _unproject_from_ndc(ndc, inv_mvp):
    """
    ndc: (x,y,z) in [-1,1]
    inv_mvp: inverse of P*MV (row-major)
    """

    clip = np.array([ndc[0], ndc[1], ndc[2], 1.0], dtype=np.float32)

    world = inv_mvp.dot(clip)
    if np.isclose(world[3], 0.0):
        return None

    world /= world[3]

    return world[:3]


# Ray vs AABB (slab method)
@_check_types.do
def _ray_intersect_aabb(orig, direc, aabb_min, aabb_max, t0=0.0, t1=inf):
    """Execute the ray intersect AABB operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param orig: Value for ``orig``.
    :type orig: UNKNOWN
    :param direc: Value for ``direc``.
    :type direc: UNKNOWN
    :param aabb_min: Value for ``aabb_min``.
    :type aabb_min: UNKNOWN
    :param aabb_max: Value for ``aabb_max``.
    :type aabb_max: UNKNOWN
    :param t0: Value for ``t0``.
    :type t0: UNKNOWN
    :param t1: Value for ``t1``.
    :type t1: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    tmin_vals = np.full(3, -inf, dtype=np.float32)
    tmax_vals = np.full(3, inf, dtype=np.float32)

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


# Ray vs OBB (slab method, using the box's own edge axes instead of world
# X/Y/Z) -- see corner ordering in utils.bounding_boxes.compute_obb:
# corner 0 = (x1,y1,z1), 1 toggles x, 3 toggles y, 4 toggles z. A rigid
# rotation + per-axis local scale preserves that edge structure, so this
# holds for any BaseVar.obb regardless of orientation.
@_check_types.do
def _ray_intersect_obb(orig, direc, obb, t0=0.0, t1=inf):
    """Test a ray against an oriented bounding box.

    Needed because :func:`_ray_intersect_aabb` against the axis-aligned
    envelope around a rotated OBB is a "loose fit" for diagonally-oriented
    objects like wires -- a long diagonal wire's AABB balloons out well
    past its actual thin cylindrical extent, so a ray can register a
    nearer AABB hit than the true surface, stealing the pick from a
    smaller object (e.g. a wire marker) that visually sits on top of it.
    Testing the real oriented box fixes that at the source.
    """
    c0, c1, c3, c4 = obb[0], obb[1], obb[3], obb[4]
    center = c0 + 0.5 * ((c1 - c0) + (c3 - c0) + (c4 - c0))

    tmin_vals = np.full(3, -inf, dtype=np.float32)
    tmax_vals = np.full(3, inf, dtype=np.float32)

    p = center - orig

    for i, edge in enumerate((c1 - c0, c3 - c0, c4 - c0)):
        length = np.linalg.norm(edge)
        if length < 1e-8:
            return False, None

        axis = edge / length
        half_extent = length * 0.5

        e = np.dot(axis, p)
        f = np.dot(axis, direc)

        if np.abs(f) > 1e-8:
            t_near = (e - half_extent) / f
            t_far = (e + half_extent) / f

            tmin_vals[i] = min(t_near, t_far)
            tmax_vals[i] = max(t_near, t_far)
        elif abs(e) > half_extent:
            # Ray is parallel to this slab and outside it -- no intersection
            return False, None

    t_enter = max(t0, np.max(tmin_vals))
    t_exit = min(t1, np.min(tmax_vals))

    if t_enter <= t_exit and t_exit >= 0.0:
        return True, t_enter

    return False, None


@_check_types.do
def _aabb_screen_bbox_and_depth(bboxes, camera: "_camera3d.Camera | _camera2d.Camera"):
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

        v = np.array([corner[0], corner[1], corner[2], 1.0], dtype=np.float32)
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
@_check_types.do
def _pick_candidates_at_mouse(mx, my, scene_objects,
                              camera: "_camera3d.Camera | _camera2d.Camera",
                              tol_pixels=3.0, attr='obj3d'):  # NOQA
    """
    scene_objects: iterable of objects exposing a wrapper attribute (named
        by *attr* -- ``'obj3d'`` for the 3D editor, ``'obj2d'`` for the
        2D schematic editor, both objects.objectsvar.BaseVar subclasses)
        with ``.obb``/``.aabb``.
    Returns list of (depth_metric, object, bbox2d) sorted by depth (closest first)
    """

    mx_screen = mx
    my_screen = my

    candidates = []
    for obj in scene_objects:
        wrapped = getattr(obj, attr)
        if wrapped.obb is None:
            continue

        for (minx, miny, maxx, maxy), depth in (
            _aabb_screen_bbox_and_depth(wrapped.obb, camera)
        ):

            if (
                minx - tol_pixels <= mx_screen <= maxx + tol_pixels and
                miny - tol_pixels <= my_screen <= maxy + tol_pixels
            ):

                candidates.append((depth, obj))

    candidates.sort(key=lambda k: k[0])

    return candidates


@_debug.logfunc
@_check_types.do
def find_object(mouse_pos, scene_objects, camera: "_camera3d.Camera | _camera2d.Camera",
                current_selection=None, attr='obj3d'):
    """Ray-cast from *mouse_pos* against every object in *scene_objects*
    and return the closest hit (or the next-closest, if the closest is
    *current_selection* -- lets repeated clicks cycle through a stack of
    overlapping objects).

    Shared between the 3D editor (``attr='obj3d'``, the default) and the
    2D schematic editor (``attr='obj2d'``) -- both wrapper classes
    (``Base3D``/``Base2D``, both ``objects.objectsvar.BaseVar``
    subclasses) expose the same ``.obb``/``.aabb``/``._pick_priority``
    contract this function relies on, and *camera* only needs
    ``.modelview``/``.projection``/``.viewport`` (see
    ``gl.canvas2d.camera.Camera._update_views``).

    :param mouse_pos: Mouse position in window/viewport pixel coordinates.
    :param scene_objects: Objects to test, each exposing *attr*.
    :param camera: Camera providing ``.modelview``/``.projection``/``.viewport``.
    :param current_selection: Currently selected object, used to cycle to the
        next closest overlapping object when the closest hit matches it.
    :param attr: Name of the wrapper attribute to pick against --
        ``'obj3d'`` or ``'obj2d'``.
    :returns: The picked object, or ``None`` if nothing was hit.
    """
    mx, my = mouse_pos.as_float[:-1]

    pj = camera.projection
    mv = camera.modelview
    viewport = camera.viewport

    candidates = _pick_candidates_at_mouse(mx, my, scene_objects, camera, attr=attr)

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
        origin = np.array(near_world, dtype=np.float32)
        direc = np.array(far_world, dtype=np.float32) - origin
        direc /= np.linalg.norm(direc)

    # Build ray once
    if origin is None:
        # fallback: just pick first candidate
        return candidates[0][1]

    # Evaluate ray hit for ALL candidates against their real oriented box
    # first (accurate) -- an AABB-only hit (ray passes through the loose
    # envelope but not the actual box) is kept as a lower-priority
    # fallback so objects near the edge of the screen-space pick
    # tolerance don't just disappear; see _ray_intersect_obb.
    #
    # Neither envelope test is precise enough to accept on its own: a
    # multi-segment object (Wire/Bundle) can't have a real oriented box at
    # all -- BaseVar3D.obb documents that it degenerates to the same loose
    # axis-aligned union-of-segments envelope as its own aabb for those
    # types -- so a ray passing anywhere through that envelope (which can
    # be huge for a routed, multi-bend wire) would otherwise register as
    # a hit far from the actual thin cylinder, stealing the pick from
    # whatever's really under the cursor (e.g. a housing/cavity behind a
    # routed wire). hit_test_step3 -- a real per-triangle mesh test,
    # already correctly implemented per-segment on Wire/Bundle and against
    # the whole mesh on every other object -- is the actual precision
    # gate; only a candidate that passes it is accepted as a genuine hit.
    hits = []
    fallback_hits = []
    for _, obj in candidates:
        wrapped = getattr(obj, attr)
        obb = wrapped.obb
        hit, t_hit = _ray_intersect_obb(origin, direc, obb) if obb is not None else (False, None)
        if hit:
            if wrapped.hit_test_step3(origin, direc):
                hits.append((t_hit, obj))
            continue

        wmin, wmax = wrapped.aabb
        hit, t_hit = _ray_intersect_aabb(origin, direc, wmin, wmax)
        if hit and wrapped.hit_test_step3(origin, direc):
            fallback_hits.append((t_hit, obj))

    if not hits:
        hits = fallback_hits

    if not hits:
        return None

    # A wire marker/wire layout handle can legitimately sit fully inside
    # its wire's tube (a layout handle has no radial offset at all), so
    # nearest-ray-distance alone can never reliably prefer it -- the
    # wire's own near surface is, correctly, physically closer along that
    # ray. BaseVar._pick_priority (default 0, bumped by WireMarker/
    # WireLayout/BundleLayout) breaks that tie explicitly: higher
    # priority wins outright, nearest-hit only tie-breaks within the same
    # priority tier.
    hits.sort(key=lambda k: (-getattr(k[1], attr)._pick_priority, k[0]))

    if current_selection is None or len(hits) == 1:
        return hits[0][1]

    # If the closest hit is the currently selected object, cycle to the next.
    if hits[0][1] is current_selection:
        return hits[1][1]

    return hits[0][1]
