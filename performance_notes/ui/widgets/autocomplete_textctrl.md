# harness_designer/ui/widgets/autocomplete_textctrl.py

## `AutoCompleteTextEdit.keyPressEvent` - runs for every key in the multi-line control
Each key calls `_is_commit_enter` (a key check first, so only Enter reaches `toPlainText()`, which is O(text length) and happens once per Enter), then Qt's own handling, then `_line_prefix` (a one-line selection, constant cost) and, for a printable key, `QCompleter.complete`, which updates the popup from the completer's filter model. Nothing rebuilds the completer model per keystroke.

## `_rebuild_completer` - a new `QStringListModel` per choice change
`Set`, `SetItems`, `Append`, `Insert`, `Delete` and `Clear` each build a new model from the whole choice list. `Append` of a list builds one model, not one per item. The multi-line property does not learn its committed text as a choice, so the list does not grow while typing; the single-line property adds one choice per new committed value.

## `_leave_single_newline` - once per commit
Removes the extra trailing newlines with one cursor edit. It is linear in the number of trailing newlines and runs only on the committing Enter.
