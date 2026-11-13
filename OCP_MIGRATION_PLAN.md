# Plan: remove build123d, use OCP (OCCT) directly

Written 2026-11-11. Status: PLAN ONLY, no code has been changed. build123d 0.10.0 and cadquery-ocp 7.8.1.1 are what is installed
(`C:\python3.11.14`), and every statement below about what build123d "does" was read from that installed source, not from memory.

## 1. Summary

* build123d is imported in **26 files** (255 references). Most of them (about 15 files) use it ONLY for the two enums `FontStyle` and
  `TextAlign`. The real geometry work is in **11 files**: 8 in `shapes/` + the two `seal.py`, the two `transition.py`, `part_orientation.py`.
* `ocp_ops.py` already replaces the text path (`build_text_mesh`) and it is exact: for `'A' 'g' '8' '('` in all four styles it gives the
  same vertex count, triangle count and bounding box as `build123d.Text + extrude` (checked 2026-11-11, throwaway script).
* The remaining geometry needs OCP code for: cylinder / sphere / box, fuse and cut, rigid moves, a plane-placed solid, a helix edge, a pipe-shell
  sweep (with a binormal / auxiliary-spine), an offset arc cross-section, a spline, and a small 2D arrow outline. Every one of those is a direct
  OCP call; build123d is only a wrapper around them (its own source shows the exact OCP calls, listed below).
* Because every public function in `ocp_ops` must be plain numpy / Python in and out and run on the OCP thread (`ocp_threadworker`), the
  multi-step solids (seal, transition body, cylinder-helix, arrow...) become **one function each that takes plain numbers and returns
  `(vertices, faces)`**. The call sites keep their own caching (`_FAILED_BODY_IDS`, `mesh_cache`, pooled VBO ids).

## 2. Things found while reading that need a decision (please read these first)

1. **BUG in the existing `ocp_ops._get_font`**: the font cache key is `(name, style)` and ignores `font_size`. Verified: `build_text_mesh('Z+', 8.0, ...)`
   after a size-1.0 call returned a mesh 8x too small (bbox about +-0.55 instead of +-4.6). `shapes/text.py` uses size 1.0 and
   `part_orientation.AxisLabel3D` uses 8.0, so switching both over without a fix would shrink the axis labels. Fix: key on `(name, style, size)`.
2. **`Location((x, y, z), (0, 1, 0))` is NOT a rotation about an axis.** In build123d the second argument is Euler *orientation in degrees*
   (verified: `Location((0,1,0),(0,1,0)).orientation == (0, 1.0, 0)`), so every one of those calls in `cylinder_helix.py` also rotates the shape by
   **1 degree** about X, Y or Z. The hand-tuned numbers in that file (`9.35`, `0.0195`, `0.133`, `0.15`, the stripe offsets) were tuned with that
   1 degree in place. To get identical output the port must reproduce the 1 degree. **Decision needed:** reproduce it exactly (my recommendation,
   written as a named constant with a comment) or drop it and re-tune by eye.
3. **The 3D and peg-board `build_bulb_solid` are NOT identical**, although the peg-board docstring says "byte-for-byte identical". When
   `bulb_offset is None`, the peg-board version adds a sphere at `offset` (the near end cap); the 3D version does not. Both pool the result under the
   same VBO id (`part_number + ':transition'`), so whichever view builds first decides the mesh for both. **Decision needed:** which one is the
   intended shape? The port will have ONE builder, so one of them has to win (and the other file just calls it).
4. `objects_3d/splice.py::_build_model` is dead code (no callers, checked with `dep_trace.py`). Delete it with its `import build123d`.
5. `shapes/disc_ring.py` imports build123d and never uses it. Delete the import.
6. OCP is already imported **outside** `ocp_ops` in four more places (`utils/model_utils.py`, `shapes/text.py`, `process/model_process.py`,
   `exporter/exporter.py`), although the `ocp_ops` docstring says it is the only module allowed to. `model_process.py` and `model_utils.py` each
   contain their own copy of the tessellation loop. This plan only removes the first two (they are build123d-related); the other two are listed in
   section 8 as follow-ups.
7. All 3 CI workflows, `pyproject.toml` and `builder/scripts/HD.spec` (`collect_all('build123d')`) pin or collect build123d (section 7).

