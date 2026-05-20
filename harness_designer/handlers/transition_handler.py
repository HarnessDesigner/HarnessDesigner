# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

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


if TYPE_CHECKING:
    from ..gl.canvas3d import camera as _camera
    from .. import ui as _ui


Config = _config.Config.colors

_BRANCH_FIT = [0.3, 1.0, 0.3, 1.0]
_BRANCH_NO_FIT = [1.0, 0.4, 0.0, 1.0]


# ── point cleanup helpers ─────────────────────────────────────────────────────

# Orphan *deletion* is intentionally NOT done inline here.  Checking every
# reference column after every drag-and-drop is expensive, and a point that
# appears temporarily unreferenced between two operations should not be
# deleted prematurely.
#
# Orphan cleanup is deferred to application exit and to an on-demand user
# action.  See database/project_db/cleanup.py for the full implementation.
#
# What IS done inline is repointing — updating every object that still
# references the old Point ID so that they connect at the new shared Point
# instead.  This must happen immediately so the object graph stays consistent
# during the current editing session.

def _repoint_all_references(ptables, old_point_id: int, new_point_id: int):
    """
    Update every row in every project table that references *old_point_id*
    so that it references *new_point_id* instead.

    This covers wire segments, wire layouts, bundle segments, splices, and
    any other object that shared the old Point — they all need to connect at
    the new shared Point after a drag-and-drop endpoint reassignment.

    Orphan deletion (removing the old Point row from pjt_points3d if nothing
    now references it) is NOT performed here.  It is handled by the deferred
    cleanup in database/project_db/cleanup.py, which runs on application exit
    and on explicit user request.
    """
    from ..database.project_db.cleanup import _POINT3D_REFS

    con = ptables.pjt_wires_table._con

    for table_name, col in _POINT3D_REFS:
        con.execute(
            f'UPDATE {table_name} SET {col} = ? WHERE {col} = ?;',
            (new_point_id, old_point_id)
        )

    con.commit()


# ── general helpers ───────────────────────────────────────────────────────────

def _get_wire_or_bundle(mouse_pos, camera):
    selected = _object_picker.find_object(
        mouse_pos, camera.objects_in_view, camera)
    if isinstance(selected, (_wire.Wire, _bundle.Bundle)):
        return selected
    return None


def _diameter_of(obj) -> float:
    if isinstance(obj, _wire.Wire):
        od = obj.db_obj.part.od_mm
        return float(od) if od else 1.0
    if isinstance(obj, _bundle.Bundle):
        d = obj.obj3d._diameter
        return float(d) if d else 1.0
    return 1.0


def _fits(diameter: float, branch) -> bool:
    return branch.min_diameter <= diameter <= branch.max_diameter


def _best_fitting_branches(branches, diameter: float):
    fitting = sorted(
        [b for b in branches if _fits(diameter, b)],
        key=lambda b: abs(diameter - (b.min_diameter + b.max_diameter) / 2.0)
    )
    if len(fitting) < 2:
        return None, None
    return fitting[0], fitting[1]


def _insert_wire(ptables, part_id, circuit_id,
                 start_id, stop_id, visible: bool):
    return ptables.pjt_wires_table.insert(
        part_id=part_id,
        circuit_id=circuit_id,
        start_point3d_id=start_id,
        stop_point3d_id=stop_id,
        start_point2d_id=None,
        stop_point2d_id=None,
        is_visible3d=visible,
        is_visible2d=False,
        layer_view_point_id=None,
        layer_id=None,
        is_filler_wire=False
    )


def _insert_bundle(ptables, part_id, start_id, stop_id):
    db = ptables.pjt_bundles_table.insert(part_id=part_id)
    db.start_position3d_id = start_id
    db.stop_position3d_id  = stop_id
    return db


