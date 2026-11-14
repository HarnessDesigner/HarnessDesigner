# harness_designer/splash_screen.py

Startup only. The costs are bounded by the splash's lifetime, but the splash sits in front of the load, so anything slow here is felt as slow startup.

## Line 45-123 (`Splash.__init__`) — the splash image is decoded and copied several times
The PNG is opened with Pillow, converted to RGBA, turned into bytes (`img.tobytes`), wrapped in a `QImage`, then `qimage.copy()` is called before `QPixmap.fromImage`. The `.copy()` is needed because `QImage` does not own the Python `bytes` buffer, so it is not waste, but at peak three copies of the image exist at once (PIL image, raw bytes, QImage copy) plus the pixmap. They are released when `__init__` returns; the splash PNG is small, so this is a one-time spike of a few MB. Loading it with `QPixmap(path)` directly would skip Pillow and two copies, at the cost of whatever the `convert('RGBA')` normalisation was guarding against (check the PNG's mode first). Low value.

## Line 302-356 (`Splash.draw`) — a new QPixmap, QPainter and QFont per status message
Every `SetText`/progress update allocates a full-size transparent pixmap, repaints the background image, bar and text, then replaces `_render_pixmap`. The loader calls `set_progress` per item, so on a long load this is a redraw per step. That is cheap for a splash a few hundred pixels wide. If progress updates ever come per file (hundreds per second), throttle to a change in whole percent. The static background could be cached in its own pixmap and only the bar and text redrawn; that trades one extra pixmap of memory for less drawing per update, and only pays off if update counts grow.

## Line 203-208 (`flush`), 359-368 (`_do_refresh`) — `QApplication.processEvents()` on every refresh
`processEvents` re-enters the event loop from inside the loader's handoff. It keeps the splash responsive but also lets any other queued event (user input, timers) run in the middle of startup. Not a speed problem; it is a re-entrancy risk to keep in mind.
