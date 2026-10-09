# harness_designer/objects/objects_3d/note.py

## Line 185-206 (`Note.refresh_canvas_registration`) — O(N) remove+add on lock/unlock
`remove_object` and `add_object` each scan the canvas's full object list. The
docstring explains this is acceptable because it runs only on user-triggered
lock/unlock and on arena growth. That reasoning holds. The camera-move path
(`shapes/text.py`'s `_CameraTrackingArena`, updated by
`gl/canvas_3d/canvas.py:152`'s `_on_camera_moved_for_notes`) is vectorized
across all tracked notes with no per-note Python loop, which is the right
design for 1000+ notes. No change recommended.

## Line 208-220 (`_start_camera_tracking`) — called once per tracked note, not per frame
Delegates to `Text.enable_camera_tracking`, which registers the note into the
arena. Runs at construction and on unlock, not per frame.

## Line 109-120 (`Note._delete`) — calls `super()._delete()`, which is fine
Deletion is not on a hot path.
