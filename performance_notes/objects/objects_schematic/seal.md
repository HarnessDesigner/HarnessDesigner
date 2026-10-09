# harness_designer/objects/objects_schematic/seal.py

`render` is overridden as a no-op (`pass`), so this view draws nothing for the object and has no per-frame cost. Only the `render` override was checked; the rest of the file (about 40 lines of constructor and wiring) was not reviewed for performance. Re-check if `render` gains a body.
