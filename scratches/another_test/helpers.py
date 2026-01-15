import math
import numpy as np


def quat_normalize(q):
    q = np.array(q, dtype=np.float64)

    n = math.sqrt((q * q).sum())

    if n == 0.0:
        return np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64)

    return (q / n).astype(np.float64)
