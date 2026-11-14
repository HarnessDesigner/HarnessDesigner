# harness_designer/ui/scraper_inspector/insertion.py

SnippetSink (ABC-like protocol: insert_snippet(self, snippet)) -- what a generated-code snippet is sent to -- and the module-level insert_snippet(editor: QtWidgets.QPlainTextEdit, snippet) function that actually performs the insert: merges the snippet's required imports into the target editor's existing import block and performs the whole insert (imports + body) as one undo step. snippet_pane.SnippetPane is the built-in sink (SnippetPane.insert_snippet); inspector.ScraperInspector.set_sink() can redirect snippets to an external sink (the script editor) instead of this pane.

Cold path (90 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
