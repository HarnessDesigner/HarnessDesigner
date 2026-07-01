# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handlers for transitions and routed wire placement."""

import math
import numpy as np
from PySide6.QtWidgets import QDialog
from typing import TYPE_CHECKING

from . import handler_base as _handler_base
from ..geometry import point as _point
from ..geometry import angle as _angle
from ..gl.canvas3d import object_picker as _object_picker
from ..objects import transition as _transition
from ..objects import bundle as _bundle
from ..objects import wire as _wire
from ..objects import wire_layout as _wire_layout
from .. import utils as _utils
from ..gl import materials as _materials
from .. import config as _config
from .. import color as _color
from ..ui.dialogs import part_search as _part_search
from ..ui.editor_db import transition as _trans_editor_page


if TYPE_CHECKING:
    from ..gl.canvas3d import camera as _camera
    from .. import ui as _ui


Config = _config.Config.colors
_SNAP_THRESHOLD = 5.0

_HOVER_HIGHLIGHT = _materials.Plastic(_color.Color(0.2, 0.6, 1.0, 0.8))
_BRANCH_FIT = _materials.Plastic(_color.Color(0.3, 1.0, 0.3, 1.0))
_BRANCH_NO_FIT = _materials.Plastic(_color.Color(1.0, 0.4, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Point / DB helpers
# ---------------------------------------------------------------------------

def _repoint_all_references(ptables, old_point_id: int, new_point_id: int) -> None:
    """
    Replace every reference to *old_point_id* with *new_point_id* across all project tables.
    """

    from ..database.project_db.cleanup import _POINT3D_REFS

    con = ptables.pjt_wires_table._con
    for table_name, col in _POINT3D_REFS:
        con.execute(
            f'UPDATE {table_name} SET {col} = ? WHERE {col} = ?;',
            (new_point_id, old_point_id))

    con.commit()


def _delete_point_if_orphaned(ptables, point_id: int) -> None:
    """
    Delete *point_id* from pjt_points3d if nothing references it.
    """

    from ..database.project_db.cleanup import _POINT3D_REFS

    con = ptables.pjt_wires_table._con
    for table_name, col in _POINT3D_REFS:
        rows = con.execute(
            f'SELECT id FROM {table_name} WHERE {col} = ? LIMIT 1;',
            (point_id,)).fetchall()

        if rows:
            return

    con.execute('DELETE FROM pjt_points3d WHERE id = ?;', (point_id,))
    con.commit()


def _insert_wire(ptables, part_id, circuit_id, start_id, stop_id, visible: bool):
    return ptables.pjt_wires_table.insert(
        part_id, circuit_id, start_id, stop_id,
        None, None, visible, False, None, None, False)


def _insert_bundle(ptables, part_id, start_id, stop_id):
    db = ptables.pjt_bundles_table.insert(part_id)
    db.start_position3d_id = start_id
    db.stop_position3d_id = stop_id

    return db


def _walk_bundle_chain(bundle_db_obj, ptables) -> list:
    """
    Walk the full bundle chain from one free end to the other.

    Returns an ordered list of Point IDs:
        [end_A_id, layout_id, ..., end_B_id]
    """
    def _has_layout(point_id):
        return bool(ptables.pjt_bundle_layouts_table.select(
            'id', position3d_id=point_id))

    def _next_section(current_id, from_point_id, visited):
        rows = (ptables.pjt_bundles_table.select(
            'id', start_point3d_id=from_point_id) +
                ptables.pjt_bundles_table.select(
                    'id', stop_point3d_id=from_point_id))

        for row in rows:
            bid = row[0]
            if bid != current_id and bid not in visited:
                return bid

        return None

    def _walk_direction(start_section_id, leaving_point_id):
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


# ---------------------------------------------------------------------------
# Diameter / wire assignment helpers (used by AddTransitionHandler)
# ---------------------------------------------------------------------------

def _wire_area(conc_wire) -> float:
    od = conc_wire.wire.part.od_mm

    return math.pi * (od / 2.0) ** 2 if od else 0.0


def effective_diameter(conc_wires, global_branch) -> float:
    """
    Effective packed diameter with 15% air gap; never below min_dia.
    """

    if not conc_wires:
        return float(global_branch.min_dia)

    total_area = sum(_wire_area(cw) for cw in conc_wires)
    raw = 2.0 * math.sqrt(total_area * 1.15 / math.pi)

    return max(raw, float(global_branch.min_dia))


def assign_wires_to_branches(conc_wires, global_output_branches) -> list:
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


def _set_angle_from_bundle(transition_db_obj, bundle) -> None:
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

    z_axis = np.cross(x_axis, world_up)
    z_len = float(np.linalg.norm(z_axis))
    if z_len < 1e-8:
        return

    z_axis /= z_len
    y_axis = np.cross(z_axis, x_axis)
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
    new_euler = _handler_base._euler_from_matrix_continuous(rot_mat, old_euler)
    obj_angle._q.w, obj_angle._q.x = float(qw), float(qx)
    obj_angle._q.y, obj_angle._q.z = float(qy), float(qz)
    cache = obj_angle._Angle__euler_angles
    if cache is not None:
        cache[0], cache[1], cache[2] = new_euler[0], new_euler[1], new_euler[2]

    obj_angle._matrix[:] = obj_angle._q.as_matrix
    obj_angle._process_callbacks()


def _create_branch_concentric(ptables, branch_db, conc_wires, diameter) -> None:
    """Create concentric → single layer → wires for one transition branch."""
    conc_db = ptables.pjt_concentrics_table.insert(None, branch_db.db_id)
    if not conc_wires:
        return

    layer_db = ptables.pjt_concentric_layers_table.insert(
        0, len(conc_wires), 0, conc_db.db_id, diameter)

    for idx, cw in enumerate(conc_wires):
        ptables.pjt_concentric_wires_table.insert(layer_db.db_id, idx, cw.wire_id, False)


def _find_bundle(mouse_pos, camera, project) -> "_bundle.Bundle | None":
    selected = _object_picker.find_object(mouse_pos, camera.objects_in_view, camera)
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


# ===========================================================================
# AddTransitionHandler
# ===========================================================================

class AddTransitionHandler(_handler_base.HandlerBase):
    """Handle interactive placement of transition fittings onto bundles.

    Workflow: hover snaps to the nearest bundle and shows a live preview.
    Click finalises the placement, creating all required DB records (transition,
    branches, concentrics, invisible wire layouts and pass-through wire segments).
    """
    obj: "_transition.Transition" = None

    def __init__(self, mainframe: "_ui.MainFrame"):
        part_id = mainframe.editor_db.editor.transitions.GetSelection()
        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _trans_editor_page.TransitionsPage,
                title='Add Transition',
                table=mainframe.global_db.transitions_table)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()
            dlg.deleteLater()

        super().__init__(mainframe, part_id)

        self._snapped_bundle: "_bundle.Bundle | None" = None
        self._highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.bundle_highlight))

        if part_id is None:
            self._finalized = True
            return

        self.part = mainframe.global_db.transitions_table[part_id]

        # Preview: build transition DB with all branch points at the origin.
        # _build_model will fire in Transition.__init__ and position them locally.
        center_db = self.ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
        init_angle = _angle.Angle()

        name = f'{self.part.manufacturer.name} {self.part.part_number}'

        transition_db = self.ptables.pjt_transitions_table.insert(
            part_id, name, center_db.db_id, init_angle)

        for branch_id in range(1, self.part.branch_count + 1):
            g_br = self.part.branches[branch_id - 1]
            pt_db = self.ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
            self.ptables.pjt_transition_branches_table.insert(
                transition_db.db_id, pt_db.db_id, branch_id, float(g_br.min_dia))

        self.obj = _transition.Transition(mainframe, transition_db)
        self.obj.obj3d.is_visible = False

    def hover(self, mouse_pos: _point.Point):
        if self._finalized:
            return

        bundle = _find_bundle(mouse_pos, self.camera, self.mainframe.project)

        if bundle is None:
            if self._snapped_bundle is not None:
                self._snapped_bundle.identify(None)
                self._snapped_bundle = None
            self.obj.obj3d.is_visible = False
            return

        trunk_global = self.part.branches[0]
        conc_wires = bundle.db_obj.wires
        if effective_diameter(conc_wires, trunk_global) > float(trunk_global.max_dia):
            if self._snapped_bundle is not None:
                self._snapped_bundle.identify(None)
                self._snapped_bundle = None
            self.obj.obj3d.is_visible = False
            return

        # I have to make this available on the budles as well.
        raw_pos, _, _ = _utils.get_closest_point_on_wire_endpoint(
            mouse_pos, self.camera, bundle)
        if not isinstance(raw_pos, _point.Point):
            raw_pos = _point.Point(*raw_pos)

        pos = self.obj.obj3d.position
        pos += raw_pos - pos

        if bundle is not self._snapped_bundle:
            if self._snapped_bundle is not None:
                self._snapped_bundle.identify(None)

            bundle.identify(self._highlight_material)
            _set_angle_from_bundle(self.obj.db_obj, bundle)
            self.obj.obj3d.build()
            self._snapped_bundle = bundle

        self.obj.obj3d.is_visible = True

    def release_capture(self):
        if self._finalized or self._captured_position is None:
            return

        if self._snapped_bundle is None:
            return

        bundle = self._snapped_bundle
        self._snapped_bundle.identify(None)
        self._snapped_bundle = None

        raw_pos, is_at_endpoint, endpoint = _utils.get_closest_point_on_wire_endpoint(
            self._captured_position, self.camera, bundle)
        if not isinstance(raw_pos, _point.Point):
            raw_pos = _point.Point(*raw_pos)

        self._finalize(bundle, raw_pos, is_at_endpoint, endpoint)

    def _finalize(self, bundle, snap_pos, is_at_endpoint, endpoint):
        project = self.mainframe.project
        ptables = self.ptables
        global_branches = self.part.branches
        trunk_global = global_branches[0]
        output_globals = global_branches[1:]

        conc_wires = bundle.db_obj.wires
        output_assignments = assign_wires_to_branches(conc_wires, output_globals)

        self.obj.delete()
        self.obj = None

        # Trunk entry point: reuse existing bundle endpoint or create new split point
        if is_at_endpoint:
            ep_pt = (bundle.obj3d.start_position if endpoint == 'start'
                     else bundle.obj3d.stop_position)
            trunk_point_id = int(ep_pt.db_id[:-2])
        else:
            pt_db = ptables.pjt_points3d_table.insert(
                float(snap_pos.x), float(snap_pos.y), float(snap_pos.z))
            trunk_point_id = pt_db.db_id

        center_db = ptables.pjt_points3d_table.insert(
            float(snap_pos.x), float(snap_pos.y), float(snap_pos.z))
        init_angle = _angle.Angle()
        transition_db = ptables.pjt_transitions_table.insert(
            self.part_id, center_db.db_id, init_angle, '')
        _set_angle_from_bundle(transition_db, bundle)

        # Branch 1 — trunk
        trunk_dia = effective_diameter(conc_wires, trunk_global)
        trunk_br_db = ptables.pjt_transition_branches_table.insert(
            transition_db.db_id, trunk_point_id, 1, trunk_dia)
        _create_branch_concentric(ptables, trunk_br_db, conc_wires, trunk_dia)

        # Invisible wire layout at trunk entry point
        trunk_wl_db = ptables.pjt_wire_layouts_table.insert(trunk_point_id)
        trunk_wl_db.is_visible3d = False
        project.add_wire_layout(_wire_layout.WireLayout(self.mainframe, trunk_wl_db))

        # Output branches — placeholder points, resolved by Transition 3D ctor
        branch_records = []
        for i, (g_br, assigned) in enumerate(zip(output_globals, output_assignments)):
            br_pt_db = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
            br_dia = effective_diameter(assigned, g_br)
            br_db = ptables.pjt_transition_branches_table.insert(
                transition_db.db_id, br_pt_db.db_id, i + 2, br_dia)
            _create_branch_concentric(ptables, br_db, assigned, br_dia)
            branch_records.append((br_db, br_pt_db.db_id, assigned))

        # Build the real 3D Transition — this updates branch point positions in the DB
        transition_obj = _transition.Transition(self.mainframe, transition_db)

        # Wire layouts at output branch points + invisible wire segments through transition
        for br_db, br_pt_id, assigned in branch_records:
            wl_db = ptables.pjt_wire_layouts_table.insert(br_pt_id)
            wl_db.is_visible3d = False
            project.add_wire_layout(_wire_layout.WireLayout(self.mainframe, wl_db))

            for cw in assigned:
                pjt_wire = cw.wire
                ptables.pjt_wires_table.insert(
                    pjt_wire.part_id, pjt_wire.circuit_id,
                    trunk_point_id, br_pt_id,
                    None, None, False, False, None, None, False)

        if not is_at_endpoint:
            from . import bundle_layout_handler as _blh

            _blh._split_bundle_at_point(project, bundle, trunk_point_id)

        project.add_transition(transition_obj)
        self._finalized = True

    def cancel(self):
        if self._snapped_bundle is not None:
            self._snapped_bundle.identify(None)
            self._snapped_bundle = None

        if self.obj is not None:
            self.obj.delete()
            self.obj = None


