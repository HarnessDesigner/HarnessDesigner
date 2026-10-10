# harness_designer/image/__init__.py

## Line 60-64 and 66-95 (`Image.png_data`, `pil`, `pixmap`, `disabled_pixmap`, `cursor`) — the file is re-read and re-decoded on every access
`png_data` reads the backing PNG from disk on every call when the image was not built from in-memory bytes (line 63-64). `pil`, `pixmap`, `disabled_pixmap` and `cursor` each call `png_data` and decode again. A widget that reads `.pixmap` on every paint re-reads the file and re-decodes the PNG each time. `ImageLoader` caches the `Image` object, but not the decoded data.

Caching the PNG bytes (or the pixmap) on first use would remove the repeat cost. Not changed in this pass, because callers may depend on the current behaviour of always reading the latest file.

## Line 98-115 (`disabled_pixmap`) — per-access image pipeline
Converts the PIL image, splits channels, merges, converts to LA and back, halves alpha with a `point` lambda, then converts to a pixmap. Several full-image passes per access. Cache with the pixmap (see above) to avoid repeating it.

## Line 127-240 (`crop`, `resize`, `resize_keep_aspect`, `rotate`, `recolor`) — each returns a new `Image` backed by encoded PNG bytes
Every operation encodes the result as PNG and returns a new `Image` holding those bytes. The next operation decodes it again. Chains of operations therefore encode and decode at every step. `recolor` (line 214-240) also calls `Image.fromarray(arr, 'RGBA')`, whose `mode` argument is deprecated in recent Pillow releases. It works today; the mode can be given by the array's shape instead.

## Line 242-283 (`__or__`) — **probable layout bug (flagged, not changed)**
When the two images differ in height, `y_offset` is set to `w1`, the width of the first image (lines 267 and 274). Vertical placement is therefore driven by a horizontal size. The docstring says the intended layout is UNKNOWN, so this cannot be confirmed from the code alone. Check the callers before changing it.

## Line 285-305 (`__add__`) — one composite per call
Copies one image, pastes the other centred, and encodes. Fine on demand.

## Line 310-423 (`ImageLoader`) — lazy module-like loader
Creates the loader once at import (line 426) and caches each attribute on first access with `self.__dict__[item] = attr`. Each name is loaded once, so the disk and decode cost is paid once per name (but see the `png_data` note above for what happens on each later use). Sub-loaders are cached the same way.

**Reflection (fixed in this pass):** `__getattr__` used `hasattr`/`getattr` against the original module and `setattr` to cache loaded attributes. These now read `self.__original_module__.__dict__` and assign `self.__dict__[item]` directly, which is the same behaviour without reflection.

**Typing (fixed in this pass):** `Union` changed to the project's `Union as _Union` alias; `PySide6.QtGui` names now imported as `from PySide6 import QtGui`; `__getattr__` returns `Any`, since it returns whatever the module holds.

## Line 429-569 (`if TYPE_CHECKING:` namespaces) — type-checking stubs only
No runtime cost.
