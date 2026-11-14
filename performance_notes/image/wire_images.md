# harness_designer/image/wire_images.py

Builds the preview pictures of wires, cables, coax and service loops by alpha-compositing PNG layers (`build_image` is the entry point; `images.build_wire(row)` calls it). Called when a wire row or a part list needs its icon, not per frame.

## Line 452-472 (`_CableImageMeta.__call__`) — an unbounded, strong image cache
Every distinct set of colours makes one image object, stored in `cls._instances` (a plain dict, never trimmed) so that "scrolling a list of wires never draws one twice" (module docstring). Each image is a 400 x 100 RGBA layer stack: 160 KB of pixel data (400 x 100 x 4 bytes) before the Qt pixmap made from it. The number of distinct images is the number of distinct (jacket, stripe, core, conductors, shield) combinations ever shown: a catalog of 148,000 wires and 1,000 colours can produce thousands over a long part-search session, which at 160 KB is hundreds of MB that is never released. This is memory held that does not need to be: images that scrolled out of view are cheap to rebuild (a handful of 400 x 100 alpha composites, on the order of a millisecond each).
Fix: bound the cache (an LRU of a few hundred images is about 30-60 MB and keeps every wire in a typical project and the visible page of a list) or hold the instances in a `weakref.WeakValueDictionary` so an image lives while some widget holds it. Speed price: a miss redraws one image. The `@functools.lru_cache(maxsize=None)` on the layer loader is also unbounded but is keyed by layer name and colour; that one is small.

## Line 960-1091 (`_draw_wire`) — database lookups per image, once
Looks up colours and platings through the tables (`colors_table[...]`, `platings_table[...]`; global wrappers, one row `SELECT` each the first time, then cached while the wrapper lives) for each conductor, then composes. Fine because the result is cached.

## Line 169-207 (`_recolor`, `_over`) — NumPy recolour and alpha composite per layer
One array allocation per layer and `Image.alpha_composite` per pair; the work is per image, not per frame.