## 3. Proposed layout: `harness_designer/ocp_ops/` (a package, replacing `ocp_ops.py`)

`__init__.py` is empty (docstring only) and callers import the submodule they need. Reason: the enums are needed by the database layer
(`pjt_note.py`), the toolbar and the add-note dialog, and none of those should pull in OCP and start the OCP worker thread just to get a number.
Only `enums.py` is OCP-free.

| File | Public (runs on the OCP thread, numpy in / numpy out) | Private helpers (TopoDS in / out, only called from inside a public function) |
|---|---|---|
| `enums.py` | `FontStyle`, `TextAlign` (moved from `ocp_ops.py`, same values) | |
| `_core.py` | | `placement(origin, z_dir, euler_deg)`, `location(position, euler_deg)`, `rotate(shape, axis_origin, axis_dir, deg)`, `fuse(*shapes)`, `cut(shape, *tools)`, `clean(shape)`, `make_cylinder(r, h, centered)`, `make_sphere(r)`, `make_box(x, y, z)` |
| `_sweep.py` | | `make_helix(pitch, height, radius, center, direction)`, `make_spline(points)`, `pipe_shell(face_or_wire, path, aux)`, `arc_band_face(radius, thickness, length)` |
| `mesh.py` | `tessellate(shape...)` is private; public is `bounding_box` not needed | `_tessellate_shape(shape, lin, ang, relative) -> (vertices, faces)` (already exists, keeps the GC-disable step) |
| `text.py` | `build_text_mesh(...)` (exists), `font_file_path(style) -> str` (new, replaces the `OCP.Font` use in `shapes/text.py`) | `_get_font` (fixed key), `_extrude_and_fuse` |
| `shapes.py` | `build_square_outline_mesh()`, `build_sws_seal_mesh(length, o_dia, i_dia)`, `build_transition_body_mesh(branches)`, `build_arrow_mesh()`, `build_helix_stripe_mesh(radius, length, pitch)`, `build_cylinder_helix_mesh()` -> `(vertices, faces, endpoint)`, `build_cylinder_helix_stripe_mesh()` | |

All functions follow the repo conventions (complete type hints incl. `None`, no inline conditionals, import order, `@_check_types.do`, no unit
tests: verification is done with throwaway scripts in `D:\harness_designer_tmp\scripts`).

Also in the same change: new `ocp_ops/MAP.md`, update `harness_designer/MAP.md` (`ocp_ops.py` entry becomes a folder entry), `CODEBASE_MAP.md`
(new directory), and `geometry/MAP.md`, `shapes/MAP.md`, `utils/MAP.md` (they describe the build123d exceptions).

## 4. Inventory: where build123d is used, what it does, what replaces it

### 4A. Enums only (no geometry) -> `ocp_ops.enums`

build123d 0.10.0 values (verified) are identical to the ones already in `ocp_ops.py`: `FontStyle` REGULAR 1, BOLD 2, ITALIC 3, BOLDITALIC 4;
`TextAlign` BOTTOM 1, CENTER 2, LEFT 3, RIGHT 4, TOP 5, TOPFIRSTLINE 6. These integers are stored in the database (`pjt_notes.style`, `h_align`)
and compared in the toolbar, so they must not change; they don't.

| File | Lines | Use |
|---|---|---|
| `database/project_db/pjt_note.py` | 7, 472-473, 482-483 | enum members as the allowed values of the style / h_align fields |
| `ui/dialogs/add_note.py` | 5, 22-31 | `TEXT_ALIGN_MAPPING`, `FONT_STYLE_MAPPING` lists of `.value` |
| `ui/toolbar/toolbar.py` | 6, 443-473 | `TextAlign.LEFT/CENTER/RIGHT.value` compare / set |
| `objects/objects_3d/note.py`, `objects_pegboard/note.py`, `objects_schematic/note.py` | 5, ~145-172 | `build123d.FontStyle(db.style)`, `build123d.TextAlign(db.h_align)` passed to `_text.Text` |
| `objects/objects_schematic/terminal.py` | 7, 227-724 | `FontStyle.REGULAR`, `TextAlign.LEFT/RIGHT` for `_text.Text` |
| `objects/objects_schematic/housing.py` | 5, 318-323 | `TextAlign.LEFT/RIGHT`, `FontStyle.ITALIC` |
| `geometry/cavity_layout.py` | 39, 236, 265 | `FontStyle.REGULAR` |
| `rotation_handlers/rotation_ring/_protractor_base.py` | 33, 264 | `FontStyle.ITALIC` |

