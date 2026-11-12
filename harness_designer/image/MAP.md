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
is actually imported until that specific attribute is touched. The `images` sub-loader additionally gets `build_wire(row)` (CHANGED 2026-11-05), the ONE entry point for wire pictures: pass a catalog `Wire`, a project `PJTWire` or a project `PJTWireServiceLoop` and it imports `wire_images` on first use and returns `wire_images.build_image(row)`, which picks the image class from the row. There is no cache or compositing in the loader any more (the old three-colour `build_wire` and `build_wire_loop` are gone); the classes cache by look.
A `TYPE_CHECKING`-only block declares `ip`/`cursors`/`icons`/`images` as plain
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

#### wire_images.py

The layered cable previews, one `Image` subclass per kind of cable, each assembling its own picture from the PNGs in
`images/` (the `twisted2_*`, `twisted3_*`, `cable_*` and `coax_*` layers, made by `diagnostics/make_wire_layers.py`; the
layout numbers at the top of this file, where the jacket and braid end and where the conductors come out, have to match that
script): `build_image(row)` (the only public function; `ImageLoader.images.build_wire` calls it: a catalog `Wire` or `PJTWire` gives `WireImage` for one unshielded conductor, `CoaxImage` for wire type Coaxial, otherwise `TwistedWireImage` / `CableImage` from the `wire_conductors` rows, or `None` for Ribbon or a wire whose colours are unknown; a `PJTWireServiceLoop` gives `WireLoopImage` in the colours of its `part`; anything else raises `TypeError`; the database classes are imported inside the function so this module stays loadable alone), `WireImageRow` / `ConductorImageRow` (NamedTuples: what `build_image` needs to draw a catalog wire when the caller has plain query results and no `Wire` row, as the parts editor's list does; the attribute names are `Wire`'s, with `wire_type_name` for `wire_type.name` and a `db` field for the colour and plating tables; `WireImageRow.from_query` builds one from the query's columns, and `build_image` accepts it like a row), `WireImage(primary, stripe or None, core)` (a single conductor, 400 x 100), `WireLoopImage(primary, stripe or None)` (the service loop's ring, 200 x 200, from `loop_layer1..9`), `TwistedWireImage(conductors, jacket_color=None, shield_color=None)` (a pair or triple; one base, stripe and
bare-core layer per conductor, so any conductor can be striped or not, already cut where the wires cross so order does
not matter), `CableImage(conductors, jacket_color, shield_color=None)` (one to three straight conductors, each the plain wire
image scaled down and lengthened to the left under the jacket) and `CoaxImage(jacket, shield, dielectric, core)`.
`conductors` is a list of `(base, stripe or None, core)` `Color` tuples; more than three draw the first three. A braid with no
jacket uses `cable_shield_bare`. **Everything else in the file is private**, and the module is imported on demand
(`from ...image import wire_images`), NOT by `__init__.py`, because the classes subclass `Image`. **Caching:** the classes use the `_CableImageMeta` metaclass (the `ColorMeta` / `_EntrySingleton` pattern: `__call__` returns the image already made for the same key; a per-class `_instances` dict and an `RLock`). A class defines `_cache_key(...)` with the signature of its `__init__` and returns colour NAMES. The cache holds STRONG references and is never emptied (user decision 2026-11-04: an image freed while the user scrolls a list of wires would be drawn again when the row comes back, and the memory is small). KEYED BY LOOK, NOT BY PART: the key is the colours (conductors, stripes, cores), the jacket and the shield, never the size, series or part number, so an 18 AWG and a 28 AWG pair of the same colours are one image. Measured on the generated catalog (2026-11-04): 4,986 distinct cable pictures for 87,670 cables (36 for the 43,120 M27500 cables, 4,950 for the 44,550 colour pairs) and 303 for the 33,572 single wires. An image holds only its compressed PNG (7 to 21 KB, a twisted pair about 18 KB, not the 160 KB of raw RGBA), so the whole set is about 90 MB if every look were ever shown, and a screenful is under a megabyte. If that ever matters, bound the dict (least recently used) rather than going back to weak references. The layers are read from the `images` folder next to the file
(`_layer`, kept with `lru_cache`, shared, never drawn on), not through the lazy loader. Layers are combined with true alpha
compositing, not `Image.__add__` (a masked paste). Imports only `check_types`, `Image` and `utils` from the package, so a
scratch script can load it under a throwaway package name (do NOT import `harness_designer` for that, it opens the real
config; PySide6 may also be missing, so stub `PySide6.QtGui`).

**A lead's part (2026-11-11):** `build_image` of a `PJTWire` whose part is a `WireConductor` (a lead of a cable's conductor) draws that conductor, `_conductor_image`: one wire in the conductor's colour, stripe and core. It raised `TypeError: cannot draw a WireConductor` for the circuit editor before.

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
