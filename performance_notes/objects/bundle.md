# harness_designer/objects/bundle.py

Wrapper for bundles; 3D + peg-board only, no schematic view (harness_designer/handlers/MAP.md DESIGN NOTES "Bundles: design lives in BUNDLE_DESIGN.md"). Placement/cross-view reaction rules are in BUNDLE_PLACEMENT.md; the rest of the bundle design (create-from-wire, extend, shared-waypoint, 1-to-1 layout spec) is in BUNDLE_DESIGN.md — read both before touching bundle code and add new decisions there.

Cold path (122 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
