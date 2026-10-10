# harness_designer/gl/canvas_base/key_handler.py

## Line 77-103 (`_process_key_event`) — list built eagerly on every lookup
The `KEY_MULTIPLES.get(...)` default argument is evaluated whether or not the key is in the table, so a fresh list (with an `ord(chr(...).upper())` call) is built even on a hit. It runs up to nine times per key event (one per binding group in `on_key_down`/`on_key_up`), so about nine small list builds per press. Cheap, but each press does more work than it needs to. Using `KEY_MULTIPLES.get(k)` with a fallback only on a miss would remove the extra work.

## Line 106-125 (`KeyHandler.__init__`) — one daemon thread per canvas, never stopped
Starts a `threading.Thread` for `_key_loop`. Nothing sets `_key_event` in this file, so the loop never exits. Every canvas that creates a `KeyHandler` leaves one thread running until the process ends. Three canvases means three threads for the life of the app. Not a CPU cost while idle (the loop waits 20 ms), but a leak. A `stop()` that sets `_key_event` would fix it, called from `cleanup`.

## Line 161-192 (`_key_loop`) — 50 Hz tick while any key is held
Every 20 ms the loop copies the held-key table under the lock, then posts one `CallAfter` per held key, then updates each key's speed factor under the lock again. Cost is proportional to the number of held keys, and the loop runs only while the table is non-empty in practice (it still ticks when empty, with an empty copy). An idle tick costs one lock acquire and one empty list, which is negligible.

## Line 194-272 (`on_key_up`) and 274-330 (`_send_event`) — per key event
`_send_event` calls `QCursor.pos()`, `mapFromGlobal`, `UnprojectPoint` (a matrix inverse path, see `camera_base.md`), and builds a `GLKeyEvent` with about 20 setter calls. This runs once per key press and once per key release, so it is fine. The nested `remove_from_queue` and `add_to_queue` functions are redefined on every call; that is one function object per event, negligible.

**Fragile comparison (flagged, not fixed):** line 325 compares `event_type is _events.EVT_GL_KEY_DOWN`. This is an identity check on strings. It works only because both sides are the same interned constant. `==` is the correct comparison and costs the same.

## Line 332-401 (`on_key_down`) — same lookup pattern as `on_key_up`
Same per-press cost as `on_key_up`.

## Line 403-568 (`_process_*_key` methods) — decorated with `@_debug.logfunc`, run at the tick rate
Each held key calls its `_process_*` method at 50 Hz (every 20 ms). Each of those methods is wrapped with `@_debug.logfunc`. Whatever `logfunc` does on each call (see `debug.py`) happens at that rate for every held key. If `logfunc` writes a log line when debugging is off, that is avoidable overhead on the most frequent path in this file. Needs a check of `debug.py` before changing; flagged.

The bodies loop over `keys` and read `self.config.<group>.<key>` in every `if` branch. Each attribute lookup is cheap, but the same config values are read four to six times per call. Caching the group config in a local at the top of each method would tidy this up.

**Typing gap:** the `*keys` parameters in `_process_*_key` and `_process_reset_key(*_)` are untyped. The annotation audit does not check `*args`/`**kwargs`, so these were missed. Left for the typing pass.
