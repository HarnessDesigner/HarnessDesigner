## FILES

#### __init__.py

Re-exports the module as `_logviewer` only; no public symbols of its own.

#### logviewer.py

`LogViewer(_dock_base.DockBase)` -- the dock wrapper, `__init__(self, mainframe: '_mainframe.MainFrame')`. `LogViewerPanel(_viewer.ViewerPanel)` subclasses `viewer.py`'s generic panel to specialize it for the app's own rotating log files (via `..dock_base` and `...logger.log_handler.RotationEvent`).

#### viewer.py

`ViewerPanel` -- the generic log-tailing panel: reads a log file off the GUI thread (`threading`, `os`), using `pandas` to parse/filter rows, and reacts to `...logger.log_handler.RotationEvent` so it keeps following the current file across a log-rotation boundary rather than silently going stale. `logviewer.py`'s `LogViewerPanel` is this panel specialized for the app's own log output; the generic base is kept separate so a differently-sourced log (if one is ever added) could reuse it without inheriting app-specific wiring.
