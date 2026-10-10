# harness_designer/bounds/manager.py

Holds one `View` per editor (3D, schematic, peg-board), each with an AABB pool, an OBB pool and a segment pool. The objects are created once and only reset when a project unloads, so nothing here runs per frame or per move. No change.
