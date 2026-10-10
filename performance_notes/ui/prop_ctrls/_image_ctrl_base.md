# harness_designer/ui/prop_ctrls/_image_ctrl_base.py

## `ImageCtrl.get_image` - blocking network fetch on the UI thread
For an `http` path the control calls `time.sleep(0.01)` and then `_resources.requests_get(path, timeout=1000)` synchronously. The timeout value is passed through as written (the unit is whatever `requests_get` uses). While the request is pending, the whole window stops repainting and accepting input. Any slow host or stalled connection freezes the editor. Moving the fetch to a worker thread and setting the pixmap on completion would remove the stall. The `time.sleep(0.01)` only adds 10 ms per fetch and can go with it.

## `ImageCtrl.get_image` - rebuilds the extension map on every call
`extensions = {'.' + v: k for k, v in self.file_types.items()}` runs on each call. `file_types` only changes through `SetFileTypes`, so the map could be built there. The cost is small (a few entries), so this is minor.

## `_no_image_pixmap` - regenerated on every use
Each call resizes `_image.images.no_image` with `resize(100, 100)`, converts it to RGBA, copies the bytes and builds a `QPixmap`. It runs in `__init__` for every control and again on every failed load. The result is constant, so a module-level cache (created on first use) would remove this work. This is a cheap, UI-thread-only cost per control.

## `_load_pil` - PIL decode and LANCZOS resize on the UI thread
`Image.open(path).convert('RGBA').resize((100, 100), LANCZOS)` runs synchronously when a saved path is set, on every control construction and on every `SetValue` that reloads. For a large source image this decode-and-resize is the main cost. A thumbnail cache keyed by `(path, mtime)` would avoid repeating it when the same property is rebuilt.

## `_set_pdf` - opens and renders a PDF on the UI thread
Each call creates a `QPdfDocument`, loads the file, renders page 0 and closes it. A large or slow PDF blocks the UI for the duration of the render. The control is only constructed for PDF-enabled properties, so the cost is limited to those, but the same file is re-rendered every time it is set.

## `_pil_to_pixmap` - copies the image bytes once more than needed
`convert('RGBA')` followed by `tobytes` copies the full image before the `QImage` wraps it. For thumbnails at 100x100 this is negligible. It becomes relevant only if the function is ever used on full-size images.
