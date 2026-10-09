# harness_designer/gl/canvas_base/mouse_handler_base.py

## Line 261-270 (`_pick_object`) and 272-327 (`_dispatch_to_active_handler`) — one full picker call per mouse event that needs a pick
`_pick_object` calls `object_picker.find_object`, which runs the coarse bounds-pool ray test and then a per-candidate `hit_test_step3` (see `object_picker.md`). Whether this runs on every mouse move depends on the caller; if it runs for hover as well as press, each mouse move pays the full pick. Gating the pick on press and drag start only, and reusing the last result while the cursor stays within a small radius, would cut that cost.

## Line 255-258, 591, 756, 985 - probes removed
The getattr/hasattr checks on the mouse path are gone. The rotation-ring check reads `_active_handler` directly after a None guard, the top-down zoom branch reads an explicit `camera.is_top_down` flag, and the cavity pick calls `try_pick_cavity`, which every view now answers (BaseVar returns None by default). None of these changes the per-event cost.

## Line 647 (signal dispatch) - name lookup on every mouse event, now a dict
Dispatch now goes through `CanvasBase.event_signal`, a dict built once in `__init__`, instead of `getattr` by name. The dict lookup is cheap, so this is a correctness change (a missing name raises KeyError, not AttributeError), not a speed change.
