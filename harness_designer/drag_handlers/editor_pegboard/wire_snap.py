# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ...geometry import point as _point
from ...handlers import snap_probe_set as _snap_probe_set


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire as _pjt_wire
    from ...objects import project as _project
    from ...objects import wire as _wire_object


class SnapProbeSet(_snap_probe_set.SnapProbeSet):

    @staticmethod
    def _get_start_position(db_obj: "_pjt_wire.PJTWire") -> dict[str, _point.Point]:
        return dict(position_pegboard=db_obj.start_position_pegboard)

    @staticmethod
    def _get_stop_position(db_obj: "_pjt_wire.PJTWire") -> dict[str, _point.Point]:
        return dict(position_pegboard=db_obj.stop_position_pegboard)

    @staticmethod
    def _get_branch_position(db_obj: "_pjt_wire.PJTWire") -> dict[str, _point.Point]:
        return dict(position_pegboard=db_obj.branch_position_pegboard)

    @staticmethod
    def _get_wire_position(db_obj: "_pjt_wire.PJTWire") -> dict[str, _point.Point]:
        return dict(position_pegboard=db_obj.wire_position_pegboard)

    @staticmethod
    def _get_view_object(obj: "_wire_object.Wire"):
        return obj.objpegboard

    @staticmethod
    def _wire_end_anchors(project: "_project.Project", wire_obj: "_wire_object.Wire"):
        # Always the 3D concrete Wire -- see
        # snap_probe_set.SnapProbeSet._wire_end_anchors's own docstring
        # (a project-wide topology fact, not a per-view rendering detail).
        from ...drag_handlers.editor_3d import wire as _wire_3d  # NOQA -- avoid a cycle at import time
        return _wire_3d.Wire.wire_end_anchors(project, wire_obj)
