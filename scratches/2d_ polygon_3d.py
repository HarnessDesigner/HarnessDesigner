
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


# ---------- geometry helpers ----------
def orthonormal_frame_from_normal(n):
    """Return orthonormal basis (u, v, w) where w is unit normal of plane."""
    w = np.array(n, dtype=float)
    w = w / np.linalg.norm(w)
    # choose an arbitrary vector not parallel to w
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
    print(u, v)
    verts = []

    for k in range(n):
        theta = 2.0 * math.pi * k / n + rotation
        p = C + radius * (math.cos(theta) * u + math.sin(theta) * v)
        verts.append((float(p[0]), float(p[1]), float(p[2])))
    return verts


def set_axes_equal(ax, verts):
    """Make 3D axes have equal scale so a regular polygon looks regular."""
    xs, ys, zs = zip(*verts)
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    zmin, zmax = min(zs), max(zs)
    xr = xmax - xmin
    yr = ymax - ymin
    zr = zmax - zmin
    max_range = max(xr, yr, zr, 1e-9)  # avoid zero
    xmid = 0.5 * (xmax + xmin)
    ymid = 0.5 * (ymax + ymin)
    zmid = 0.5 * (zmax + zmin)
    ax.set_xlim(xmid - max_range/2.0, xmid + max_range/2.0)
    ax.set_ylim(ymid - max_range/2.0, ymid + max_range/2.0)
    ax.set_zlim(zmid - max_range/2.0, zmid + max_range/2.0)
    # Matplotlib >=3.3 has set_box_aspect — attempt to use it (harmless if available)
    try:
        ax.set_box_aspect((1,1,1))
    except Exception:
        pass

# ---------- parameters ----------
center = (0.0, 0.0, 0.0)
normal = [0.0, 0.0, 1.0]   # tilted plane using all 3 axes
angles = [0.0, 0.0, 0.0]
radius = 10.0
n = 16

# initial geometry
verts = regular_ngon_3d(center, normal, radius=radius, n=n, rotation=0.0)
poly_closed = verts + [verts[0]]   # for plotting edges

# ---------- plotting ----------
fig = plt.figure(figsize=(8,7))
ax = fig.add_subplot(111, projection='3d')
plt.subplots_adjust(bottom=0.25)  # space for slider

# polygon face (one polygon)
poly_coll = Poly3DCollection([verts], alpha=0.35)

print([verts])

poly_coll.set_facecolor((0.0, 1.0, 1.0, 0.35))  # cyan-ish with alpha
ax.add_collection3d(poly_coll)

# edges (closed)
xs, ys, zs = zip(*poly_closed)
line, = ax.plot(xs, ys, zs, linestyle='-', linewidth=2, color='tab:blue')

# vertices scatter (only unique n vertices, not the closing one)
vx, vy, vz = zip(*verts)
scatter = ax.scatter(vx, vy, vz, color='red', s=60)

ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")
ax.set_title("Tilted Regular Octagon (normal=(1,1,1))")

# equal axis scaling so the octagon is not visually distorted
set_axes_equal(ax, verts)


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
    new_verts = regular_ngon_3d(center, normal, radius=radius, n=n, rotation=rot)
    new_closed = new_verts + [new_verts[0]]
    # update face (Poly3DCollection expects sequence of sequences of 3-tuples)
    poly_coll.set_verts([list(map(tuple, new_verts))])
    # update edge line
    xs, ys, zs = zip(*new_closed)
    line.set_data(xs, ys)
    line.set_3d_properties(zs)
    # update scatter (unique vertices only)
    vx, vy, vz = zip(*new_verts)
    scatter._offsets3d = (np.array(vx), np.array(vy), np.array(vz))
    # keep equal axes so shape remains regular-looking
    set_axes_equal(ax, new_verts)
    fig.canvas.draw_idle()


slider.on_changed(update)

ax_slider = plt.axes([0.18, 0.11, 0.64, 0.04])