# ===========================================================================
# RouteThroughTransitionHandler
# ===========================================================================

class RouteThroughTransitionHandler(_handler_base.HandlerBase):
    """Reconnect an existing wire or bundle endpoint to a compatible transition branch."""

    def __init__(self, mainframe: "_ui.MainFrame", target, is_start: bool):
        super().__init__(mainframe, None)
        self.target = target
        self.is_start = is_start
        self.diameter = self._diameter_of(target)
        self._highlighted = []

    @staticmethod
    def _diameter_of(obj) -> float:
        if isinstance(obj, _wire.Wire):
            od = obj.db_obj.part.od_mm
            return float(od) if od else 1.0

        if isinstance(obj, _bundle.Bundle):
            d = obj.obj3d._diameter
            return float(d) if d else 1.0

        return 1.0

    @staticmethod
    def _fits(diameter: float, branch) -> bool:
        return branch.min_diameter <= diameter <= branch.max_diameter

    def _highlight_branches(self):
        for t_obj in self.mainframe.project.transitions:
            for branch in t_obj.obj3d._branches:
                mat = _BRANCH_FIT if self._fits(self.diameter, branch) else _BRANCH_NO_FIT
                branch.identify(mat)
                self._highlighted.append(branch)

    def _clear_highlights(self):
        for b in self._highlighted:
            b.identify(None)

        self._highlighted.clear()

    def hover(self, mouse_pos: _point.Point):
        pass

    def release_capture(self):
        if self._finalized or self._captured_position is None:
            return

        from ..objects.objects3d.transition import Branch as _Branch3D

        selected = _object_picker.find_object(
            self._captured_position, self.camera.objects_in_view, self.camera)

        self._clear_highlights()
        self._finalized = True

        if not isinstance(selected, _Branch3D):
            return

        if not self._fits(self.diameter, selected):
            return

        old_point_id = (self.target.db_obj.start_position3d_id if self.is_start
                        else self.target.db_obj.stop_position3d_id)
        branch_p_id = int(selected.db_obj.position3d.db_id[:-2])
        if old_point_id == branch_p_id:
            return

        _repoint_all_references(self.ptables, old_point_id, branch_p_id)
        _delete_point_if_orphaned(self.ptables, old_point_id)
        self.mainframe.editor3d.Refresh(False)

    def cancel(self):
        self._clear_highlights()


