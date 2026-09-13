from ...geometry import point as _point
from ...handlers import snap_probe_set as _snap_probe_set


class SnapProbeSet(_snap_probe_set.SnapProbeSet):

    @staticmethod
    def _get_start_position(db_obj) -> dict[str, _point.Point]:
        return dict(position3d=db_obj.start_position3d)

    @staticmethod
    def _get_stop_position(db_obj) -> dict[str, _point.Point]:
        return dict(position3d=db_obj.stop_position3d)

    @staticmethod
    def _get_branch_position(db_obj) -> dict[str, _point.Point]:
        return dict(position3d=db_obj.branch_position3d)

    @staticmethod
    def _get_wire_position(db_obj) -> dict[str, _point.Point]:
        return dict(position3d=db_obj.wire_position3d)

    @staticmethod
    def _get_view_object(obj):
        return obj.obj3d

    @staticmethod
    def _wire_end_anchors(project, wire_obj):
        from . import wire as _wire_3d  # NOQA -- avoid a cycle at import time
        return _wire_3d.Wire.wire_end_anchors(project, wire_obj)
