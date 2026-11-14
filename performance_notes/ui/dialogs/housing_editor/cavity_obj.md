# harness_designer/ui/dialogs/housing_editor/cavity_obj.py

Cavity(ObjectBase) + Cavity3D -- this dialog's own cavity wrapper, paired with housing_obj.py.

Cold path (401 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
