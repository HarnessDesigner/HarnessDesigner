# harness_designer/shapes/helix.py

## Line 97-137 (`create`) — builds a helix through the CAD converter
Creates the helix solid with build123d and converts it to a mesh through `utils.convert_model_to_mesh`, which is the slow per-vertex Python copy described in `utils/model_utils.md`. Runs once per primitive.

**Typing (fixed in this pass):** `radius`, `length`, `pitch` are `float`.
