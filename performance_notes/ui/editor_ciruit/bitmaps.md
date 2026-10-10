# harness_designer/ui/editor_ciruit/bitmaps.py

## `make_wire_pixmap` - one QPixmap and QPainter per distinct wire key
Each miss creates a `QPixmap` at the requested size, a `QPainter`, and about 15 draw calls. Nested `_cylinder_gradient` closures are redefined per call (they are not hoisted). The render is CPU-bound and happens once per distinct key, so the cost is bounded by the number of distinct wire colour and width combinations, not by the number of paints.

## `WIRE_PIXMAP_CACHE` - the key includes width and height, so it grows with resizing
`cached_wire_pixmap` keys on `(primary, stripe, material, width, height)`. The width comes from the live column width in `WireDelegate.paint`, so each distinct column width during a resize adds a full set of entries. Entries are dropped only when `EditorCircuitPanel.refresh()` runs. Rendering at one fixed height and scaling to width, or quantising the width, would bound the cache to the distinct colour combinations.

## `placeholder_connector_pixmap` - not cached
Called from `_build_row` once for the From connector and once per distinct To connector for every circuit. Each call creates a new `QPixmap`, painter, gradient and `QFont`. The output depends only on `(name, height)`, so a small cache keyed on those would avoid redrawing the same connector for every row that shares it. Because connector images never load (README bug 2), this is the only connector path in use today.

## `scale_housing_pixmap` - cheap, but unreachable today
A single `scaledToHeight` call. It is only reached when a housing has an image, which never happens now (README bug 2).

## `conductor_color` - linear scan over 11 entries per call
Substring match over the colour table on every call. It is called once per `make_wire_pixmap` miss, so the cost is negligible.