# ===========================================================================
# RouteThroughBundleHandler
# ===========================================================================

class RouteThroughBundleHandler(_handler_base.HandlerBase):
    """Reconnect an existing wire endpoint so it shares a selected bundle endpoint."""

    def __init__(self, mainframe: "_ui.MainFrame", target: "_wire.Wire", is_start: bool):
        super().__init__(mainframe, None)
        self.target = target
        self.is_start = is_start
        self._hovered_bundle = None

    def hover(self, mouse_pos: _point.Point):
        selected = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)

        if not isinstance(selected, _bundle.Bundle):
            if self._hovered_bundle is not None:
                self._hovered_bundle.identify(None)
                self._hovered_bundle = None

            return

        if selected is not self._hovered_bundle:
            if self._hovered_bundle is not None:
                self._hovered_bundle.identify(None)

            selected.identify(_HOVER_HIGHLIGHT)
            self._hovered_bundle = selected

    def release_capture(self):
        if self._finalized or self._captured_position is None:
            return

        if self._hovered_bundle is not None:
            self._hovered_bundle.identify(None)
            self._hovered_bundle = None

        selected = _object_picker.find_object(
            self._captured_position, self.camera.objects_in_view, self.camera)

        self._finalized = True

        if not isinstance(selected, _bundle.Bundle):
            return

        old_point_id = (self.target.db_obj.start_position3d_id if self.is_start
                        else self.target.db_obj.stop_position3d_id)

        wire_p = (self.target.obj3d.start_position if self.is_start
                  else self.target.obj3d.stop_position)

        start_np = selected.obj3d.start_position.as_numpy
        stop_np = selected.obj3d.stop_position.as_numpy
        wire_np = wire_p.as_numpy
        d_start = float(np.linalg.norm(wire_np - start_np))
        d_stop = float(np.linalg.norm(wire_np - stop_np))

        bundle_start_id = int(selected.obj3d.start_position.db_id[:-2])
        bundle_stop_id = int(selected.obj3d.stop_position.db_id[:-2])
        bundle_p_id = bundle_start_id if d_start <= d_stop else bundle_stop_id

        if old_point_id == bundle_p_id:
            return

        _repoint_all_references(self.ptables, old_point_id, bundle_p_id)
        self.mainframe.editor3d.Refresh(False)

    def cancel(self):
        if self._hovered_bundle is not None:
            self._hovered_bundle.identify(None)
            self._hovered_bundle = None


