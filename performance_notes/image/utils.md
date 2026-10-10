# harness_designer/image/utils.py

## Line 12-57 (`bytes_data_2_pil_image`, `pil_image_2_png_bytes`, `bytes_data_2_qpixmap`) — decode and encode helpers
PNG decode and encode through in-memory buffers. Called from `Image` on every access (see `__init__.md`). The cost is the PNG codec, not the buffer handling.

## Line 60-88 (`pil_image_2_qpixmap`, `pil_image_2_qimage`) — raw RGBA conversion
Converts the image to RGBA, copies the raw bytes, and wraps them in a `QImage`. The `pil_image_2_qimage` path copies the buffer again (`qimg.copy()`) so the result does not depend on the PIL buffer's lifetime. Needed for correctness.

## Line 109-121 (`rotate_pil_image`) — bicubic rotation with expand
Bicubic resampling is the slowest of the standard resample filters. It is fine for icons. Not changed.

## Line 124-144 (`pil_image_2_qcursor`) — conversion per call
Builds a pixmap, then a cursor. Called from `Image.cursor`, which has no caching (see `__init__.md`).
