# harness_designer/ui/widgets/foldpanelbar.py

A collapsible accordion container (a port of a wx control). 56 KB of custom Qt paint code.

## Line 1265-1291 (`FoldPanelItem.paintEvent`) and 566-614 (`CaptionBar.paintEvent`) — a `QPainter` per paint and a `QPen` per separator
Each paint makes a `QPainter`, and `FoldPanelItem.paintEvent` makes one `QPen` per separator inside its loop (line 1279). A paint is a few hundred microseconds at most and panels have few separators, so this is not a bottleneck; hoisting the pen out of the loop is a one-line cleanup. `CaptionBar.paintEvent` creates a `QColor` and a `QPen` per paint; caching them on the bar (a few hundred bytes) would remove that.

## Line 546-563 (`CaptionBar.sizeHint`) — a `QFontMetrics` per call
Qt calls `sizeHint` during every layout pass. A `QFontMetrics` is cheap to build, and the result could be cached until the font changes.
