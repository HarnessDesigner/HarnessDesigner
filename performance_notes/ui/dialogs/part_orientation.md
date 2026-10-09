# harness_designer/ui/dialogs/part_orientation.py

## `_recenter_model` / `_update_forward_up` - run on every rotation button press
Each rotation button calls `_recenter_model()` and `_update_forward_up()`. Both are cheap: `_recenter_model` does one centroid calculation and one position update, and `_update_forward_up` calls `_obb_face_for_direction` twice, which runs a short loop over 8 corners. Button presses are human-paced, so nothing here needs to change.

## `_obb_face_for_direction` - Python loop over 8 corners
The function rotates the 8 OBB corners with a list comprehension (`q @ c` per corner) and then loops over 3 axes and 2 faces in Python. The work is a few dozen small operations per call and runs twice per rotation, so it is not a hot path. If it ever moves into a per-frame path, vectorise the rotation as one matrix product.

## `MeshStatsOverlay` - static text, built once
The overlay sets its text once at construction, as its docstring says, and does not repaint per frame. Its `eventFilter` repositions it only on resize. This is the cheap design; no change.

## `_flush_and_invalidate_vbo` - runs on accept, reject and close
Runs once per dialog close. It writes the working angle and position back to the database (several writes) and then evicts the pooled VBO. These are one-time costs per dialog session.

## Typing change in this pass
`vbo.id` was guarded with `hasattr(vbo, 'id')`. It is now `isinstance(vbo, _vbo.PooledVBOHandler)`, since `id` is only assigned in `PooledVBOHandler` (`gl/vbo.py`). Behaviour is the same for both handler types.
