# harness_designer/drag_handlers/editor_3d/wire_snap.py

`SnapProbeSet` builds and queries wire end anchors (`_wire_end_anchors`, which calls the 3D `wire_end_anchors`). If that runs on every move while the probe set is live, it is a per-move cost. Check the caller before changing anything. Not profiled.
