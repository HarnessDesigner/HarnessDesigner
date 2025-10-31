
import numpy as np
import math
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.widgets import Slider


def _rotate_point(origin, point, angle):
    angle = math.radians(angle)

    ox, oy = origin
    px, py = point

    cos = math.cos(angle)
    sin = math.sin(angle)

    x = px - ox
    y = py - oy

    qx = ox + (cos * x) - (sin * y)
    qy = oy + (sin * x) + (cos * y)
    return qx, qy


def orthonormal_frame_from_normal(n):
    w = np.array(n, dtype=float)
    w = w / np.linalg.norm(w)

    if abs(w[0]) < 0.9:
        a = np.array([1.0, 0.0, 0.0])
    else:
        a = np.array([0.0, 1.0, 0.0])

    u = a - np.dot(a, w) * w
    u /= np.linalg.norm(u)
    v = np.cross(w, u)
    v /= np.linalg.norm(v)

    return np.array([1.0, 0.0, 0.0],  dtype=float), np.array([0.0, 1.0, 0.0], dtype=float), None


def regular_ngon_3d(center, normal, radius=1.0, n=8, rotation=0.0):
    """Return list of n (x,y,z) vertices for a regular n-gon with given circumradius."""
    C = np.array(center, dtype=float)
    u, v, _ = orthonormal_frame_from_normal(normal)

    verts = []

    x_angle, y_angle, z_angle = angles

    for k in range(n):
        theta = 2.0 * math.pi * k / n + rotation
        p = C + radius * (math.cos(theta) * u + math.sin(theta) * v)

        x, y, z = (float(p[0]), float(p[1]), float(p[2]))
        y, z = _rotate_point((center[1], center[2]), (y, z), x_angle)
        z, x = _rotate_point((center[2], center[0]), (z, x), y_angle)
        x, y = _rotate_point((center[0], center[1]), (x, y), z_angle)

        verts.append((x, y, z))

    return verts


def set_axes_equal(ax, verts):
    xs, ys, zs = zip(*verts)
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    zmin, zmax = min(zs), max(zs)
    xr = xmax - xmin
    yr = ymax - ymin
    zr = zmax - zmin
    max_range = max(xr, yr, zr, 1e-9)
    xmid = 0.5 * (xmax + xmin)
    ymid = 0.5 * (ymax + ymin)
    zmid = 0.5 * (zmax + zmin)
    ax.set_xlim(xmid - max_range/2.0, xmid + max_range/2.0)
    ax.set_ylim(ymid - max_range/2.0, ymid + max_range/2.0)
    ax.set_zlim(zmid - max_range/2.0, zmid + max_range/2.0)

    try:
        ax.set_box_aspect((1, 1, 1))
    except Exception:
        pass


center1 = (-4.5, 25.0, 0.0)
center2 = (0.0, 25.0, 0.0)
center3 = (4.5, 25.0, 0.0)

normal = [0.0, 0.0, 1.0]
angles = [90.0, 0.0, 0.0]
radius = 2.0
n = 16


# initial geometry
verts1 = regular_ngon_3d(center1, normal, radius=radius, n=n, rotation=0.0)
poly_closed1 = verts1 + [verts1[0]]   # for plotting edges

verts2 = regular_ngon_3d(center2, normal, radius=radius, n=n, rotation=0.0)
poly_closed2 = verts2 + [verts2[0]]   # for plotting edges

verts3 = regular_ngon_3d(center3, normal, radius=radius, n=n, rotation=0.0)
poly_closed3 = verts3 + [verts3[0]]   # for plotting edges


# ---------- plotting ----------
fig = plt.figure(figsize=(8,7))
ax = fig.add_subplot(111, projection='3d')
plt.subplots_adjust(bottom=0.25)  # space for slider

from mpl_toolkits import mplot3d

import stl

