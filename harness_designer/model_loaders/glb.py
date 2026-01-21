import json
import os
import struct
import tempfile

from . import gltf as _gltf
from .. import debug as _debug


def _read_glb_chunks(glb_path: str):
    with open(glb_path, "rb") as f:
        header = f.read(12)
        if len(header) != 12:
            raise ValueError("Invalid GLB header")

        magic, version, length = struct.unpack("<4sII", header)
        if magic != b"glTF":
            raise ValueError("Not a GLB file (bad magic)")

        if version != 2:
            raise ValueError(f"Unsupported GLB version: {version}")

        json_bytes = None
        bin_bytes = None

        # chunks: [chunkLength(uint32), chunkType(4 bytes), chunkData]
        while f.tell() < length:
            chunk_header = f.read(8)
            if len(chunk_header) < 8:
                break

            chunk_len, chunk_type = struct.unpack("<I4s", chunk_header)
            chunk_data = f.read(chunk_len)

            if chunk_type == b"JSON":
                json_bytes = chunk_data
            elif chunk_type == b"BIN\0":
                bin_bytes = chunk_data

        if json_bytes is None:
            raise ValueError("GLB missing JSON chunk")

        gltf = json.loads(json_bytes.decode("utf-8"))
        return gltf, (bin_bytes or b"")


@_debug.timeit
def load(file):
    gltf, bin_blob = _read_glb_chunks(file)

    with tempfile.TemporaryDirectory() as td:
        gltf_path = os.path.join(td, "model.gltf")
        bin_path = os.path.join(td, "buffer0.bin")

        # Ensure buffer[0] uses the temp bin file.
        # If buffers[0] already has a uri, override it.
        if "buffers" in gltf and len(gltf["buffers"]) > 0:
            gltf["buffers"][0]["uri"] = os.path.basename(bin_path)
        else:
            gltf["buffers"] = [{"byteLength": len(bin_blob), "uri": os.path.basename(bin_path)}]

        with open(gltf_path, "w", encoding="utf-8") as f:
            json.dump(gltf, f)

        with open(bin_path, "wb") as f:
            f.write(bin_blob)

        # Now reuse your existing glTF loader (OCP).
        return _gltf.load(gltf_path)