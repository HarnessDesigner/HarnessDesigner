# harness_designer/ui/prop_ctrls/_array_dialog_base.py

## `_ArrayDialog.__init__` - builds one line-edit per item up front
The dialog creates one `QLineEdit` per value in `values` when it opens. The array sizes in this editor are small (a handful of values), so the cost is proportional to a small number of widgets. No change is needed.

## `_ArrayDialog` - focus handlers call the base class on every focus change
`_on_item_focus` and `_on_item_kill_focus` forward the event to `QLineEdit.focusInEvent` and `focusOutEvent` directly. This is a cheap call per focus change, not a cost to fix.
