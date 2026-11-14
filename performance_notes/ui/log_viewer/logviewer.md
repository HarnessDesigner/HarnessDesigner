# harness_designer/ui/log_viewer/logviewer.py

LogViewer(_dock_base.DockBase) -- the dock wrapper, __init__(self, mainframe: '_mainframe.MainFrame'). LogViewerPanel(_viewer.ViewerPanel) subclasses viewer.py's generic panel to specialize it for the app's own rotating log files (via ..dock_base and ...logger.log_handler.RotationEvent).

Cold path (45 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
