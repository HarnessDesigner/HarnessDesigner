
import numpy as np
import math
import time
import functools


class Config:
    function_time = True


# decorator function to tine how long functions take to run.
def timeit(func):

    if not Config.function_time:
        return func

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        start_time = time.time()
        res = func(*args, **kwargs)
        end_time = time.time()
        print(f'{func.__qualname__}: {round((end_time - start_time) * 1000, 2)}ms')
        return res

    return _wrapper


def remap(value, old_min, old_max, new_min, new_max):
    old_range = old_max - old_min
    new_range = new_max - new_min
    new_value = (((value - old_min) * new_range) / old_range) + new_min
    return new_value

import numpy as np
import build123d
from OCP.TopAbs import TopAbs_REVERSED
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location

def convert_model_to_mesh(model):
    loc = TopLoc_Location()
    BRepMesh_IncrementalMesh(
        theShape=model.wrapped, theLinDeflection=0.001,
        isRelative=True, theAngDeflection=0.1, isInParallel=True
        )

    vertices = []
    faces = []
    offset = 0
    for facet in model.faces():
        if not facet:
            continue

        poly_triangulation = BRep_Tool.Triangulation_s(
            facet.wrapped,
            loc
            )  # NOQA

        if not poly_triangulation:
            continue

        trsf = loc.Transformation()

        node_count = poly_triangulation.NbNodes()
        for i in range(1, node_count + 1):
            gp_pnt = poly_triangulation.Node(i).Transformed(trsf)
            pnt = (gp_pnt.X(), gp_pnt.Y(), gp_pnt.Z())
            vertices.append(pnt)

        facet_reversed = facet.wrapped.Orientation() == TopAbs_REVERSED

        order = [1, 3, 2] if facet_reversed else [1, 2, 3]
        for tri in poly_triangulation.Triangles():
            faces.append([tri.Value(i) + offset - 1 for i in order])

        offset += node_count

    vertices = np.array(vertices, dtype=np.dtypes.Float64DType)
    faces = np.array(faces, dtype=np.dtypes.Int32DType)

    return vertices, faces

@timeit
def _build_model(wire_length, wire_radius):

    # Create the wire
    model = build123d.Cylinder(float(wire_radius), float(wire_length), align=build123d.Align.NONE)

    # Extract the axis of rotation from the wire to create the stripe
    wire_axis = model.faces().filter_by(build123d.GeomType.CYLINDER)[0].axis_of_rotation

    # the stripe is actually a separate 3D object and it carries with it a thickness.
    # The the stripe is not thick enough the wire color will show through it. We don't
    # want to use a hard coded thickness because the threshold for for this happpening
    # causes the stripe thickness to increaseto keep the "bleed through" from happening.
    # A remap of the diameter to a thickness range is done to get a thickness where the
    # bleed through will not occur while keeping the stripe from looking like it is not
    # apart of the wire.
    
    edges = model.edges().filter_by(build123d.GeomType.CIRCLE)
    edges = edges.sort_by(lambda e: e.distance_to(wire_axis.position))[0]
    edges = edges.trim_to_length(0, float(wire_radius * 2 / 3.0 * build123d.MM))

    stripe_arc = build123d.Face(edges.offset_2d(0.25, side=build123d.Side.RIGHT))

    # Define the twist path to follow the wire
    twist = build123d.Helix(
        pitch=float(wire_length / 2.0),
        height=float(wire_length),
        radius=float(wire_radius),
        center=wire_axis.position,
        direction=wire_axis.direction,
    )

    # Sweep the arc to create the stripe
    stripe = build123d.sweep(
        stripe_arc,
        build123d.Line(wire_axis.position, wire_length * wire_axis.direction),
        binormal=twist
    )

    return convert_model_to_mesh(stripe)

