# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from dataclasses import dataclass
import numpy as np


@dataclass
class Surface:
    tri_indices: list[int]   # 0-based indices into triangle soup
    normal: np.ndarray  # unit normal, float32, canonical direction
    plane_dist: float   # dot(centroid, normal) — signed dist from origin
