# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
#
# harness_designer/database/global_db/model3d/model_data.py
#
# Custom NPZ-compatible cache format for 3D model geometry.
#
# An NPZ file is a ZIP archive of .npy files.  We extend that by adding a
# metadata entry inside the same archive.
#
# Archive layout (triangle soup - no index array)
# ───────────────────────────────────────────────
#   positions       (F*3*3,) float32   expanded vertex positions
#   flat_normals    (F*3*3,) float32   face normal replicated 3x per tri
#   smooth_normals  (F*3*3,) float32   area-weighted normal, expanded
#   metadata       UTF-8 JSON object
#
# Metadata schema (spec_version 1)
# ─────────────────────────────────
# {
#   "spec_version":  1,
#   "manufacturer":  "TE Connectivity",
#   "part_number":   "1-123456-7",
#   "source_format": "stp",
#   "source_url":    "https://www.te.com/...",
#   "created_utc":   "2025-06-01T12:00:00",
#   "vertex_count":  36927
# }
#
# Recovery:
#   If metadata is corrupted the UUID in the filename is the primary key
#   into the models3d database table, which stores the original path/URL
#   so the file can be re-downloaded and re-converted.

import io
import json
import zipfile
import datetime
import os
import uuid

import numpy as np


SPEC_VERSION = '1.0.0'


class ModelDataMeta(type):

    def __call__(cls, *args, **kwargs):
        if 'version' not in kwargs:
            kwargs['version'] = SPEC_VERSION

        if len(args) == 1:
            path = args[0]
            if not os.path.isfile(path):
                raise FileNotFoundError(f'Model cache not found: {path}')

            with zipfile.ZipFile(path, 'r') as zf:
                if 'metadata' not in zf.namelist():
                    raise RuntimeError('invalid file format')

                with zf.open('metadata') as f:
                    metadata = json.loads(f.read().decode('utf-8'))

                if 'version' not in metadata:
                    raise RuntimeError('invalid file format')

                version = metadata['version']
                read_func = globals()[f'_read_hdz_v{version.replace(".", "")}']

                data = read_func(zf, metadata)

        else:
            data = super().__call__(*args, **kwargs)

        return data


class ModelDataV100(metaclass=ModelDataMeta):
    """
    Container returned by :func:`read`.

    Attributes
    ----------
    positions      (F*3*3,) float32  - pass directly to VBOHandler
    flat_normals   (F*3*3,) float32
    smooth_normals (F*3*3,) float32
    count          int               - F*3, pass to glDrawArrays
    metadata       dict
    """

    def __init__(self, vertices, face_normals=None, smooth_normals=None, /, **metadata):
        self._vertices = np.ascontiguousarray(np.asarray(vertices, dtype=np.float32))
        self._face_normals = np.ascontiguousarray(np.asarray(face_normals, dtype=np.float32))
        self._smooth_normals = np.ascontiguousarray(np.asarray(smooth_normals, dtype=np.float32))
        self._metadata = metadata
        self._metadata['version'] = '1.0.0'
        self._metadata['vertex_count'] = len(vertices) // 3

    @property
    def vertices(self) -> np.ndarray:
        return self._vertices

    @property
    def face_normals(self) -> np.ndarray:
        return self._face_normals

    @property
    def smooth_normals(self) -> np.ndarray:
        return self._smooth_normals

    @property
    def uuid(self) -> str:
        if 'uuid' not in self._metadata:
            self._metadata['uuid'] = str(uuid.uuid4())

        return self._metadata['uuid']

    @property
    def vertex_count(self) -> int:
        return self._metadata['vertex_count']

    @property
    def manufacturer(self) -> str:
        return self._metadata.get('manufacturer', '')

    @manufacturer.setter
    def manufacturer(self, value: str):
        self._metadata['manufacturer'] = value

    @property
    def part_number(self) -> str:
        return self._metadata.get('part_number', '')

    @part_number.setter
    def part_number(self, value: str):
        self._metadata['part_number'] = value

    @property
    def source_location(self) -> str:
        return self._metadata.get('source_location', '')

    @source_location.setter
    def source_location(self, value: str):
        self._metadata['source_location'] = value

    @property
    def source_type(self) -> str:
        return self._metadata.get('source_type', '')

    @source_type.setter
    def source_type(self, value: str):
        self._metadata['source_type'] = value

    @property
    def version(self) -> str:
        return self._metadata['version']

    def save(self, model_dir):
        self._metadata['created_utc'] = datetime.datetime.utcnow().isoformat(timespec='seconds')

        def _npy_bytes(arr: np.ndarray) -> bytes:
            buf = io.BytesIO()
            np.save(buf, arr)
            return buf.getvalue()

        path = os.path.join(model_dir, f'{self.uuid}.hdz')

        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('positions', _npy_bytes(self._vertices))
            zf.writestr('flat_normals', _npy_bytes(self._face_normals))
            zf.writestr('smooth_normals', _npy_bytes(self._smooth_normals))
            zf.writestr('metadata', json.dumps(self._metadata, indent=2).encode('utf-8'))


def _read_hdz_v100(zf, metadata) -> ModelDataV100:
    def _load(zipf: zipfile.ZipFile, name: str) -> np.ndarray:

        if name not in zipf.namelist():
            raise ValueError(f'Cache missing required entry: {name}')

        with zipf.open(name) as file:
            return np.load(io.BytesIO(file.read()))

    positions = _load(zf, 'positions')
    flat_normals = _load(zf, 'flat_normals')
    smooth_normals = _load(zf, 'smooth_normals')

    return ModelData(positions, flat_normals, smooth_normals, **metadata)


# There is some vood doo magic code that runs for this class.
# Either a file path can be passed to load a file or data is able
# to be fed to it to create the instance.
class ModelData(ModelDataV100):
    pass
