# harness_designer/ui/widgets/cad_datasheet_ctrl.py

## `CADDatasheetPreviewCtrl.paintEvent` - rescales the whole page on every paint
`paintEvent` calls `self._pixmap.scaled(self.size(), KeepAspectRatio, SmoothTransformation)` each time Qt repaints. Smooth scaling of a full datasheet page is the costliest step in this control, and a repaint happens on resize, on focus changes, and whenever the parent window is exposed. The result depends only on the pixmap and the widget size, so caching the scaled pixmap and rebuilding it on `set_pixmap`, `set_pdf`, and resize would leave the paint path a single `drawPixmap`.

## `CADDatasheetPreviewCtrl.set_pdf` - renders the page synchronously on the UI thread
`set_pdf` calls `document.render(page, render_size)` on the UI thread and converts the result with `QPixmap.fromImage`. The render cost grows with the page size and the target size, and it runs each time a page is set. Rendering off the UI thread, or caching the rendered page per `(document, page, size)`, would stop it from blocking input.

## `CADDatasheetPreviewCtrl.set_svg` / `set_dxf` - renders into a new QImage per call
Both allocate a `QImage` of the target size and render into it. These run on set, not on paint, so the cost is per selection rather than per frame. No change is needed unless selection changes are frequent.

## PDF pane navigation and zoom - cheap
The navigation and zoom handlers only set view state on `QPdfView`, which does its own page caching. No extra work is done here.
