# harness_designer/ui/dialogs/dimensions_dialog.py

DimensionsDialog -- prompts for a catalog part's length/width/height when the catalog leaves one or more at 0.0 (a 0.0 dimension collapses that axis in the placeholder VBO, making the object invisible); meant to be called from every start_add classmethod right after the user picks a part, before any project row is created.

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `_DimensionField.keyPressEvent` (line 83-98): no loops or allocations found.
None of them allocates or loops in a way the AST pass flags, so they are cheap per call.

Status: static read of the code only. Nothing here has been profiled.
