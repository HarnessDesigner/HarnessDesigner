# harness_designer/scraping/runner.py

Runner/ScriptRun — a generated/edited script runs in a daemon thread of this same process with its own namespace and its own print.

Starts threads or workers at line 83 (`class ScriptRun(Thread)`); work in them is off the UI thread, so the cost to check is the hand-off back to the UI thread (see `CallAfter` in `app.py`).

Status: static read of the code only. Nothing here has been profiled.
