# Type-conflict fix checklist

Flat list only, from TYPE_CONFLICT_REPORT.md sections 1a/1c/1d/1e. Mark the ones to fix.

| Fix? | File | Line | Current type | Should be |
|------|---|---|---|---|
| [x]  | `harness_designer/database/create_database/accessories.py` | 79 | `str` | `str \| None` |
| [x]  | `harness_designer/database/create_database/colors.py` | 100 | `bytes` | `int \| None -- give it its own name instead` |
| [x]  | `harness_designer/database/create_database/manufacturers.py` | 175 | `bytes` | `int \| None -- give it its own name instead` |
| [x]  | `harness_designer/database/create_database/platings.py` | 98 | `bytes` | `int \| None -- give it its own name instead` |
| [x]  | `harness_designer/database/create_database/seal_types.py` | 115 | `bytes` | `int \| None -- give it its own name instead` |
| [x]  | `harness_designer/database/create_database/splice_types.py` | 96 | `bytes` | `int \| None -- give it its own name instead` |
| [x]  | `harness_designer/database/create_database/splices.py` | 225 | `bytes` | `bytes \| None` |
| [x]  | `harness_designer/database/create_database/temperatures.py` | 96 | `bytes` | `int \| None -- give it its own name instead` |
| [x]  | `harness_designer/database/create_database/terminals.py` | 208 | `bytes` | `bytes \| None` |
| [x]  | `harness_designer/database/create_database/wire_service_loops.py` | 24 | `bytes` | `bytes \| None` |
| [x]  | `harness_designer/database/db_connectors/sqlite_connector/connector.py` | 407 | `list[Any]` | `list[Any] \| None` |
| [x]  | `harness_designer/database/global_db/boot.py` | 130 | `str` | `str \| None` |
| [x]  | `harness_designer/database/global_db/cover.py` | 131 | `str` | `str \| None` |
| [x]  | `harness_designer/database/global_db/cpa_lock.py` | 131 | `str` | `str \| None` |
| [x]  | `harness_designer/database/global_db/housing.py` | 147 | `str` | `str \| None` |
| [x]  | `harness_designer/database/global_db/housing.py` | 148 | `str` | `str \| None` |
| [x]  | `harness_designer/database/global_db/housing.py` | 149 | `str` | `str \| None` |
| [x]  | `harness_designer/database/global_db/mixins/color.py` | 99 | `list[list[Any]]` | `list[list[Any]] \| None` |
| [x]  | `harness_designer/database/global_db/mixins/resource.py` | 276 | `dict[Any, Any]` | `dict[Any, Any] \| None` |
| [x]  | `harness_designer/database/global_db/seal.py` | 135 | `str` | `str \| None` |
| [x]  | `harness_designer/database/global_db/terminal.py` | 159 | `str` | `str \| None` |
| [x]  | `harness_designer/database/global_db/tpa_lock.py` | 131 | `str` | `str \| None` |
| [x]  | `harness_designer/database/global_db/used_part.py` | 59 | `bytes` | `bytes \| None` |
| [x]  | `harness_designer/database/global_db/used_part.py` | 60 | `bytes` | `bytes \| None` |
| [x]  | `harness_designer/database/project_db/mixins/color.py` | 87 | `list[list[Any]]` | `list[list[Any]] \| None` |
| [x]  | `harness_designer/database/project_db/mixins/smooth.py` | 50 | `int` | `bool \| None -- give it its own name instead` |
| [x]  | `harness_designer/database/project_db/pjt_bases.py` | 445 | `str` | `str \| None` |
| [x]  | `harness_designer/database/project_db/pjt_bundle_layout.py` | 153 | `bytes` | `bytes \| None` |
| [x]  | `harness_designer/database/project_db/pjt_bundle_layout.py` | 154 | `bytes` | `bytes \| None` |
| [x]  | `harness_designer/database/project_db/pjt_cpa_lock.py` | 221 | `DefaultStoredValue` | `DefaultStoredValueType` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 212 | `bytes` | `bytes \| None` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 213 | `bytes` | `bytes \| None` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 867 | `list[Any]` | `list[Any] \| None` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 942 | `dict[Any, Any]` | `dict[Any, Any] \| None` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 1029 | `list[Any]` | `list[Any] \| None` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 1136 | `DefaultStoredValue` | `DefaultStoredValueType` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 1199 | `DefaultStoredValue` | `DefaultStoredValueType` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 1262 | `DefaultStoredValue` | `DefaultStoredValueType` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 1322 | `DefaultStoredValue` | `DefaultStoredValueType` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 1385 | `DefaultStoredValue` | `DefaultStoredValueType` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 1448 | `DefaultStoredValue` | `DefaultStoredValueType` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 1511 | `DefaultStoredValue` | `DefaultStoredValueType` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 1758 | `DefaultStoredValue` | `DefaultStoredValueType` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 2307 | `list[Any]` | `list[Any] \| None` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 2308 | `list[Any]` | `list[Any] \| None` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 2608 | `list[Any]` | `list[Any] \| None` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 2609 | `list[Any]` | `list[Any] \| None` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 2840 | `list[Any]` | `list[Any] \| None` |
| [x]  | `harness_designer/database/project_db/pjt_housing.py` | 2841 | `list[Any]` | `list[Any] \| None` |
| [x]  | `harness_designer/database/project_db/pjt_seal.py` | 144 | `bytes` | `bytes \| None` |
| [x]  | `harness_designer/database/project_db/pjt_tpa_lock.py` | 137 | `bytes` | `bytes \| None` |
| [x]  | `harness_designer/database/project_db/pjt_transition.py` | 501 | `list[Any]` | `list[Any] \| None` |
| [x]  | `harness_designer/database/project_db/pjt_transition.py` | 502 | `list[Any]` | `list[Any] \| None` |
| [x]  | `harness_designer/database/project_db/pjt_transition.py` | 570 | `list[Any]` | `list[Any] \| None` |
| [x]  | `harness_designer/database/project_db/pjt_transition.py` | 571 | `list[Any]` | `list[Any] \| None` |
| [x]  | `harness_designer/database/project_db/pjt_wire_layout.py` | 139 | `bytes` | `bytes \| None` |
| [x]  | `harness_designer/database/project_db/pjt_wire_layout.py` | 140 | `bytes` | `bytes \| None` |
| [x]  | `harness_designer/gl/canvas_base/camera_base.py` | 952 | `numpy.float64 (np.linalg.norm() result, via target_distance = current_distance - float(delta))` | `float -- wrap as target_distance = float(current_distance - float(delta)) so it stays a plain float through both branches` |
| [x]  | `harness_designer/gl/canvas_base/camera_base.py` | 954 | `numpy.float64 (np.linalg.norm() result, via target_distance = current_distance - float(delta))` | `float -- wrap as target_distance = float(current_distance - float(delta)) so it stays a plain float through both branches` |
| [x]  | `harness_designer/gl/canvas_base/camera_base.py` | 1009 | `numpy.ndarray (move_dir, from self._right/self._forward) divided by numpy.float64 (mdn, from np.linalg.norm())` | `unreliable as reported -- self._right/self._forward are declared bare (self._right = None) in __init__ with no annotation, then reassigned real np.ndarray values elsewhere (same declared-twice issue as section 2a); annotate self._right/self._forward: np.ndarray \| None = None first, then recheck this line` |
| [x]  | `harness_designer/gl/canvas_base/camera_base.py` | 1085 | `numpy.ndarray (move_dir, from self._right/self._up) divided by numpy.float64 (mdn, from np.linalg.norm())` | `unreliable as reported -- same self._right/self._up declared-twice root cause as line 1009; fix the attribute annotations first, then recheck` |
| [x]  | `harness_designer/gl/canvas_base/canvas_base.py` | 350 | `str` | `str \| None` |
| [x]  | `harness_designer/gl/canvas_base/canvas_base.py` | 368 | `QSize` | `QSize \| None` |
| [x]  | `harness_designer/handlers/wire_routing_drag.py` | 322 | `str` | `str \| None` |
| [x]  | `harness_designer/objects/objects_3d/wire_service_loop.py` | 310 | `list[Any]` | `list[Any] \| None` |
| [x]  | `harness_designer/objects/objects_3d/wire_service_loop.py` | 311 | `list[Any]` | `list[Any] \| None` |
| [x]  | `harness_designer/objects/objects_3d/wire_service_loop.py` | 312 | `list[Any]` | `list[Any] \| None` |
| [x]  | `harness_designer/objects/objects_pegboard/wire.py` | 880 | `tuple[Any, ...]` | `tuple[Any, ...] \| None` |
| [x]  | `harness_designer/objects/objects_pegboard/wire.py` | 880 | `bytes` | `bytes \| None` |
| [x]  | `harness_designer/objects/objectsvar/base_var.py` | 145 | `ndarray[Any, Any]` | `ndarray[Any, Any] \| None` |
| [x]  | `harness_designer/plugins/register.py` | 24 | `str` | `str \| None` |
| [x]  | `harness_designer/process/image_process.py` | 222 | `dict[Any, Any]` | `dict[Any, Any] \| None` |
| [x]  | `harness_designer/process/image_process.py` | 376 | `dict[Any, Any]` | `dict[Any, Any] \| None` |
| [x]  | `harness_designer/process/image_process.py` | 386 | `dict[Any, Any]` | `dict[Any, Any] \| None` |
| [x]  | `harness_designer/ray_tracing/dialog.py` | 56 | `QImage` | `QImage \| None` |
| [x]  | `harness_designer/ray_tracing/dialog.py` | 167 | `QImage` | `QImage \| None` |
| [x]  | `harness_designer/ui/mainframe.py` | 555 | `str` | `str \| None` |
| [x]  | `harness_designer/ui/object_browser/objectbrowser.py` | 590 | `QTreeWidgetItem` | `QTreeWidgetItem \| None` |
| [x]  | `harness_designer/ui/object_browser/objectbrowser.py` | 591 | `QTreeWidgetItem` | `QTreeWidgetItem \| None` |
| [x]  | `harness_designer/ui/object_browser/objectbrowser.py` | 592 | `QTreeWidgetItem` | `QTreeWidgetItem \| None` |
| [x]  | `harness_designer/ui/object_browser/objectbrowser.py` | 593 | `QTreeWidgetItem` | `QTreeWidgetItem \| None` |
| [x]  | `harness_designer/ui/object_browser/objectbrowser.py` | 594 | `QTreeWidgetItem` | `QTreeWidgetItem \| None` |
| [x]  | `harness_designer/ui/object_browser/objectbrowser.py` | 595 | `QTreeWidgetItem` | `QTreeWidgetItem \| None` |
| [x]  | `harness_designer/ui/object_browser/objectbrowser.py` | 596 | `QTreeWidgetItem` | `QTreeWidgetItem \| None` |
| [x]  | `harness_designer/ui/object_browser/objectbrowser.py` | 597 | `QTreeWidgetItem` | `QTreeWidgetItem \| None` |
| [x]  | `harness_designer/ui/object_browser/objectbrowser.py` | 598 | `QTreeWidgetItem` | `QTreeWidgetItem \| None` |
| [x]  | `harness_designer/ui/object_browser/objectbrowser.py` | 599 | `QTreeWidgetItem` | `QTreeWidgetItem \| None` |
| [x]  | `harness_designer/ui/object_browser/objectbrowser.py` | 600 | `QTreeWidgetItem` | `QTreeWidgetItem \| None` |
| [x]  | `harness_designer/ui/object_browser/objectbrowser.py` | 601 | `QTreeWidgetItem` | `QTreeWidgetItem \| None` |
| [x]  | `harness_designer/ui/object_browser/objectbrowser.py` | 602 | `QTreeWidgetItem` | `QTreeWidgetItem \| None` |
| [x]  | `harness_designer/ui/object_browser/objectbrowser.py` | 603 | `QTreeWidgetItem` | `QTreeWidgetItem \| None` |
| [x]  | `harness_designer/ui/object_browser/objectbrowser.py` | 604 | `QTreeWidgetItem` | `QTreeWidgetItem \| None` |
| [x]  | `harness_designer/ui/widgets/foldpanelbar.py` | 1186 | `QColor` | `QColor \| None` |
| [x]  | `harness_designer/ui/widgets/stipple_ctrl.py` | 42 | `QWidget` | `QWidget \| None` |
| [x]  | `harness_designer/utils/mesh_surface_picker.py` | 161 | `int` | `int \| None` |
| [x]  | `harness_designer/utils/mesh_surface_picker.py` | 728 | `int` | `int \| None` |
| [x]  | `harness_designer/utils/model_utils.py` | 154 | `list[list[Any]]` | `ndarray[tuple[int,...], dtype[int32]] -- give it its own name instead` |
