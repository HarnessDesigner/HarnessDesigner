# harness_designer/ui/scraper_inspector/response_panel.py

ResponsePanel(QtWidgets.QWidget) -- shows one selected request's response as either a json_tree.JsonTree or plain source text (source_viewer.SourceViewer), plus request details and a "repeat request" action. Uses ui/widgets/wrap_label.py's WrapLabel for its Response header line, per that widget's "any label that can show a server/API message" rule (see ui/widgets/MAP.md).

Cold path (241 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