**To do:** replace `import build123d` with `from ..ocp_ops import enums as _ocp_enums` (relative depth per file) and every
`build123d.FontStyle` / `build123d.TextAlign` with `_ocp_enums.FontStyle` / `_ocp_enums.TextAlign`. Pure rename, no behaviour change.

### 4B. Text -> `ocp_ops.text`

| File | Lines | What build123d does today | OCP replacement |
|---|---|---|---|
| `shapes/text.py` `_tessellate_char` | 30, 288-317 | `Text(char, 1.0, font_style=style, text_align=[LEFT, BOTTOM])` then `extrude(model, depth)` then `utils.convert_model_to_mesh(model, 0.01, 0.5)` | `ocp_ops.text.build_text_mesh(char, 1.0, depth, font_style=..., text_align=(LEFT, BOTTOM), lin_deflection=0.01, ang_deflection=0.5)`. Already exists and matches (verified). The glyph cache version does not need a bump if parity holds. |
| `shapes/text.py` `_font_metrics` | 33-35, 144-156 | Uses `build123d.FontStyle.*.value` to map to `OCP.Font.Font_FontAspect` and asks `Font_FontMgr` for the Arial file path (then reads it with fontTools) | New `ocp_ops.text.font_file_path(style: int, name: str = 'Arial') -> str`; `shapes/text.py` then has no `import OCP` and no `import build123d`. Its many comments that mention build123d get reworded. |
| `shapes/text.py` `Text.__init__` | 924-1071 | Types / compares `FontStyle`, `TextAlign` | enum rename only (4A) |
| `ui/dialogs/part_orientation.py` `AxisLabel3D` | 7, 273-278 | `Text(text, font_size=8.0, text_align=[CENTER, CENTER])`, `extrude(model, 0.5)`, `convert_model_to_mesh(model)` (default 0.001 / 0.5, relative) | `build_text_mesh(text, 8.0, 0.5, text_align=(CENTER, CENTER))`. **Needs the font-cache fix (section 2.1).** |

Port notes: build123d's `Compound.make_text` ends with `translate(bbox.to_align_offset(align))`; with `align=None` (both call sites) that is zero, so
`build_text_mesh` needs no bounding-box alignment. `build_text_mesh` should also set `SetRunParallel` explicitly in the fuse (build123d sets it to True).

### 4C. Tessellation -> `ocp_ops.mesh`

`utils/model_utils.py::convert_model_to_mesh(model, lin, ang, is_relative)` takes a build123d shape (`.wrapped`, `.faces()`); 10 call sites
(arrow, cylinder_helix x2, helix, square_outline, text, part_orientation, both seals, both transitions). The raw-OCP version already exists as
`ocp_ops._tessellate_shape`. **To do:** every call site stops calling it (they call the builders in 4D / 4E, which return arrays); delete
`convert_model_to_mesh` and the `TYPE_CHECKING` build123d import, and keep `compute_edges` there. Keep the GC-disable step (it is cheap insurance).

### 4D. Primitive meshes in `shapes/`

For each of these, the builder moves into `ocp_ops.shapes`; the `shapes/*.py` file keeps the VBO / mesh_cache / normals / AABB / OBB code and
calls it. `_MESH_CACHE_VERSION` is bumped once each is ported (the triangulation can differ in the last digits, so old disk caches are discarded).

**`shapes/square_outline.py`** (lines 13, 62-64) -- `Box(1,1,1) - Box(0.9, 1.2, 0.9)`.
OCP: `BRepPrimAPI_MakeBox(gp_Ax2(gp_Pnt(-x/2,-y/2,-z/2), gp_Dir(0,0,1)), x, y, z)` for each (build123d boxes are centered, `Box(length, width, height)` = X, Y, Z),
then `BRepAlgoAPI_Cut` + `ShapeUpgrade_UnifySameDomain`. Easy.

