# harness_designer/gl/canvas_schematic/canvas_window.py

## Line 21-46 (`CanvasWindow.__init__`, `add_preview_object`) — construction and one forwarding call
`__init__` builds the inner `Canvas` once. `add_preview_object` forwards to `Canvas.add_preview_object`, which runs when a wire is being drawn; it is one call per object added, not per frame. Nothing to gain.
