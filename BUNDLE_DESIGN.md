# Bundle design

Single home for everything bundle-specific: how bundles are supposed to work, what has been decided, what is still open, and what the code currently does. Add to this file as the design firms up; do not scatter bundle design into MEMORY.md (which only keeps a pointer here).

Placement of bundles/transitions (the skeleton phase) and how the 3D and peg-board views react to each other are in `BUNDLE_PLACEMENT.md`.

Last updated: 2026-09-26.

Sections:
1. Scope and view rules
2. Design spec (decided)
3. Open questions (undecided -- ask before building on them)
4. Current code state (audit, 2026-09-25)
5. Known bugs
6. Implementation order
7. Decision log

---

## 1. Scope and view rules

- Bundles are visible **only in the 3D view and the pegboard view**. They have **no schematic presence** (confirmed 2026-09-25).
- `objects/objects_schematic/bundle.py` and `bundle_layout.py` stay as the inert stubs every facade carries (same convention as cover/seal/boot in MEMORY.md's "2D schematic scope"). They are not removed.
- A bundle always starts from a wire. Bundles are not placed in free space.
- **A bundle is one object that exists in BOTH views (decided 2026-09-25).** If it exists in 3D it MUST exist in pegboard. Its layouts and waypoints are stored per view and do **not** have to align with each other (different counts, different positions) -- that is fine because the number of them per view is not fixed and is always looked up from the DB. The 1-to-1 wire/bundle layout rule (2.4) applies **within each view separately**.
- "One view at a time" is a build order only, not a data-model split: the bundle row, its start/stop/waypoints and its layouts must end up existing in both views, even while only one view's code is being written.

## 2. Design spec (decided)

**2026-09-26 workflow change (user): SKELETON FIRST, then route wires onto it.** Bundles and transitions are created first (a bundle is placed on its own, transitions attach at its ends); wires are then dragged and dropped onto them and routed through. This SUPERSEDES the "bundle starts from a wire" flow: sections 2.1 (Create New Bundle), 2.2, 2.3 (Extend), the clickable-section rules, the centroid rule and the "move the wire waypoints" idea are OBSOLETE (kept below for history). Still valid: bundles are 3D + pegboard only, a bundle exists in both views, housing points belong to the housing, service loops stay outside bundles, the toolbar Add Bundle button (now places a free bundle), and the 2.6 storage design. See 2.7.

Given 2026-09-25. Supersedes the old toolbar "Add Bundle" wire-snap flow (`Bundle.start_add` in `objects/objects_3d/bundle.py` and `add_handlers/editor_3d/bundle.py`), which spans one whole wire.

### 2.1-2.3 Creation, sharing, extending -- REMOVED (obsolete, superseded by 2.7 on 2026-09-26)

The original create-from-wire flow ("Create New Bundle" on a right-clicked wire section, shared start/stop points, "Extend" with a centroid rule) is fully superseded by the skeleton-first workflow in 2.7. See the decision log for the 2026-09-26 workflow change.

### 2.4 One-to-one rule

- While a wire is inside a bundle, the wire must have a **1-to-1 match with the bundle layouts**: every bundle waypoint/layout has a corresponding wire waypoint.
- Reason: attaching to the bundle waypoints is what lets the wire's length be calculated.

### 2.4b Housing points and service loops -- SUPERSEDED by 2.7

The general rule still stands (housing points -- terminal-back, cavity wire point -- belong to the housing, never a bundle endpoint; service loops sit between a bundle and the housing, not inside it), but the mechanism is now 2.7's housing breakout point + guard rules, not a clickable-wire-section test. See 2.7.

### 2.4c How a wire is tied to its bundle -- SUPERSEDED by 2.6

Early proposals here (a `bundle_id` column on the wire table, then a `pjt_bundle_wires` hub table with anchor/branch columns) are replaced by the `pjt_wire_path` table (2.6). What still stands from this exploration: a wire can be in several bundles, membership must not depend on concentric packing (not every harness is concentric-twisted), and schema changes are free (app unreleased, no migration). Schema changes go in BOTH `harness_designer/database/create_database/` and the sibling builder repo's `create_database` (see MEMORY.md).

### 2.4e Transitions -- storage superseded by 2.6, chain rule stands

- A transition branch has a position, stored in the point table with the transition branch id attached to it. A bundle's start or stop pulls that position and uses it as its own start/stop; the same position is also a wire waypoint.
- **Chain rule:** when a branch position is a wire waypoint, the very NEXT waypoint on the wire must be the transition's own centre position, and the waypoint after that is another branch position of the same transition. **What goes in must come out, or the wire must end via a splice.** (Referenced directly by 2.7.)
- **Splice placement rule (user, 2026-10-03, answering the "what does ending via a splice mean" open question):** a wire that does not come back out another branch must exit or attach to a splice, and that splice is located INSIDE the transition. Splices can also exist inside a bundle's own span -- EXCEPT when the bundle uses concentric twisting, where a splice inside the bundle is not allowed. When concentric twisting is in use, a splice must instead sit either outside the bundle or inside a transition. (The existing `PJTSplice`/`objects/splice.py` model is the current 2-wire-in-1-branch-out shape, already flagged by its own module docstring TODO for a rewrite to a diameter-driven point-count model -- that rewrite is a separate, not-yet-scoped task; this placement rule is about WHERE a splice may sit relative to a bundle/transition, independent of that still-pending point-count rework.)

### 2.4d Joining wires, and the toolbar -- mechanics superseded by 2.7

The "click and drag to join" idea and the toolbar Add Bundle button's continued existence are carried forward into 2.7's dragging-a-wire-onto-a-terminus flow, which fully specifies the mechanics this section only sketched.

### 2.5 Schema constraint to respect

- `pjt_points3d` and `pjt_points_pegboard` rows are tagged `wire_id` **or** `bundle_id` (plus `idx`), never both, and a row can only carry one `wire_id`. So one row cannot be a waypoint of several wires; the wire-table bundle-id column (2.4c) is the way around it.
- Bundle start/stop are FK columns on the bundle row (not waypoint-tagged), so a wire's waypoint row can be a bundle's start/stop without conflict. The conflict only appears when an end becomes an interior bundle waypoint on extend, or when several wires share one point.
- A `PJTBundleLayout` row is exclusive to one view (`point3d_id` xor `point_pegboard_id`).

### 2.7 Skeleton-first routing (user, 2026-09-26)

**The harness skeleton.** Bundles are the edges, transitions the nodes. A *terminus* is a place a wire can enter or leave: a bundle end that is not attached to a transition (a *free end*), or a transition branch with nothing attached (a *free branch*).

**Dragging a wire.** The wire must already be drawn; the user clicks it and drags it onto the skeleton.
- Valid drop = a terminus only.
  - A bundle with a free end: OK. A bundle with no free end: the drop is BLOCKED.
  - A transition: only onto a free branch.
  - A branch with a bundle attached: if that bundle has 1 free end, treat it as a drop on the bundle; if it has none, BLOCKED.
- From the entry point the wire is routed along the bundle to its far end. At a transition the route STOPS at the transition centre and the user selects the next bundle (or exit branch) to route down. This repeats until a free end is reached. "What goes in must come out, or it must end via a splice" (2.4e).

**Where the route starts (user, 2026-09-26, confirmed):** the wire section that is dragged onto the bundle/transition branch is where the attachment with the shared points begins. A section is the stretch between two consecutive points of the wire's own path, P(i) and P(i+1); the wire's own points up to P(i) stay, the direct P(i)-to-P(i+1) line is dropped, and the route to the entry terminus and along the skeleton replaces it.

**Confirmed 2026-09-26:** after the route reaches its exit terminus, the wire's remaining own points (P(i+1) onward) resume from there, so the route is a detour spliced between P(i) and P(i+1). The user handles deleting any extra wire waypoints/layouts and shortening the wire; nothing deletes them automatically.

**Guard waypoints (user, 2026-09-26): there MUST be a single wire waypoint placed before the wire enters and another after the wire exits the bundle/skeleton route. The user cannot delete those waypoints; they must always exist.** Each has a wire layout like any waypoint. If the wire's own P(i) is a housing/terminal point or the crimp start it cannot serve as the guard, so one is created.
- **Ownership and movement (user, 2026-09-26):** a guard is NOT owned by the bundle; it is owned by the wire. It is attached to the bundle so that it can only move when the free end of the bundle moves. It cannot be moved when the wire segment connected to it moves, and it cannot be clicked on and moved directly. (Supersedes my earlier assumption that a guard could still be moved.) Segment drags therefore stop at a guard and the segment stretches.
- **Several guards per bundle end:** there can be more than one guard attached to a bundle, because of how a wire is terminated after it exits the bundle (wires leaving one bundle end go to different terminations).
- **Guards are shared per group (user proposal 2026-09-26, I agree; pending confirmation of the open items):** because a bundle can have 100+ wires and the guard moves with the bundle, all wires of one group share ONE guard point per bundle end. A group is by housing, terminal, or free. So a guard is one shared point row referenced by every member wire's path row (not one per wire; the earlier "owned by the wire" wording means the wire references it, not that each wire has its own). **Guard position (user, 2026-09-26):** the guard sits ALONG THE LINE from the group's center to the bundle's actual end, at the guard distance from the bundle end. The line is only a geometric construction used to compute the position -- it is not literally drawn (never rendered) and not stored. The center is the housing's center for a housing group, the terminal's center for a terminal group, and for FREE wires the centroid of the group's wire ends. So all free wires leaving one bundle end form ONE group with one shared guard (this also answers "is each free wire its own group": no). **Guard movement rules confirmed 2026-09-26 (user):** (1) when the BUNDLE END moves, the guard's angle to the bundle end stays constant (the guard follows rigidly, same direction and distance); (2) when the group's CENTER moves (e.g. a housing is moved, or a terminal, or the free-end centroid changes), the guard's angle to the bundle end is RECOMPUTED and the guard is moved to sit on the newly computed line at the guard distance. Consequence: after only a bundle-end move the guard need not lie on the center-to-end line until the center next moves. No stored angle is needed: the direction is always the current vector from the bundle end to the guard (a rigid follow keeps it; a center move overwrites it).
- **Placement (user, 2026-09-26): a set distance from the bundle end**, on both the entry and the exit side. **Distance accepted 2026-09-26: the larger of a config minimum (mm) and a config multiple of the bundle's diameter**, both under the editor config; the same rule is used for a free bundle end and for waypoint placement generally. It is NOT the housing standoff.
- **Restated by user 2026-09-26:** the guard CAN move, but only when the bundle end moves.
- **Pending (my reading):** a guard is a wire path row with its own point row, whose position is driven by the bundle end through a point callback; it is locked against direct edits and against segment-drag propagation. How several guards are laid out around one bundle end is open.

**Removing a wire (user, 2026-09-26):** a wire can NOT be dragged out of the bundle/transition path. Instead a table, like the one the pegboard view already has, is shown for the 3D view too; in 3D the direction the table faces tracks the camera. The table lets the user locate a wire, right-click it and choose **"Remove from bundle/transition"**, at which point the wire is drawn directly between its two mandatory guard waypoints (the ones at the enter and exit sites). That is why the guards MUST always exist. Consequences: every skeleton row for that wire is removed from its path; the guards become ordinary waypoints; concentric packing is recomputed for each bundle it left. New feature implied: a camera-facing (billboard) wire table for 3D (the pegboard table code, `objects_pegboard/pegboard_table.py`, `ui/pegboard_table/`, and the bundle "Show Table" menu item exist as reference; the same right-click removal may be doable in the pegboard tables sooner). Until it exists there is no way to remove a wire from the skeleton in 3D.

**3D table geometry (user, 2026-09-30):** unlike the peg-board table (a flat quad effectively pinned to the peg-board plane, `y` fixed/derived), the 3D billboard table gets all three position coordinates set freely (it floats wherever it's placed/tracked in true 3D space, not projected onto a plane). The captured table image is rendered onto a real box (not a zero-thickness quad) with a depth of 0.1 mm -- i.e. `objects_3d.pegboard_table`'s eventual VBO/scale should mirror the peg-board table's rectangle mesh but with a genuine, if thin, third dimension instead of collapsing it to 0.

**Entry end for a bundle with two free ends (user, 2026-09-26):** the closest waypoint on the wire to the closest end of the bundle. Confirmed 2026-09-26: "closest waypoint" is measured over only the 2 waypoints involved in the drag (the two points of the dragged section, P(i) and P(i+1)), not all of the wire's waypoints.

**Still pending (my reading):** a wire with one dangling end just ends at the exit terminus.

**Rules confirmed 2026-09-26 (user):**
- **Dangling wires:** a wire with a dangling end cannot be placed in a bundle. Dragging onto a bundle or transition has a hard requirement that the dragged thing be a section between 2 waypoints.
- **Empty bundles:** when a bundle's last wire is deleted the bundle remains, empty, and the user deletes it manually. A bundle or transition CANNOT be deleted while any wire is inside it. (So the `_delete` on `objects_3d/bundle.py` that restores member wires' visibility, added 2026-09-25, is obsolete and should be removed in the storage rewrite; deleting a wire that is inside a bundle just removes its rows.)
- **Layouts:** a bundle layout attaches like a layout on a wire. The layout's point must be inserted into the routing table (`pjt_wire_path`) for EACH wire in the bundle, with the index correct for each wire (indexes differ per wire and per direction).
- **Branch concentric:** not worked out yet.

**Housing breakout point (user's algorithm, 2026-09-26; my reading CONFIRMED as "spot on"):** collect the wire layout positions at the cavity points; take their centroid C; R = the furthest distance from C to any cavity wire layout/waypoint; the target distance is 2R. Pull C away from the housing on the wire side, square to the back of the housing, until that furthest cavity point is 2R from the moved point (a distance of sqrt(3)*R behind the housing, a 30 degree fan each side). The moved point is the mandatory enter/exit waypoint of the housing. Clarified 2026-09-26:
- It says where wires leave the HOUSING. It does NOT describe where a bundle should start or end; that is the guard rule above (the same problem as a free bundle end).
- It is computed from ALL wires common to a single housing (not only those in one bundle). Each housing gets its own point; one group of wires can exit one housing and another group another housing.
- Wires attached to a terminal and free-floating wires that exit the same position are handled the same way, in the manner in which the wire terminates when exiting the housing.
- **The calculated distance is a MINIMUM (user, 2026-09-26): the position cannot be any closer to the back of the housing than the calculated distance.** So it is a constraint on where the housing's mandatory point (and anything else of the wire's) may sit, not just a default. No extra floor has been asked for: for R = 0 (a single-cavity housing, a lone free terminal or a free wire end) the calculated distance is 0.
- **User question 2026-09-26 (it was a question, NOT a decision -- an earlier note here wrongly called it accepted):** is the calculated minimum a reasonable amount for the housing? My assessment: reasonable for a typical multi-cavity housing (outermost wire converges at 30 degrees off the back-face normal), but it under-shoots for a small or single-cavity housing (R near 0 gives a distance near 0, so the wire would bend right at the seal) and it ignores anything sticking out behind the housing (boot, cover, backshell). Suggested: distance = max(sqrt(3)*R, config multiple of the largest wire OD in the group, depth of any boot/cover on that housing). **Agreed 2026-09-26: the housing distance gets a LOWER CLAMP** (distance = max(sqrt(3)*R, floor)). **Floor decided 2026-09-26 (user): the same floor logic as the guard distance from a bundle end** -- floor = max(config minimum in mm, config multiple of a diameter), reusing the same config values; no boot/cover-depth term (so the breakout point can still land inside a boot; accepted). **Diameter (user, 2026-09-26): the housing point is only calculated when a wire is being added to a bundle, so the diameter is that bundle's diameter, which is readily available.** (Supersedes my suggestion of the wire group's effective diameter.) **Recompute rule confirmed 2026-09-26:** the housing's point is recomputed every time a wire from that housing joins a bundle, using the LARGEST diameter among the bundles that housing's wires enter, and it never moves closer to the housing (it only ever moves outward, so earlier-routed wires never end up violating the minimum).