**`shapes/arrow.py`** (lines 9, 53-80) -- the hardest single port, but small. build123d: a 6 mm line `Edge.extrude(Vertex(2,0,0),(6,0,0))`;
`ArrowHead(size=2, rotation=tangent_angle - 20, CURVED)` (a face bounded by two tangent arcs and two lines, mirrored about XZ); a triangle
`Polygon((7.5,.2),(6.5,-.125),(8.5,-.125))`; the shaft = the line trimmed from 1/6 to 1, a perpendicular 0.25 line at its start swept along it
(a 0.25 wide rectangle, x 3 to 8); head moved to (8.5,-0.125,0); head + shaft + triangle fused into one face; `extrude(0.25, +Z)`; moved +2.5 in X.
Result measured: 1 solid, valid, 8 faces, bbox x 5.5..11, y -0.125..1.1855, z 0..0.25, volume 0.49374.
OCP: head from `GC_MakeArcOfCircle(p0, tangent_vec, p1)` (that is what `TangentArc` is), `BRepBuilderAPI_MakeEdge` for the lines, mirror with
`gp_Trsf.SetMirror(gp_Ax2)`, `BRepBuilderAPI_MakeWire` + `BRepBuilderAPI_MakeFace`; the shaft is just a rectangle face (4 points) so no sweep is needed;
polygon via `BRepBuilderAPI_MakePolygon`; fuse the three faces (`BRepAlgoAPI_Fuse`, clean); `BRepPrimAPI_MakePrism(face, gp_Vec(0,0,0.25))`; `Moved`.
Check: compare face / vertex counts, bbox and volume against the numbers above.

**`shapes/helix.py`** (lines 9, 110-127) -- striped helix for straight wires. build123d: `Cylinder(r, L, align=NONE)` is used ONLY to read three
things from it: the axis (origin, +Z), a bottom circle edge, and a 2/3 radius long arc of it; `offset_2d(0.01, side=RIGHT)` + `Face(...)` makes the stripe
cross-section; `Helix(pitch, height=L, radius=r)` is the binormal guide; `Line((0,0,0),(0,0,L))` is the spine; `sweep(face, line, binormal=helix)`.
Verified numbers: the profile is the annular sector from radius r to r + 0.01 (RIGHT of a circle is outward, both for a forward and a reversed circle edge),
arc length 2/3 r; the helix is right-handed, starts at (r,0,0) and for L=100, pitch=60 has length 100.137 and ends at angle 600 degrees.
OCP: no cylinder is needed. Build the face directly (two `Geom_Circle` arcs of radius r and r + t with the same 2/3 rad sweep, two radial lines,
`BRepBuilderAPI_MakeWire` + `MakeFace`); `make_helix` is build123d's own recipe, which is already pure OCP (`Geom_CylindricalSurface(gp_Ax3(center, normal), r)`,
`Geom2d_Line(gp_Pnt2d(0,0), gp_Dir2d(2*pi, pitch) normalised)` trimmed to `length / dir.Y`, `BRepBuilderAPI_MakeEdge(curve2d, surface)`,
`BRepLib.BuildCurves3d_s(edge, 1e-9, MaxSegment=2000)`); the spine is `BRepBuilderAPI_MakeEdge(gp_Pnt, gp_Pnt)`; the sweep is
`BRepOffsetAPI_MakePipeShell(spine_wire)`, `SetMode(helix_wire, True)` (binormal / auxiliary spine, curvilinear equivalence), `SetTransitionMode(BRepBuilderAPI_Transformed)`,
`Add(profile_wire, False, False)`, `Build()`, `MakeSolid()`. Tessellation stays absolute (0.05 mm, 0.15 rad, `is_relative=False`). Keep the bottom-arc start angle
identical to build123d (check the first vertex of the profile against the original).

**`shapes/cylinder_helix.py`** (lines 10, 57-344, 54 references) -- the service-loop part. Two functions:
`create_vbo()` = cylinder + swept helix loop + second cylinder, and `create_stripe_vbo()` = three striped sweeps. build123d pieces and their OCP equivalents:

