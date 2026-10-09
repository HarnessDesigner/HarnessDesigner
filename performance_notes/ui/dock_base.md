# harness_designer/ui/dock_base.py

The dock wrapper is a thin layer over `QDockWidget`. `Show` and `Raise` each make one Qt call, and they run from the user's actions. Nothing in this file is on a hot path, so there is nothing to change.
