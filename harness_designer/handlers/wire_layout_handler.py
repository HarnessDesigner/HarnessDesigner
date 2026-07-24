# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for adding wire layout points.
"""

import math
import numpy as np
from typing import TYPE_CHECKING

from . import handler_base as _handler_base
from ..geometry import point as _point
from ..geometry import line as _line
from ..gl.canvas3d import object_picker as _object_picker
from ..objects import wire_layout as _wire_layout
from ..objects import wire as _wire
from ..gl import materials as _materials
from .. import config as _config
from .. import color as _color


if TYPE_CHECKING:
    from ..gl.canvas3d import camera as _camera
    from .. import ui as _ui


Config = _config.Config.colors

_SNAP_THRESHOLD = 5.0


def _find_wire(
    mouse_pos: _point.Point,
    camera: "_camera.Camera",
    project
) -> "_wire.Wire | None":
    """Return the wire under the mouse, or the closest one within the snap threshold."""
    selected = _object_picker.find_object(
        mouse_pos, camera.objects_in_view, camera)

    if isinstance(selected, _wire.Wire):
        return selected

    world_pos = camera.get_position_on_focal_plane(mouse_pos).as_numpy
    best_wire = None
    best_dist_sq = _SNAP_THRESHOLD ** 2

    for w in project.wires:
        if not w.is_in_3dview:
            continue

        p1 = w.obj3d.start_position.as_numpy
        p2 = w.obj3d.stop_position.as_numpy
        seg = p2 - p1
        seg_len_sq = float(np.dot(seg, seg))
        if seg_len_sq < 1e-8:
            continue

        t = max(0.0, min(1.0, float(np.dot(world_pos - p1, seg)) / seg_len_sq))
        closest = p1 + t * seg
        dist_sq = float(np.sum((world_pos - closest) ** 2))

        if dist_sq < best_dist_sq:
            best_dist_sq = dist_sq
            best_wire = w

    return best_wire


def _create_wire_layout_at_endpoint(
    project,
    wire: "_wire.Wire",
    endpoint: str
) -> "_wire_layout.WireLayout":
    if endpoint == 'start':
        point = wire.obj3d.start_position
    else:
        point = wire.obj3d.stop_position

    coord_id = int(point.db_id[:-2])
    db_obj = project.ptables.pjt_wire_layouts_table.insert(coord_id)
    layout_obj = _wire_layout.WireLayout(project.mainframe, db_obj)
    project.add_wire_layout(layout_obj)

    return layout_obj


def _create_wire_layout_on_wire(
    project,
    wire: "_wire.Wire",
    position: _point.Point
) -> "_wire_layout.WireLayout":
    pos_db = project.ptables.pjt_points3d_table.insert(
        float(position.x), float(position.y), float(position.z))
    coord_id = pos_db.db_id

    db_obj = project.ptables.pjt_wire_layouts_table.insert(coord_id)

    # Split the wire (creates the two new pjt_wires rows referencing
    # coord_id as their shared endpoint) BEFORE constructing the
    # WireLayout object -- WireLayout.__init__ derives its diameter/
    # color from db_obj.attached_wires, which queries pjt_wires for
    # rows whose start/stop point matches coord_id. Constructing it
    # first would find nothing yet and silently fall back to the
    # hardcoded default (3.0mm, gray).
    _split_wire_at_point(project, wire, coord_id)

    layout_obj = _wire_layout.WireLayout(project.mainframe, db_obj)
    project.add_wire_layout(layout_obj)

    return layout_obj


def _split_wire_at_point(
    project,
    original_wire: "_wire.Wire",
    shared_coord_id: int
) -> tuple["_wire.Wire", "_wire.Wire"]:
    orig = original_wire.db_obj
    part_id = orig.part_id
    name = orig.name
    circuit_id = orig.circuit_id
    layer_id = orig.layer_id
    layer_view_point_id = orig.layer_view_position_id
    is_filler_wire = orig.is_filler_wire
    is_visible3d = orig.is_visible3d
    is_visible2d = orig.is_visible2d

    start_id = int(original_wire.obj3d.start_position.db_id[:-2])
    stop_id = int(original_wire.obj3d.stop_position.db_id[:-2])

    # wire1 keeps the original wire's own start point, so it inherits its
    # stripe_clip_start unchanged -- wire2 starts exactly where wire1 now
    # ends, so its stripe_clip_start is wire1's stripe_clip_start plus
    # wire1's own (freshly split) length. See objects.objects3d.wire.Wire
    # and gl.shaders.faces' stripeClipStart/stripeClipStop uniforms.
    wire1_stripe_clip_start = orig.stripe_clip_start

    wire1_db = project.ptables.pjt_wires_table.insert(
        part_id, name, circuit_id, start_id, shared_coord_id,
        None, None, is_visible3d, is_visible2d,
        layer_view_point_id, layer_id, is_filler_wire,
        stripe_clip_start=wire1_stripe_clip_start)

    p1 = wire1_db.start_position3d.as_numpy
    p2 = wire1_db.stop_position3d.as_numpy
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dz = p2[2] - p1[2]
    wire1_length = math.sqrt(dx * dx + dy * dy + dz * dz)
    wire2_stripe_clip_start = wire1_stripe_clip_start + wire1_length

    wire2_db = project.ptables.pjt_wires_table.insert(
        part_id, name, circuit_id, shared_coord_id, stop_id,
        None, None, is_visible3d, is_visible2d,
        layer_view_point_id, layer_id, is_filler_wire,
        stripe_clip_start=wire2_stripe_clip_start)

    wire1_obj = _wire.Wire(project.mainframe, wire1_db)
    wire2_obj = _wire.Wire(project.mainframe, wire2_db)

    # wire2 takes over the "back half" of the original wire's identity
    # (same stop point), so it inherits whatever wire came after the
    # original wire in the chain, if any -- and wire1 now continues
    # into wire2, same as the original wire continued into whatever
    # wire2 just inherited.
    wire2_obj.obj3d.sibling = original_wire.obj3d.sibling
    wire1_obj.obj3d.sibling = wire2_obj.obj3d

    project.add_wire(wire1_obj)
    project.add_wire(wire2_obj)

    # The original wire row is about to be deleted outright below (not
    # just re-pointed), so any wire marker attached to it via wire_id
    # would otherwise be orphaned -- still bound to the old start/stop
    # Points, with a wire_id that no longer resolves to any row. Move
    # each one onto whichever new half-segment it actually still sits
    # on (its own world position didn't change, only the wire data
    # model split around it).
    orig_start = original_wire.obj3d.start_position
    split_distance = _line.Line(orig_start, wire1_obj.obj3d.stop_position).length()

    for marker in project.wire_markers:
        if marker.db_obj.wire_id != orig.db_id:
            continue

        marker_distance = _line.Line(orig_start, marker.obj3d.position).length()
        new_wire = wire1_obj if marker_distance <= split_distance else wire2_obj

        marker.db_obj.wire_id = new_wire.db_obj.db_id
        marker.obj3d.rebind_wire(new_wire.db_obj)

    if project.mainframe.get_selected() is original_wire:
        original_wire.set_selected(False)
    original_wire.delete()

    return wire1_obj, wire2_obj


class AddWireLayoutHandler(_handler_base.HandlerBase):
    """Handle interactive placement of wire layout points along existing wires."""
    obj: _wire_layout.WireLayout = None

    def __init__(self, mainframe: "_ui.MainFrame"):
        """Initialize the handler and create the placement preview.

        :param mainframe: Main application frame that owns the editor and project state.
        :type mainframe: "_ui.MainFrame"
        """
        super().__init__(mainframe, None)

        self._highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.wire_highlight))

        self._snapped_wire: "_wire.Wire | None" = None

        pos_db = self.ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
        layout_db = self.ptables.pjt_wire_layouts_table.insert(pos_db.db_id)
        self.obj = _wire_layout.WireLayout(mainframe, layout_db)
        self.obj.obj3d.is_visible = False

    def hover(self, mouse_pos: _point.Point):
        """Snap the preview to the nearest wire and update its diameter and color.

        :param mouse_pos: Mouse position used for picking or preview updates.
        :type mouse_pos: _point.Point
        """
        wire = _find_wire(mouse_pos, self.camera, self.mainframe.project)

        if wire is None:
            self.obj.obj3d.is_visible = False
            if self._snapped_wire is not None:
                self._snapped_wire.identify(None)
                self._snapped_wire = None

            return

        raw_pos, _, _ = wire.obj3d.get_closest_endpoint(mouse_pos)

        if not isinstance(raw_pos, _point.Point):
            raw_pos = _point.Point(*raw_pos)

        pos = self.obj.obj3d.position
        pos += raw_pos - pos

        if wire is not self._snapped_wire:
            if self._snapped_wire is not None:
                self._snapped_wire.identify(None)

            wire.identify(self._highlight_material)

            diameter = wire.db_obj.part.od_mm
            scale = self.obj.obj3d.scale
            scale += _point.Point(diameter, diameter, diameter) - scale

            color = wire.db_obj.part.color.ui
            material = _materials.Plastic(color)
            self.obj.obj3d._material = material
            self.obj.obj3d._unselected_material = material

            self._snapped_wire = wire

        self.obj.obj3d.is_visible = True

    def release_capture(self) -> None:
        """Finalize placement: split the wire or attach to an endpoint.
        """
        if self._finalized:
            return

        if self._captured_position is None:
            return

        wire = self._snapped_wire
        if wire is None:
            return

        self._snapped_wire.identify(None)
        self._snapped_wire = None

        mouse_pos = self._captured_position
        raw_pos, is_at_endpoint, endpoint = wire.obj3d.get_closest_endpoint(mouse_pos)

        self._finalized = True

        if is_at_endpoint:
            if endpoint == 'start':
                wire.obj3d.start_position.attach(self.obj.obj3d.position)
            else:
                wire.obj3d.stop_position.attach(self.obj.obj3d.position)

            # .attach() only makes the delegator (this layout's own preview
            # point) track the wire endpoint live, in-memory, for this
            # session -- the layout's own DB row still stores its original
            # throwaway point's id. Repoint it to the wire endpoint's real
            # id (now what self.obj.obj3d.position.db_id reports, since a
            # delegator forwards db_id to its root) so the sharing survives
            # a reload instead of only existing as a live delegation.
            self.obj.db_obj.position3d_id = int(self.obj.obj3d.position.db_id[:-2])
        else:
            coord_id = int(self.obj.obj3d.position.db_id[:-2])
            _split_wire_at_point(self.mainframe.project, wire, coord_id)

        self.obj.obj3d.is_visible = True
        self.mainframe.project.add_wire_layout(self.obj)
        self.obj = None

    def cancel(self):
        """Cancel placement and clean up the preview."""
        if self._snapped_wire is not None:
            self._snapped_wire.identify(None)
            self._snapped_wire = None

        if self.obj is not None:
            self.obj.delete()
            self.obj = None
