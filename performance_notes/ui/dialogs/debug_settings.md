# harness_designer/ui/dialogs/debug_settings.py

DebugSettingsDialog (_ColourPickerCtrl helper) -- developer-facing debug toggles, developer-facing toggles for the faces / edges / normals / vertices passes and the other debug drawing options (the "Wire Benchmark" group and the GPU performance logging were removed 2026-11-08, together with the gpu_single_wires / pooled_wires / batched_wires check boxes).

Cold path (315 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