@timeit
def helical_ribbon_solid_mesh_sheared(
    pitch, radius, length, width, thickness, n_steps,
    n_width=16,
    face_shift=1,          # integer shift across width per step (inner/outer faces)
    wrap_width=False       # if True, wrap j+shift modulo n_width (usually False for a ribbon)
):
    """
    radius    = inside radius
    thickness = radial build-out (outer radius = radius + thickness)
    width     = band width (tangential)
    Helix axis = +Z, ends capped.

    Adds width subdivisions and uses a sheared connectivity (index shift) on the
    INNER and OUTER faces to avoid the "straight across" triangulation pattern.

    Outputs:
      vertices_tris : (n_tris, 3, 3) float64
      faces        : (n_tris, 3)    int32
    """
    pitch = float(pitch)
    radius = float(radius)
    length = float(length)
    width = float(width)
    thickness = float(thickness)
    n = int(n_steps)
    nw = int(n_width)
    shift = int(face_shift)

    if n < 2:
        raise ValueError("n_steps must be >= 2")
    if nw < 2:
        raise ValueError("n_width must be >= 2")

    r_in = radius
    r_out = radius + thickness

    # parameterize by z for exact end planes
    z = np.linspace(0.0, length, n, dtype=np.float64)
    theta = (2.0 * np.pi / pitch) * z
    c = np.cos(theta)
    s = np.sin(theta)

    Er = np.stack([c, s, np.zeros_like(z)], axis=1)   # radial
    Et = np.stack([-s, c, np.zeros_like(z)], axis=1)  # tangential
    Z = np.stack([np.zeros_like(z), np.zeros_like(z), z], axis=1)

    # width coordinates across the band (tangential offsets)
    u = np.linspace(-0.5 * width, 0.5 * width, nw, dtype=np.float64)

    # Build vertex grid:
    # We keep 4 "layers" like before but now each ring has nw samples across width:
    # layer 0: inner surface (r_in) at width samples
    # layer 1: outer surface (r_out) at width samples
    #
    # Then we also need the two "side walls" at u=-w/2 and u=+w/2, but those can be
    # formed from the same grids by taking j=0 and j=nw-1 and connecting r_in<->r_out.
    #
    # V layout: for each step i, store inner row (nw), then outer row (nw)
    # total vertices = n * (2*nw)
    V = np.empty((n * (2 * nw), 3), dtype=np.float64)

    def v_index(i, layer, j):
        # layer: 0=inner, 1=outer
        return i * (2 * nw) + layer * nw + j

    # Fill vertices
    for i in range(n):
        # base vectors at step i
        eri = Er[i]
        eti = Et[i]
        zi = Z[i]
        # inner and outer rows
        inner = (r_in * eri)[None, :] + u[:, None] * eti[None, :] + zi[None, :]
        outer = (r_out * eri)[None, :] + u[:, None] * eti[None, :] + zi[None, :]
        V[i*(2*nw) + 0*nw : i*(2*nw) + 1*nw] = inner
        V[i*(2*nw) + 1*nw : i*(2*nw) + 2*nw] = outer

    # Helpers to add quads as two triangles with optional diagonal flip
    def add_quad(faces, k, a, b, c_, d, flip=False):
        if not flip:
            faces[k+0] = (a, b, c_)
            faces[k+1] = (a, c_, d)
        else:
            faces[k+0] = (a, b, d)
            faces[k+1] = (b, c_, d)
        return k + 2

    # Count triangles:
    # - Inner face: (n-1) * (nw-1) quads -> *2 tris
    # - Outer face: same
    # - Two side walls (at j=0 and j=nw-1): each (n-1) quads -> *2 tris, and there are 2 walls
    # - Two end caps: each is a rectangle between inner+outer across width -> (nw-1) quads -> *2 tris, and there are 2 caps
    segs = n - 1
    quads_inner = segs * (nw - 1)
    quads_outer = segs * (nw - 1)
    quads_walls = 2 * segs * 1
    quads_caps  = 2 * (nw - 1)

    n_tris = 2 * (quads_inner + quads_outer + quads_walls + quads_caps)
    faces = np.empty((n_tris, 3), dtype=np.int32)

    k = 0

    # INNER face with sheared connectivity
    for i in range(segs):
        for j in range(nw - 1):
            j0 = j
            j1 = j + 1

            # next ring indices are shifted
            if wrap_width:
                jp0 = (j0 + shift) % nw
                jp1 = (j1 + shift) % nw
            else:
                jp0 = min(max(j0 + shift, 0), nw - 1)
                jp1 = min(max(j1 + shift, 0), nw - 1)

            a = v_index(i,   0, j0)
            b = v_index(i,   0, j1)
            c_ = v_index(i+1, 0, jp1)
            d = v_index(i+1, 0, jp0)

            # alternate diagonals slightly too (optional but helps)
            flip = ((i + j) & 1) == 1
            k = add_quad(faces, k, a, b, c_, d, flip)

    # OUTER face with the same sheared connectivity (can use -shift if you prefer)
    for i in range(segs):
        for j in range(nw - 1):
            j0 = j
            j1 = j + 1

            if wrap_width:
                jp0 = (j0 + shift) % nw
                jp1 = (j1 + shift) % nw
            else:
                jp0 = min(max(j0 + shift, 0), nw - 1)
                jp1 = min(max(j1 + shift, 0), nw - 1)

            a = v_index(i,   1, j0)
            b = v_index(i,   1, j1)
            c_ = v_index(i+1, 1, jp1)
            d = v_index(i+1, 1, jp0)

            flip = ((i + j) & 1) == 1
            k = add_quad(faces, k, a, b, c_, d, flip)

    # Side wall at j=0 (one edge of width): connect inner<->outer
    j = 0
    for i in range(segs):
        a = v_index(i,   0, j)
        b = v_index(i,   1, j)
        c_ = v_index(i+1, 1, j)
        d = v_index(i+1, 0, j)
        flip = (i & 1) == 1
        k = add_quad(faces, k, a, b, c_, d, flip)

    # Side wall at j=nw-1 (other edge of width)
    j = nw - 1
    for i in range(segs):
        a = v_index(i,   0, j)
        b = v_index(i,   1, j)
        c_ = v_index(i+1, 1, j)
        d = v_index(i+1, 0, j)
        flip = (i & 1) == 1
        k = add_quad(faces, k, a, b, c_, d, flip)

    # Start cap at z=0: between inner and outer across width (i=0)
    i = 0
    for j in range(nw - 1):
        a = v_index(i, 0, j)
        b = v_index(i, 0, j+1)
        c_ = v_index(i, 1, j+1)
        d = v_index(i, 1, j)
        flip = (j & 1) == 1
        k = add_quad(faces, k, a, b, c_, d, flip)

    # End cap at z=length (reverse winding by swapping)
    i = n - 1
    for j in range(nw - 1):
        a = v_index(i, 0, j)
        b = v_index(i, 1, j)
        c_ = v_index(i, 1, j+1)
        d = v_index(i, 0, j+1)
        flip = (j & 1) == 1
        k = add_quad(faces, k, a, b, c_, d, flip)

    # Origin at center of start cap:
    # average of inner/outer across width at i=0
    start_ring = V[i*(2*nw):(i*(2*nw)+2*nw)] if False else V[0:(2*nw)]
    start_center = start_ring.mean(axis=0)
    V = V - start_center


    return V, faces


