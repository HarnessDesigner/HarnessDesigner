# harness_designer/utils/hdm.py

Reads and writes `.hdm` files: a short `#` text header followed by what NumPy itself would write (`.npy` for an imported 3D model, `.npz` for the primitive and glyph caches). Every model and primitive load goes through `load` / `load_arrays`.

## Line 59-84 (`_skip_header`), 131-185 (`load`, `load_arrays`) — a byte loop over the header, then a plain NumPy load
`_skip_header` reads the `#` header lines until the first non-`#` byte (a few lines), then NumPy reads the payload. Loading a model is one file read; the array is read fully into memory (no memory map), so the cost is proportional to the mesh size (a few MB for a large housing). The file is uncompressed on purpose (loading is faster than decompressing; the price is disk space).

## Line 225-252 (`migrate`), 188-222 (`_convert`)
A one-time conversion of older cache files; runs at startup only when old files are found. Not a concern.