def _walk_bundle_chain(bundle_db_obj, ptables):
    """
    Walk the entire chain of bundle sections connected through shared
    layout Points, starting from *bundle_db_obj*.

    Returns an ordered list of Point IDs representing every boundary in
    the chain from one true end to the other:

        [end_A_id, layout_id, layout_id, ..., end_B_id]

    The first and last IDs are free endpoints (no layout attached).
    Every ID in between is a layout Point shared by two adjacent sections.

    A wire routed through the full bundle needs:
    - One invisible wire segment per consecutive pair of IDs
    - One invisible wire layout at each intermediate Point so that wire
      length calculations follow the actual routed path, not a chord
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
        pts = []
        current_id = start_section_id
        current_pt = leaving_point_id
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


# ══════════════════════════════════════════════════════════════════════════════
# AddTransitionHandler
# ══════════════════════════════════════════════════════════════════════════════

class AddTransitionHandler(_handler_base.HandlerBase):
    obj: _transition.Transition = None

    def __init__(self, mainframe: '_ui.MainFrame', part_id: int):
        super().__init__(mainframe, part_id)
        self.target = None

        self._preview_material = _materials.Plastic(
            _color.Color(*Config.add_object.preview_color))
        self._wire_highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.wire_highlight))
        self._bundle_highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.bundle_highlight))

    def release_capture(self) -> None:
        raise NotImplementedError

    def hover(self, mouse_pos: _point.Point):
        target = _get_wire_or_bundle(mouse_pos, self.camera)
        if target is None:
            if self.target is not None:
                self.target.identify(None)
                self.target = None
            return
        if target != self.target:
            if self.target is not None:
                self.target.identify(None)
            target.identify(_HOVER_HIGHLIGHT)
            self.target = target

    def start(self, mouse_pos: _point.Point):
        self.is_active = True
        self.finalize(mouse_pos)

    def finalize(self, mouse_pos: _point.Point):
        if not self.is_active:
            return

        if self.target is not None:
            self.target.identify(None)
            self.target = None

        target = _get_wire_or_bundle(mouse_pos, self.camera)
        if target is None:
            self.is_active = False
            return

        position, wire_angle = _utils.get_closest_point_on_wire(
            mouse_pos, self.camera, target)
        if None in (position, wire_angle):
            self.is_active = False
            return

        diameter  = _diameter_of(target)
        is_bundle = isinstance(target, _bundle.Bundle)
        part      = self.mainframe.project.gtables.transitions_table[self.part_id]

        centre_p3d = self.ptables.pjt_points3d_table.insert(
            position.x, position.y, position.z)
        transition_db = self.ptables.pjt_transitions_table.insert(
            self.part_id, centre_p3d.db_id, wire_angle, part.name)

        for i, branch_data in enumerate(part.branches):
            bp3d = self.ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
            self.ptables.pjt_transition_branches_table.insert(
                transition_id=transition_db.db_id,
                point_id=bp3d.db_id,
                branch_id=i + 1,
                diameter=float(branch_data.min_dia)
            )

        transition_obj = _transition.Transition(self.mainframe, transition_db)
        self.mainframe.project.add_transition(transition_obj)

        entry_branch, exit_branch = _best_fitting_branches(
            transition_obj.obj3d._branches, diameter)
        if entry_branch is None:
            self.is_active = False
            return

        entry_p_id        = int(entry_branch.db_obj.position3d.db_id[:-2])
        exit_p_id         = int(exit_branch.db_obj.position3d.db_id[:-2])
        original_start_id = int(target.obj3d.start_position.db_id[:-2])
        original_stop_id  = int(target.obj3d.stop_position.db_id[:-2])
        part_id           = target.db_obj.part_id
        circuit_id        = getattr(target.db_obj, 'circuit_id', None)

        if is_bundle:
            seg1 = _insert_bundle(
                self.ptables, part_id, original_start_id, entry_p_id)
            seg2 = _insert_bundle(
                self.ptables, part_id, exit_p_id, original_stop_id)
            self.mainframe.project.add_bundle(
                _bundle.Bundle(self.mainframe, seg1))
            self.mainframe.project.add_bundle(
                _bundle.Bundle(self.mainframe, seg2))
        else:
            seg1 = _insert_wire(
                self.ptables, part_id, circuit_id,
                original_start_id, entry_p_id, visible=True)
            seg2 = _insert_wire(
                self.ptables, part_id, circuit_id,
                exit_p_id, original_stop_id, visible=True)
            self.mainframe.project.add_wire(
                _wire.Wire(self.mainframe, seg1))
            self.mainframe.project.add_wire(
                _wire.Wire(self.mainframe, seg2))

        target.delete()
        self.is_active = False


# ══════════════════════════════════════════════════════════════════════════════
# RouteThroughTransitionHandler
# Drag an existing wire/bundle endpoint into a transition branch.
# ══════════════════════════════════════════════════════════════════════════════

class RouteThroughTransitionHandler(_handler_base.HandlerBase):

    def __init__(self, mainframe: '_ui.MainFrame',
                 target, is_start: bool):
        super().__init__(mainframe, None)
        self.target       = target
        self.is_start     = is_start
        self.diameter     = _diameter_of(target)
        self._highlighted = []

    def _highlight_all_branches(self):
        for t_obj in self.mainframe.project.transitions:
            for branch in t_obj.obj3d._branches:
                color = (_BRANCH_FIT if _fits(self.diameter, branch)
                         else _BRANCH_NO_FIT)
                branch.identify(color)
                self._highlighted.append(branch)

    def _clear_highlights(self):
        for b in self._highlighted:
            b.identify(None)
        self._highlighted.clear()

    def start(self, mouse_pos: _point.Point):
        self.is_active = True
        self._highlight_all_branches()

    def hover(self, mouse_pos: _point.Point):
        pass

    def finalize(self, mouse_pos: _point.Point):
        if not self.is_active:
            return

        from ..objects.objects3d.transition import Branch as _Branch3D
        selected = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)

        self._clear_highlights()
        self.is_active = False

        if not isinstance(selected, _Branch3D):
            return
        if not _fits(self.diameter, selected):
            return

        if self.is_start:
            old_point_id = self.target.db_obj.start_position3d_id
        else:
            old_point_id = self.target.db_obj.stop_position3d_id

        branch_p_id = int(selected.db_obj.position3d.db_id[:-2])

        if old_point_id == branch_p_id:
            return

        _repoint_all_references(self.ptables, old_point_id, branch_p_id)
        _delete_point_if_orphaned(self.ptables, old_point_id)

        self.mainframe.editor3d.Refresh(False)


# ══════════════════════════════════════════════════════════════════════════════
# RouteThroughBundleHandler
# Drag an existing wire endpoint onto a bundle endpoint.
#
# Cleanup model
# -------------
# When the wire's endpoint Point is replaced by the bundle's Point, the
# old Point may be orphaned — nothing references it.  We also need to
# repoint any other wires or layouts that shared the old Point, because
# they were connected at that junction and should now connect at the
# bundle endpoint instead.
#
# _repoint_all_references updates every table in one pass.
# _delete_point_if_orphaned checks all tables before deleting.
# ══════════════════════════════════════════════════════════════════════════════

class RouteThroughBundleHandler(_handler_base.HandlerBase):

    def __init__(self, mainframe: '_ui.MainFrame',
                 target: _wire.Wire, is_start: bool):
        super().__init__(mainframe, None)
        self.target          = target
        self.is_start        = is_start
        self._hovered_bundle = None

    def hover(self, mouse_pos: _point.Point):
        selected = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)

        if not isinstance(selected, _bundle.Bundle):
            if self._hovered_bundle is not None:
                self._hovered_bundle.identify(None)
                self._hovered_bundle = None
            return

        if selected != self._hovered_bundle:
            if self._hovered_bundle is not None:
                self._hovered_bundle.identify(None)
            selected.identify(_HOVER_HIGHLIGHT)
            self._hovered_bundle = selected

    def start(self, mouse_pos: _point.Point):
        self.is_active = True

    def finalize(self, mouse_pos: _point.Point):
        if not self.is_active:
            return

        if self._hovered_bundle is not None:
            self._hovered_bundle.identify(None)
            self._hovered_bundle = None

        selected = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)

        self.is_active = False

        if not isinstance(selected, _bundle.Bundle):
            return

        # Determine which bundle endpoint the wire should connect to.
        # Use the bundle endpoint nearest to the wire's current position.
        if self.is_start:
            old_point_id = self.target.db_obj.start_position3d_id
            wire_p = self.target.obj3d.start_position
        else:
            old_point_id = self.target.db_obj.stop_position3d_id
            wire_p = self.target.obj3d.stop_position

        bundle_start_id = int(selected.obj3d.start_position.db_id[:-2])
        bundle_stop_id  = int(selected.obj3d.stop_position.db_id[:-2])

        bundle_start_p = selected.obj3d.start_position
        bundle_stop_p  = selected.obj3d.stop_position

        dist_start = (wire_p - bundle_start_p).length
        dist_stop  = (wire_p - bundle_stop_p).length

        bundle_p_id = (bundle_start_id
                       if dist_start <= dist_stop
                       else bundle_stop_id)

        if old_point_id == bundle_p_id:
            return

        # Repoint every object that referenced the old Point so they all
        # connect at the bundle endpoint instead — covers other wire
        # segments, wire layouts, and anything else at that junction.
        # Orphan deletion is deferred to cleanup.py (runs on exit / on demand).
        _repoint_all_references(self.ptables, old_point_id, bundle_p_id)

        self.mainframe.editor3d.Refresh(False)


# ══════════════════════════════════════════════════════════════════════════════
# RoutedWireHandler
#
# Draw a new wire that passes through bundles and transitions.
#
# Bundle traversal
# ----------------
# Clicking any section of a bundle walks the full chain via
# _walk_bundle_chain, returning the ordered list of every boundary Point
# ID from one true end to the other.  The handler commits one invisible
# wire segment per consecutive pair, and one invisible wire layout at
# each intermediate Point so wire length follows the actual routed path.
#
# Transition traversal
# --------------------
# Clicking a branch sphere shows remaining branches as exit candidates.
# Clicking an exit branch commits one invisible segment entry→exit,
# both Points shared with the transition branches.
#
# Visibility rule
# ---------------
# Outside any container  → is_visible3d=True
# Inside bundle          → is_visible3d=False  (+ invisible wire layouts)
# Inside transition      → is_visible3d=False
# ══════════════════════════════════════════════════════════════════════════════

class RoutedWireHandler(_handler_base.HandlerBase):

    _IDLE     = 'idle'
    _ROUTING  = 'routing'
    _IN_TRANS = 'in_transition'

    def __init__(self, mainframe: '_ui.MainFrame', part_id: int):
        super().__init__(mainframe, part_id)
        self._state        = self._IDLE
        self._segments     = []
        self._seg_start_id = None
        self._entry_branch = None
        self._preview      = None
        self._highlighted  = []

    def _clear_highlights(self):
        for obj in self._highlighted:
            obj.identify(None)
        self._highlighted.clear()

    def _commit(self, stop_id: int, visible: bool):
        if self._seg_start_id is not None:
            self._segments.append((self._seg_start_id, stop_id, visible))
        self._seg_start_id = stop_id

    def _commit_chain(self, ordered_point_ids: list):
        for i in range(len(ordered_point_ids) - 1):
            self._segments.append(
                (ordered_point_ids[i], ordered_point_ids[i + 1], False))
        self._seg_start_id = ordered_point_ids[-1]

    def _delete_preview(self):
        if self._preview is not None:
            self._preview.delete()
            self._preview = None

    def _wire_od(self) -> float:
        od = self.mainframe.project.gtables.wires_table[self.part_id].od_mm
        return float(od) if od else 1.0

    def _highlight_exit_branches(self, diameter: float, exclude_branch):
        for t_obj in self.mainframe.project.transitions:
            for branch in t_obj.obj3d._branches:
                if branch is exclude_branch:
                    branch.identify(None)
                    continue
                color = (_BRANCH_FIT if _fits(diameter, branch)
                         else _BRANCH_NO_FIT)
                branch.identify(color)
                self._highlighted.append(branch)

    def start(self, mouse_pos: _point.Point):
        if self._state == self._IDLE:
            self._begin(mouse_pos)
        elif self._state == self._ROUTING:
            self._handle_routing_click(mouse_pos)
        elif self._state == self._IN_TRANS:
            self._handle_exit_click(mouse_pos)

    def hover(self, mouse_pos: _point.Point):
        if self._state == self._ROUTING:
            self._update_preview(mouse_pos)

    def finalize(self, mouse_pos: _point.Point):
        if self._state == self._ROUTING:
            self._place_all(mouse_pos)

    def _begin(self, mouse_pos: _point.Point):
        pos = _utils.get_position_on_focal_plane(mouse_pos, self.camera)
        if pos is None:
            return
        p3d = self.ptables.pjt_points3d_table.insert(pos.x, pos.y, pos.z)
        self._seg_start_id = p3d.db_id
        self._state = self._ROUTING
        self.is_active = True

    def _update_preview(self, mouse_pos: _point.Point):
        target = _get_wire_or_bundle(mouse_pos, self.camera)
        if target is not None:
            pos, _ = _utils.get_closest_point_on_wire(
                mouse_pos, self.camera, target)
        else:
            pos = _utils.get_position_on_focal_plane(mouse_pos, self.camera)
        if pos is None:
            return

        if self._preview is None:
            end_p3d = self.ptables.pjt_points3d_table.insert(
                pos.x, pos.y, pos.z)
            wire_db = _insert_wire(
                self.ptables, self.part_id, None,
                self._seg_start_id, end_p3d.db_id, visible=True)
            self._preview = _wire.Wire(self.mainframe, wire_db)
            self._preview.obj3d._material.alpha = 0.5
            self.mainframe.add_object(self._preview)
        else:
            end_pos = self._preview.obj3d.stop_position
            delta = pos - end_pos
            end_pos += delta

    def _handle_routing_click(self, mouse_pos: _point.Point):
        from ..objects.objects3d.transition import Branch as _Branch3D

        selected = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)

        diameter = self._wire_od()

        if isinstance(selected, _bundle.Bundle):
            chain = _walk_bundle_chain(selected.db_obj, self.ptables)

            # Orient chain: entry end is the one closer to current wire pos
            cur_p     = self.ptables.pjt_points3d_table[self._seg_start_id].point
            end_a     = self.ptables.pjt_points3d_table[chain[0]].point
            end_b     = self.ptables.pjt_points3d_table[chain[-1]].point
            dist_a    = (cur_p - end_a).length if cur_p else float('inf')
            dist_b    = (cur_p - end_b).length if cur_p else float('inf')

            if dist_b < dist_a:
                chain = list(reversed(chain))

            # Visible segment from previous point to bundle entry
            self._commit(chain[0], visible=True)

            # Invisible segments through every bundle section
            self._commit_chain(chain)

            self._delete_preview()

        elif isinstance(selected, _Branch3D):
            if not _fits(diameter, selected):
                return

            entry_p_id = int(selected.db_obj.position3d.db_id[:-2])
            self._commit(entry_p_id, visible=True)

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
        if not _fits(self._wire_od(), selected):
            return

        self._clear_highlights()

        exit_p_id = int(selected.db_obj.position3d.db_id[:-2])
        self._commit(exit_p_id, visible=False)

        self._entry_branch = None
        self._state = self._ROUTING

    def _place_all(self, mouse_pos: _point.Point):
        self._delete_preview()
        self._clear_highlights()

        target = _get_wire_or_bundle(mouse_pos, self.camera)
        if target is not None:
            pos, _ = _utils.get_closest_point_on_wire(
                mouse_pos, self.camera, target)
        else:
            pos = _utils.get_position_on_focal_plane(mouse_pos, self.camera)

        if pos is None or self._seg_start_id is None:
            self._reset()
            return

        end_p3d = self.ptables.pjt_points3d_table.insert(pos.x, pos.y, pos.z)
        self._commit(end_p3d.db_id, visible=True)

        # Insert all wire segments.  For invisible runs through bundles,
        # also insert invisible wire layouts at every intermediate Point
        # so wire length calculations follow the actual routed path.
        intermediate_layout_points = set()

        for i, (start_id, stop_id, visible) in enumerate(self._segments):
            wire_db = _insert_wire(
                self.ptables, self.part_id, None,
                start_id, stop_id, visible=visible)
            self.mainframe.project.add_wire(
                _wire.Wire(self.mainframe, wire_db))

            if not visible:
                # If the next segment is also invisible, stop_id is an
                # intermediate bundle layout Point — needs a wire layout
                if (i + 1 < len(self._segments) and
                        not self._segments[i + 1][2]):
                    intermediate_layout_points.add(stop_id)

        for point_id in intermediate_layout_points:
            layout_db = self.ptables.pjt_wire_layouts_table.insert(
                point_id=point_id)
            layout_db.is_visible3d = False
            layout_db.is_visible2d = False
            self.mainframe.project.add_wire_layout(
                _wire_layout.WireLayout(self.mainframe, layout_db))

        self._reset()

    def _reset(self):
        self._stat = self._IDLE
        self._segments = []
        self._seg_start_id = None
        self._entry_branch = None
        self._preview = None
        self.is_active = False
