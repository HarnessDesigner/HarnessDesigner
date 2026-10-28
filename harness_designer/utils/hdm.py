# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Reading and writing ``.hdm`` ("harness designer model") files.

Every numpy file this application keeps on disk -- an imported 3D model
(``<model_path>/<uuid[:2]>/<uuid>.hdm``, one ``.npy`` array) and the
primitive caches (``<appdata>/<name>.hdm`` and ``glyph_cache.hdm``, a
``.npz`` archive of several arrays) -- is an ``.hdm`` file: a short text
header followed, byte for byte, by what numpy itself would have written.

    # © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
    # The data contained in this file is used from unknown sources. ...
    <the .npy or .npz bytes>

numpy has no slot for metadata in either format and refuses to open a file
that does not start with its own magic bytes, so nothing here may be read
with ``np.load(path)`` directly: :func:`load` and :func:`load_arrays` skip
the header first. A header line starts with ``#`` and a numpy payload never
does (``.npy`` starts with ``0x93``, ``.npz`` with ``PK``), so the header
ends at the first byte that is not ``#`` and a line may be added to it later
without touching the readers.
"""

from typing import BinaryIO as _BinaryIO
from collections.abc import Callable

import os
import shutil
import threading
import numpy as np

from .. import check_types as _check_types


EXTENSION = '.hdm'

COPYRIGHT = '© 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>'

NOTICE = ('The data contained in this file is used from unknown sources. '
          'The copyright above only applies to the way the data has been '
          'written, not to the actual data contained in this file.')

HEADER = f'# {COPYRIGHT}\n# {NOTICE}\n'.encode('utf-8')

# The header is two short lines; this only stops a file that is not an .hdm
# file at all (a text file full of '#' lines) from being read to its end.
_MAX_HEADER_SIZE = 4096

_COPY_CHUNK_SIZE = 4 * 1024 * 1024

# A file that is open cannot be replaced or deleted on Windows, so two threads
# must never convert the same file at once.
_migrate_lock = threading.Lock()

_MMAP_MODES = ('r', 'r+', 'c')
_NPY_MAGIC = b'\x93NUMPY'
_NPZ_MAGIC = b'PK'


def _skip_header(fp: _BinaryIO) -> int:
    """Leave *fp* on the first byte after the text header.

    :returns: The offset of that byte from the start of the file.
    :raises ValueError: *fp* does not start with an ``.hdm`` header.
    """
    start = fp.tell()

    while True:
        position = fp.tell()

        if fp.read(1) != b'#':
            fp.seek(position)
            break

        fp.readline()

        if fp.tell() - start > _MAX_HEADER_SIZE:
            raise ValueError('not an hdm file: header is too long')

    if position == start:
        raise ValueError('not an hdm file: header is missing')

    return position


def _write(path: str, write: Callable[[_BinaryIO], None]) -> None:
    """Write the header, then whatever *write* puts in the file, to *path*.

    Goes through a temp file moved into place with ``os.replace`` so an
    interrupted write never leaves a partial file under the real name. The
    temp name carries the process and thread, so two writers of the same
    path never share one.
    """
    if not path.endswith(EXTENSION):
        raise ValueError(f'{path!r} does not end in {EXTENSION!r}')

    tmp_path = f'{path}.{os.getpid()}.{threading.get_ident()}.tmp'

    try:
        with open(tmp_path, 'wb') as f:
            f.write(HEADER)
            write(f)

        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        raise


@_check_types.do
def save(path: str, array: np.ndarray) -> None:
    """Write *array* to the ``.hdm`` file *path* (header, then ``.npy`` data)."""
    _write(path, lambda f: np.save(f, array, allow_pickle=False))


@_check_types.do
def save_arrays(path: str, arrays: dict[str, np.ndarray]) -> None:
    """Write *arrays* to the ``.hdm`` file *path* (header, then ``.npz`` data)."""
    _write(path, lambda f: np.savez(f, **arrays))


@_check_types.do
def load(path: str, mmap_mode: str | None = None) -> np.ndarray:
    """Return the array stored in the ``.hdm`` file *path* by :func:`save`.

    With *mmap_mode* (``'r'``, ``'r+'`` or ``'c'``, as for ``np.load``) the
    array is a memory map of the file at the offset where the data starts,
    so a large model is paged in on demand and never copied.
    """
    if mmap_mode is not None and mmap_mode not in _MMAP_MODES:
        raise ValueError(f'mmap_mode must be one of {_MMAP_MODES}, not {mmap_mode!r}')

    with open(path, 'rb') as f:
        _skip_header(f)

        if mmap_mode is None:
            return np.lib.format.read_array(f, allow_pickle=False)

        version = np.lib.format.read_magic(f)

        if version == (1, 0):
            shape, fortran_order, dtype = np.lib.format.read_array_header_1_0(f)
        elif version == (2, 0):
            shape, fortran_order, dtype = np.lib.format.read_array_header_2_0(f)
        else:
            raise ValueError(f'unsupported .npy version {version} in {path!r}')

        if dtype.hasobject:
            raise ValueError(f'{path!r} holds Python objects, which cannot be memory mapped')

        offset = f.tell()

    return np.memmap(path, dtype=dtype, mode=mmap_mode, offset=offset, shape=shape,
                     order='F' if fortran_order else 'C')


@_check_types.do
def load_arrays(path: str) -> dict[str, np.ndarray]:
    """Return every array stored in the ``.hdm`` file *path* by
    :func:`save_arrays`, by name. The arrays are read in full, so nothing
    stays open once this returns."""
    with open(path, 'rb') as f:
        _skip_header(f)

        if f.read(len(_NPZ_MAGIC)) != _NPZ_MAGIC:
            raise ValueError(f'{path!r} does not hold an array archive')

        f.seek(-len(_NPZ_MAGIC), os.SEEK_CUR)

        with np.load(f, allow_pickle=False) as data:
            return {name: data[name] for name in data.files}


def _convert(legacy_path: str, path: str) -> None:
    """Rewrite the pre-hdm numpy file *legacy_path* as the ``.hdm`` file
    *path*, check the result, and only then delete *legacy_path*."""
    if legacy_path.endswith('.npy'):
        with open(legacy_path, 'rb') as src:
            if src.read(len(_NPY_MAGIC)) != _NPY_MAGIC:
                raise ValueError(f'{legacy_path!r} is not a .npy file')

            src.seek(0)
            _write(path, lambda f: shutil.copyfileobj(src, f, _COPY_CHUNK_SIZE))

        # the data is copied untouched, so the new file is exactly one header longer
        if os.path.getsize(path) != len(HEADER) + os.path.getsize(legacy_path):
            os.remove(path)
            raise OSError(f'{path!r} is not the size of {legacy_path!r} plus the header')

        with open(path, 'rb') as f:
            _skip_header(f)
            np.lib.format.read_magic(f)
    else:
        with np.load(legacy_path, allow_pickle=False) as data:
            arrays = {name: data[name] for name in data.files}

        save_arrays(path, arrays)

        if set(load_arrays(path)) != set(arrays):
            os.remove(path)
            raise OSError(f'{path!r} does not hold the arrays of {legacy_path!r}')

    os.remove(legacy_path)


@_check_types.do
def migrate(path: str) -> None:
    """Upgrade the numpy file this application used to keep at *path*.

    *path* is an ``.hdm`` path. If it does not exist yet but a ``.npy`` or
    ``.npz`` file of the same name does (written before the ``.hdm`` format),
    that file is rewritten as *path* and then deleted; otherwise nothing happens. It is
    a one-time upgrade of data that cannot be rebuilt (a model's source file is
    deleted once it is converted) -- :func:`load` and :func:`load_arrays` only
    ever read ``.hdm`` files.
    """
    if os.path.exists(path):
        return

    stem = os.path.splitext(path)[0]

    with _migrate_lock:
        if os.path.exists(path):  # another thread converted it while this one waited
            return

        for extension in ('.npy', '.npz'):
            legacy_path = stem + extension

            if os.path.exists(legacy_path):
                _convert(legacy_path, path)
                return
