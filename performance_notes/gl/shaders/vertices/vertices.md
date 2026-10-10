# harness_designer/gl/shaders/vertices/vertices.py

## Line 12-39 (`compile_program`) — one-time compile per canvas
Three unclosed file reads, three compiles and a link, run once per canvas start-up. Not on the frame path. Same note as `edges.md` about closing the file handles.
