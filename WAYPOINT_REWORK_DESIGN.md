# Wire / bundle / cable rendering and waypoint rework (spec from the user, 2026-11-08)

Written down the moment it was given, so it survives a context compaction. Status lines at the bottom.

## The request (the user's words, condensed, nothing dropped)

1. The batched wire rendering works ("the wire is rendering properly"). **Enable everything, remove the check boxes**
   (`pooled_wires`, `batched_wires`, and what `gpu_single_wires` switches) and **remove any old unused code from the old way
   the wire was rendered.**
2. **Bundles** get upgraded to render the same way as wires (pool + batch). **Keep the curved corners.**
3. **Layouts are no longer rendered.** Where a waypoint would be drawn on the curve of the wire, the waypoint is instead made
   **draggable when the wire is selected.** Today, with a wire selected, what can be dragged is the two ends and a middle
   section, NOT the waypoints. Waypoints become draggable. **The dragging code is the same for wires, bundles and cables.**
4. **Pegboard editor**: check whether the curved corners render there; if not, add them. The new wire rendering is also done in
   the pegboard editor. **Bundles in the pegboard editor use the same rendering technique as the wires.**
5. **3D editor, placing a layout / waypoint** (keep the current placement design, with these changes):
   * the preview shows as the sphere it does now, but sized **1.25 x the diameter of the wire** (easy to see for placement);
   * the preview should **follow the curve** of the wire / bundle / cable as it is positioned (preview mode), if possible;
   * on the click that places it, the preview sphere is removed and only the waypoint is created;
   * the sphere can still be used to determine the **drag location**; the drag location is only active when the
     wire / cable / bundle is selected.
6. **Deleting a waypoint**: right click on a waypoint -> context menu -> option **"delete layout"** (today it only says
   "delete"; there is no visible indication of what the menu belongs to, so the label must say "delete layout").

## Rules that apply (MEMORY.md)

No unit tests; no fallback paths; no backwards compat shims (pre-release); no inline conditional expressions; every parameter
fully type hinted (Cython); new files are `git add`ed at once; do not launch the app; update the directory `MAP.md` files.

## Status

* 2026-11-08 built (not run in the app; the shared drawing was checked offscreen, pixel-identical to the saved per-piece image over 100 random wires, 8 arenas and a compaction; ordinary meshes identical to the committed shaders):
  1. switches, check boxes and the old drawing code removed; `objects/mixins/tube.py` (`TubeMixin`) draws the 3D and pegboard wire, cable and bundle;
  2. bundles (3D and board) drawn by the batch with rounded corners of one diameter; the board's wire and bundle get the curved corners too (they were plain cylinders);
  3. layouts not drawn; `objects/mixins/waypoint_handles.py`: drag handles while the owner is selected (3D and board), the same `Generic` drag for wire / bundle / cable;
  4. placement preview 1.25 x the diameter riding on the drawn path (3D only; the waypoint itself goes on the straight path), removed on the click;
  5. layout menu item renamed **Delete Layout** (3D).
* Later the same day: bare conductor ends are back (an entry of their own over a sub-range of the wire's rows); NO cable has layouts at its waypoints (user: a cable is drawn with the curved turns; the only layouts shown are the split markers where a split-out cable's conductors join the broken-out wires).
* Open / flagged: a cable's waypoints have no handle to drag; the board's preview does not ride the curve and has no menu; the debug passes are not drawn for wires any more.
* Floor outline of a selected wire / bundle / cable: the top-down outline of the drawn path (`gl/floor_outline.py`), in the floor-projection colour (the debug setting, default a light red), instead of one rectangle per section.
* The wire / bundle / cable menus (3D) have **Delete Layout** (grayed out without waypoints), removing the waypoint nearest the right click. The pegboard menus do not have it yet.
* The wire benchmark (GPU performance logging) is removed: `gl/wire_benchmark.py`, `Config.debug.rendering3d.wire_benchmark`, the Debug Settings check box and every hook in the canvas, the batch, the mixin and the 3D wire.
* Layouts have no geometry (3D and pegboard; the rows and data objects stay for the routing logic): the owner picks a waypoint's handle (sphere on the drawn path) and runs the drag; the placement preview keeps a sphere; the cable's split markers and the snap probes are still drawn. The schematic's layouts are untouched. Smooth normals across a bend are in the shader.
* The wire / bundle menus' **Add Handle** is now **Add Layout** (3D wire, bundle, cable; the board's wire and bundle too; the schematic's wire keeps its own). A cable has it as well (3D): the placement flow of a wire, no end snapping, and the click adds a point to the cable's route (`Cable.add_waypoint`) instead of making a layout.
* The ray tracer draws wires, cables and bundles from the viewport's own pieces (`ray_tracing/tube_mesh.py`, `TubeMixin.ray_trace_meshes`): rounded corners, twist, stripes, bare ends. `WireStripe` (the helix stripe object of the 3D and board wires) is removed: a wire's stripe is a material (`_stripe_material`). `shapes/helix.py` stays for the schematic wire; the project column `wire_stripe_max_length` is no longer written by the 3D / board wires.