slider_x = Slider(ax_slider, 'X Angle', 0.0, 359.0, valinit=0.0, valstep=1.0)


def update_x(val):
    angles[0] = slider_x.val

    new_verts = verts[:]

    for i, (x, y, z) in enumerate(new_verts):
        x_angle, y_angle, z_angle = angles
        y, z = _rotate_point((0, 0), (y, z), x_angle)
        z, x = _rotate_point((0, 0), (z, x), y_angle)
        x, y = _rotate_point((0, 0), (x, y), z_angle)
        new_verts[i] = (x, y, z)

    new_closed = new_verts + [new_verts[0]]
    # update face (Poly3DCollection expects sequence of sequences of 3-tuples)
    poly_coll.set_verts([list(map(tuple, new_verts))])
    # update edge line
    xs, ys, zs = zip(*new_closed)
    line.set_data(xs, ys)
    line.set_3d_properties(zs)
    # update scatter (unique vertices only)
    vx, vy, vz = zip(*new_verts)
    scatter._offsets3d = (np.array(vx), np.array(vy), np.array(vz))
    # keep equal axes so shape remains regular-looking
    set_axes_equal(ax, new_verts)
    fig.canvas.draw_idle()


slider_x.on_changed(update_x)

ax_slider = plt.axes([0.18, 0.14, 0.64, 0.04])

slider_y = Slider(ax_slider, 'Y Angle', 0.0, 359.0, valinit=0.0, valstep=1.0)


def update_y(val):
    angles[1] = slider_y.val

    new_verts = verts[:]

    for i, (x, y, z) in enumerate(new_verts):
        x_angle, y_angle, z_angle = angles
        y, z = _rotate_point((0, 0), (y, z), x_angle)
        z, x = _rotate_point((0, 0), (z, x), y_angle)
        x, y = _rotate_point((0, 0), (x, y), z_angle)
        new_verts[i] = (x, y, z)

    new_closed = new_verts + [new_verts[0]]
    # update face (Poly3DCollection expects sequence of sequences of 3-tuples)
    poly_coll.set_verts([list(map(tuple, new_verts))])
    # update edge line
    xs, ys, zs = zip(*new_closed)
    line.set_data(xs, ys)
    line.set_3d_properties(zs)
    # update scatter (unique vertices only)
    vx, vy, vz = zip(*new_verts)
    scatter._offsets3d = (np.array(vx), np.array(vy), np.array(vz))
    # keep equal axes so shape remains regular-looking
    set_axes_equal(ax, new_verts)
    fig.canvas.draw_idle()


slider_y.on_changed(update_y)

ax_slider = plt.axes([0.18, 0.17, 0.64, 0.04])

slider_z = Slider(ax_slider, 'Z Angle', 0.0, 359.0, valinit=0.0, valstep=1.0)


def update_z(val):
    angles[2] = slider_z.val

    new_verts = verts[:]

    for i, (x, y, z) in enumerate(new_verts):
        x_angle, y_angle, z_angle = angles
        y, z = _rotate_point((0, 0), (y, z), x_angle)
        z, x = _rotate_point((0, 0), (z, x), y_angle)
        x, y = _rotate_point((0, 0), (x, y), z_angle)
        new_verts[i] = (x, y, z)

    new_closed = new_verts + [new_verts[0]]
    # update face (Poly3DCollection expects sequence of sequences of 3-tuples)
    poly_coll.set_verts([list(map(tuple, new_verts))])
    # update edge line
    xs, ys, zs = zip(*new_closed)
    line.set_data(xs, ys)
    line.set_3d_properties(zs)
    # update scatter (unique vertices only)
    vx, vy, vz = zip(*new_verts)
    scatter._offsets3d = (np.array(vx), np.array(vy), np.array(vz))
    # keep equal axes so shape remains regular-looking
    set_axes_equal(ax, new_verts)
    fig.canvas.draw_idle()


slider_z.on_changed(update_z)
plt.show()