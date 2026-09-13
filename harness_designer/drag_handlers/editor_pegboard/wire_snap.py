from ...geometry import point as _point
from ...handlers import snap_probe_set as _snap_probe_set


class SnapProbeSet(_snap_probe_set.SnapProbeSet):

    @staticmethod
    def _get_start_position(db_obj):
        return dict(position_pegboard=db_obj.start_position_pegboard)

    @staticmethod
    def _get_stop_position(db_obj):
        return dict(position_pegboard=db_obj.stop_position_pegboard)

    @staticmethod
    def _get_branch_position(db_obj):
        return dict(position_pegboard=db_obj.branch_position_pegboard)

    @staticmethod
    def _get_wire_position(db_obj):
        return dict(position_pegboard=db_obj.wire_position_pegboard)

    @staticmethod
    def _get_view_object(obj):
        return obj.objpegboard

    @staticmethod
    def _wire_end_anchors(project, wire_obj):
        # Always the 3D concrete Wire -- see
        # snap_probe_set.SnapProbeSet._wire_end_anchors's own docstring
        # (a project-wide topology fact, not a per-view rendering detail).
        from ...drag_handlers.editor_3d import wire as _wire_3d  # NOQA -- avoid a cycle at import time
        return _wire_3d.Wire.wire_end_anchors(project, wire_obj)