**Guard distance:** accepted as the larger of a config minimum and a config multiple of the bundle diameter (see the guard paragraph above).

**A routed wire, end to end:** cavity point -> housing breakout point (mandatory, shared by that housing's wires) -> own waypoints -> entry guard -> bundle/transition route -> exit guard -> own waypoints -> housing breakout point at the far housing -> cavity point.

**Effects on storage.** A wire's route is topology (bundle + direction, transition + in-branch/out-branch); its `pjt_wire_path` rows are generated from it for each view from that view's skeleton points. Later skeleton edits (adding a bundle waypoint) still fan out to every routed wire in one transaction. Concentric packing is recomputed for each bundle along the route as wires are added.

### 2.6 Storage design: `pjt_wire_path` (converged 2026-09-26)

**Problem it solves.** The same shared components sit at different positions in different wires' waypoint lists, so an index cannot live on the point row.

**Standard test scenario (user, 2026-09-25).** Wires X and Y; bundles A (3 waypoints), B (6), C (10); transitions M, N, O. A: one free end, other end on a branch of M. B: M branch to N branch. C: N branch to O branch. Wire X runs through A, B, C; wire Y enters at an M branch and runs through B and C.
- Wire X, in order: 0 A start; 1-3 A waypoints; 4 M branch/A end; 5 M centre; 6 M branch/B start; 7-12 B waypoints; 13 N branch/B end; 14 N centre; 15 N branch/C start; 16-25 C waypoints; 26 O branch/C end; 27 O centre; 28 O branch.
- Wire Y, in order: 0 M branch; 1 M centre; 2 M branch/B start; 3-8 B waypoints; 9 N branch/B end; 10 N centre; 11 N branch/C start; 12-21 C waypoints; 22 O branch/C end; 23 O centre; 24 O branch.
- Same points, different indexes per wire. Any storage design must reproduce both lists.

**Table (user's design, adopted).**
```
pjt_wire_path
  id                  project-scoped UUID like every pjt table
  wire_id             NOT NULL -> pjt_wires.id
  point3d_id          NULL -> pjt_points3d.id
  point_pegboard_id   NULL -> pjt_points_pegboard.id
  point2d_id          NULL -> pjt_points2d.id
  idx                 NOT NULL
  bundle_id           NULL -> pjt_bundles.id            (row lies inside this bundle's span)
  concentric_id       NULL -> pjt_concentrics.id        (only when concentric twisting is used)
  transition_id       NULL -> pjt_transitions.id        (branch positions and the transition centre)
  transition_branch_id NULL -> pjt_transition_branches.id  (branch positions)
```
Four tag columns added by the user 2026-09-26. Every row always has `wire_id`, exactly one point column and `idx`; the four tag columns describe what the row is. Row meaning: ordinary wire point = none of the four tags set; point inside a bundle span = `bundle_id` (+ `concentric_id` if twisted); branch position = `transition_branch_id` + `transition_id`; branch position that is also a bundle's end (e.g. M branch / A end) = branch columns + `bundle_id` (the bundle shares the branch's position, so the row of any branch that has a bundle plugged in always carries that bundle's id; a branch with NO bundle plugged in leaves `bundle_id` NULL, e.g. wire Y row 0 and wire X row 28 in the test scenario; user confirmed 2026-09-26: `bundle_id` is optional); transition centre = `transition_id` only. `transition_id` is derivable from the branch but kept for direct "which wires go through transition M" lookups.
- Exactly one of the three point columns is set (enforced in the table's `insert()`, like the layout tables). One table therefore holds a wire's 3D, pegboard and schematic lists; each view's list is that view's rows ordered by `idx` (independent per view).
- Each wire owns one row per point in its route. Rows reference SHARED point rows, so bundle waypoints, transition branch positions, transition centres and housing points are single point rows referenced by many wires' path rows. Moving a shared point updates one point row, no path rows.
- Direction needs no flag: each wire lists its points in its own order.
- Length = sum of consecutive path rows in `idx` order (twist factor for concentric spans applied on stretches known to be inside a bundle).
- Point rows carry NO owner tags any more (`wire_id`, `idx`, `parent_point_id` on the point tables are to go; the per-wire clone mechanism is unnecessary).
- Recommended: unique (wire_id, point column, idx); contiguous `idx` (a structure change already touches each wire's rows, so spacing gains little).
- **No `project_id` column** (confirmed 2026-09-26): ids already embed the project id, project scoping is the id-prefix range (`_project_id_bounds`). Bulk project load = one range scan per table; a stored column would add nothing and could disagree with the id. Any future schema-wide `project_id` column is a separate task.

**Lookups (all from this one table, index the tag columns).** A wire's bundles/transitions/concentrics = its rows with those columns set. A bundle's wires and concentric = distinct `wire_id`/`concentric_id` over rows with that `bundle_id`. A transition's wires = rows with that `transition_id`. A concentric's bundle and wires = rows by `concentric_id`. No separate membership/hub table and no `pjt_bundle_path` table are needed (both proposed earlier, dropped 2026-09-26): membership IS the tagged rows; a bundle's own waypoints stay as today -- point rows tagged with the bundle id + `idx`, plus its start/stop links on the bundle row (only the wire tag on point rows goes away).

**Rules and costs.**
1. Bundle structure changes (Extend, adding/removing a bundle waypoint) fan out: a row is inserted into every member wire's path, in ONE transaction, so the bundle and its wires cannot disagree. Moving points has no fan-out. Tag values repeat on every row of a span, so add a validation check.
2. 1-to-1 rule check: for each member wire, the number of its rows with that `bundle_id` equals the number of the bundle's points in that view.
3. The transition rule (branch position, centre, another branch position or a splice) is checked from the tags.
4. A wire's slot in the twist (layer, position) stays in the concentric wires table keyed by concentric + wire. `pjt_concentrics` loses `bundle_id`.
5. A point is deleted only when no path row (wire or bundle) and no structural owner (cavity, terminal, transition branch) references it; shared points are edited in place, never replaced.
6. Layouts: still to decide how wire/bundle layouts attach (per point, exclusive per view, as today).

**Open on this design (updated 2026-09-26).** Answered: empty bundles stay (blocked-delete rule, 2.7); layouts insert a row into every member wire's path. Still open: how a transition branch's own concentric fits the path rows (and whether a plugged-in bundle's concentric equals its branch's).

## 3. Open questions

The original 5 questions here (pegboard span mapping, housing standoff, wire-to-bundle column details, click-and-drag-to-join mechanics, which cover part a right-click uses) were all obsoleted or answered by the 2026-09-26 skeleton-first workflow change (2.7) and the `pjt_wire_path` storage design (2.6). Live open items now live at the end of 2.6 and in 2.7/`BUNDLE_PLACEMENT.md`.

**ANSWERED 2026-10-03:** "must end via a splice" -- see 2.4e's new splice-placement rule (splice inside the transition, or inside a bundle unless that bundle is concentric-twisted, in which case outside the bundle or inside a transition). **ANSWERED (already, via 2.6):** a wire with no bundle plugged into a branch still has a `pjt_wire_path` row at that branch position -- `transition_id`/`transition_branch_id` set, `bundle_id` left NULL (2.6's own test-scenario rows for wire Y row 0 / wire X row 28 already show this; `bundle_id` is explicitly optional per 2.6's row-meaning paragraph). No remaining genuinely-open items in this section as of 2026-10-03.

## 4. Current code state (audit, 2026-09-25)

Static read of the code plus `diagnostics/dep_trace.py`; the app was not run.

### Written, but never run

User, 2026-09-26: **none of the bundle code has ever been tested.** Everything in this section (and every routing handler, including `RouteThroughBundleHandler`/`RoutedWireHandler`, which also have no UI entry point) is an untested draft judged only by reading it. Nothing here is a constraint on the design; reuse it only where it has been read and checked.

- **DB.** `pjt_bundle` (3D and pegboard start/stop, `waypoints3d`/`waypoints_pegboard`, `length_mm`, smooth, table overlay). `pjt_bundle_layout` (exclusive per view). `pjt_concentric`/`_layer`/`_wire` tables.
- **Facade.** `objects/bundle.py` builds `obj3d`, `objpegboard`, `objschematic` (stub). Keeps the bundle-to-Transition sibling graph; rebuilt on load by `_reconcile_bundle_sibling_graph` in `objects/project.py`.
- **3D.** Multi-segment render and per-segment picking; toolbar placement by wire-snap; waypoints (`BundleLayout`); rigid whole-path drag (`drag_handlers/editor_3d/bundle.py`); transition attach; `merge_bundles` (`handlers/bundle_topology.py`); wire-contents dialog; context menu; BOM cut sheet.
- **Pegboard.** Multi-segment render and picking; segment drag with length budget (`drag_handlers/editor_pegboard/bundle.py`); Add Waypoint; table overlay; context menu. The pegboard toolbar only enables Connector, so bundles cannot be created there today.

### Missing or wrong (relative to the spec above)

1. **New or merged bundles are degenerate in pegboard.** `start/stop_position_pegboard` auto-create at (0,0,0) and nothing seeds them. `add_handlers/editor_3d/bundle.py` `_finalize` never sets them; `merge_bundles` migrates only the 3D points/waypoints and then deletes both originals. Depends on open question 1.
2. **Wire membership is split across two mechanisms.** Only `_finalize` writes concentric rows (one layer, one wire). The "Add to bundle" menu items (3D `objects_3d/wire.py` `WireMenu.on_add_to_bundle`, pegboard `objects_pegboard/wire.py` `WireMenu.on_add_to_bundle`) only call `obj3d.add_wire`, an in-memory weakref plus hide, with no concentric row. Membership is lost on reload and invisible to `PJTBundle.wires`, the dialog and the table overlay. Nothing rebuilds `obj3d._wires` from the concentric rows on load. Closest-bundle selection is by midpoint distance with no diameter-fit check.
3. **Pegboard wire visibility is wrong.** The pegboard `Wire.is_visible` setter writes `db_obj.is_visible` (the 3D column), so hiding in one view hides in the other; it should use `is_visible_pegboard`. Nothing sets `is_visible_pegboard` from bundle membership. The "leader"/bare-end exception (a wire's exposed tails outside the bundle) is not handled; the pegboard bundle docstring says its spec lives in TODO.md, but TODO.md is currently empty, so that spec may be lost.
4. **Diameter and packing.** `PJTBundle.diameter` returns a concentric row id and its setter is a stub. There is no packing solver (see MEMORY.md "Wire bundle packing requirements"): adding a second wire does not create or recompute layers. `layers[-1].diameter` raises `IndexError` on an empty concentric (both bundle-layout view objects and `PJTBundleLayout.diameter`). **FIXED 2026-09-29 (guards only, not the underlying stub) -- and concentrics DETACHED FROM BUNDLES for the time being (user decision):** a skeleton bundle no longer gets an empty placeholder `pjt_concentrics` row at placement time at all (`objects_3d.bundle.Bundle.start_add`/`_new_placeholder_bundle_db`) -- same treatment `PJTTransitionBranch` already got (section 3, question 5 below). `PJTBundle.concentric` now returns `None` (guarded `select()`, was an unguarded `[0][0]`) instead of crashing, and every reader (`PJTBundle.wires`/`.diameter`, `objects_3d/objects_pegboard` `Bundle.__init__`'s diameter/color seeding, both `BundleLayout.__init__`s and `PJTBundleLayout.diameter`) was updated to treat `None`/empty as the normal case, preferring the bundle's own live view-object diameter when one exists. `pjt_concentrics`'s own schema also had a real bug this surfaced: `transition_branch_id` was `NOT NULL` with no default even though `PJTConcentricsTable.insert()`'s own signature already typed it `bytes | None` (a bundle-only concentric, `transition_branch_id=None`, could never satisfy it) -- fixed to nullable. Also fixed in the same pass: `pjt_bundles.start_point3d_id`/`stop_point3d_id` are `NOT NULL` with no default, but `PJTBundlesTable.insert()` never accepted them -- every caller inserted the row then set them after, which could never satisfy the constraint; `insert()` now takes them as required params (`objects_3d/bundle.py`, `handlers/bundle_topology.py`, `handlers/transition_handler.py`'s dead `_insert_bundle` all updated). None of this had ever been caught before because none of this code had ever actually run until skeleton bundle placement (section 3 of `BUNDLE_PLACEMENT.md`) did.
5. **Menu parity.** The pegboard bundle menu lacks Wire Contents and Add Transition, which 3D has. Pegboard "Add to bundle" reaches into `obj3d`.

## 5. Known bugs

**Fixed 2026-09-25 (3D step 1, syntax-checked only, not run):**
- `PJTBundle.delete()` and `PJTBundleLayoutsTable.get_from_position3d_id` now query the real `point3d_id` column (`get_from_position3d_id` has no callers; method name kept).
- Bundle delete now restores member wires' 3D visibility: new `_delete` on `objects_3d/bundle.py` `Bundle` reads membership from the concentric rows (not the in-memory `_wires`) and sets `wire.obj3d.is_visible = True`; the dead facade `_delete` in `objects/bundle.py` was removed.

**Still open:**
- **New gap found while fixing the above:** deleting a *wire* never removes its `pjt_concentric_wires` row (nothing in `pjt_wire.py`, `objects/wire.py` or `objects_3d/wire.py` touches concentric). A bundle can therefore hold a dangling membership row, and the new `_delete` above would raise on `concentric_wire.wire.get_object()` returning `None` when that bundle is deleted. Needs a real design answer (what happens to a bundle when one of its wires is deleted) as part of the membership work; deliberately not papered over with a None-guard.
- Pegboard `Wire.is_visible` writing the 3D column (pegboard step, later).
- Items 3 and 4 of section 4 (visibility, diameter/packing) are also bugs in their own right.

## 6. Implementation order

**Approach (decided 2026-09-25): one view at a time, 3D first.** Pegboard-specific code (e.g. computing a bundle's length there) is deliberately deferred until both views' bundle code is mostly written.

**Approach detail:** Each view gets the full spec (Create New Bundle, Extend, shared waypoints, 1-to-1 layout rule, visibility, delete) working end to end before starting the next. Order of views is not yet fixed; 3D is the proposed first, since the existing bundle code and the wire-snap flow live there. Because a bundle must exist in both views (section 1), the 3D work needs at least a minimal pegboard counterpart (start/stop points in the pegboard tables) from the start; how it is derived is open question 1. Pegboard-specific behavior beyond that (e.g. length) comes later.

**Phased plan (user, 2026-09-26; supersedes every older step list, which were based on the obsolete create-from-wire workflow). Storage migration comes FIRST:**

- **Phase 1 -- add the `pjt_wire_path` table to the schema and create the Python classes needed to interact with it** (table class + entry class, exclusivity/validation in `insert()`, lookups per wire/view/bundle/transition/branch). Schema goes in both `create_database` locations (see 2.4c).
- **Phase 1 status (2026-09-26): WRITTEN, NEVER RUN (py_compile only).** New files `database/create_database/wire_paths.py` (schema) and `database/project_db/pjt_wire_path.py` (`PJTWirePathsTable`/`PJTWirePath`), registered in `pjt_bases.py` (`pjt_wire_paths_table`). Notes: table named plural `pjt_wire_paths` to match every other table (rename if the singular is wanted); all four tag columns and the three point columns are real FK columns; not added to the sibling `harness_designer_database` repo (already drifted, it lacks the newer tables); the schema DSL (`SQLTable`) has NO multi-column UNIQUE constraint and NO indexes, so the planned unique (wire_id, point column, idx) constraint and the indexes on the tag columns are not in place -- lookups are unindexed `SELECT`s like every other table's; adding index support to the connector is a separate decision.
- **Phase 2 + 3 status (2026-09-26): WRITTEN, NEVER RUN (py_compile only).** Decisions taken along the way (user): the new tables are the ONLY source of waypoint order -- bundle waypoints moved too (option B), so a new `pjt_bundle_paths` table (`create_database/bundle_paths.py`, `project_db/pjt_bundle_path.py`, registered as `pjt_bundle_paths_table`) exists beside `pjt_wire_paths`; `wire_id`, `bundle_id` and `idx` were removed from the three point tables (schema + `PJTPoint3D`/`PJTPoint2D`/`PJTPointPegboard` properties, `insert()` kwargs, `for_wire`/`for_bundle`); `parent_point_id` deliberately STAYS (the terminal/cavity clone mechanism, see 2.6 notes); no migration -- the app is unreleased, existing databases simply keep the old unused columns. Writers switched to `pjt_wire_paths_table.add/append/remove/set_route`: `add_handlers/editor_3d/wire.py`, `add_handlers/editor_pegboard/wire_layout.py`, `handlers/wire_layout_handler.py`, `handlers/wire_topology.py` (split/merge), `handlers/wire_drag_base.py` (merge), `handlers/wire_slack.py`, `objects/terminal.py` (attach/detach), the three `objects_*/wire_layout.py` delete paths, `objects_schematic/wire.py`, `wire_routing/reroute.py`, `drag_handlers/editor_schematic/wire.py`. Bundle writers switched to `pjt_bundle_paths_table`: `handlers/bundle_layout_handler.py`, `add_handlers/editor_pegboard/bundle_layout.py`, `handlers/bundle_topology.py` (merge), `objects_pegboard/bundle_layout.py`, `PJTBundleLayout.attached_bundles`. `PJTWire.delete`/`PJTBundle.delete` delete their own path rows; `PJTWireLayout.attached_wires` and the three point classes' `is_referenced()` now read the path tables. Things to watch when it is first run: split/merge must clear the ORIGINAL wire's/bundle's rows before deleting it (else its delete sweeps layouts the new one still uses -- done, untested); `PJTBundle` merge only carries the 3D waypoints (pre-existing gap: peg-board waypoints of merged bundles are dropped); a bundle waypoint added later is NOT yet inserted into the routes of wires running through the bundle (comes with wire routing); the `_delete` on `objects_3d/bundle.py` added 2026-09-25 is obsolete per the empty-bundle rule and still there.
- **Phase 2 checklist (found while doing phase 1; items (b), (c) and (d) are DONE as above):** (a) `PJTTableBase._find_unreferenced_point_ids` (pjt_bases.py) finds referencing columns by NAME SUFFIX and would not match the new plain `point3d_id`/`point2d_id` columns -- user 2026-09-26: that code is not currently used, so it will be fixed at a later date; (b) `PJTWire.delete()` must call `pjt_wire_paths_table.delete_for_wire`; (c) point-table deletion checks (`pjt_point3d.py` ~714, `pjt_point_pegboard.py` ~588, `pjt_point2d.py` ~356) need the new table added; (d) every reader of `waypoints3d`/`waypoints_pegboard`/`for_wire()`/`for_bundle()`.
- **Phase 2 scope confirmed 2026-09-26 (user):** the path rows hold a wire's INTERIOR waypoints only; the wire's start and stop stay as columns on the wire, exterior to the waypoint list, exactly as today. The full route (including endpoints) may come later with the skeleton routing. A bundle's own waypoints stay tagged on the point rows (proposed, not yet confirmed).
- **Phase 2 design (user, 2026-09-26):** every writer goes through ONE entry point, on the table class, and index renumbering happens there. None of the existing writers needs batching (they are per-row `wp.wire_id = x; wp.idx = i` loops; there are no batch inserts; the only `batch_update` in this area moves housing points and never touches path rows). `PJTWirePathsTable` now has `add(wire_id, view, index, point_id, ...)`, `append`, `remove(wire_id, view, point_id)`, `set_route(wire_id, view, point_ids)`, `for_wire(wire_id, view)`, `for_point`/`wire_ids_for_point`; `add`/`remove` renumber the following rows in a single `batch_update`. `PJTWire.waypoints3d`/`waypoints2d`/`waypoints_pegboard` keep returning the same point-row objects, now read from the path rows, so readers do not change.
- **Phase 2 -- update the existing code that uses the point rows to track waypoints (`wire_id`/`bundle_id`/`idx` tags, `for_wire()`/`for_bundle()`, `waypoints3d`/`waypoints_pegboard`) so it uses the new table instead.**
- **Phase 3 -- remove the columns from the point tables that no longer need to be there** (`wire_id`, `bundle_id`, `idx`, and `parent_point_id` if nothing else uses it).
- Then, in order: the skeleton without wires (bundles/transitions created and working, 3D first; a minimal pegboard counterpart), the tables (pegboard-style, camera-facing in 3D; attach to bundles and transitions, possibly housings and splices), wires onto the skeleton (routing, guards, housing breakout points, removal), concentric twisting, then pegboard-specific behavior.

**Pending for the skeleton phase (my suggestion):** a free bundle placed in one view gets its other-view start/stop from the x/z projection of the placed points, the way a housing placed in 3D gets a pegboard position (x, 0, z) and vice versa.

## 7. Decision log

- 2026-09-25: Build one view at a time (section 6).
- 2026-09-25: A bundle exists in both views; per-view layouts/waypoints independent (section 1).
- 2026-09-25: App is unreleased and no bundles exist in any project: no migration, no backwards compatibility, schema changes free.
- 2026-09-25: Housing points (terminal back, cavity wire point) belong to the housing; not clickable, not bundle endpoints; bundle keeps a standoff from the housing; service loops can't be in a bundle (2.4b).
- 2026-09-25: Wire table gets a bundle-id column; wire pulls the bundle's waypoints as its own (2.4c).
- 2026-09-25: Wires join a bundle by click and drag (2.4d).
- 2026-09-26: Workflow changed to skeleton-first: create bundles and transitions, then drag drawn wires onto termini (free bundle ends / free branches); route stops at each transition centre until the user picks the next bundle; blocked otherwise (2.7). Old create-from-wire/Extend/centroid spec obsolete. None of the existing bundle code has ever been tested.
- 2026-09-26: Detour confirmed; a single undeletable guard waypoint must exist before entry and after exit of the skeleton route (2.7).
- 2026-09-26: Wires are removed from the skeleton only via a wire table (billboard in 3D) right-click "Remove from bundle/transition", never by dragging out; the wire is then drawn between its two guards (2.7).
- 2026-09-26: Guards are wire-owned, attached to the bundle end so they move only when the free end moves (not clickable, not moved by adjacent segments, several per bundle end); guard distance = max(config minimum, config multiple of bundle diameter); the housing breakout point is per housing, from all wires common to that housing, and is not a bundle-placement rule; the calculated distance is a minimum (lower clamp agreed: same floor logic as the guard distance).
- 2026-09-26: Phased plan (section 6): storage migration first -- phase 1 add `pjt_wire_path` + Python classes, phase 2 move existing waypoint code onto it, phase 3 drop the now-unneeded point-table columns; then skeleton without wires, tables, wire routing, concentric twisting, pegboard-specific behavior. Tables attach to bundles and transitions, possibly housings and splices (undecided).
- 2026-09-26: Dangling wires can't join a bundle (dragged section must be between 2 waypoints); empty bundles stay and can't be deleted while wires are inside; bundle layouts insert a row into every member wire's path; housing standoff algorithm given (2.7).
- 2026-09-26: Storage = `pjt_wire_path` (user's design): one row per point per wire, exactly one of three point columns, `idx` per wire; shared point rows carry no owner tags; NO `project_id` column (ids embed it). Supersedes hub/anchor/branch-column ideas (2.6). Four tag columns on the path table (`bundle_id`, `concentric_id`, `transition_id`, `transition_branch_id`) replace the companion tables and the hub (2.6).
- 2026-09-25: Transition branch position lives on the point table tagged with the branch id; bundle ends and wire waypoints read it from there; wire chain through a transition is branch position, transition centre, another branch position (or ends at a splice) (2.4e).
- 2026-09-25: Transition branch added to the hub table (`pjt_bundle_wires`) as start/stop branch columns (up to 2 per bundle) -- placement pending, see 2.4c.
- 2026-09-25: A wire can be in several bundles; membership lives in a new `pjt_bundle_wires` table (wire, bundle, per-view splice anchors, optional concentric link), not in the concentric tables and not a `pjt_wires` column (2.4c).
- 2026-09-25: Toolbar Add Bundle button stays (2.4d).
- 2026-09-25: Bundles always start from a wire via right-click "Create New Bundle"; waypoint-to-waypoint only; extend via bundle right-click; central-point rule; 1-to-1 wire/bundle-layout rule (section 2).
- 2026-09-25: Bundles are 3D and pegboard only; schematic stubs stay inert (section 1).
- 2026-10-03: Splice placement answered (2.4e, section 3): a wire ending via a splice (not coming back out another transition branch) attaches to a splice located INSIDE the transition; a splice may also sit inside a bundle's own span, except when that bundle is concentric-twisted, in which case the splice must be outside the bundle or inside a transition instead. The existing `PJTSplice` 2-wire-in/1-branch-out model's own pending diameter-driven point-count rewrite (its module docstring TODO) stays a separate, not-yet-scoped task -- this only settles WHERE a splice may sit, not its internal shape.
- 2026-09-30: The 3D billboard table (still unbuilt) gets all three position coordinates set freely, unlike the peg-board table's plane-pinned position; its captured image renders onto a real box with 0.1 mm depth, not a zero-thickness quad (2.7).
