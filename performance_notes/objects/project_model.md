# harness_designer/objects/project_model.py

Wrapper for the project's own loaded 3D model (as opposed to a catalog part) — set via "Add/Edit Project Model" (ui/dialogs/project_model_dialog.py). Note it has no position/scale/angle columns of its own today; objects_3d/project_model.py hardcodes the model at the origin (this file's DESIGN NOTES, "Empty-space right-click menus" entry).

Cold path (48 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
