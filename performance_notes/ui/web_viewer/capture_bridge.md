# harness_designer/ui/web_viewer/capture_bridge.py

CaptureBridge(QtCore.QObject) -- the QWebChannel object the injected page-side hook (...scraping.capture_hook) calls into from JS, feeding captured network/DOM data back into ...scraping.capture_model on the Python side.

Cold path (46 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
