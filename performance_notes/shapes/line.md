# harness_designer/shapes/line.py

## Line 24-310 (`Line` setters and `_get_pixmap`) — the pixmap is rebuilt when the line changes
`width`, `color`, `stripe_color`, `p1` and `p2` each refresh the artist when set (see `_update_artist`, line 283). A cached pixmap (`_get_pixmap`, line 198) holds the drawn line and stripes. A drag that moves an endpoint sets `p1` or `p2` on every mouse move, so the pixmap is rebuilt on each move. Caching the pixmap per (width, colours, length) and invalidating only when those change would avoid most of the work.
