# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union

import numpy as np
from math import inf

from .. import debug as _debug
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .canvas_3d import camera as _camera3d
    from .canvas_schematic import camera as _camera2d


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


@_check_types.do
def _build_ray(mouse_pos, camera: Union["_camera3d.Camera", "_camera2d.Camera"]):
    """Unproject *mouse_pos* into a world-space ray (*origin*, *direc*,
    *direc* already normalized), or ``(None, None)`` if the camera's
    current matrices can't be inverted (degenerate view -- callers treat
    that as "nothing to pick").
    """
    mx, my = mouse_pos.as_float[:-1]

    pj = camera.projection
    mv = camera.modelview
    viewport = camera.viewport

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
        return None, None

    origin = np.array(near_world, dtype=np.float32)
    direc = np.array(far_world, dtype=np.float32) - origin
    direc /= np.linalg.norm(direc)

    return origin, direc


@_debug.logfunc
@_check_types.do
def find_object(mouse_pos, camera: Union["_camera3d.Camera", "_camera2d.Camera"],
                canvas, current_selection=None):
    """Ray-cast from *mouse_pos* against every object registered with
    *canvas*'s own :class:`~harness_designer.bounds.Manager` view (see
    ``canvas.bounds_manager.aabb``/``canvas.bounds_manager.obb`` --
    identical API across the 3D/schematic/peg-board canvases) and
    return the closest hit (or the next-closest, if the closest is
    *current_selection* -- lets repeated clicks cycle through a stack
    of overlapping objects).

    The coarse candidate list is produced by the bounds pool itself
    (:meth:`~harness_designer.bounds.array_pool.ArrayPool.hit_test`) --
    a single vectorized ray test against every currently-visible OBB
    (falling back to AABB only if the OBB pass finds nothing, mirroring
    the box degenerating to the same loose union-of-segments envelope a
    multi-segment Wire/Bundle's own OBB already uses). Each surviving
    candidate is then narrowed with its own real, precise
    ``hit_test_step3`` (a per-triangle mesh test) -- the bounds-pool
    pass is deliberately only the cheap first filter, never the final
    answer on its own.

    :param mouse_pos: Mouse position in window/viewport pixel coordinates.
    :param camera: Camera providing ``.modelview``/``.projection``/``.viewport``.
    :param canvas: The canvas being picked against -- only
        ``canvas.bounds_manager.aabb``/``.obb`` are used, so any object
        exposing that same pair works (matches ``canvas3d``/
        ``canvas_schematic``/``canvas_pegboard`` today).
    :param current_selection: Currently selected object, used to cycle to the
        next closest overlapping object when the closest hit matches it.
    :returns: The picked object, or ``None`` if nothing was hit.
    """
    origin, direc = _build_ray(mouse_pos, camera)
    if origin is None:
        return None

    # Real oriented box first (accurate) -- an AABB-only hit (through the
    # loose envelope but not the actual box) is only ever used as a
    # fallback when the OBB pass finds nothing at all, so a genuinely
    # inert/degenerate box (see ArrayPool's sentinel-row/degenerate-axis
    # guards) never wrongly swallows a real pick.
    candidates = canvas.bounds_manager.obb.hit_test(origin, direc)
    if not candidates:
        candidates = canvas.bounds_manager.aabb.hit_test(origin, direc)

    if not candidates:
        return None

    hits = [wrapped for wrapped in candidates if wrapped.hit_test_step3(origin, direc)]

    if not hits:
        return None

    # A wire marker/wire layout handle can legitimately sit fully inside
    # its wire's tube (a layout handle has no radial offset at all), so
    # nearest-ray-distance alone can never reliably prefer it -- the
    # wire's own near surface is, correctly, physically closer along that
    # ray. BaseVar._pick_priority (default 0, bumped by WireMarker/
    # WireLayout/BundleLayout) breaks that tie explicitly: higher
    # priority wins outright. ``hit_test`` already returned *candidates*
    # nearest-hit first, and Python's sort is stable, so re-sorting on
    # priority alone preserves that original distance order within each
    # priority tier.
    hits.sort(key=lambda wrapped: -wrapped._pick_priority)  # NOQA

    picked = [wrapped.parent for wrapped in hits]

    if current_selection is None or len(picked) == 1:
        return picked[0]

    # If the closest hit is the currently selected object, cycle to the next.
    if picked[0] is current_selection:
        return picked[1]

    return picked[0]