* `Cylinder(r, h, align=NONE)` -> `BRepPrimAPI_MakeCylinder(gp_Ax2(origin, +Z), r, h)` (base on the XY plane, z 0..h). Centered cylinders (4E) are the same shifted by -h/2.
* `Sphere(r)` is used ONLY to find the second connection point (`sphere2.center()`); nothing of it is drawn. In OCP no sphere is needed: apply the same
  chain of rigid transforms to `gp_Pnt(0,0,diameter)` and return it (`gp_Trsf` composition). This also removes a boolean-free but non-trivial solid build.
* `Helix(radius=1, pitch=1.15, height=1.15, cone_angle=0, direction=(1,0,0))` -> `make_helix` above.
* `sweep(path=helix, sections=(helix ^ 0) * Circle(r))` -> `helix ^ 0` is `location_at(0)` = a Frenet frame at the start (`GeomFill_Frenet`, `gp_Ax3(pnt, tangent, normal)`);
  the profile is `BRepBuilderAPI_MakeFace(gp_Circ)` moved into that frame; sweep = `BRepOffsetAPI_MakePipeShell(helix)`, `SetMode(False)` (corrected Frenet), transformed
  transition, `Add`, `Build`, `MakeSolid`, then build123d's `clean()` (`ShapeUpgrade_UnifySameDomain`).
* `.rotate(Axis(origin, dir), deg)` -> `gp_Trsf.SetRotation(gp_Ax1, rad)` + `BRepBuilderAPI_Transform(shape, trsf, True)`.
* `.move(Location(pos, (ax, ay, az)))` -> **a rigid transform with a translation AND a rotation of (ax, ay, az) DEGREES, intrinsic XYZ** (section 2.2):
  `gp_Quaternion.SetEulerAngles(gp_Extrinsic/Intrinsic_XYZ, ...)` -> `gp_Trsf.SetRotation(quat)` -> `SetTranslationPart(pos)` -> `shape.Moved(TopLoc_Location(trsf))`.
  Verified in the source: `Location.__init__` builds `trsf.SetRotation(quat)` with `gp_Intrinsic_XYZ`, then `SetTranslationPart(position)`.
* `a + b` / `cyl += x` -> `BRepAlgoAPI_Fuse` then `ShapeUpgrade_UnifySameDomain(shape, True, True, True)` with `AllowInternalEdges(False)` (build123d does both).
  Keep the same grouping / order: `(cyl + loop) + cyl2`, and `(stripe1 + loop_stripe) + stripe2`.
* Stripe profile `_stripe_profile`: `Circle(ride_radius).edges()[0].trim_to_length(0, ride_radius*2/3)` + `offset_2d(0.075, RIGHT)` + `Face` = annular sector radius
  r - t/2 to r + t/2 (ride_radius = r - t/2); optional `Rotation(Z=extra_deg) * face`. Built directly (see helix.py) with `gp_Trsf` rotation about Z.
  Verified: the arc starts at (r, 0) and runs counter-clockwise by arc length 2/3 r.
* `_loop_stripe_guide`: 41 sample points `path.location_at(t) * Rotation(Z=twist) * Location((r,0,0))`, then `Spline(*points)` -> `GeomAPI_Interpolate(TColgp_HArray1OfPnt, False, 1e-6)` +
  `BRepBuilderAPI_MakeEdge(curve)` (verified in `Edge.make_spline`). `location_at(t)` is the Frenet frame with t a normalised parameter (`param_at`).
* `_loop_stripe`: `sweep(sections=path.location_at(0) * Rotation(Z=start) * profile, path=path, binormal=guide)` -> pipe shell with `SetMode(guide_wire, True)` (the `Wire`/`Edge`
  branch of `Solid._set_sweep_mode`), `Add(profile_wire, False, False)`.

Risk: this file is where visual parity matters most (the stripes must still meet at the joints). Plan: port, then compare against the build123d mesh (vertex /
triangle counts, bbox, and the endpoint `cn`) before touching the cache version. `PJTWireServiceLoop.length_mm` depends on the same numbers, so the numeric constants
are not changed.

**`shapes/disc_ring.py`** -- dead `import build123d`, delete. **`shapes/mesh_cache.py`, `shapes/__init__.py`** -- comments only, reword.

### 4E. Object meshes

