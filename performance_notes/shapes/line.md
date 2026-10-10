# harness_designer/shapes/line.py

## Line 32-300 (`Line` setters and `_get_pixmap`) — the pixmap is rebuilt when the line changes
`width`, `color`, `stripe_color`, `p1` and `p2` each refresh the artist when set (see `_update_artist`, line 283). A cached pixmap (`_get_pixmap`, line 198) holds the drawn line and stripes. A drag that moves an endpoint sets `p1` or `p2` on every mouse move, so the pixmap is rebuilt on each move. Caching the pixmap per (width, colours, length) and invalidating only when those change would avoid most of the work.

**Typing (fixed in this pass):** Qt names are module-qualified (`QtGui`, `QtCore`) instead of individually imported. The setters return `None`; `_get_pixmap` returns `QtGui.QPixmap`; `is_added` returns `bool`.
