# harness_designer/ui/widgets/wrap_label.py

WrapLabel(QLabel) -- caps a label's sizeHint/minimumSizeHint widths, shows plain text only, and puts any text the caller can't control (a page address, a server/API message, a file path, script output) into the tooltip instead of letting it set layout size. Exists because of a real production bug (2026-10-17): a 1,155-character, no-spaces Google search URL went into the scraper inspector's word-wrapped message label.

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `WrapLabel.sizeHint` (line 44-49): no loops or allocations found.
None of them allocates or loops in a way the AST pass flags, so they are cheap per call.

Status: static read of the code only. Nothing here has been profiled.