**`objects_3d/seal.py::_build_sws` (lines 40-70) and `objects_pegboard/seal.py::_build_sws` (lines 40-59)** -- identical copies.
build123d: `Cylinder(or, L*0.5)` (centered, z -L/4..L/4) moved by `Location((0,0,-L*0.25))` (pure translation here, since the second argument is omitted; in build123d 0.10
`Shape.move` mutates in place and returns self, verified, so the move DOES apply) = z -L/2..0; `Cylinder(or*0.66, L)` centered; fuse; then cut `Cylinder(ir, L)` centered.
OCP: `ocp_ops.shapes.build_sws_seal_mesh(length, o_dia, i_dia)` with `make_cylinder(r, h, centered=True)`, a translation `Moved`, `fuse`, `cut`, then `_tessellate_shape` (defaults 0.001 / 0.5, relative).
Both seal files call the one function (the duplicate `_build_sws` is deleted from the peg-board file, which already imports the 3D module for its mesh id).
The ends of the hole are coplanar with the ends of the outer cylinder; build123d handles that and OCCT does too, but the parity check should confirm the same face count.

**`objects_3d/transition.py` (lines 6, 537-603, 744-752) and `objects_pegboard/transition.py` (lines 6, 322-391, 509-517)** -- `Branch.build_bulb_solid()` builds, per branch, in LOCAL space:
`Plane(origin=(bulb_offset or offset), z_dir=(1,0,0)).rotated(angle_euler_deg)`; `plane * extrude(Circle(max_dia/2), bulb_len)` (a cylinder with its base on the plane, along the plane's Z);
`Plane(origin, z_dir=(1,0,0)) * Sphere(max_dia/2)` at the near end (only when `bulb_offset` is set; see section 2.3 for the pegboard's extra one); and a far-end sphere at
`(bulb_len*cos(angle.z), bulb_len*sin(angle.z), 0) + (bulb_offset or offset)` that is first `rotate(Axis((0,0,0),(1,0,0)), angle.z)` (a rotation of a sphere about its own centre: no change of shape, but it
does change where the sphere's seam / tessellation falls, so keep it for identical meshes). `_build_body_model` then fuses all branches (`body += model`) and tessellates the result.
The meaning of the `Plane` calls (verified in the source and numerically):
  * `Plane(origin, z_dir=(1,0,0))` = `gp_Pln(gp_Ax3(origin, z_dir))`, x axis chosen by OCCT's own rule (it came out as (0,0,1) for z = +X).
  * `.rotated((rx, ry, rz))` rotates the plane's X and Z axes by the intrinsic-XYZ euler rotation (degrees) about the WORLD origin of the plane's vectors and keeps the origin; it builds `Plane(origin, new_x, new_z)`.
  * `plane * shape` = `shape.Moved(Location(plane))`, where `Location(plane)` = `trsf.SetTransformation(gp_Ax3(origin, z, x)); trsf.Invert()` (local -> world).
OCP: `ocp_ops.shapes.build_transition_body_mesh(branches: list[tuple[...]])` where each tuple is plain numbers `(max_dia, bulb_len, angle_euler_deg, offset_xyz, bulb_offset_xyz | None)`, built from `catalog_branch`
by the call site (`Branch.build_bulb_solid` becomes `Branch.bulb_spec()`, no OCP types leave the thread). Inside: `_core.placement()` implements the three bullets with `gp_Ax3`/`gp_Quaternion`/`gp_Trsf`; the cylinder is `BRepPrimAPI_MakeCylinder`
(base at the plane origin, +Z), spheres `BRepPrimAPI_MakeSphere(gp_Ax2(origin, +Z), r)` (build123d uses `Plane.XY` axes, angles -90..90..360), fuse everything in the same order. The 3D and peg-board `_build_body_model` keep their per-part-number VBO pooling and `_FAILED_BODY_IDS`.

**`objects_3d/splice.py::_build_model` (lines 6, 44-73)** -- dead; delete function + import (it only built a cylinder to read its bounding box).

### 4F. Dependency / packaging references

| File | Change |
|---|---|
| `pyproject.toml:38` | remove `build123d==0.10.0` (keep `cadquery-ocp==7.8.1.1`) |
| `.github/workflows/windows.yml:48`, `macos.yml:61`, `unix.yml:87` | remove `build123d==0.10.0` from the pip install lines |
| `builder/scripts/HD.spec:85` | remove `collect_all('build123d')` (check that `OCP` is still collected; build123d's `collect_all` may be what pulled some of its runtime data) |
| `MEMORY.md` | drop the `build123d` line from "Third-party dependencies", update the "Python 3.14t ... drop build123d + VTK" entry, and the TRANSITION_DESIGN.md text that cites `build123d.Plane.rotated()` |
| installed extras | `ocp_gordon`, `ocpsvg`, `vtk` are build123d's dependencies; they leave with it |

## 5. Order of work (each step is verified before the next)

0. **Package + enums + font fix**: turn `ocp_ops.py` into the package (move code as is, add `enums.py`), fix the `_get_font` key. Verify: the text probe again (size 1.0 then 8.0).
1. **Rename sweep** (4A): 15 files, enum rename only. Verify with `py_compile` and `dep_trace.py` (no remaining `build123d.FontStyle/TextAlign`). No rendering change possible.
2. **Text sites** (4B): `shapes/text.py` -> `build_text_mesh` + `font_file_path`; `part_orientation`. Verify: parity of all 4 styles over the ASCII range actually used (compare V/F counts, bbox, glyph widths) between the old and new `_tessellate_char`.
3. **Booleans + primitives** (`_core.py`): `square_outline`, seals, transitions (4D / 4E), including the dedupe of the two seal / two transition builders. Verify: build123d vs OCP mesh, vertex / triangle counts, bbox, volume (`GProp_GProps`), for every catalog transition part (the DB has them) and several seal sizes.
4. **Sweeps** (`_sweep.py`): `helix.py`, `cylinder_helix.py` (both functions). Verify: counts, bbox, volume, `cn`, and the stripe-to-loop joints (overlay the two meshes numerically).
5. **Arrow** (4D).
6. **Remove**: `convert_model_to_mesh`, the dead code, the dependency lines (4F). Run a final `dep_trace.py` check that no `build123d` text is left, delete the stale comments, bump the mesh cache versions, update the MAP files.

build123d stays installed until step 5 is done so every step can be compared against it with a throwaway script (same approach as the text probe used here). The app is not
launched from here; after step 6 the user runs it and checks the transitions, seals, arrow, loop and the text labels visually.

## 6. What was verified for this plan (throwaway scripts, `D:\harness_designer_tmp\scripts`)

* `probe_text.py`: old (`Text` + `extrude` + tessellate) vs `ocp_ops.build_text_mesh`: identical vertex / triangle count and bbox for 4 glyphs x 4 styles at size 1.0;
  size 8.0 differed because of the font-cache bug (section 2.1).
* `probe_geom.py`: `Location` second argument = euler degrees; stripe profile = outward annular sector; helix handedness, start point and length; `Plane(...)` axes for z = +X and after `.rotated`;
  arrow dimensions (section 4D numbers).
* Everything else in this file is from reading build123d 0.10.0's installed source (`Text`/`make_text`, `extrude`, `sweep`, `Solid.sweep`, `_set_sweep_mode`, `Shape.__add__/__sub__/_bool_op/clean`, `Plane`, `Location`,
  `Edge.make_spline`, `Edge.location_at`, `Edge.offset_2d`, `Edge.trim_to_length`, `Wire.make_helix`, `ArrowHead`). Not yet checked: any OCP replacement code below the "recipe" level (none is written).

## 7. Decisions I need from you

1. Keep the 1 degree `Location(pos, (0,1,0))` rotations in `cylinder_helix.py` for identical output (recommended), or drop them and re-tune?
2. Transition bulb: should a branch with no `bulb_offset` have the near end sphere at `offset` (peg-board version) or not (3D version)?
3. Package layout as in section 3 (empty `__init__`, import the submodule you need)?
4. Go ahead with step 0 to 6 in that order (I would stop after steps 0 to 2 for you to run the app, since those touch every note / label)?

## 8. Out of scope, noticed

* `process/model_process.py`, `exporter/exporter.py`, `utils/model_utils.py` (top-level `OCP` imports) bypass the OCP worker thread; for 3.14t they should move into `ocp_ops` later.
  `model_process.py` carries a third copy of the tessellation loop.
* `shapes/MAP.md` / `geometry/MAP.md` describe build123d as a deliberate exception; those paragraphs get rewritten.