# Load the STL files and add the vectors to the plot
for m in stl.Mesh.from_3mf_file(r'35323414_3D_STP(1).3mf'):
    vect = m.vectors

    coords = np.array((10.0, 10.0, 10.0), dtype=float)
    vect += coords
    poly_collection = mplot3d.art3d.Poly3DCollection(vect, facecolors=(0.7, 0.7, 0.7, 1.0), shade=True, linewidth=0.001)
    # poly_collection.set_color((0.7, 0.7, 0.7))  # play with color
    ax.add_collection3d(poly_collection)


# polygon face (one polygon)
poly_coll1 = Poly3DCollection([verts1], alpha=1.0)
poly_coll1.set_facecolor((1.0, 0.0, 0.0, 1.0))  # cyan-ish with alpha
ax.add_collection3d(poly_coll1)

poly_coll2 = Poly3DCollection([verts2], alpha=1.0)
poly_coll2.set_facecolor((1.0, 0.0, 0.0, 1.0))  # cyan-ish with alpha
ax.add_collection3d(poly_coll2)

poly_coll3 = Poly3DCollection([verts3], alpha=1.0)
poly_coll3.set_facecolor((1.0, 0.0, 0.0, 1.0))  # cyan-ish with alpha
ax.add_collection3d(poly_coll3)

# edges (closed)
xs, ys, zs = zip(*poly_closed1)
line1, = ax.plot(xs, ys, zs, linestyle='-', linewidth=2, color='tab:blue')

xs, ys, zs = zip(*poly_closed2)
line2, = ax.plot(xs, ys, zs, linestyle='-', linewidth=2, color='tab:blue')

xs, ys, zs = zip(*poly_closed3)
line3, = ax.plot(xs, ys, zs, linestyle='-', linewidth=2, color='tab:blue')

# vertices scatter (only unique n vertices, not the closing one)
# vx, vy, vz = zip(*verts)
# scatter = ax.scatter(vx, vy, vz, color='red', s=60)

ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")
ax.set_title("Tilted Regular Octagon (normal=(1,1,1))")


ax.set_xlim(-5, 40)
ax.set_ylim(-5, 40)
ax.set_zlim(-5, 40)

# set_axes_equal(ax, verts)


def get_angles(x1, y1, z1, x2, y2, z2):

    #               x1, y1, x2, y2
    def _get_angle(p1, p2, p3, p4):
        r = math.atan2(p4 - p2, p3 - p1)
        angle = math.degrees(r)

        if angle < 0:
            angle += 360.0

        return angle

    z_angle = _get_angle(x1, y1, x2, y2)
    y_angle = _get_angle(x1, z1, x2, z2)
    x_angle = _get_angle(z1, y1, z2, y2)

    return x_angle, y_angle, z_angle


# ---------- slider for rotation ----------
ax_slider = plt.axes([0.18, 0.08, 0.64, 0.04])

slider = Slider(ax_slider, 'Rotation', 0.0, 2.0 * math.pi, valinit=0.0)


def update(val):
    rot = slider.val
    new_verts1 = regular_ngon_3d(center1, normal, radius=radius, n=n, rotation=rot)
    new_closed1 = new_verts1 + [new_verts1[0]]

    new_verts2 = regular_ngon_3d(center2, normal, radius=radius, n=n, rotation=rot)
    new_closed2 = new_verts2 + [new_verts2[0]]

    new_verts3 = regular_ngon_3d(center3, normal, radius=radius, n=n, rotation=rot)
    new_closed3 = new_verts3 + [new_verts3[0]]

    poly_coll1.set_verts([list(map(tuple, new_verts1))])

    xs, ys, zs = zip(*new_closed1)
    line1.set_data(xs, ys)
    line1.set_3d_properties(zs)

    poly_coll2.set_verts([list(map(tuple, new_verts2))])

    xs, ys, zs = zip(*new_closed2)
    line2.set_data(xs, ys)
    line2.set_3d_properties(zs)

    poly_coll3.set_verts([list(map(tuple, new_verts3))])

    xs, ys, zs = zip(*new_closed3)
    line3.set_data(xs, ys)
    line3.set_3d_properties(zs)

    # update scatter (unique vertices only)
    # vx, vy, vz = zip(*new_verts)
    # scatter._offsets3d = (np.array(vx), np.array(vy), np.array(vz))
    # # keep equal axes so shape remains regular-looking
    # set_axes_equal(ax, new_verts)
    fig.canvas.draw_idle()


