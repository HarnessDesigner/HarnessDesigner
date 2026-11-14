# harness_designer/ui/scraper_inspector/background.py

BackgroundJob(QtCore.QObject) -- __init__(self, work: Callable[[], object], parent=None); runs an arbitrary callable off the GUI thread via threading, reporting the result (or a captured traceback) back through a Qt signal. Used by source_viewer.py so turning a selection into code doesn't block the UI thread.

Starts threads or workers at line 33 (`Thread`); work in them is off the UI thread, so the cost to check is the hand-off back to the UI thread (see `CallAfter` in `app.py`).

Status: static read of the code only. Nothing here has been profiled.
