# harness_designer/ui/dialogs/about_dialog.py

AboutDialog -- app info, an update check against the GitHub releases API (_UpdateCheckWorker, a QThread), and a package-credits/license viewer (_PackageInfo) built from importlib.metadata over installed dist-info dirs, including Python itself.

Starts threads or workers at line 229 (`class _UpdateCheckWorker(QThread)`); work in them is off the UI thread, so the cost to check is the hand-off back to the UI thread (see `CallAfter` in `app.py`).
Nested loops (cost grows with the product of the sizes; check the sizes are small): `_version_tuple` (lines 214-226, depth 2).

Status: static read of the code only. Nothing here has been profiled.