v, f = _build_model(914.4, 2.5)

# v, f = helical_ribbon_solid_mesh_sheared(40.0, 1.0, 75, 1.0, 0.25, 300)


for item in v[f].tolist():
    print(item)


from stl import mesh

triangles = v[f]  # (F, 3, 3)

print(len(triangles))


data = np.zeros(len(triangles), dtype=mesh.Mesh.dtype)

m = mesh.Mesh(data, calculate_normals=False, remove_empty_areas=False)
m.vectors = triangles

m.save(r'C:\Users\drsch\PycharmProjects\harness_designer\scratches\mobius.stl', update_normals=True)


'''
BROOK FOREST WATER DIST                 18.8260
COUNTY                                  23.3320
EVERGREEN FIRE DIST                     12.3800
EVERGREEN PARK & REC DIST               6.8570
LAW ENFORCE AUTHORITY                   2.5490
REGIONAL TRANSPORTATION DIST            0.0000
SCHOOL                                  47.0750
Total Mill Levy                         111.0190
	


total assessed value                    $29,887.00

this is what I paid for school taxes in 2019
29,887.00 * 47.0750 / 1000 = $1,406.93


and now in 2025 this is what I am paying in school taxes...



 BROOK FOREST WATER DIST                  18.6410
COUNTY                                    26.9780
EVERGREEN FIRE DIST                       11.3649
EVERGREEN PARK & REC DIST                 6.1290
LAW ENFORCE AUTHORITY                     2.4990
REGIONAL TRANSPORTATION DIST              0.0000
SCHOOL                                   44.3490
Total Mill Levy                         109.9609 
	

total assessed value                     $49,947 



$49,947 * 44.3490 / 1000 = 2,215.10


NOW: $2,215.10
THEN: $1,406.93

that's a 37% increase that is being paid to the schools. 

They are getting the entire 40%. 




'''