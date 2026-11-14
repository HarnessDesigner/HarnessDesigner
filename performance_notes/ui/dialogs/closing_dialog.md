# harness_designer/ui/dialogs/closing_dialog.py

ClosingDialog -- borderless, button-less progress dialog shown while the app shuts down (deliberately has no buttons at all, since there's nothing to confirm/cancel during shutdown).

Cold path (119 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
