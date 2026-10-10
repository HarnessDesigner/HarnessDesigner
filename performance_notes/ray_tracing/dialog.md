# harness_designer/ray_tracing/dialog.py

## Line 203-232 (`RayTracingDialog.update_progress`) — converts and paints each chunk
Each chunk of the rendered image is pasted into the image and the preview is refreshed. The image copy and the pixmap conversion run on the UI thread for every chunk, so the chunk count sets how often the UI does this work. Batching chunks, or rate-limiting the refresh to a timer, would cut the UI-thread cost. The method returns whether the user cancelled, which the renderer checks between chunks.

## Line 233-257 (`_update_ui`) — refresh of the progress widgets
Updates the labels, the bar and the preview. Runs from `update_progress`. Each refresh is several widget updates on the UI thread.

## Line 127-200 (`on_settings`, `on_mfb1`, `on_mfb2`) — dialog actions
Open the settings dialog or start a render. Run on a button press. Fine.

**Typing and Qt imports (fixed in this pass):** the dialog now imports PySide6 as modules (`QtCore`, `QtGui`, `QtWidgets`) instead of individual names. Signatures are typed; `get_image` returns `QImage | None` through the `_Union` alias.
