# harness_designer/gl/shaders/faces/faces.py

## Line 12-39 (`compile_program`) — file reads and compile once per canvas
Same pattern as `edges.md`: three unclosed `open(...).read()` calls, three compiles and a link, run once per canvas start-up. Not on the frame path. Using `with` blocks would release the file handles promptly.
