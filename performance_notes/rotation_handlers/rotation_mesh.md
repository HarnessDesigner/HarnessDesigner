# harness_designer/rotation_handlers/rotation_mesh.py

## Line 146-170 (torus mesh builder) — nested loops over the torus grid
Builds the ring's torus with a loop over the major and tube segments. Runs once per ring build. Cost grows with the square of the segment count; the default counts are small.
