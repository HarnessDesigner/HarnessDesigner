# harness_designer/ui/dialogs/properties_dialog.py

PropertiesDialog -- opens a selected object's property control modelessly (show(), not exec()) with a fresh instance of the same control class the object-editor dock uses, so both can display different objects at once. Must call tab_widget.set_obj(None) on close, per the dialog design convention described under dialog_base.py below.

Cold path (33 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
