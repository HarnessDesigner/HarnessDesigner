# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Bundle-snapping transition placement for the 3D editor.

Ported from ``handlers.transition_handler.AddTransitionHandler`` --
unlike Splice/Bundle, the preview here is repositioned/rebuilt in place
during hover (``Transition.obj3d.build()``, not delete-and-recreate) --
only the final commit swaps it out, deleting the preview and building a
brand-new, fully-resolved ``Transition`` facade separately, exactly as
the original did. The two other classes still living in
``handlers.transition_handler`` (``RouteThroughTransitionHandler``,
``RouteThroughBundleHandler``) and ``RoutedWireHandler`` are not
reachable from any menu or toolbar entry anywhere in the app -- dead
code, not part of this migration.
"""

from typing import TYPE_CHECKING

import numpy as np

from ...gl.canvas_base import interaction as _interaction
from ...geometry import point as _point
from ...objects import bundle as _bundle
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ... import objects as _objects


class Transition(_base.AddHandlerBase):
    """Bundle-snapping transition placement -- see the module docstring."""

    @_check_types.do
    def __init__(
        self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase", part_id: bytes,
        part, highlight_material
    ):
        super().__init__(canvas, target)

        self.mainframe = canvas.mainframe
        self.camera = canvas.camera

        self._part_id = part_id
        self._part = part
        self._highlight_material = highlight_material
        self._snapped_bundle: "_bundle.Bundle | None" = None
        self._finalized = False

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    @_check_types.do
    def __call__(
        self, last_pos, current_pos, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        if self._finalized:
            return False

        if interaction_type is _interaction.MouseInteraction.CANCEL:
            self.cancel()
            self._finalized = True
            return True

        if interaction_type is _interaction.MouseInteraction.MOVE:
            self.hover(current_pos)
            return True

        if interaction_type is _interaction.MouseInteraction.LEFT_UP and not had_motion:
            self._finalize(current_pos)
            return True

        return False

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
        from ...handlers import transition_handler as _transition_handler
        from ... import utils as _utils

        bundle = _transition_handler._find_bundle(  # NOQA
            mouse_pos, self.camera, self.mainframe.project)

        if bundle is None:
            if self._snapped_bundle is not None:
                self._snapped_bundle.identify(None)
                self._snapped_bundle = None

            self.target.obj3d.is_visible = False
            return

        trunk_global = self._part.branches[0]
        conc_wires = bundle.db_obj.wires
        if _transition_handler.effective_diameter(
                conc_wires, trunk_global) > float(trunk_global.max_dia):
            if self._snapped_bundle is not None:
                self._snapped_bundle.identify(None)
                self._snapped_bundle = None

            self.target.obj3d.is_visible = False
            return

        raw_pos, _, _ = _utils.get_closest_point_on_wire_endpoint(
            mouse_pos, self.camera, bundle)
        if not isinstance(raw_pos, _point.Point):
            raw_pos = _point.Point(*raw_pos)

        pos = self.target.obj3d.position
        pos += raw_pos - pos

        if bundle is not self._snapped_bundle:
            if self._snapped_bundle is not None:
                self._snapped_bundle.identify(None)

            bundle.identify(self._highlight_material)
            _transition_handler._set_angle_from_bundle(self.target.db_obj, bundle)  # NOQA
            self.target.obj3d.build()
            self._snapped_bundle = bundle

        self.target.obj3d.is_visible = True

    @_check_types.do
    def _finalize(self, mouse_pos: _point.Point) -> None:
        from ... import utils as _utils

        if self._snapped_bundle is None:
            return

        bundle = self._snapped_bundle
        self._snapped_bundle.identify(None)
        self._snapped_bundle = None

        raw_pos, is_at_endpoint, endpoint = _utils.get_closest_point_on_wire_endpoint(
            mouse_pos, self.camera, bundle)
        if not isinstance(raw_pos, _point.Point):
            raw_pos = _point.Point(*raw_pos)

        self._commit(bundle, raw_pos, is_at_endpoint, endpoint)
        self._finalized = True

    @_check_types.do
    def _commit(self, bundle: "_bundle.Bundle", snap_pos: _point.Point,
                is_at_endpoint: bool, endpoint) -> None:
        from ...geometry import angle as _angle
        from ...handlers import transition_handler as _transition_handler
        from ...objects import transition as _transition_facade
        from ...objects import wire_layout as _wire_layout

        project = self.mainframe.project
        ptables = project.ptables
        global_branches = self._part.branches
        trunk_global = global_branches[0]
        output_globals = global_branches[1:]

        conc_wires = bundle.db_obj.wires
        output_assignments = _transition_handler.assign_wires_to_branches(
            conc_wires, output_globals)

        self.target.delete()
        self.target = None

        if is_at_endpoint:
            ep_pt = (bundle.obj3d.start_position if endpoint == 'start'
                     else bundle.obj3d.stop_position)
            trunk_point_id = ep_pt.db_id[:-2]
        else:
            pt_db = ptables.pjt_points3d_table.insert(
                float(snap_pos.x), float(snap_pos.y), float(snap_pos.z))
            trunk_point_id = pt_db.db_id

        center_db = ptables.pjt_points3d_table.insert(
            float(snap_pos.x), float(snap_pos.y), float(snap_pos.z))
        init_angle = _angle.Angle()
        name = f'{self._part.manufacturer.name} {self._part.part_number}'
        transition_db = ptables.pjt_transitions_table.insert(
            self._part_id, name, center_db.db_id, init_angle)
        _transition_handler._set_angle_from_bundle(transition_db, bundle)  # NOQA

        trunk_dia = _transition_handler.effective_diameter(conc_wires, trunk_global)
        trunk_br_db = ptables.pjt_transition_branches_table.insert(
            trunk_global.db_id, transition_db.db_id, trunk_point_id, 1, trunk_dia)
        _transition_handler._create_branch_concentric(  # NOQA
            ptables, trunk_br_db, conc_wires, trunk_dia)

        trunk_wl_db = ptables.pjt_wire_layouts_table.insert(trunk_point_id)
        trunk_wl_db.is_visible3d = False
        project.add_wire_layout(_wire_layout.WireLayout(self.mainframe, trunk_wl_db))

        branch_records = []
        for i, (g_br, assigned) in enumerate(zip(output_globals, output_assignments)):
            br_pt_db = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
            br_dia = _transition_handler.effective_diameter(assigned, g_br)
            br_db = ptables.pjt_transition_branches_table.insert(
                g_br.db_id, transition_db.db_id, br_pt_db.db_id, i + 2, br_dia)
            _transition_handler._create_branch_concentric(  # NOQA
                ptables, br_db, assigned, br_dia)
            branch_records.append((br_db, br_pt_db.db_id, assigned))

        transition_obj = _transition_facade.Transition(self.mainframe, transition_db)

        for br_db, br_pt_id, assigned in branch_records:
            wl_db = ptables.pjt_wire_layouts_table.insert(br_pt_id)
            wl_db.is_visible3d = False
            project.add_wire_layout(_wire_layout.WireLayout(self.mainframe, wl_db))

            for cw in assigned:
                pjt_wire = cw.wire
                ptables.pjt_wires_table.insert(
                    pjt_wire.part_id, pjt_wire.name, pjt_wire.circuit_id,
                    trunk_point_id, br_pt_id,
                    None, None, False, False, None, None, False)

        if is_at_endpoint:
            end = endpoint
        else:
            # Per the "a Transition never forks a bundle" rule, the
            # bundle shrinks to end exactly at the transition's own
            # trunk point rather than splitting into two rows -- whatever
            # lay past that point is abandoned (see the original
            # handler's own comment, preserved for the "why" here).
            from ...handlers import bundle_layout_handler as _blh

            snap_np = np.array([float(snap_pos.x), float(snap_pos.y), float(snap_pos.z)])
            split_idx = _blh._find_insertion_index(bundle, snap_np)  # NOQA

            layouts_table = ptables.pjt_bundle_layouts_table
            for point in bundle.db_obj.waypoints3d[split_idx:]:
                for row in layouts_table.select('id', position3d_id=point.db_id):
                    layout_db = layouts_table[row[0]]
                    layout_obj = layout_db.get_object()
                    if layout_obj is not None:
                        layout_obj.delete()
                    else:
                        layout_db.delete()

                point.delete()

            bundle.db_obj.stop_position3d_id = trunk_point_id
            bundle.obj3d.set_stop_position(pt_db.point)
            end = 'stop'

        transition_obj.add_bundle(bundle, end, 1)
        project.add_transition(transition_obj)

    @_check_types.do
    def cancel(self) -> None:
        if self._snapped_bundle is not None:
            self._snapped_bundle.identify(None)
            self._snapped_bundle = None

        if self.target is not None:
            self.target.delete()
            self.target = None

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self.cancel()
            self._finalized = True
