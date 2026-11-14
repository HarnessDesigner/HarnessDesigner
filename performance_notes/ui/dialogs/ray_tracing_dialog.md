# harness_designer/ui/dialogs/ray_tracing_dialog.py

RayTracingDialog(BaseDialog) -- ray tracing settings (an embedded RenderSettingsPanel) next to the image as it renders (_PreviewView, which scales to fit and coalesces repaints).

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `_PreviewView.paintEvent` (line 81-98): QColor x1, QPainter x1.
The ones that allocate Qt objects or run loops in a paint or move handler are the ones to look at first: Qt objects such as `QPixmap`, `QFont`, `QPen` and `QPainter` created per paint can usually be created once in `__init__` (a few hundred bytes each) and reused; a cache of rendered pixmaps trades memory (width x height x 4 bytes each) for speed and is worth it only for pixmaps that are expensive to produce.

Status: static read of the code only. Nothing here has been profiled.
