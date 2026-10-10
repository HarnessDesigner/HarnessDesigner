# harness_designer/gpu/nvidia/backend.py

## Line 22-189 (`NvidiaBackend.__init__`) — roughly twenty nvapi queries per detection
Every metric is one `try` block around an nvapi attribute read. A detection makes around twenty driver calls, plus one per display port and per display for the EDID and timing reads. Everything is read once and stored; nothing is polled. The cost is driver round-trips at detection time.

The display loop (line 133-187) calls `display.get_timing(0, 0, 0)` for each display. Each call is a driver round-trip. If the display list is large, the loop cost grows with the number of connected displays.

No functional issues found. Each failure is caught and leaves the field at `None`, which matches the base-class convention.

**Typing (fixed in this pass):** `__init__` returns `None`.
