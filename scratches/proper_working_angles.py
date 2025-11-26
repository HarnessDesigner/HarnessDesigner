
import numpy as np
from scipy.spatial.transform import Rotation


def calculate_angle(p1, p2):
    # the sign for all of the verticies in the array needs to be flipped in
    # order to handle the -Z axis being near
    p1 = -np.asarray(p1, dtype=np.dtypes.Float64DType)
    p2 = -np.asarray(p2, dtype=np.dtypes.Float64DType)

    f = p2 - p1
    fn = np.linalg.norm(f)

    if fn == 0:
        raise ValueError("p1 and p2 must be different points")

    f = f / fn  # world-space direction of the line

    local_forward = np.array([0.0, 0.0, -1.0], dtype=np.dtypes.Float64DType)
    nz = np.nonzero(local_forward)[0][0]
    sign = np.sign(local_forward[nz])
    forward_world = f * sign

    up = np.asarray((0.0, 1.0, 0.0), dtype=np.dtypes.Float64DType)

    if np.allclose(np.abs(np.dot(forward_world, up)), 1.0, atol=1e-8):
        up = np.array([0.0, 0.0, 1.0], dtype=np.dtypes.Float64DType)

        if np.allclose(np.abs(np.dot(forward_world, up)), 1.0, atol=1e-8):
            up = np.array([1.0, 0.0, 0.0], dtype=np.dtypes.Float64DType)

    right = np.cross(up, forward_world)
    rn = np.linalg.norm(right)

    if rn < 1e-8:
        raise RuntimeError("degenerate right vector")

    right = right / rn

    true_up = np.cross(forward_world, right)

    R = np.column_stack((right, true_up, forward_world))

    rot = Rotation.from_matrix(R)
    q = rot.as_quat()
    return q.tolist(), R.T


if __name__ == "__main__":
    import math

    p1 = [-15.0, -5.0, -1.5]
    p2 = [10.0, 0.0, 0.0]

    quat, matrix = calculate_angle(p1, p2)
    print('quat:', quat)
    # print('euler:', angles)
    print('matrix:', matrix)

    length = math.dist(p1, p2)

    points = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, length]], dtype=np.dtypes.Float64DType)
    points @= matrix
    print('calculated points:', points)

    p1 = np.array(p1, dtype=np.dtypes.Float64DType)
    points += p1
    print(points)
