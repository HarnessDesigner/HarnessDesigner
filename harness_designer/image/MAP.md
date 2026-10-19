## FILES

#### __init__.py

`Image` — wraps a PNG asset (by path or in-memory bytes) and converts it on demand: `.pil`/`.pil_image`
(PIL, RGBA), `.pixmap`/`.disabled_pixmap` (Qt, the latter greyscaled with halved opacity for disabled UI
states), `.cursor` (Qt, centered), plus `crop()`/`resize()`/`resize_keep_aspect()`/`rotate()`/`recolor()`
(RGB channel replace, alpha preserved) and `__add__`/`__or__` compositing — each returning a new `Image`.
`ImageLoader` is a dynamic, lazy stand-in for this module and every subdirectory under it: on first access
of an attribute it checks for a matching subdirectory (wrapped as a nested `ImageLoader`) or a matching
`<name>.png` (wrapped as an `Image`), caches the result on itself, and raises `AttributeError` otherwise —
done to save memory by only loading icons/images actually used, rather than eagerly loading the whole
`image/` tree at import time. The top-level loader replaces this module itself in `sys.modules`, which is
why `harness_designer.image.icons.camera` works like a normal nested-module attribute even though nothing
is actually imported until that specific attribute is touched. The `images` sub-loader additionally gets a
`build_wire(primary_color, stripe_color, conductor_color)` method (cached by color triple) that composites
`wire_base`/`wire_stripe`/`wire_conductor`/`wire_shadow` PNGs, recolored per the given `Color` objects, into
one wire-preview `Image`. A `TYPE_CHECKING`-only block declares `ip`/`cursors`/`icons`/`images` as plain
classes purely so IDEs/type-checkers see concrete attribute names for assets that are otherwise only ever
discovered dynamically at runtime.

#### icon_128x128.png

The application icon at 128x128 (window/taskbar icon, installer icon, etc. — see the other `icon_*` sizes
below for the same asset at other resolutions).

#### icon_16x16.png

The application icon at 16x16.

#### icon_256x256.png

The application icon at 256x256.

#### icon_32x32.png

The application icon at 32x32.

#### icon_64x64.png

The application icon at 64x64.

#### large_splash.png

The startup splash screen image, large size (presumably for higher-DPI/larger displays — see
`small_splash.png` below for the other size).

#### small_splash.png

The startup splash screen image, small size.

#### utils.py

Stateless PIL/Qt conversion helpers `Image`'s properties/methods above are built from:
`bytes_data_2_pil_image`/`pil_image_2_png_bytes` (PNG bytes ↔ PIL `Image`, always normalized to RGBA on
decode), `bytes_data_2_qpixmap`/`pil_image_2_qpixmap`/`pil_image_2_qimage` (→ Qt), `resize_pil_image`
(Lanczos, aspect-preserving when height is omitted), `rotate_pil_image` (bicubic, transparent fill), and
`pil_image_2_qcursor` (defaults the hotspot to the image center).

## FOLDERS

#### cursors/

Custom Qt cursor PNGs (move/rotate/resize handles, pointer, grab/hand, etc.) loaded lazily as `Image`s via
`ImageLoader` and converted to `QCursor` through `utils.pil_image_2_qcursor`.

#### electrical/

Schematic symbol icons for electronic components (diode variants, transistors, relays, LED, photoresistor,
solar cell, data latch, etc.) — not referenced anywhere in `CODEBASE_MAP.md`'s `image/` section, so likely
feeds the schematic editor's component palette. See its own `MAP.md` for specifics.

#### icons/

The bulk of the app's UI toolbar/menu icons (move/rotate/scale gizmo icons, align/flip tools, connector/
terminal/seal/wire glyphs, lock/unlock, zoom, etc.) — the largest asset subdirectory here (~88 files).

#### images/

General-purpose images: header banners, a "no image" placeholder, numbered `download_N` icons, and the
`wire_base`/`wire_stripe`/`wire_conductor`/`wire_shadow` layer PNGs `ImageLoader.build_wire()` (in
`__init__.py`) composites into per-color wire previews.

#### ip/

IP-rating icon overlays (`IP0X`…`IP6X`, `IPX0`…`IPX9`/`IPX9K`, `IPXX`) used to show a connector/housing's
ingress-protection rating. Note `IPX2.PNG` is uppercase-extension, unlike every sibling `.png` — worth
checking case-sensitivity assumptions if an `ip` lookup ever fails only on that one entry.
