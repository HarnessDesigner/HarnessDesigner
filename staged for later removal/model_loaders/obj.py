
import numpy as np
from .. import debug as _debug


def _obj_parse_vertex_index(tok: str, vcount: int) -> int:
    # token can include / separators; the first field is the position index
    head = tok.split("/", 1)[0].strip()
    if not head:
        raise ValueError(f"Invalid face token: {tok!r}")

    idx = int(head)
    if idx > 0:
        # OBJ is 1-based
        return idx - 1

    elif idx < 0:
        # negative indices are relative to the end (vcount-1 is -1)
        return vcount + idx

    else:
        raise ValueError(f"OBJ index cannot be 0: {tok!r}")


def _obj_triangulate_fan(poly: list[int]) -> list[tuple[int, int, int]]:
    if len(poly) < 3:
        return []

    i0 = poly[0]
    return [(i0, poly[i], poly[i + 1]) for i in range(1, len(poly) - 1)]


@_debug.timeit
def load(file):
    vertices = []
    faces = []

    with open(file, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            # Split on whitespace; OBJ is whitespace-delimited
            parts = line.split()
            tag = parts[0]

            if tag == "v":
                # v x y z [w]  -> we take x,y,z and ignore w
                if len(parts) < 4:
                    continue
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))

            elif tag == "f":
                # f v1 v2 v3 ...
                if len(parts) < 4:
                    continue

                vcount = len(vertices)
                # Parse the position indices for this face
                poly = []
                for tok in parts[1:]:
                    try:
                        poly.append(_obj_parse_vertex_index(tok, vcount))
                    except ValueError:
                        # skip malformed tokens
                        poly = []
                        break

                # Triangulate (works for tris, quads, ngons)
                for tri in _obj_triangulate_fan(poly):
                    faces.append(tri)

            else:
                # Ignore vt/vn/vp/usemtl/mtllib/o/g/s/etc.
                continue

    v = np.asarray(vertices, dtype=np.float64).reshape(-1, 3)
    f = np.asarray(faces, dtype=np.int32).reshape(-1, 3)
    return [[v, f]]
