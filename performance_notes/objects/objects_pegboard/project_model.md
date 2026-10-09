# harness_designer/objects/objects_pegboard/project_model.py

`render` is overridden as a no-op (`pass`), so this view draws nothing for the object and has no per-frame cost. Only the `render` override was checked; the rest of the file was not reviewed for performance. Re-check if `render` gains a body.
