from typing import TYPE_CHECKING

from . import handler_base as _handler_base

from ..geometry import point as _point
from ..geometry import angle as _angle
from ..gl.canvas3d import object_picker as _object_picker
from ..gl import materials as _materials
from ..objects import wire as _wire
from ..objects import splice as _splice
from .. import utils as _utils


if TYPE_CHECKING:
    from ..gl.canvas3d import camera as _camera
    from .. import ui as _ui


def _get_wire_at_mouse(
    mouse_pos: _point.Point,
    camera: "_camera.Camera"
) -> _wire.Wire | None:

    """
    Check if mouse is over a wire object.

    Returns:
        Wire object if found, None otherwise
    """
    selected = _object_picker.find_object(mouse_pos, camera.objects_in_view, camera)

    if isinstance(selected, _wire.Wire):
        return selected

    return None


class AddSpliceHandler(_handler_base.HandlerBase):
    """
    Manages interactive splice placement on wires.

    Splices can ONLY be placed on wires and automatically:
    - Align with the wire's direction
    - Split the wire at the placement point
    - Inherit the wire's circuit

    Workflow:
    - Hover over a wire: wire highlights cyan, a semi-transparent preview
      splice tracks along the wire showing exact size and orientation
    - Click to place: wire is broken at the splice position, splice start
      and stop points share the resulting wire endpoint Points so the
      callback system keeps everything connected when the wire is moved
    """

    obj: _splice.Splice = None

    # Cyan wire highlight — distinct from the green used for compatibility
    WIRE_HIGHLIGHT = [0.0, 0.8, 1.0, 0.6]

    # Warm amber preview — reads clearly against the cyan wire highlight
    PREVIEW_COLOR = [1.0, 0.75, 0.2, 0.45]

    def __init__(self, mainframe: "_ui.MainFrame", part_id: int):
        super().__init__(mainframe, part_id)
        self.wire = None
        self._preview_material = _materials.Rubber(self.PREVIEW_COLOR)

    def _get_splice_length(self) -> float:
        part = self.mainframe.project.gtables.splices_table[self.part_id]
        return float(part.length) if part.length else 5.0

    def _make_preview_splice(
        self,
        position: _point.Point,
        wire_angle: _angle.Angle,
        circuit_id: int | None
    ) -> _splice.Splice:
        """
        Create a temporary preview splice at the given position and angle.
        Uses independent temporary points — the wire is NOT broken here.
        """
        splice_length = self._get_splice_length()
        direction = wire_angle.as_matrix_numpy[:, 2]
        half_length = splice_length / 2.0

        start_xyz = position.as_numpy - direction * half_length
        stop_xyz = position.as_numpy + direction * half_length
        branch_xyz = position.as_numpy

        start_p3d = self.ptables.pjt_points3d_table.insert(*start_xyz)
        stop_p3d = self.ptables.pjt_points3d_table.insert(*stop_xyz)
        branch_p3d = self.ptables.pjt_points3d_table.insert(*branch_xyz)

        db_obj = self.ptables.pjt_splices_table.insert(
            self.part_id,
            start_p3d.db_id,
            stop_p3d.db_id,
            branch_p3d.db_id,
            point2d_id=None,
            circuit_id=circuit_id
        )

        preview = _splice.Splice(self.mainframe, db_obj)
        preview.obj3d._material = self._preview_material

        self.mainframe.add_object(preview)

        return preview

    def _update_preview_position(
        self,
        position: _point.Point,
        wire_angle: _angle.Angle
    ):
        """
        Move the preview splice to a new position along the wire.
        Updates all three points without touching the wire geometry.
        """
        if self.obj is None:
            return

        splice_length = self._get_splice_length()
        direction = wire_angle.as_matrix_numpy[:, 2]
        half_length = splice_length / 2.0

        new_start = position.as_numpy - direction * half_length
        new_stop = position.as_numpy + direction * half_length
        new_branch = position.as_numpy

        cur_start = self.obj.obj3d.start_position
        cur_start += _point.Point(*new_start.tolist()) - cur_start

        cur_stop = self.obj.obj3d.stop_position
        cur_stop += _point.Point(*new_stop.tolist()) - cur_stop

        cur_branch = self.obj.obj3d.branch_position
        cur_branch += _point.Point(*new_branch.tolist()) - cur_branch

    def _delete_preview(self):
        """Remove the preview splice and its temporary DB rows."""
        if self.obj is not None:
            self.obj.delete()
            self.obj = None

    def hover(self, mouse_pos: _point.Point):
        """
        Track mouse over wires — highlight wire and show/update preview splice.
        The wire is never modified here.
        """
        wire = _get_wire_at_mouse(mouse_pos, self.camera)

        if wire is None:
            if self.wire is not None:
                self.wire.identify(None)
                self.wire = None

            self._delete_preview()
            return

        position, wire_angle = _utils.get_closest_point_on_wire(
            mouse_pos, self.camera, wire)

        if None in (position, wire_angle):
            if self.wire is not None:
                self.wire.identify(None)
                self.wire = None

            self._delete_preview()
            return

        if wire != self.wire:
            if self.wire is not None:
                self.wire.identify(None)

            wire.identify(self.WIRE_HIGHLIGHT)
            self.wire = wire

        if self.obj is None:
            self.obj = self._make_preview_splice(
                position, wire_angle, wire.db_obj.circuit_id)
        else:
            self._update_preview_position(position, wire_angle)

    def finalize(self, mouse_pos: _point.Point):
        """
        Place the splice on click.

        Removes the preview, breaks the wire at the splice centre position,
        and creates the real splice whose start/stop points share the wire
        segment boundary Points so the callback chain stays intact.
        """
        if not self.is_active:
            return

        self.hover(mouse_pos)

        if self.wire is None:
            self._delete_preview()
            return

        wire = self.wire
        position, wire_angle = _utils.get_closest_point_on_wire(
            mouse_pos, self.camera, wire)

        if None in (position, wire_angle):
            self._delete_preview()
            if self.wire is not None:
                self.wire.identify(None)
                self.wire = None
            return

        # Remove the preview before creating the real object
        self._delete_preview()

        if self.wire is not None:
            self.wire.identify(None)
            self.wire = None

        # ── Compute splice endpoint positions ────────────────────────────
        splice_length = self._get_splice_length()
        direction = wire_angle.as_matrix_numpy[:, 2]
        half_length = splice_length / 2.0

        start_xyz = position.as_numpy - direction * half_length
        stop_xyz = position.as_numpy + direction * half_length
        branch_xyz = position.as_numpy

        # ── Get original wire data ───────────────────────────────────────
        original_start_db_id = int(wire.obj3d.start_position.db_id[:-2])
        original_stop_db_id = int(wire.obj3d.stop_position.db_id[:-2])
        part_id = wire.db_obj.part_id
        circuit_id = wire.db_obj.circuit_id

        # ── Create splice points ─────────────────────────────────────────
        # start and stop are the wire-facing stubs — they become shared
        # boundary points with the two new wire segments so the callback
        # system keeps the splice pinned to the wire ends when moved
        splice_start_p3d = self.ptables.pjt_points3d_table.insert(*start_xyz)
        splice_stop_p3d = self.ptables.pjt_points3d_table.insert(*stop_xyz)
        branch_p3d = self.ptables.pjt_points3d_table.insert(*branch_xyz)

        splice_start_db_id = splice_start_p3d.db_id
        splice_stop_db_id = splice_stop_p3d.db_id

        # ── Create first wire segment: original start → splice start ─────
        wire1_db = self.ptables.pjt_wires_table.insert(
            part_id=part_id,
            circuit_id=circuit_id,
            start_point3d_id=original_start_db_id,
            stop_point3d_id=splice_start_db_id,
            start_point2d_id=None,
            stop_point2d_id=None,
            is_visible3d=True,
            is_visible2d=False,
            layer_view_point_id=None,
            layer_id=None,
            is_filler_wire=False
        )

        # ── Create second wire segment: splice stop → original stop ──────
        wire2_db = self.ptables.pjt_wires_table.insert(
            part_id=part_id,
            circuit_id=circuit_id,
            start_point3d_id=splice_stop_db_id,
            stop_point3d_id=original_stop_db_id,
            start_point2d_id=None,
            stop_point2d_id=None,
            is_visible3d=True,
            is_visible2d=False,
            layer_view_point_id=None,
            layer_id=None,
            is_filler_wire=False
        )

        wire1_obj = _wire.Wire(self.mainframe, wire1_db)
        wire2_obj = _wire.Wire(self.mainframe, wire2_db)

        self.mainframe.project.add_wire(wire1_obj)
        self.mainframe.project.add_wire(wire2_obj)

        wire.delete()

        # ── Create the real splice referencing the shared boundary points ─
        db_obj = self.ptables.pjt_splices_table.insert(
            self.part_id,
            splice_start_db_id,
            splice_stop_db_id,
            branch_p3d.db_id,
            point2d_id=None,
            circuit_id=circuit_id
        )

        splice = _splice.Splice(self.mainframe, db_obj)
        self.mainframe.project.add_splice(splice)

        self.is_active = False

    def start(self, mouse_pos: _point.Point):
        """First click activates placement; second click (finalize) places it."""
        if not self.is_active:
            wire = _get_wire_at_mouse(mouse_pos, self.camera)
            if wire is not None:
                self.is_active = True
        else:
            self.finalize(mouse_pos)
