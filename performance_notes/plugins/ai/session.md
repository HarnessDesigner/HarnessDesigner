# harness_designer/plugins/ai/session.py

Session — one open-ended activity (named from its first message — mechanism not yet built); holds history; runs Jobs one at a time on its own plain threading.Thread (never QThread).

Starts threads or workers at line 88 (`Thread`); work in them is off the UI thread, so the cost to check is the hand-off back to the UI thread (see `CallAfter` in `app.py`).

Status: static read of the code only. Nothing here has been profiled.
