# harness_designer/ui/editor_circuit/bitmaps.py

## `placeholder_connector_pixmap` - not cached
Called from `_build_row` once for the From connector and once per distinct To connector for every circuit. Each call creates a new `QPixmap`, painter, gradient and `QFont`. The output depends only on `(name, height)`, so a small cache keyed on those would avoid redrawing the same connector for every row that shares it. Because connector images never load (README bug 2), this is the only connector path in use today.

## `scale_housing_pixmap` - cheap, but unreachable today
A single `scaledToHeight` call. It is only reached when a housing has an image, which never happens now (README bug 2).

## The wire pictures are not made here any more (2026-10-25)
The wire swatch painter (`make_wire_pixmap`, its cache and `conductor_color`) was removed: the pictures come from the image module's generator (see `editor_widget.md`).
