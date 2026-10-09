# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Interactive handlers for routed wire placement, plus the transition-
placement helper functions reused by ``objects.objects_3d.transition.
Transition.start_add`` (see ``add_handlers.editor_3d.transition`` for
the actual interactive placement session, which replaced this
module's own former ``AddTransitionHandler``). ``RouteThroughTransitionHandler``/
``RouteThroughBundleHandler``/``RoutedWireHandler`` below have no UI
entry point anywhere in the app -- kept as-is, not part of that
migration.

``RouteThroughTransitionHandler``'s and ``RoutedWireHandler``'s own
branch highlighting/clearing were updated (2026-09-28) to use
``Transition.highlight_branch``/``branch_fits`` instead of a branch's
own (now-removed) ``identify()`` -- a branch is no longer its own
pickable ``Base3D`` object, see ``objects_3d.transition``'s own module
docstring. ``RouteThroughTransitionHandler.release_capture`` was updated
the same way, using ``Transition.hit_test_branch_ray`` in place of the
generic canvas picker for branch resolution. ``RoutedWireHandler``'s OWN
branch-picking (``_handle_routing_click``/``_handle_exit_click``,
`isinstance(selected, _Branch3D)` against a plain
``gl.object_picker.find_object`` result) was left AS IS -- already dead
before this session, and now structurally unreachable rather than just
unwired (``find_object`` can never resolve to a branch any more, so that
``isinstance`` is always ``False``) -- fixing it properly needs the same
`_object_picker.build_ray`/``hit_test_branch_ray`` swap the other two
handlers got, folded into its own mixed wire/bundle/branch pick logic;
left for whoever actually revives this handler, since there is still no
way to exercise or verify it.
"""

from typing import TYPE_CHECKING, Union as _Union

import math
import numpy as np

from . import handler_base as _handler_base
from ..geometry import point as _point
from ..gl import object_picker as _object_picker
from ..objects import bundle as _bundle
from ..objects.objects_pegboard import base_pegboard as _base_pegboard
from ..objects import wire as _wire
from ..objects import wire_layout as _wire_layout
from .. import utils as _utils
from ..gl import materials as _materials
from .. import config as _config
from .. import color as _color
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..database.project_db import pjt_bases as _pjt_bases
    from ..database.project_db import pjt_wire as _pjt_wire
    from ..database.project_db import pjt_bundle as _pjt_bundle
    from ..database.project_db import pjt_transition as _pjt_transition
    from ..database.project_db import pjt_transition_branch as _pjt_transition_branch
    from ..database.global_db import transition_branch as _global_transition_branch
    from ..objects import transition as _transition_obj
    from ..gl.canvas_3d import camera as _camera
    from .. import ui as _ui
    from ..objects import project as _project
    from ..objects.objects_3d import transition as _transition_3d


Config = _config.Config.colors
_SNAP_THRESHOLD = 5.0

# Public (not module-private): used by several other modules directly
# (add_handlers.editor_3d.bundle/transition, handlers.wire_routing_drag)
# for the same green/orange/blue fit-highlight materials this module's
# own branch-highlighting code uses.
HOVER_HIGHLIGHT = _materials.Plastic(_color.Color(0.2, 0.6, 1.0, 0.8))
BRANCH_FIT = _materials.Plastic(_color.Color(0.3, 1.0, 0.3, 1.0))
BRANCH_NO_FIT = _materials.Plastic(_color.Color(1.0, 0.4, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Point / DB helpers
# ---------------------------------------------------------------------------

@_check_types.do
def _repoint_all_references(
    ptables: "_pjt_bases.PJTTables",
    old_point_id: int,
    new_point_id: int
) -> None:

    """
    Replace every reference to *old_point_id* with *new_point_id* across all project tables.
    """

    from ..database.project_db.cleanup import _POINT3D_REFS

    con = ptables.pjt_wires_table._con  # NOQA
    for table_name, col in _POINT3D_REFS:
        con.execute(
            f'UPDATE {table_name} SET {col} = ? WHERE {col} = ?;',
            (new_point_id, old_point_id))

    con.commit()


@_check_types.do
def _delete_point_if_orphaned(ptables: "_pjt_bases.PJTTables", point_id: int) -> None:
    """
    Delete *point_id* from pjt_points3d if nothing references it.
    """

    from ..database.project_db.cleanup import _POINT3D_REFS

    con = ptables.pjt_wires_table._con  # NOQA
    for table_name, col in _POINT3D_REFS:
        rows = con.execute(
            f'SELECT id FROM {table_name} WHERE {col} = ? LIMIT 1;',
            (point_id,)).fetchall()

        if rows:
            return

    con.execute('DELETE FROM pjt_points3d WHERE id = ?;', (point_id,))
    con.commit()


@_check_types.do
def _insert_wire(
    ptables: "_pjt_bases.PJTTables",
    part_id: bytes,
    name: str,
    circuit_id: bytes | None,
    start_id: bytes | None,
    stop_id: bytes | None,
    visible: bool
) -> "_pjt_wire.PJTWire":
    return ptables.pjt_wires_table.insert(
        part_id, name, circuit_id, start_id, stop_id,
        None, None, visible, False, None, None, False)


@_check_types.do
def _insert_bundle(
    ptables: "_pjt_bases.PJTTables", part_id: bytes, name: str, start_id: bytes, stop_id: bytes
) -> "_pjt_bundle.PJTBundle":
    return ptables.pjt_bundles_table.insert(part_id, name, start_id, stop_id)


@_check_types.do
def _walk_bundle_chain(bundle_db_obj: "_pjt_bundle.PJTBundle", ptables: "_pjt_bases.PJTTables") -> list[bytes]:
    """
    Walk the full bundle chain from one free end to the other.

    Returns an ordered list of Point IDs:
        [end_A_id, layout_id, ..., end_B_id]
    """

    def _has_layout(point_id: bytes) -> bool:
        return bool(ptables.pjt_bundle_layouts_table.select(
            'id', position3d_id=point_id))

    def _next_section(current_id: bytes, from_point_id: bytes, visited: set[bytes]) -> bytes | None:
        rows = (ptables.pjt_bundles_table.select(
            'id', start_point3d_id=from_point_id) +
                ptables.pjt_bundles_table.select(
                    'id', stop_point3d_id=from_point_id))

        for row in rows:
            bid = row[0]
            if bid != current_id and bid not in visited:
                return bid

        return None

    def _walk_direction(start_section_id: bytes, leaving_point_id: bytes) -> list[bytes]:
        pts, current_id, current_pt = [], start_section_id, leaving_point_id
        visited = {start_section_id}
        while True:
            pts.append(current_pt)
            if not _has_layout(current_pt):
                break

            next_id = _next_section(current_id, current_pt, visited)
            if next_id is None:
                break

            visited.add(next_id)
            next_db = ptables.pjt_bundles_table[next_id]
            next_start = next_db.start_position3d_id
            next_stop = next_db.stop_position3d_id
            current_pt = next_stop if next_start == current_pt else next_start
            current_id = next_id

        return pts

    section_id = bundle_db_obj.db_id
    start_id = bundle_db_obj.start_position3d_id
    stop_id = bundle_db_obj.stop_position3d_id
    toward_start = _walk_direction(section_id, start_id)
    toward_stop = _walk_direction(section_id, stop_id)

    return list(reversed(toward_start)) + toward_stop


@_check_types.do
def _wire_area(conc_wire: "_pjt_wire.PJTWire") -> float:
    od = conc_wire.wire.part.od_mm

    return math.pi * (od / 2.0) ** 2 if od else 0.0


@_check_types.do
def effective_diameter(conc_wires: list["_pjt_wire.PJTWire"], global_branch: "_global_transition_branch.TransitionBranch") -> float:
    """
    Effective packed diameter with 15% air gap; never below min_dia.
    """

    if not conc_wires:
        return float(global_branch.min_dia)

    total_area = sum(_wire_area(cw) for cw in conc_wires)
    raw = 2.0 * math.sqrt(total_area * 1.15 / math.pi)

    return max(raw, float(global_branch.min_dia))


@_check_types.do
def assign_wires_to_branches(conc_wires: list, global_output_branches: list) -> list:
    """
    First-come-first-serve: fill each output branch until it's over capacity.
    """

    assignments = [[] for _ in global_output_branches]
    for cw in conc_wires:
        placed = False
        for i, (g_br, assigned) in enumerate(zip(global_output_branches, assignments)):
            if effective_diameter(assigned + [cw], g_br) <= float(g_br.max_dia):
                assigned.append(cw)
                placed = True
                break

        if not placed:
            assignments[-1].append(cw)

    return assignments


@_check_types.do
def _set_angle_from_bundle(
    transition_db_obj: "_pjt_transition.PJTTransition",  # NOQA
    bundle: _bundle.Bundle
) -> None:
    """
    Align the transition so its local X axis follows the bundle direction.
    """

    p1 = bundle.obj3d.start_position.as_numpy
    p2 = bundle.obj3d.stop_position.as_numpy
    seg = p2 - p1
    seg_len = float(np.linalg.norm(seg))
    if seg_len < 1e-8:
        return

    x_axis = seg / seg_len

    world_up = np.array([0.0, 0.0, 1.0], dtype=float)
    if abs(float(np.dot(x_axis, world_up))) > 0.99:
        world_up = np.array([0.0, 1.0, 0.0], dtype=float)

    z_axis = np.cross(x_axis, world_up)  # NOQA
    z_len = float(np.linalg.norm(z_axis))
    if z_len < 1e-8:
        return

    z_axis /= z_len
    y_axis = np.cross(z_axis, x_axis)  # NOQA
    rot_mat = np.column_stack([x_axis, y_axis, z_axis]).astype(np.float64)

    # Shepperd stable quaternion from rotation matrix
    trace = rot_mat[0, 0] + rot_mat[1, 1] + rot_mat[2, 2]
    if trace > 0:
        s = math.sqrt(trace + 1.0) * 2
        qw = 0.25 * s
        qx = (rot_mat[2, 1] - rot_mat[1, 2]) / s
        qy = (rot_mat[0, 2] - rot_mat[2, 0]) / s
        qz = (rot_mat[1, 0] - rot_mat[0, 1]) / s

    elif rot_mat[0, 0] > rot_mat[1, 1] and rot_mat[0, 0] > rot_mat[2, 2]:
        s = math.sqrt(1.0 + rot_mat[0, 0] - rot_mat[1, 1] - rot_mat[2, 2]) * 2
        qw = (rot_mat[2, 1] - rot_mat[1, 2]) / s
        qx = 0.25 * s
        qy = (rot_mat[0, 1] + rot_mat[1, 0]) / s
        qz = (rot_mat[0, 2] + rot_mat[2, 0]) / s

    elif rot_mat[1, 1] > rot_mat[2, 2]:
        s = math.sqrt(1.0 + rot_mat[1, 1] - rot_mat[0, 0] - rot_mat[2, 2]) * 2
        qw = (rot_mat[0, 2] - rot_mat[2, 0]) / s
        qx = (rot_mat[0, 1] + rot_mat[1, 0]) / s
        qy = 0.25 * s
        qz = (rot_mat[1, 2] + rot_mat[2, 1]) / s

    else:
        s = math.sqrt(1.0 + rot_mat[2, 2] - rot_mat[0, 0] - rot_mat[1, 1]) * 2
        qw = (rot_mat[1, 0] - rot_mat[0, 1]) / s
        qx = (rot_mat[0, 2] + rot_mat[2, 0]) / s
        qy = (rot_mat[1, 2] + rot_mat[2, 1]) / s
        qz = 0.25 * s

    obj_angle = transition_db_obj.angle3d
    old_euler = obj_angle.as_euler_float

    new_euler = (
        _handler_base.HandlerBase.euler_from_matrix_continuous(rot_mat, old_euler))

    obj_angle._q.w, obj_angle._q.x = float(qw), float(qx)  # NOQA
    obj_angle._q.y, obj_angle._q.z = float(qy), float(qz)  # NOQA
    cache = obj_angle._Angle__euler_angles  # NOQA
    if cache is not None:
        cache[0], cache[1], cache[2] = new_euler[0], new_euler[1], new_euler[2]

    obj_angle._matrix[:] = obj_angle._q.as_matrix  # NOQA
    obj_angle._process_callbacks()  # NOQA


@_check_types.do
def _create_branch_concentric(ptables: "_pjt_bases.PJTTables", branch_db: "_pjt_transition_branch.PJTTransitionBranch", conc_wires: list["_pjt_wire.PJTWire"], diameter: float) -> None:
    """
    Create concentric → single layer → wires for one transition branch.
    """

    conc_db = ptables.pjt_concentrics_table.insert(None, branch_db.db_id)
    if not conc_wires:
        return

    layer_db = ptables.pjt_concentric_layers_table.insert(
        0, len(conc_wires), 0, conc_db.db_id, diameter)

    for idx, cw in enumerate(conc_wires):
        point2d = ptables.pjt_points2d_table.insert(0.0, 0.0, 0.0)
        ptables.pjt_concentric_wires_table.insert(
            layer_db.db_id, idx, cw.wire_id, point2d.db_id, False)

    # The transition's one table lists every branch's wires
    # (PJTTransition.wires is the union of its branches' own).
    _base_pegboard.notify_table_wires_changed(branch_db.transition)


@_check_types.do
def _find_bundle(mouse_pos: _point.Point, camera: "_camera.Camera",
                  project: "_project.Project") -> _bundle.Bundle | None:
    selected = _object_picker.find_object(mouse_pos, camera, camera.canvas)

    if isinstance(selected, _bundle.Bundle):
        return selected

    world_pos = camera.get_position_on_focal_plane(mouse_pos).as_numpy
    best, best_dist_sq = None, _SNAP_THRESHOLD ** 2

    for bndl in project.bundles:
        if not bndl.is_in_3dview:
            continue

        p1 = bndl.obj3d.start_position.as_numpy
        p2 = bndl.obj3d.stop_position.as_numpy
        seg = p2 - p1
        seg_len_sq = float(np.dot(seg, seg))
        if seg_len_sq < 1e-8:
            continue

        t = max(0.0, min(1.0, float(np.dot(world_pos - p1, seg)) / seg_len_sq))
        dist_sq = float(np.sum((world_pos - (p1 + t * seg)) ** 2))
        if dist_sq < best_dist_sq:
            best_dist_sq, best = dist_sq, bndl

    return best


@_check_types.do
def is_bundle_end_free(ptables: "_pjt_bases.PJTTables", bundle: _bundle.Bundle, endpoint: str) -> bool:
    """Whether *bundle*'s *endpoint* ('start'/'stop') has nothing already
    attached to it -- BUNDLE_PLACEMENT.md section 5/8: "free-end/free-
    branch helpers" needed by placement, "which one is the source of
    truth for 'free' needs to be settled while writing the helpers."
    Settled here as: a point row that no transition branch already
    references. Mirrors the same by-point-id lookup
    ``PJTTransitionBranch.bundle`` already does in the opposite
    direction (branch -> attached bundle, by matching
    start/stop_point3d_id). Public (not module-private) because
    handlers.wire_routing_drag calls this from outside this module.
    """
    point_id = (bundle.db_obj.start_position3d_id if endpoint == 'start'
                else bundle.db_obj.stop_position3d_id)

    rows = ptables.pjt_transition_branches_table.select('id', point3d_id=point_id)
    return not rows


@_check_types.do
def _find_free_bundle_end(
    mouse_pos: _point.Point, camera: "_camera.Camera", project: "_project.Project"
) -> tuple[_bundle.Bundle, str] | None:
    """The closest FREE bundle end (start or stop -- never a mid-span
    point) within snapping distance of the mouse, or ``None``.

    BUNDLE_PLACEMENT.md section 4: "no mid-bundle placement... a
    transition is never snapped onto the middle of a bundle" -- unlike
    ``_find_bundle`` above (kept for whatever still-reachable code uses
    it), this only ever considers the two actual endpoints of each
    bundle, and skips one already attached to another transition branch.
    """
    world_pos = camera.get_position_on_focal_plane(mouse_pos).as_numpy
    ptables = project.ptables

    best = None
    best_dist_sq = _SNAP_THRESHOLD ** 2

    for bndl in project.bundles:
        if not bndl.is_in_3dview:
            continue

        for endpoint, point in (
            ('start', bndl.obj3d.start_position), ('stop', bndl.obj3d.stop_position)
        ):
            if not is_bundle_end_free(ptables, bndl, endpoint):
                continue

            dist_sq = float(np.sum((world_pos - point.as_numpy) ** 2))
            if dist_sq < best_dist_sq:
                best_dist_sq, best = dist_sq, (bndl, endpoint)

    return best


@_check_types.do
def _find_free_branch_ray(
    origin: np.ndarray, direc: np.ndarray, project: "_project.Project",
    exclude_transition: _Union["_transition_obj.Transition", None] = None
) -> tuple["_transition_obj.Transition", "_transition_3d.Branch"] | None:
    """The first FREE branch (no bundle already attached), across every
    transition in the project, that world-space ray (*origin*, *direc* --
    from ``gl.object_picker.build_ray``) actually intersects -- the
    bundle-placement mirror of ``_find_free_bundle_end`` above (which
    finds a free BUNDLE end for a transition being placed; this finds a
    free BRANCH for a bundle being placed). Same first-hit-wins scan
    ``RouteThroughTransitionHandler.release_capture``/``RoutedWireHandler.
    _highlight_exit_branches`` already use -- no cross-transition
    "closest" comparison, since real ray-sphere intersection
    (``Transition.hit_test_branch_ray``) makes a hit unambiguous and
    transitions essentially never overlap along one ray in practice.

    *exclude_transition* (if given) skips that whole transition --
    BUNDLE_PLACEMENT.md section 5's hard rule: "a bundle cannot have both
    of its ends connected to the same transition" -- so a bundle's own
    already-attached start transition is never offered again for its
    stop end.
    """
    for t_obj in project.transitions:
        if t_obj is exclude_transition:
            continue

        branch = t_obj.obj3d.hit_test_branch_ray(origin, direc)
        if branch is None:
            continue

        if branch.db_obj is not None and branch.db_obj.bundle is not None:
            continue  # already occupied

        return t_obj, branch

    return None


@_check_types.do
def _rotation_matrix_between(v_from: np.ndarray, v_to: np.ndarray) -> np.ndarray:
    """3x3 rotation matrix mapping unit vector *v_from* onto unit vector
    *v_to* (Rodrigues' rotation formula) -- plain linear algebra, not the
    matrix-to-euler decomposition ``_apply_rotation`` below still has to
    do (see that function's own docstring for why THAT part is the
    genuinely delicate operation, not this one).
    """
    norm_from = float(np.linalg.norm(v_from))
    norm_to = float(np.linalg.norm(v_to))
    v_from = v_from / (norm_from or 1.0)
    v_to = v_to / (norm_to or 1.0)

    axis = np.cross(v_from, v_to)
    axis_len = float(np.linalg.norm(axis))
    cos_angle = float(np.clip(np.dot(v_from, v_to), -1.0, 1.0))

    if axis_len < 1e-8:
        if cos_angle > 0:
            return np.eye(3, dtype=np.float64)

        # 180 degrees -- v_from and v_to are anti-parallel, so any axis
        # perpendicular to v_from is a valid rotation axis.
        perp = np.array([1.0, 0.0, 0.0]) if abs(v_from[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        axis = np.cross(v_from, perp)
        axis /= np.linalg.norm(axis)
        angle = math.pi
    else:
        axis = axis / axis_len
        angle = math.acos(cos_angle)

    k = np.array([
        [0.0, -axis[2], axis[1]],
        [axis[2], 0.0, -axis[0]],
        [-axis[1], axis[0], 0.0],
    ], dtype=np.float64)

    return np.eye(3, dtype=np.float64) + math.sin(angle) * k + (1.0 - math.cos(angle)) * (k @ k)


@_check_types.do
def _apply_rotation(transition_db_obj: "_pjt_transition.PJTTransition", rot_mat: np.ndarray) -> None:
    """Set *transition_db_obj*'s ``angle3d`` to match rotation matrix
    *rot_mat*, continuously (no jump relative to its current value) --
    the same Shepperd-stable-quaternion-plus-``euler_from_matrix_
    continuous`` technique ``_set_angle_from_bundle`` above already uses
    (duplicated here, not factored out, to avoid touching that
    already-working function while it still has its own caller) -- see
    that function's own comment for why matrix->euler decomposition is
    the genuinely delicate half of this (TRANSITION_DESIGN.md's own
    euler-vs-quaternion decision is specifically about never needing to
    do this for a *stored* branch angle; this is the one place in the
    whole transition feature that still does, because there is no other
    way to persist "the transition, as a whole, is rotated this way" as
    euler degrees).
    """
    trace = rot_mat[0, 0] + rot_mat[1, 1] + rot_mat[2, 2]
    if trace > 0:
        s = math.sqrt(trace + 1.0) * 2
        qw = 0.25 * s
        qx = (rot_mat[2, 1] - rot_mat[1, 2]) / s
        qy = (rot_mat[0, 2] - rot_mat[2, 0]) / s
        qz = (rot_mat[1, 0] - rot_mat[0, 1]) / s
    elif rot_mat[0, 0] > rot_mat[1, 1] and rot_mat[0, 0] > rot_mat[2, 2]:
        s = math.sqrt(1.0 + rot_mat[0, 0] - rot_mat[1, 1] - rot_mat[2, 2]) * 2
        qw = (rot_mat[2, 1] - rot_mat[1, 2]) / s
        qx = 0.25 * s
        qy = (rot_mat[0, 1] + rot_mat[1, 0]) / s
        qz = (rot_mat[0, 2] + rot_mat[2, 0]) / s
    elif rot_mat[1, 1] > rot_mat[2, 2]:
        s = math.sqrt(1.0 + rot_mat[1, 1] - rot_mat[0, 0] - rot_mat[2, 2]) * 2
        qw = (rot_mat[0, 2] - rot_mat[2, 0]) / s
        qx = (rot_mat[0, 1] + rot_mat[1, 0]) / s
        qy = 0.25 * s
        qz = (rot_mat[1, 2] + rot_mat[2, 1]) / s
    else:
        s = math.sqrt(1.0 + rot_mat[2, 2] - rot_mat[0, 0] - rot_mat[1, 1]) * 2
        qw = (rot_mat[1, 0] - rot_mat[0, 1]) / s
        qx = (rot_mat[0, 2] + rot_mat[2, 0]) / s
        qy = (rot_mat[1, 2] + rot_mat[2, 1]) / s
        qz = 0.25 * s

    obj_angle = transition_db_obj.angle3d
    old_euler = obj_angle.as_euler_float

    new_euler = _handler_base.HandlerBase.euler_from_matrix_continuous(rot_mat, old_euler)

    obj_angle._q.w, obj_angle._q.x = float(qw), float(qx)  # NOQA
    obj_angle._q.y, obj_angle._q.z = float(qy), float(qz)  # NOQA
    cache = obj_angle._Angle__euler_angles  # NOQA
    if cache is not None:
        cache[0], cache[1], cache[2] = new_euler[0], new_euler[1], new_euler[2]

    obj_angle._matrix[:] = obj_angle._q.as_matrix  # NOQA
    obj_angle._process_callbacks()  # NOQA


@_check_types.do
def _branch_local_direction(branch: "_global_transition_branch.TransitionBranch") -> np.ndarray:
    """A catalog branch's own trunk direction in the transition's local
    space -- local +X rotated by the branch's own 3-axis euler angle.
    Same definition ``objects_3d.transition._branch_direction`` (and its
    peg-board equivalent) use, duplicated rather than imported -- the
    user's own steer (2026-09-27) that this whole apparatus belongs
    directly in each consumer rather than a shared module.
    """
    direction = np.array([1.0, 0.0, 0.0], dtype=np.float32) @ branch.angle
    direction = np.asarray(direction, dtype=np.float64)
    norm = float(np.linalg.norm(direction))
    if norm > 1e-9:
        direction /= norm

    return direction


@_check_types.do
def _align_branch_to_bundle(
    transition_db_obj: "_pjt_transition.PJTTransition", branch_local_direction: np.ndarray, bundle: _bundle.Bundle,
    endpoint: str
) -> None:
    """Rotate *transition_db_obj* so the branch whose own local direction
    is *branch_local_direction* ends up pointing back along *bundle* from
    *endpoint* -- BUNDLE_PLACEMENT.md section 4: "the branch's outward
    axis points back along the bundle, so the bundle runs straight into
    the branch mouth." Generalizes ``_set_angle_from_bundle``'s own
    "align local X to the bundle" special case (which assumed the
    trunk's own local direction always WAS local +X) to whichever branch
    the user actually picked.
    """
    p1 = bundle.obj3d.start_position.as_numpy
    p2 = bundle.obj3d.stop_position.as_numpy
    seg = p2 - p1
    seg_len = float(np.linalg.norm(seg))
    if seg_len < 1e-8:
        return

    bundle_direction = seg / seg_len
    target_direction = bundle_direction if endpoint == 'stop' else -bundle_direction

    rot_mat = _rotation_matrix_between(branch_local_direction, target_direction)
    _apply_rotation(transition_db_obj, rot_mat)


class RouteThroughTransitionHandler(_handler_base.HandlerBase):
    """
    Reconnect an existing wire or bundle endpoint to a compatible transition branch.
    """

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame", target: _Union[_wire.Wire, _bundle.Bundle],
                 is_start: bool) -> None:
        super().__init__(mainframe, None)
        self.target = target
        self.is_start = is_start
        self.diameter = self._diameter_of(target)
        self._highlighted = []

    @staticmethod
    @_check_types.do
    def _diameter_of(obj: _Union[_wire.Wire, _bundle.Bundle]) -> float:
        if isinstance(obj, _wire.Wire):
            od = obj.db_obj.part.od_mm

            if od:
                return float(od)

            return 1.0

        if isinstance(obj, _bundle.Bundle):
            d = obj.obj3d.diameter

            if d:
                return float(d)

            return 1.0

        return 1.0

    @staticmethod
    @_check_types.do
    def _fits(diameter: float, branch: "_transition_3d.Branch") -> bool:
        return branch.min_diameter <= diameter <= branch.max_diameter

    @_check_types.do
    def _highlight_branches(self) -> None:
        # (obj3d, branch) pairs, not bare branches -- clearing a branch's
        # own highlight override (2026-09-28: Transition.highlight_branch/
        # clear_branch_highlight, a branch is no longer its own pickable
        # Base3D object with its own identify()) needs the OWNING
        # transition, not just the branch.
        for t_obj in self.mainframe.project.transitions:
            for branch in t_obj.obj3d.branches:
                mat = (BRANCH_FIT if t_obj.obj3d.branch_fits(branch, self.diameter)
                       else BRANCH_NO_FIT)
                t_obj.obj3d.highlight_branch(branch, mat)
                self._highlighted.append((t_obj.obj3d, branch))

    @_check_types.do
    def _clear_highlights(self) -> None:
        for obj3d, branch in self._highlighted:
            obj3d.clear_branch_highlight(branch)

        self._highlighted.clear()

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
        pass

    @_check_types.do
    def release_capture(self) -> None:
        if self._finalized or self._captured_position is None:
            return

        # Real ray-sphere test against each transition's own branches
        # (Transition.hit_test_branch_ray), not the generic canvas
        # object picker -- a branch is no longer its own pickable
        # Base3D object the picker could resolve to (2026-09-28).
        origin, direc = _object_picker.build_ray(self._captured_position, self.camera)

        selected = None
        if origin is not None:
            for t_obj in self.mainframe.project.transitions:
                selected = t_obj.obj3d.hit_test_branch_ray(origin, direc)
                if selected is not None:
                    break

        self._clear_highlights()
        self._finalized = True

        if selected is None:
            return

        if not self._fits(self.diameter, selected):
            return

        if self.is_start:
            old_point_id = self.target.db_obj.start_position3d_id
        else:
            old_point_id = self.target.db_obj.stop_position3d_id

        branch_p_id = selected.db_obj.position3d.db_id[:-2]
        if old_point_id == branch_p_id:
            return

        _repoint_all_references(self.ptables, old_point_id, branch_p_id)
        _delete_point_if_orphaned(self.ptables, old_point_id)
        self.mainframe.editor3d.Refresh(False)

    @_check_types.do
    def cancel(self) -> None:
        self._clear_highlights()


class RouteThroughBundleHandler(_handler_base.HandlerBase):
    """
    Reconnect an existing wire endpoint so it shares a selected bundle endpoint.
    """

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame",
                 target: _wire.Wire, is_start: bool) -> None:

        super().__init__(mainframe, None)
        self.target = target
        self.is_start = is_start
        self._hovered_bundle = None

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
        selected = _object_picker.find_object(mouse_pos, self.camera, self.camera.canvas)

        if not isinstance(selected, _bundle.Bundle):
            if self._hovered_bundle is not None:
                self._hovered_bundle.identify(None)
                self._hovered_bundle = None

            return

        if selected is not self._hovered_bundle:
            if self._hovered_bundle is not None:
                self._hovered_bundle.identify(None)

            selected.identify(HOVER_HIGHLIGHT)
            self._hovered_bundle = selected

    @_check_types.do
    def release_capture(self) -> None:
        if self._finalized or self._captured_position is None:
            return

        if self._hovered_bundle is not None:
            self._hovered_bundle.identify(None)
            self._hovered_bundle = None

        selected = _object_picker.find_object(self._captured_position, self.camera, self.camera.canvas)

        self._finalized = True

        if not isinstance(selected, _bundle.Bundle):
            return

        if self.is_start:
            old_point_id = self.target.db_obj.start_position3d_id
            wire_p = self.target.obj3d.start_position
        else:
            old_point_id = self.target.db_obj.stop_position3d_id
            wire_p = self.target.obj3d.stop_position

        start_np = selected.obj3d.start_position.as_numpy
        stop_np = selected.obj3d.stop_position.as_numpy
        wire_np = wire_p.as_numpy
        d_start = float(np.linalg.norm(wire_np - start_np))
        d_stop = float(np.linalg.norm(wire_np - stop_np))

        bundle_start_id = selected.obj3d.start_position.db_id[:-2]
        bundle_stop_id = selected.obj3d.stop_position.db_id[:-2]

        if d_start <= d_stop:
            bundle_p_id = bundle_start_id
        else:
            bundle_p_id = bundle_stop_id

        if old_point_id == bundle_p_id:
            return

        _repoint_all_references(self.ptables, old_point_id, bundle_p_id)
        self.mainframe.editor3d.Refresh(False)

    @_check_types.do
    def cancel(self) -> None:
        if self._hovered_bundle is not None:
            self._hovered_bundle.identify(None)
            self._hovered_bundle = None


class RoutedWireHandler(_handler_base.HandlerBase):
    """
    Create a new wire that can pass through bundle chains and transitions.

    Click to start, click again to add waypoints (clicking bundles / transition
    branches routes through them automatically), final click places the wire.
    """

    _IDLE = 'idle'
    _ROUTING = 'routing'
    _IN_TRANS = 'in_transition'

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame", part_id: bytes) -> None:
        super().__init__(mainframe, part_id)
        self._state = self._IDLE
        self._segments = []
        self._seg_start_id = None
        self._entry_branch = None
        self._preview = None
        self._highlighted = []

    @_check_types.do
    def _clear_highlights(self) -> None:
        # (obj3d, branch) pairs, not bare branches -- see
        # RouteThroughTransitionHandler._clear_highlights's own comment
        # for why (a branch is no longer its own pickable Base3D object
        # with its own identify()).
        for obj3d, branch in self._highlighted:
            obj3d.clear_branch_highlight(branch)

        self._highlighted.clear()

    @_check_types.do
    def _delete_preview(self) -> None:
        if self._preview is not None:
            self._preview.delete()
            self._preview = None

    @_check_types.do
    def _wire_od(self) -> float:
        od = self.mainframe.global_db.wires_table[self.part_id].od_mm

        return float(od) if od else 1.0

    @_check_types.do
    def _wire_name(self) -> str:
        part = self.mainframe.global_db.wires_table[self.part_id]

        return f'{part.manufacturer.name} {part.part_number}'

    @_check_types.do
    def _fits(self, diameter: float, branch: "_transition_3d.Branch") -> bool:
        return branch.min_diameter <= diameter <= branch.max_diameter

    @_check_types.do
    def _highlight_exit_branches(self, diameter: float, exclude_branch: "_transition_3d.Branch") -> None:
        for t_obj in self.mainframe.project.transitions:
            for branch in t_obj.obj3d.branches:
                if branch is exclude_branch:
                    continue

                mat = BRANCH_FIT if self._fits(diameter, branch) else BRANCH_NO_FIT
                t_obj.obj3d.highlight_branch(branch, mat)
                self._highlighted.append((t_obj.obj3d, branch))

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
        if self._state == self._ROUTING:
            self._update_preview(mouse_pos)

    @_check_types.do
    def release_capture(self) -> None:
        if self._finalized or self._captured_position is None:
            return

        if self._state == self._IDLE:
            self._begin(self._captured_position)
        elif self._state == self._ROUTING:
            self._handle_routing_click(self._captured_position)
        elif self._state == self._IN_TRANS:
            self._handle_exit_click(self._captured_position)

    @_check_types.do
    def _begin(self, mouse_pos: _point.Point) -> None:
        pos = self.camera.get_position_on_focal_plane(mouse_pos)
        if pos is None:
            return

        p3d = self.ptables.pjt_points3d_table.insert(
            float(pos.x), float(pos.y), float(pos.z))

        self._seg_start_id = p3d.db_id
        self._state = self._ROUTING

    @_check_types.do
    def _update_preview(self, mouse_pos: _point.Point) -> None:
        target = _object_picker.find_object(mouse_pos, self.camera, self.camera.canvas)

        if isinstance(target, (_wire.Wire, _bundle.Bundle)):
            # TODO: locate missig get_closest_point_on_wire_endpoint function
            pos, _ = _utils.get_closest_point_on_wire_endpoint(
                mouse_pos, self.camera, target)[:2]

            if not isinstance(pos, _point.Point):
                pos = _point.Point(*pos)
        else:
            pos = self.camera.get_position_on_focal_plane(mouse_pos)

        if pos is None:
            return

        if self._preview is None:
            end_p3d = self.ptables.pjt_points3d_table.insert(
                float(pos.x), float(pos.y), float(pos.z))

            wire_db = _insert_wire(
                self.ptables, self.part_id, self._wire_name(), None,
                self._seg_start_id, end_p3d.db_id, visible=True)

            self._preview = _wire.Wire(self.mainframe, wire_db)
            self.mainframe.add_object(self._preview)
        else:
            end_pos = self._preview.obj3d.stop_position
            end_pos += pos - end_pos

    @_check_types.do
    def _handle_routing_click(self, mouse_pos: _point.Point) -> None:
        from ..objects.objects_3d.transition import Branch as _Branch3D

        selected = _object_picker.find_object(mouse_pos, self.camera, self.camera.canvas)

        diameter = self._wire_od()

        if isinstance(selected, _bundle.Bundle):
            chain = _walk_bundle_chain(selected.db_obj, self.ptables)
            # Entry end: whichever bundle end is closer to current position
            cur_p3d = self.ptables.pjt_points3d_table[self._seg_start_id]

            cur_np = np.array(
                [cur_p3d.x, cur_p3d.y, cur_p3d.z], dtype=float)

            end_a_db = self.ptables.pjt_points3d_table[chain[0]]

            end_a_np = np.array(
                [end_a_db.x, end_a_db.y, end_a_db.z], dtype=float)

            end_b_db = self.ptables.pjt_points3d_table[chain[-1]]

            end_b_np = np.array(
                [end_b_db.x, end_b_db.y, end_b_db.z], dtype=float)

            if (
                float(np.linalg.norm(cur_np - end_b_np)) <
                float(np.linalg.norm(cur_np - end_a_np))
            ):
                chain = list(reversed(chain))

            # Visible segment up to bundle entry, then invisible through bundle
            self._segments.append((self._seg_start_id, chain[0], True))

            for i in range(len(chain) - 1):
                self._segments.append((chain[i], chain[i + 1], False))

            self._seg_start_id = chain[-1]
            self._delete_preview()

        elif isinstance(selected, _Branch3D):
            if not self._fits(diameter, selected):
                return

            entry_p_id = selected.db_obj.position3d.db_id[:-2]
            self._segments.append((self._seg_start_id, entry_p_id, True))
            self._seg_start_id = entry_p_id
            self._delete_preview()
            self._clear_highlights()
            self._entry_branch = selected
            self._highlight_exit_branches(diameter, exclude_branch=selected)
            self._state = self._IN_TRANS

        else:
            self._place_all(mouse_pos)

    @_check_types.do
    def _handle_exit_click(self, mouse_pos: _point.Point) -> None:
        from ..objects.objects_3d.transition import Branch as _Branch3D

        selected = _object_picker.find_object(mouse_pos, self.camera, self.camera.canvas)

        if not isinstance(selected, _Branch3D):
            return

        if not self._fits(self._wire_od(), selected):
            return

        self._clear_highlights()
        exit_p_id = selected.db_obj.position3d.db_id[:-2]
        self._segments.append((self._seg_start_id, exit_p_id, False))
        self._seg_start_id = exit_p_id
        self._entry_branch = None
        self._state = self._ROUTING

    @_check_types.do
    def _place_all(self, mouse_pos: _point.Point) -> None:
        self._delete_preview()
        self._clear_highlights()

        target = _object_picker.find_object(mouse_pos, self.camera, self.camera.canvas)

        if isinstance(target, (_wire.Wire, _bundle.Bundle)):
            # TODO: locate missing get_closest_point_on_wire_endpoint function
            pos, _ = _utils.get_closest_point_on_wire_endpoint(
                mouse_pos, self.camera, target)[:2]

            if not isinstance(pos, _point.Point):
                pos = _point.Point(*pos)
        else:
            pos = self.camera.get_position_on_focal_plane(mouse_pos)

        if pos is None or self._seg_start_id is None:
            self._reset()
            return

        end_p3d = self.ptables.pjt_points3d_table.insert(
            float(pos.x), float(pos.y), float(pos.z))

        self._segments.append((self._seg_start_id, end_p3d.db_id, True))

        intermediate_layout_points = set()
        name = self._wire_name()

        # NOTE: each routed segment still becomes its own pjt_wires row
        # here (pre-dating the single-wire/waypoint model -- see
        # handlers.wire_handler.AddWireHandler._commit_waypoint for the
        # up-to-date equivalent); stripe continuity across these rows is
        # no longer stitched via a persisted/cascaded value or a runtime
        # sibling link (both removed), so consecutive segments' stripes
        # each start fresh rather than visually continuing -- a follow-up
        # to fold this tool onto the same one-wire-plus-waypoints model
        # would fix that as a side effect.
        for i, (start_id, stop_id, visible) in enumerate(self._segments):
            wire_db = _insert_wire(
                self.ptables, self.part_id, name,
                None, start_id, stop_id, visible=visible)

            wire_obj = _wire.Wire(self.mainframe, wire_db)
            self.mainframe.project.add_wire(wire_obj)

            if (
                not visible and
                i + 1 < len(self._segments) and
                not self._segments[i + 1][2]
            ):

                intermediate_layout_points.add(stop_id)

        for point_id in intermediate_layout_points:
            layout_db = self.ptables.pjt_wire_layouts_table.insert(point_id)
            layout_db.is_visible3d = False
            layout_db.is_visible2d = False

            self.mainframe.project.add_wire_layout(
                _wire_layout.WireLayout(self.mainframe, layout_db))

        self._reset()

    @_check_types.do
    def _reset(self) -> None:
        self._state = self._IDLE
        self._segments = []
        self._seg_start_id = None
        self._entry_branch = None
        self._preview = None
        self._finalized = True

    @_check_types.do
    def cancel(self) -> None:
        self._delete_preview()
        self._clear_highlights()
        self._reset()
