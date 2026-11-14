# harness_designer/ui/scraper_inspector/source_viewer.py

A highlighted read-only view of a page's source. Highlighting and selection-to-code run off the UI thread through `background.BackgroundJob`.

## Line 61-67 (`SpanHighlighter.highlightBlock`) — precomputed per line, the right shape
Looks up the spans for its own block (`self._lines[number]`) and calls `setFormat` for each; no lexing per call. Cost is O(spans in the line). This is the pattern `ui/widgets/code_editor_ctrl.py`'s Pygments highlighter should follow.

## Memory
`_lines` holds a list of spans per line for the whole page; a large HTML page (several MB of source) produces hundreds of thousands of spans, tens of MB in Python tuples. Page source is only held for the page being inspected, so it is released when the page changes. If large pages are routine, store spans in a NumPy array per line or merge adjacent spans of the same style.
