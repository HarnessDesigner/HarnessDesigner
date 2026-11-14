# harness_designer/ui/widgets/code_editor_ctrl.py

The Python editor used by the scraper tool (script editor and the generated-script pane): `QPlainTextEdit` plus line numbers and Pygments highlighting.

## Line 48-68 (`_PygmentsHighlighter.highlightBlock`) — re-lexes the whole document for every block
`highlightBlock` is called by Qt once per text block (line) that needs highlighting: every block when a document is loaded or reset, and the edited block plus any following blocks whose state changes after a keystroke. Each call runs `self._lexer.get_tokens(self.document().toPlainText())`, which converts the whole document to a string and lexes all of it, then walks the token stream from the start until it passes the block (`token_end <= block_start: continue`). So highlighting costs O(blocks x document size): loading a 1,000-line script runs 1,000 full lexes, and a 5,000-line script a few thousand. Typing a character re-lexes the whole document at least once and again for each following block Qt re-highlights.
Fix: lex once per document change and cache the result per block. A `contentsChange` handler (or the first `highlightBlock` after a change) builds a list of `(column, length, token_type)` spans per line from one `get_tokens` call, and `highlightBlock` then only does `setFormat` for its own line, which is exactly what `ui/scraper_inspector/source_viewer.py` `SpanHighlighter` already does with precomputed `_lines`. Memory: one span tuple per token (about 100 bytes), a few hundred KB for a 5,000-line script, freed with the document. Pygments is the slow part (tens of microseconds per token), so the saving is large: the cost drops from O(blocks x tokens) to O(tokens) per edit.

## Line 174-194 (`keyPressEvent`) — cheap
A few comparisons per key. The auto-indent helpers (`_insert_auto_indented_newline`, `_indent_selection`) touch the text cursor once. Fine.
