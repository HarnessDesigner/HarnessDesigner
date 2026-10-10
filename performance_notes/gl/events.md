# harness_designer/gl/events.py

## Line 1-116 — module constants
Plain string constants for each event name and button bitmask. No runtime cost beyond import.

## Line 118-237 (`_GLEventBase`) — accessors
One object per event, with getters and setters. Each call is a method call; events are created per user action, not per frame. Fine.

## Line 245-286 (`GLCameraEvent.from_canvas`) — per camera move
Reads the cursor position, checks it is inside the canvas, and reads the mouse-button state. It runs on every camera move (see `canvas_base/camera_base.md`). When the cursor is outside the canvas it returns `None`, so the camera signal is not emitted and the hover refresh is skipped. That is probably intended (no hover target outside the canvas), but it means keyboard zoom with the mouse outside the canvas does not refresh the active handler.

## Line 296-end — event subclasses (`GLCameraEvent`, `GLEvent`, `GLObjectEvent`, `GLKeyEvent`)
Each has a set of `Get*`/`Set*` pairs and modifier helpers. `GLKeyEvent` has about 20 setters called per key event (see `key_handler.md`). The cost is a few dozen attribute writes per key event. Fine.

**Typing/import:** lines 19-20 import `Union as _Union` twice (`from typing import Union as _Union` and again in `from typing import TYPE_CHECKING, Union as _Union`). Harmless, but it should be one import. Flagged for cleanup.
