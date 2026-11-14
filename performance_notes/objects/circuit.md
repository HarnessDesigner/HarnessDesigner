# harness_designer/objects/circuit.py

Circuit(ObjectBase) — the wrapper for a pjt_circuits row: a logical grouping, not a placed part. It has an inert placeholder view in every editor (objects_3d/circuit.py, objects_schematic/circuit.py, objects_pegboard/circuit.py; added 2026-10-25, built like a Note that was never placed there: no vbo/position/angle/scale/material, not visible, obb None).

Nested loops (cost grows with the product of the sizes; check the sizes are small): `Circuit.highlight` (lines 677-702, depth 2).

Status: static read of the code only. Nothing here has been profiled.