# ===========================================================================
# RoutedWireHandler
# ===========================================================================

class RoutedWireHandler(_handler_base.HandlerBase):
    """Create a new wire that can pass through bundle chains and transitions.

    Click to start, click again to add waypoints (clicking bundles / transition
    branches routes through them automatically), final click places the wire.
    """
    _IDLE = 'idle'
    _ROUTING = 'routing'
    _IN_TRANS = 'in_transition'

    def __init__(self, mainframe: "_ui.MainFrame", part_id: int):
        super().__init__(mainframe, part_id)
        self._state = self._IDLE
        self._segments = []
        self._seg_start_id = None
        self._entry_branch = None
        self._preview = None
        self._highlighted = []

    def _clear_highlights(self):
        for obj in self._highlighted:
            obj.identify(None)

        self._highlighted.clear()

    def _delete_preview(self):
        if self._preview is not None:
            self._preview.delete()
            self._preview = None

    def _wire_od(self) -> float:
        od = self.mainframe.global_db.wires_table[self.part_id].od_mm

        return float(od) if od else 1.0

    def _fits(self, diameter: float, branch) -> bool:
        return branch.min_diameter <= diameter <= branch.max_diameter

    def _highlight_exit_branches(self, diameter: float, exclude_branch):
        for t_obj in self.mainframe.project.transitions:
            for branch in t_obj.obj3d._branches:
                if branch is exclude_branch:
                    continue

                mat = _BRANCH_FIT if self._fits(diameter, branch) else _BRANCH_NO_FIT
                branch.identify(mat)
                self._highlighted.append(branch)

    def hover(self, mouse_pos: _point.Point):
        if self._state == self._ROUTING:
            self._update_preview(mouse_pos)

    def release_capture(self):
        if self._finalized or self._captured_position is None:
            return

        if self._state == self._IDLE:
            self._begin(self._captured_position)
        elif self._state == self._ROUTING:
            self._handle_routing_click(self._captured_position)
        elif self._state == self._IN_TRANS:
            self._handle_exit_click(self._captured_position)

    def _begin(self, mouse_pos: _point.Point):
        pos = self.camera.get_position_on_focal_plane(mouse_pos)
        if pos is None:
            return

        p3d = self.ptables.pjt_points3d_table.insert(
            float(pos.x), float(pos.y), float(pos.z))

        self._seg_start_id = p3d.db_id
        self._state = self._ROUTING

    def _update_preview(self, mouse_pos: _point.Point):
        target = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)
        if isinstance(target, (_wire.Wire, _bundle.Bundle)):
            pos, _ = (_utils.get_closest_point_on_wire_endpoint(
                mouse_pos, self.camera, target)[:2])

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
                self.ptables, self.part_id, None,
                self._seg_start_id, end_p3d.db_id, visible=True)

            self._preview = _wire.Wire(self.mainframe, wire_db)
            self.mainframe.add_object(self._preview)
        else:
            end_pos = self._preview.obj3d.stop_position
            end_pos += pos - end_pos

    def _handle_routing_click(self, mouse_pos: _point.Point):
        from ..objects.objects3d.transition import Branch as _Branch3D

        selected = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)

        diameter = self._wire_od()

        if isinstance(selected, _bundle.Bundle):
            chain = _walk_bundle_chain(selected.db_obj, self.ptables)
            # Entry end: whichever bundle end is closer to current position
            cur_p3d = self.ptables.pjt_points3d_table[self._seg_start_id]
            cur_np = np.array([cur_p3d.x, cur_p3d.y, cur_p3d.z], dtype=float)
            end_a_db = self.ptables.pjt_points3d_table[chain[0]]
            end_a_np = np.array([end_a_db.x, end_a_db.y, end_a_db.z], dtype=float)
            end_b_db = self.ptables.pjt_points3d_table[chain[-1]]
            end_b_np = np.array([end_b_db.x, end_b_db.y, end_b_db.z], dtype=float)

            if float(np.linalg.norm(cur_np - end_b_np)) < float(np.linalg.norm(cur_np - end_a_np)):
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

            entry_p_id = int(selected.db_obj.position3d.db_id[:-2])
            self._segments.append((self._seg_start_id, entry_p_id, True))
            self._seg_start_id = entry_p_id
            self._delete_preview()
            self._clear_highlights()
            self._entry_branch = selected
            self._highlight_exit_branches(diameter, exclude_branch=selected)
            self._state = self._IN_TRANS

        else:
            self._place_all(mouse_pos)

    def _handle_exit_click(self, mouse_pos: _point.Point):
        from ..objects.objects3d.transition import Branch as _Branch3D

        selected = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)

        if not isinstance(selected, _Branch3D):
            return

        if not self._fits(self._wire_od(), selected):
            return

        self._clear_highlights()
        exit_p_id = int(selected.db_obj.position3d.db_id[:-2])
        self._segments.append((self._seg_start_id, exit_p_id, False))
        self._seg_start_id = exit_p_id
        self._entry_branch = None
        self._state = self._ROUTING

    def _place_all(self, mouse_pos: _point.Point):
        self._delete_preview()
        self._clear_highlights()

        target = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)

        if isinstance(target, (_wire.Wire, _bundle.Bundle)):
            pos, _ = (_utils.get_closest_point_on_wire_endpoint(
                mouse_pos, self.camera, target)[:2])

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
        for i, (start_id, stop_id, visible) in enumerate(self._segments):
            wire_db = _insert_wire(
                self.ptables, self.part_id, None, start_id, stop_id, visible=visible)

            self.mainframe.project.add_wire(_wire.Wire(self.mainframe, wire_db))

            if not visible and (i + 1 < len(self._segments) and
                                not self._segments[i + 1][2]):

                intermediate_layout_points.add(stop_id)

        for point_id in intermediate_layout_points:
            layout_db = self.ptables.pjt_wire_layouts_table.insert(point_id)
            layout_db.is_visible3d = False
            layout_db.is_visible2d = False

            self.mainframe.project.add_wire_layout(
                _wire_layout.WireLayout(self.mainframe, layout_db))

        self._reset()

    def _reset(self):
        self._state = self._IDLE
        self._segments = []
        self._seg_start_id = None
        self._entry_branch = None
        self._preview = None
        self._finalized = True

    def cancel(self):
        self._delete_preview()
        self._clear_highlights()
        self._reset()
