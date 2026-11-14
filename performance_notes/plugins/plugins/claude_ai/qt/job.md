# harness_designer/plugins/plugins/claude_ai/qt/job.py

ClaudeJob — one Claude call run on a background thread with results delivered back via Qt signals on the GUI thread; exposes cancel().

Starts threads or workers at line 63 (`Thread`); work in them is off the UI thread, so the cost to check is the hand-off back to the UI thread (see `CallAfter` in `app.py`).

Status: static read of the code only. Nothing here has been profiled.
