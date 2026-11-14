# harness_designer/objects/boot.py

One-file-per-part wrapper, same shape as housing.py — ObjectBase subclass fanning out to whichever of objects_3d/objects_schematic/objects_pegboard the part has a view in. Boot design (shape/geometry, whether/how it bends to follow the routed harness) lives in BOOT_DESIGN.md at the repo root — read it in full before touching boot code, and add new decisions there, not here.

Cold path (56 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
