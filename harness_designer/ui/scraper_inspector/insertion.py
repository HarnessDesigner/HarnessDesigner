# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Putting a snippet into a script editor.

:class:`SnippetSink` is what the inspector sends snippets to: the little
"generated script" pane under the inspector, or the real script editor once
that dock is open. Both use :func:`insert_snippet`, so a snippet lands the
same way in either.
"""

from PySide6 import QtGui
from PySide6 import QtWidgets

from ...scraping import script_builder as _script_builder
from ...scraping import snippets as _snippets
from ... import check_types as _check_types


class SnippetSink:
    """Anything snippets can be inserted into."""

    @_check_types.do
    def taken_names(self) -> set[str]:
        """Names the script already uses (so new code does not reuse them)."""
        raise NotImplementedError

    @_check_types.do
    def insert_snippet(self, snippet: _snippets.Snippet) -> None:
        """Add *snippet* (and the imports it needs) to the script."""
        raise NotImplementedError


@_check_types.do
def insert_snippet(editor: QtWidgets.QPlainTextEdit, snippet: _snippets.Snippet) -> None:
    """Insert *snippet* on the line after the cursor's, add any missing
    imports at the top, and leave the cursor at the end of the new code.

    It is one undo step.
    """
    document = editor.document()
    before = editor.toPlainText()
    block = _script_builder.snippet_block(snippet)

    edit = QtGui.QTextCursor(document)
    edit.beginEditBlock()

    target = QtGui.QTextCursor(editor.textCursor())
    target.movePosition(QtGui.QTextCursor.MoveOperation.EndOfBlock)

    if not before.strip():
        separator = ''
    elif target.block().text().strip():
        separator = '\n\n'
    else:
        separator = '\n'

    target.insertText(separator + block)
    end_position = target.position()

    imports = _script_builder.import_text(document.toPlainText(), snippet.imports)
    if imports:
        end_position += _insert_imports(document, imports)

    edit.endEditBlock()

    cursor = editor.textCursor()
    cursor.setPosition(end_position)
    editor.setTextCursor(cursor)
    editor.ensureCursorVisible()


@_check_types.do
def _insert_imports(document: QtGui.QTextDocument, imports: str) -> int:
    """Insert *imports* where they belong; returns how many characters
    were added."""
    position = _script_builder.import_position(document.toPlainText())
    cursor = QtGui.QTextCursor(document)
    block = document.findBlockByNumber(position)

    if block.isValid():
        cursor.setPosition(block.position())
        text = imports
    else:
        # The script ends right after its last import line.
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        text = '\n' + imports.rstrip('\n')

    cursor.insertText(text)
    return len(text)
