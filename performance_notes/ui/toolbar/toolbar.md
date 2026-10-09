# harness_designer/ui/toolbar/toolbar.py

## `_get_icon` / `_get_lock_icon` / `_make_icon` - recomposed and re-decoded on every call
Each icon helper rebuilds its icon from scratch on every call:
- `Image.__add__` (used by `_get_icon` to add the checkbox overlay) reads `self.pil` and `other.pil`. `Image.pil` is a property that decodes the PNG bytes each time it is read, so each composite decodes two PNGs, composes them, and returns a new image.
- `_make_icon` calls `img.resize(size, size).pixmap`. `resize` makes another image, and `pixmap` decodes PNG bytes again (`utils.bytes_data_2_qpixmap`).

`set_buttons` calls `_get_icon` three times per call, and `set_buttons` runs from six call sites, including the note-selection and align paths. So a single selection change can decode, compose, and re-encode several PNGs before anything is drawn. The exact count was not measured. The inputs are fixed (a small set of icon images, two checkbox states, and a lock state), so the results never change.

Candidate fix: memoise the composed `QIcon` for each (checkbox state, base icon) pair, and for each lock state, in a small dict. There are only a handful of combinations, so the cache is tiny. This is the case the project's performance rules call "genuinely expensive to recompute", so a cache is justified here.

## `_apply_selection_filter` - resets and re-enables every button per 3D selection
Each 3D selection resets about 20 action enables, then re-enables the ones that apply. That is a cheap loop over Qt actions, with no image or database work, so it needs no change.
