# harness_designer/ui/widgets/auto_complete.py

## `_refresh_completer` - rebuilds the completer model on each choice change
`SetAutoCompleteChoices` calls `completer.setModel(QStringListModel(choices))`, which creates a new model from the full choice list. The choice list is set when the control is configured, not on each keystroke, so the cost is small. Keystrokes go through the completer's own filter model, which does not rebuild anything.
