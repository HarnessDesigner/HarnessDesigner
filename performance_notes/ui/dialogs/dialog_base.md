# harness_designer/ui/dialogs/dialog_base.py

BaseDialog(QDialog) -- the shared base every dialog in this directory (and its housing_editor//transition_editor/ subpackages) derives from, using CustomizeWindowHint plus a custom draggable Header widget (header.py) instead of the native OS title bar. Dialogs intentionally have no native close (X) button and no Escape-to-close behavior -- the only way to dismiss one is via the QDialogButtonBox buttons at the bottom.

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `BaseDialog.mouseMoveEvent` (line 139-156): no loops or allocations found.
- `BaseDialog.mousePressEvent` (line 159-172): no loops or allocations found.
- `BaseDialog.mouseReleaseEvent` (line 175-187): no loops or allocations found.
None of them allocates or loops in a way the AST pass flags, so they are cheap per call.

Status: static read of the code only. Nothing here has been profiled.