slider.on_changed(update)


def update_verts():

    new_verts1 = verts1[:]
    x_angle, y_angle, z_angle = angles

    x_angle = np.radians(x_angle)
    y_angle = np.radians(y_angle)
    z_angle = np.radians(z_angle)

    Rx = np.array(
        [[1, 0, 0],
         [0, np.cos(float(x_angle)), -np.sin(float(x_angle))],
         [0, np.sin(float(x_angle)), np.cos(float(x_angle))]]
        )

    Ry = np.array(
        [[np.cos(float(y_angle)), 0, np.sin(float(y_angle))],
         [0, 1, 0],
         [-np.sin(float(y_angle)), 0, np.cos(float(y_angle))]]
        )

    Rz = np.array(
        [[np.cos(float(z_angle)), -np.sin(float(z_angle)), 0],
         [np.sin(float(z_angle)), np.cos(float(z_angle)), 0],
         [0, 0, 1]]
        )

    xyz = np.array(center1, dtype=float)

    R = Rz @ Ry @ Rx

    new_verts1 = np.array(new_verts1, dtype=float) - xyz
    new_verts1 = new_verts1 @ R
    new_verts1 += xyz

    new_verts1 = new_verts1.tolist()

    new_closed1 = new_verts1 + [new_verts1[0]]

    poly_coll1.set_verts([list(map(tuple, new_verts1))])

    xs, ys, zs = zip(*new_closed1)
    line1.set_data(xs, ys)
    line1.set_3d_properties(zs)

    new_verts2 = verts2[:]
    xyz = np.array(center2, dtype=float)

    new_verts2 = np.array(new_verts2, dtype=float) - xyz
    new_verts2 = new_verts2 @ R + xyz
    new_verts2 += xyz

    new_verts2 = new_verts2.tolist()

    new_closed2 = new_verts2 + [new_verts2[0]]
    poly_coll2.set_verts([list(map(tuple, new_verts2))])
    xs, ys, zs = zip(*new_closed2)
    line2.set_data(xs, ys)
    line2.set_3d_properties(zs)

    new_verts3 = verts3[:]
    xyz = np.array(center3, dtype=float)

    new_verts3 = np.array(new_verts3, dtype=float) - xyz
    new_verts3 = new_verts3 @ R + xyz
    new_verts3 += xyz

    new_verts3 = new_verts3.tolist()

    new_closed3 = new_verts3 + [new_verts3[0]]
    poly_coll3.set_verts([list(map(tuple, new_verts3))])
    xs, ys, zs = zip(*new_closed3)
    line3.set_data(xs, ys)
    line3.set_3d_properties(zs)

    # update scatter (unique vertices only)
    # vx, vy, vz = zip(*new_verts)
    # scatter._offsets3d = (np.array(vx), np.array(vy), np.array(vz))
    # keep equal axes so shape remains regular-looking
    # set_axes_equal(ax, new_verts)
    fig.canvas.draw_idle()


ax_slider = plt.axes([0.18, 0.11, 0.64, 0.04])

slider_x = Slider(ax_slider, 'X Angle', 0.0, 359.0, valinit=90.0, valstep=1.0)



def update_x(val):
    angles[0] = slider_x.val
    update_verts()


slider_x.on_changed(update_x)


ax_slider = plt.axes([0.18, 0.14, 0.64, 0.04])

slider_y = Slider(ax_slider, 'Y Angle', 0.0, 359.0, valinit=0.0, valstep=1.0)


def update_y(val):
    angles[1] = slider_y.val

    update_verts()


slider_y.on_changed(update_y)


ax_slider = plt.axes([0.18, 0.17, 0.64, 0.04])

slider_z = Slider(ax_slider, 'Z Angle', 0.0, 359.0, valinit=0.0, valstep=1.0)


def update_z(val):
    angles[2] = slider_z.val

    update_verts()


slider_z.on_changed(update_z)
plt.show()
